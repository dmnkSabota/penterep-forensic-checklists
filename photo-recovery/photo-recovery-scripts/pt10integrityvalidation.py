#!/usr/bin/env python3
"""
    Copyright (c) 2026 Bc. Dominik Sabota, VUT FIT Brno

    ptintegrityvalidation - Forensic file integrity validation

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License.
    See <https://www.gnu.org/licenses/> for details.
"""

# LAST CHANGES:
#   - FIXED: validates files IN-PLACE (no third full disk copy created).
#   - IMAGE_EXTENSIONS replaced with import from _constants.
#   - Removed _custom_sigint_handler + signal.signal(): handled in base.
#   - Replaced inline add_properties({5 common fields}) with _init_properties().
#   - Changed --json boolean flag to --json-out <file> for consistency.

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ._version import __version__
from ._constants import IMAGE_EXTENSIONS
from .ptforensictoolbase import ForensicToolBase
from ptlibs import ptjsonlib, ptprinthelper
from ptlibs.ptprinthelper import ptprint

SCRIPTNAME         = "ptintegrityvalidation"
DEFAULT_OUTPUT_DIR = "/var/forensics/images"
VALIDATE_TIMEOUT   = 30

CORRUPTION_TYPES: Dict[str, str] = {
    "missing_footer":   "Missing end marker (EOI/EOF)",
    "invalid_header":   "Invalid or corrupt file header",
    "corrupt_segments": "Damaged internal segments",
    "truncated":        "File appears truncated",
    "corrupt_data":     "Image data region is damaged",
    "unknown":          "Unclassified corruption",
}


class PtIntegrityValidation(ForensicToolBase):
    """
    Validates integrity of recovered image files using a three-stage approach.
    Files are validated IN-PLACE – no copies are created.
    """

    def __init__(self, args: argparse.Namespace) -> None:
        self.ptjsonlib  = ptjsonlib.PtJsonLib()
        self.args       = args
        self.case_id    = args.case_id.strip()
        self.analyst    = getattr(args, "analyst", "Analyst")
        self.dry_run    = args.dry_run
        self.output_dir = Path(args.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.consolidated_dir = self.output_dir / f"{self.case_id}_consolidated"

        self._s: Dict[str, Any] = {
            "total": 0, "valid": 0, "repairable": 0, "corrupted": 0,
            "by_format": {}, "corruption_types": {},
        }
        self._results: List[Dict] = []

        self._init_properties(__version__)

    # ------------------------------------------------------------------
    # Format-specific detailed validation (Stage 2)
    # ------------------------------------------------------------------

    def _validate_jpeg_detail(self, path: Path) -> Tuple[str, str]:
        r = self._run_command(["jpeginfo", "-c", str(path)], timeout=VALIDATE_TIMEOUT)

        if r["success"]:
            out = r["stdout"].lower()
            if "ok" in out and "error" not in out:
                return "valid", "none"
            if "unexpected end" in out or "premature end" in out:
                return "repairable", "truncated"
            if "missing eoi" in out or "extraneous bytes" in out:
                return "repairable", "missing_footer"
            if "invalid marker" in out or "corrupt" in out:
                return "repairable", "corrupt_segments"

        try:
            from PIL import Image
            Image.MAX_IMAGE_PIXELS = None
            img = Image.open(str(path))
            img.verify()
            return "valid", "none"
        except ImportError:
            pass
        except Exception as exc:
            exc_s = str(exc).lower()
            if "truncat" in exc_s:
                return "repairable", "truncated"
            if "header" in exc_s or "magic" in exc_s:
                return "repairable", "invalid_header"
            return "repairable", "corrupt_data"

        try:
            from PIL import Image, ImageFile
            ImageFile.LOAD_TRUNCATED_IMAGES = True
            img = Image.open(str(path))
            img.load()
            return "repairable", "truncated"
        except Exception:
            pass

        return "corrupted", "unknown"

    def _validate_png_detail(self, path: Path) -> Tuple[str, str]:
        r = self._run_command(["pngcheck", "-v", str(path)],
                              timeout=VALIDATE_TIMEOUT)
        if r["success"]:
            out = r["stdout"].lower()
            if "ok" in out and "error" not in out:
                return "valid", "none"
        if r["stderr"]:
            err = r["stderr"].lower()
            if "crc error" in err or "invalid chunk" in err:
                return "repairable", "corrupt_segments"
            if "premature end" in err or "truncat" in err:
                return "repairable", "truncated"
            return "corrupted", "unknown"
        return "corrupted", "unknown"

    def _validate_tiff_detail(self, path: Path) -> Tuple[str, str]:
        r = self._run_command(["tiffinfo", str(path)], timeout=VALIDATE_TIMEOUT)
        if r["success"]:
            return "valid", "none"
        err = (r["stderr"] + r["stdout"]).lower()
        if "bad value" in err or "corrupt" in err:
            return "repairable", "corrupt_segments"
        if "unrecognized" in err or "not a tiff" in err:
            return "corrupted", "invalid_header"
        return "corrupted", "unknown"

    def _validate_generic_detail(self, path: Path) -> Tuple[str, str]:
        try:
            from PIL import Image
            img = Image.open(str(path))
            img.verify()
            return "valid", "none"
        except ImportError:
            pass
        except Exception:
            return "repairable", "corrupt_data"
        return "corrupted", "unknown"

    # ------------------------------------------------------------------
    # Full three-stage validation
    # ------------------------------------------------------------------

    def _validate_full(self, path: Path) -> Dict:
        ext = path.suffix.lower()

        base_status, vinfo = self._validate_image_file(path)

        if base_status == "invalid":
            return {
                "path":           str(path),
                "filename":       path.name,
                "status":         "corrupted",
                "corruptionType": "invalid_header",
                "sizeBytes":      vinfo.get("size", 0),
                "imageFormat":    None,
                "dimensions":     None,
            }

        if base_status == "valid":
            if ext in (".jpg", ".jpeg"):
                det_status, ctype = self._validate_jpeg_detail(path)
            elif ext == ".png":
                det_status, ctype = self._validate_png_detail(path)
            elif ext in (".tif", ".tiff"):
                det_status, ctype = self._validate_tiff_detail(path)
            else:
                det_status, ctype = self._validate_generic_detail(path)
        else:
            det_status, ctype = "repairable", "corrupt_data"

        if det_status == "valid":
            final_status = "valid"
            ctype        = "none"
        elif det_status == "repairable":
            final_status = "repairable"
        else:
            final_status = "corrupted"
            if ctype == "none":
                ctype = "unknown"

        return {
            "path":           str(path),
            "filename":       path.name,
            "status":         final_status,
            "corruptionType": ctype,
            "sizeBytes":      vinfo.get("size", 0),
            "imageFormat":    vinfo.get("imageFormat"),
            "dimensions":     vinfo.get("dimensions"),
        }

    # ------------------------------------------------------------------
    # Phases
    # ------------------------------------------------------------------

    def check_tools(self) -> bool:
        ptprint("\n[1/2] Checking validation tools", "TITLE", condition=self._out())
        tools = {
            "identify":  "ImageMagick (Stage 1 – required)",
            "file":      "file type detection (Stage 1 – required)",
            "jpeginfo":  "JPEG validation (Stage 2 – optional)",
            "pngcheck":  "PNG validation  (Stage 2 – optional)",
            "tiffinfo":  "TIFF validation (Stage 2 – optional)",
        }
        missing_required = []
        for t, desc in tools.items():
            found = self._check_command(t)
            ptprint(f"  [{'OK' if found else 'WARN'}] {t}: {desc}",
                    "OK" if found else "WARNING", condition=self._out())
            if not found and "required" in desc:
                missing_required.append(t)

        if missing_required:
            ptprint(f"  Missing required: {', '.join(missing_required)}",
                    "ERROR", condition=self._out())
            self._add_node("toolsCheck", False, missingRequired=missing_required)
            return False

        ptprint("  Optional tools (jpeginfo/pngcheck/tiffinfo) fall back to "
                "PIL/Pillow if unavailable.", "INFO", condition=self._out())
        self._add_node("toolsCheck", True, tools=list(tools))
        return True

    def validate_all(self) -> bool:
        ptprint("\n[2/2] Validating files (in-place – no copies created)",
                "TITLE", condition=self._out())

        if not self.consolidated_dir.exists() and not self.dry_run:
            return self._fail("integrityValidation",
                              f"{self.consolidated_dir.name} not found – "
                              "run Recovery Consolidation first.")

        candidates = []
        if not self.dry_run:
            candidates = [
                f for f in self.consolidated_dir.rglob("*")
                if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
            ]

        ptprint(f"  Files to validate: {len(candidates)}",
                "INFO", condition=self._out())

        if not candidates:
            if not self.dry_run:
                ptprint("  No image files found in consolidated directory.",
                        "WARNING", condition=self._out())
            self._add_node("integrityValidation", True,
                           dryRun=self.dry_run, totalFiles=0)
            return True

        for idx, fp in enumerate(candidates, 1):
            if idx % 100 == 0 or idx == len(candidates):
                pct = idx * 100 // len(candidates)
                ptprint(f"  {idx}/{len(candidates)} ({pct}%)",
                        "INFO", condition=self._out())

            result = self._validate_full(fp)
            self._results.append(result)

            status = result["status"]
            ext    = fp.suffix.lower()
            fmt    = ext.lstrip(".")

            self._s["total"] += 1
            self._s[status]  = self._s.get(status, 0) + 1
            self._s["by_format"][fmt] = self._s["by_format"].get(fmt, 0) + 1

            if status in ("repairable", "corrupted"):
                ctype = result["corruptionType"]
                self._s["corruption_types"][ctype] = (
                    self._s["corruption_types"].get(ctype, 0) + 1)

        s = self._s
        ptprint(f"\n  Validated: {s['total']}  |  "
                f"Valid: {s.get('valid', 0)}  |  "
                f"Repairable: {s.get('repairable', 0)}  |  "
                f"Corrupted: {s.get('corrupted', 0)}",
                "OK", condition=self._out())
        if s["corruption_types"]:
            ptprint("  Corruption types:", "INFO", condition=self._out())
            for ctype, count in sorted(s["corruption_types"].items()):
                desc = CORRUPTION_TYPES.get(ctype, ctype)
                ptprint(f"    {count:4d}× {desc}", "INFO", condition=self._out())

        self._add_node("integrityValidation", True,
                       totalFiles=s["total"],
                       validFiles=s.get("valid", 0),
                       repairableFiles=s.get("repairable", 0),
                       corruptedFiles=s.get("corrupted", 0),
                       corruptionTypes=s["corruption_types"],
                       byFormat=s["by_format"])
        return True

    # ------------------------------------------------------------------
    # Run and save
    # ------------------------------------------------------------------

    def run(self) -> None:
        ptprint("=" * 70, "TITLE", condition=self._out())
        ptprint(f"INTEGRITY VALIDATION v{__version__}  |  "
                f"Case: {self.case_id}", "TITLE", condition=self._out())
        if self.dry_run:
            ptprint("MODE: DRY-RUN", "WARNING", condition=self._out())
        ptprint("=" * 70, "TITLE", condition=self._out())

        if not self.check_tools():
            self.ptjsonlib.set_status("finished"); return
        self.validate_all()

        s = self._s
        self.ptjsonlib.add_properties({
            "compliance":      ["NIST SP 800-86", "ISO/IEC 27037:2012"],
            "method":          "in_place_validation",
            "totalFiles":      s["total"],
            "validFiles":      s.get("valid", 0),
            "repairableFiles": s.get("repairable", 0),
            "corruptedFiles":  s.get("corrupted", 0),
            "corruptionTypes": s["corruption_types"],
            "byFormat":        s["by_format"],
            "consolidatedDir": str(self.consolidated_dir),
        })
        self.ptjsonlib.add_node(self.ptjsonlib.create_node_object(
            "chainOfCustodyEntry",
            properties={
                "action":    (f"Integrity validation complete – "
                              f"{s.get('valid', 0)} valid, "
                              f"{s.get('repairable', 0)} repairable, "
                              f"{s.get('corrupted', 0)} corrupted"),
                "result":    "SUCCESS",
                "analyst":   self.analyst,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "note":      "Files validated in-place; no copies created",
            }
        ))

        ptprint("\n" + "=" * 70, "TITLE", condition=self._out())
        ptprint("VALIDATION COMPLETE", "OK", condition=self._out())
        ptprint(f"Total: {s['total']}  |  Valid: {s.get('valid', 0)}  |  "
                f"Repairable: {s.get('repairable', 0)}  |  "
                f"Corrupted: {s.get('corrupted', 0)}",
                "INFO", condition=self._out())
        ptprint("NOTE: Files remain in consolidated dir – no copies created.",
                "INFO", condition=self._out())
        ptprint("Next: Repair Decision", "INFO", condition=self._out())
        ptprint("=" * 70, "TITLE", condition=self._out())
        self.ptjsonlib.set_status("finished")

    def save_report(self) -> Optional[str]:
        json_file = (Path(self.args.json_out) if self.args.json_out
                     else self.output_dir /
                          f"{self.case_id}_integrity_validation.json")
        report = {
            "result":      json.loads(self.ptjsonlib.get_result_json()),
            "fileResults": self._results,
        }
        json_file.write_text(
            json.dumps(report, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8")
        if self.args.json_out:
            ptprint(self.ptjsonlib.get_result_json(), "", True)
        ptprint(f"JSON report: {json_file.name}", "OK", condition=self._out())
        ptprint(f"  Contains path + status + corruptionType for "
                f"{len(self._results)} files.",
                "INFO", condition=self._out())
        return str(json_file)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def get_help() -> List[Dict]:
    return [
        {"description": [
            "Forensic file integrity validation – ptlibs compliant",
            "Three-stage validation: file(1) + ImageMagick + format-specific tools",
            "Validates files IN-PLACE (no copies created) – no extra disk space needed",
            "Compliant with NIST SP 800-86 and ISO/IEC 27037:2012",
        ]},
        {"usage": ["ptintegrityvalidation <case-id> [options]"]},
        {"usage_example": [
            "ptintegrityvalidation PHOTORECOVERY-2025-01-26-001",
            "ptintegrityvalidation CASE-001 --dry-run",
            "ptintegrityvalidation CASE-001 --json-out step10.json",
        ]},
        {"options": [
            ["case-id",            "",      "Forensic case identifier – REQUIRED"],
            ["-o", "--output-dir", "<dir>", f"Output directory (default: {DEFAULT_OUTPUT_DIR})"],
            ["-a", "--analyst",    "<n>",   "Analyst name"],
            ["-j", "--json-out",   "<f>",   "Save JSON report to file"],
            ["-q", "--quiet",      "",      "Suppress terminal output"],
            ["--dry-run",          "",      "Simulate without reading files"],
            ["-h", "--help",       "",      "Show help"],
            ["--version",          "",      "Show version"],
        ]},
        {"notes": [
            "Stage 1 (required): file(1) + ImageMagick identify",
            "Stage 2 (optional): jpeginfo | pngcheck | tiffinfo | PIL fallback",
            "Output: {case_id}_integrity_validation.json with per-file classification",
            "Files are NOT moved or copied – referenced by path only",
            "Install optional tools: sudo apt install jpeginfo pngcheck libtiff-tools",
        ]},
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("case_id")
    parser.add_argument("-o", "--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("-a", "--analyst",    default="Analyst")
    parser.add_argument("-j", "--json-out",   default=None)
    parser.add_argument("-q", "--quiet",      action="store_true")
    parser.add_argument("--dry-run",          action="store_true")
    parser.add_argument("--version", action="version",
                        version=f"{SCRIPTNAME} {__version__}")

    if len(sys.argv) == 1 or {"-h", "--help"} & set(sys.argv):
        ptprinthelper.help_print(get_help(), SCRIPTNAME, __version__)
        sys.exit(0)

    args      = parser.parse_args()
    args.json = bool(args.json_out)
    if args.json:
        args.quiet = True
    ptprinthelper.print_banner(SCRIPTNAME, __version__, args.json)
    return args


def main() -> int:
    try:
        args = parse_args()
        tool = PtIntegrityValidation(args)
        tool.run()
        tool.save_report()
        props = json.loads(tool.ptjsonlib.get_result_json())["result"]["properties"]
        return 0 if props.get("totalFiles", 0) > 0 else 1
    except KeyboardInterrupt:
        ptprint("Interrupted by user.", "WARNING", condition=True)
        return 130
    except Exception as exc:
        ptprint(f"ERROR: {exc}", "ERROR", condition=True)
        return 99


if __name__ == "__main__":
    sys.exit(main())