#!/usr/bin/env python3
"""
    Copyright (c) 2026 Bc. Dominik Sabota, VUT FIT Brno

    ptphotorepair - Forensic JPEG/PNG photo repair tool

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License.
    See <https://www.gnu.org/licenses/> for details.
"""

# LAST CHANGES:
#   - Fixed repair_all_files(): duplicate line
#       self._s[method] = self._s["by_method"].get(method, 0) + 1
#     wrote to the wrong key in self._s (method name as top-level key instead
#     of inside by_method). The line is now removed; only the correct
#       self._s["by_method"][method] = ...
#     remains.
#   - Removed _custom_sigint_handler + signal.signal(): handled in base.
#   - Replaced inline add_properties({5 common fields}) with
#     self._init_properties(__version__).
#   - Added repair_png_resave() for PNG files: PIL open + verify + save.
#   - Updated repair_all_files() with extension-based dispatch so PNG files
#     are sent to repair_png_resave() instead of JPEG repair functions.
#   - Added explicit note in docstring: byte-level repair is JPEG-only.
#     TIFF repair is not implemented; TIFF files are noted as unsupported.
#
# SCOPE OF REPAIR (documented limitation for thesis):
#   JPEG: byte-level repair (missing_footer, invalid_header, corrupt_segments,
#         truncated) – most reliable, most common format in photo recovery.
#   PNG:  PIL resave – handles minor chunk damage; no byte-level repair.
#   TIFF: not supported – files classified as REPAIRABLE/TIFF will be
#         noted as repair_failed in the output.
#   Other formats: not supported.

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ._version import __version__
from .ptforensictoolbase import ForensicToolBase
from ptlibs import ptjsonlib, ptprinthelper
from ptlibs.ptprinthelper import ptprint

SCRIPTNAME         = "ptphotorepair"
DEFAULT_OUTPUT_DIR = "/var/forensics/images"

# JPEG structural constants
JPEG_SOI = b"\xff\xd8"
JPEG_EOI = b"\xff\xd9"
JPEG_APP0 = b"\xff\xe0"
JPEG_APP1 = b"\xff\xe1"
JPEG_SOS  = b"\xff\xda"
JPEG_DQT  = b"\xff\xdb"
JPEG_SOF  = b"\xff\xc0"

try:
    from PIL import Image, ImageFile
    ImageFile.LOAD_TRUNCATED_IMAGES = True
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

_STRATEGY_MAP: Dict[str, str] = {
    "missing_footer":   "repair_missing_footer",
    "invalid_header":   "repair_invalid_header",
    "corrupt_segments": "repair_invalid_segments",
    "corrupt_segment":  "repair_invalid_segments",
    "invalid_segment":  "repair_invalid_segments",
    "corrupt_data":     "repair_truncated_file",
    "truncated":        "repair_truncated_file",
    "unknown":          "repair_invalid_header",
}


class PtPhotoRepair(ForensicToolBase):
    """
    Attempts automated repair of corrupted image files.

    Supported formats:
      JPEG – byte-level repair: missing_footer, invalid_header,
             corrupt_segments, truncated, corrupt_data.
      PNG  – PIL resave: handles minor chunk-level damage.
      TIFF – NOT supported; files will be marked as repair_failed.

    Repair is performed on copies in the repaired/ subdirectory.
    Originals in the consolidated directory are never modified.
    """

    def __init__(self, args: argparse.Namespace) -> None:
        self.ptjsonlib  = ptjsonlib.PtJsonLib()
        self.args       = args
        self.case_id    = args.case_id.strip()
        self.analyst    = getattr(args, "analyst", "Analyst")
        self.dry_run    = args.dry_run
        self.output_dir = Path(args.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.repaired_dir = self.output_dir / f"{self.case_id}_repaired"
        self.failed_dir   = self.output_dir / f"{self.case_id}_repair_failed"

        self._s: Dict = {
            "total": 0, "repaired": 0, "failed": 0, "skipped": 0,
            "by_method": {},
        }
        self._repair_results: List[Dict] = []

        self._init_properties(__version__)

    # ------------------------------------------------------------------
    # JPEG byte-level repair methods
    # ------------------------------------------------------------------

    def repair_missing_footer(self, path: Path) -> Tuple[bool, str]:
        """Append JPEG EOI marker if missing."""
        if self.dry_run:
            return True, "[DRY-RUN] append EOI simulated"
        try:
            data = path.read_bytes()
            if data.endswith(JPEG_EOI):
                return True, "EOI already present"
            if not data.startswith(JPEG_SOI):
                return False, "Not a valid JPEG (missing SOI)"
            path.write_bytes(data + JPEG_EOI)
            return True, f"Appended EOI to {len(data)} byte file"
        except Exception as exc:
            return False, str(exc)

    def repair_invalid_header(self, path: Path) -> Tuple[bool, str]:
        """
        Reconstruct JPEG header. Strategy:
          1. Find SOS or DQT marker in the file.
          2. Prepend a minimal valid SOI + APP0 header.
          3. Ensure EOI is present at the end.
        """
        if self.dry_run:
            return True, "[DRY-RUN] header reconstruction simulated"
        try:
            data = path.read_bytes()
            sos_pos = data.find(JPEG_SOS)
            if sos_pos == -1:
                dqt_pos = data.find(JPEG_DQT)
                if dqt_pos == -1:
                    return False, "No SOS or DQT marker found – unrecoverable"
                image_data = data[dqt_pos:]
            else:
                image_data = data[sos_pos:]

            app0 = (b"\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00")
            rebuilt = JPEG_SOI + app0 + image_data
            if not rebuilt.endswith(JPEG_EOI):
                rebuilt += JPEG_EOI

            path.write_bytes(rebuilt)

            if PIL_AVAILABLE:
                try:
                    img = Image.open(str(path))
                    img.load()
                    w, h = img.size
                    return True, f"Header rebuilt: {w}×{h} px"
                except Exception as exc:
                    return False, f"Header rebuilt but PIL verify failed: {exc}"

            return True, f"Header rebuilt ({len(rebuilt)} bytes)"
        except Exception as exc:
            return False, str(exc)

    def repair_invalid_segments(self, path: Path) -> Tuple[bool, str]:
        """
        Strip unknown or damaged segments, keeping recognised marker types.
        """
        if self.dry_run:
            return True, "[DRY-RUN] segment stripping simulated"
        try:
            data = path.read_bytes()
            if not data.startswith(JPEG_SOI):
                return False, "Not a valid JPEG (missing SOI)"

            kept_segments: List[bytes] = [JPEG_SOI]
            pos = 2

            while pos < len(data) - 1:
                if data[pos] != 0xFF:
                    pos += 1
                    continue
                marker = data[pos:pos + 2]
                if len(marker) < 2:
                    break
                if marker == JPEG_SOS:
                    kept_segments.append(data[pos:])
                    break
                if marker == JPEG_EOI:
                    kept_segments.append(JPEG_EOI)
                    break
                if pos + 4 <= len(data):
                    seg_len = int.from_bytes(data[pos + 2:pos + 4], "big")
                    if 2 <= seg_len <= len(data) - pos - 2:
                        seg = data[pos:pos + 2 + seg_len]
                        if 0xFF <= data[pos + 1] <= 0xFE:
                            kept_segments.append(seg)
                        pos += 2 + seg_len
                        continue
                pos += 2

            rebuilt = b"".join(kept_segments)
            if not rebuilt.endswith(JPEG_EOI):
                rebuilt += JPEG_EOI
            path.write_bytes(rebuilt)

            if PIL_AVAILABLE:
                try:
                    img = Image.open(str(path))
                    img.load()
                    w, h = img.size
                    return True, f"Segments stripped: {w}×{h} px"
                except Exception as exc:
                    return False, f"Stripped but PIL verify failed: {exc}"

            return True, f"Segments stripped ({len(rebuilt)} bytes)"
        except Exception as exc:
            return False, str(exc)

    def repair_truncated_file(self, path: Path) -> Tuple[bool, str]:
        """
        Attempt to recover a truncated JPEG using PIL LOAD_TRUNCATED_IMAGES
        mode. If PIL manages to decode the partial data, resave the result.
        """
        if self.dry_run:
            return True, "[DRY-RUN] truncated repair simulated"
        if not PIL_AVAILABLE:
            return self.repair_missing_footer(path)
        tmp = path.with_name(path.stem + "_trunc_tmp.jpg")
        try:
            img = Image.open(str(path))
            img.load()
            w, h = img.size
            if w == 0 or h == 0:
                return False, "Zero dimensions after truncated load"
            img.save(tmp, "JPEG", quality=95)
            shutil.move(str(tmp), str(path))
            return True, f"Truncated JPEG recovered: {w}×{h} px"
        except Exception as exc:
            if tmp.exists():
                tmp.unlink(missing_ok=True)
            return False, str(exc)

    # ------------------------------------------------------------------
    # PNG repair method
    # ------------------------------------------------------------------

    def repair_png_resave(self, path: Path) -> Tuple[bool, str]:
        """
        Attempt PIL resave for PNG files with minor corruption.

        PIL/Pillow can recover PNGs where trailing chunks are damaged
        (e.g., CRC errors in IEND or non-critical ancillary chunks) because
        it reads only what it needs to reconstruct the image data.

        Limitation: this does not repair damaged IDAT chunks or a corrupt
        header; those cases result in a PIL exception and return False.
        """
        if not PIL_AVAILABLE:
            return False, "PIL/Pillow not available (pip install pillow)"
        if self.dry_run:
            return True, "[DRY-RUN] PNG resave simulated"
        tmp = path.with_name(path.stem + "_png_tmp.png")
        try:
            img = Image.open(str(path))
            img.load()
            w, h = img.size
            if w == 0 or h == 0:
                return False, "Zero dimensions"
            img.save(tmp, "PNG", optimize=True)
            shutil.move(str(tmp), str(path))
            return True, f"PNG resave: {w}×{h} px"
        except Exception as exc:
            if tmp.exists():
                tmp.unlink(missing_ok=True)
            return False, str(exc)

    # ------------------------------------------------------------------
    # Main dispatch
    # ------------------------------------------------------------------

    def repair_file(self, src_path: Path,
                    corruption_type: str) -> Tuple[bool, str, str]:
        """
        Copy file to repaired_dir and attempt repair in-place there.
        Returns (success, method_used, message).
        """
        ext = src_path.suffix.lower()

        if ext in (".tif", ".tiff"):
            return (False, "not_supported",
                    "TIFF repair not implemented – "
                    "mark as MANUAL_REVIEW in ptrepairdecision")

        if ext not in (".jpg", ".jpeg", ".png"):
            return (False, "not_supported",
                    f"Format not supported for automated repair: {ext}")

        if ext == ".png":
            method_name = "repair_png_resave"
        else:
            method_name = _STRATEGY_MAP.get(corruption_type, "repair_invalid_header")

        if not self.dry_run:
            dest = self.repaired_dir / src_path.name
            if dest.exists():
                dest = self.repaired_dir / f"{src_path.stem}_{src_path.stat().st_size}{ext}"
            shutil.copy2(str(src_path), str(dest))
        else:
            dest = self.repaired_dir / src_path.name

        method = getattr(self, method_name)
        success, msg = method(dest)

        if not success and not self.dry_run and dest.exists():
            dest.unlink(missing_ok=True)

        return success, method_name, msg

    def repair_all_files(self) -> bool:
        ptprint("\n[1/1] Repairing files", "TITLE", condition=self._out())

        f = (Path(self.args.decisions_file)
             if getattr(self.args, "decisions_file", None)
             else self.output_dir / f"{self.case_id}_repair_decisions.json")

        if not f.exists():
            return self._fail("photoRepair",
                              f"{f.name} not found – run Repair Decision first.")
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception as exc:
            return self._fail("photoRepair",
                              f"Cannot read decisions file: {exc}")

        decisions = data.get("decisions", [])
        to_repair = [d for d in decisions if d.get("decision") == "ATTEMPT_REPAIR"]
        ptprint(f"  Files to repair: {len(to_repair)} / {len(decisions)} total",
                "INFO", condition=self._out())

        if not to_repair:
            ptprint("  Nothing to repair.", "OK", condition=self._out())
            self._add_node("photoRepair", True, filesRepaired=0, filesFailed=0)
            return True

        if not self.dry_run:
            self.repaired_dir.mkdir(parents=True, exist_ok=True)
            self.failed_dir.mkdir(parents=True, exist_ok=True)

        for idx, decision in enumerate(to_repair, 1):
            path_s = decision.get("path")
            ctype  = decision.get("corruptionType", "unknown")
            src    = Path(path_s) if path_s else None

            if not src or (not src.exists() and not self.dry_run):
                self._s["skipped"] += 1
                self._repair_results.append({
                    "filename": decision.get("filename"), "success": False,
                    "method": "skipped", "message": "File not found at recorded path",
                })
                continue

            self._s["total"] += 1
            ptprint(f"  [{idx}/{len(to_repair)}] {src.name} ({ctype})",
                    "INFO", condition=self._out())

            success, method, msg = self.repair_file(src, ctype)

            # FIX: removed duplicate line `self._s[method] = ...` which wrote
            # to the wrong top-level key in self._s. Only by_method is updated.
            self._s["by_method"][method] = self._s["by_method"].get(method, 0) + 1

            if success:
                self._s["repaired"] += 1
                ptprint(f"    ✓ {method}: {msg}", "OK", condition=self._out())
            else:
                self._s["failed"] += 1
                ptprint(f"    ✗ {method}: {msg}", "ERROR", condition=self._out())
                if not self.dry_run and src.exists():
                    shutil.copy2(str(src), str(self.failed_dir / src.name))

            self._repair_results.append({
                "filename":       src.name,
                "corruptionType": ctype,
                "success":        success,
                "method":         method,
                "message":        msg,
                "repairedPath":   (str(self.repaired_dir / src.name)
                                   if success else None),
            })

        s = self._s
        ptprint(f"\n  Total: {s['total']}  |  Repaired: {s['repaired']}  |  "
                f"Failed: {s['failed']}  |  Skipped: {s['skipped']}",
                "OK", condition=self._out())

        if s["total"] > 0:
            rate = round(s["repaired"] / s["total"] * 100, 1)
            ptprint(f"  Repair success rate: {rate}%", "OK", condition=self._out())

        self._add_node("photoRepair", True,
                       filesTotal=s["total"],
                       filesRepaired=s["repaired"],
                       filesFailed=s["failed"],
                       filesSkipped=s["skipped"],
                       byMethod=s["by_method"])
        return True

    # ------------------------------------------------------------------
    # Run and save
    # ------------------------------------------------------------------

    def run(self) -> None:
        ptprint("=" * 70, "TITLE", condition=self._out())
        ptprint(f"PHOTO REPAIR v{__version__}  |  Case: {self.case_id}",
                "TITLE", condition=self._out())
        if self.dry_run:
            ptprint("MODE: DRY-RUN", "WARNING", condition=self._out())
        ptprint("=" * 70, "TITLE", condition=self._out())
        ptprint("\nNOTE: Byte-level repair is JPEG-only. PNG: PIL resave. "
                "TIFF: not supported.", "INFO", condition=self._out())
        ptprint("Originals are never modified (working copies only).",
                "INFO", condition=self._out())

        self.repair_all_files()

        s = self._s
        success_rate = (round(s["repaired"] / max(s["total"], 1) * 100, 1)
                        if s["total"] else None)

        self.ptjsonlib.add_properties({
            "compliance":        ["NIST SP 800-86", "ISO/IEC 27037:2012"],
            "filesTotal":        s["total"],
            "filesRepaired":     s["repaired"],
            "filesFailed":       s["failed"],
            "filesSkipped":      s["skipped"],
            "repairSuccessRate": success_rate,
            "byMethod":          s["by_method"],
            "repairedDir":       str(self.repaired_dir),
            "failedDir":         str(self.failed_dir),
            "supportedFormats":  ["JPEG (byte-level)", "PNG (PIL resave)"],
            "unsupportedFormats": ["TIFF", "RAW formats", "BMP", "WebP"],
        })
        self.ptjsonlib.add_node(self.ptjsonlib.create_node_object(
            "chainOfCustodyEntry",
            properties={
                "action":    (f"Photo repair complete – "
                              f"{s['repaired']} repaired, "
                              f"{s['failed']} failed"),
                "result":    "SUCCESS" if s["repaired"] > 0 else "NO_REPAIRS",
                "analyst":   self.analyst,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "note":      ("Originals preserved; repairs applied to "
                              "copies in repaired/ directory"),
            }
        ))

        ptprint("\n" + "=" * 70, "TITLE", condition=self._out())
        ptprint("REPAIR COMPLETE", "OK", condition=self._out())
        ptprint(f"Repaired: {s['repaired']}  |  Failed: {s['failed']}  |  "
                f"Skipped: {s['skipped']}",
                "INFO", condition=self._out())
        if success_rate is not None:
            ptprint(f"Success rate: {success_rate}%", "OK", condition=self._out())
        ptprint("Next: EXIF Analysis", "INFO", condition=self._out())
        ptprint("=" * 70, "TITLE", condition=self._out())
        self.ptjsonlib.set_status("finished")

    def save_report(self) -> Optional[str]:
        json_file = (Path(self.args.json_out) if self.args.json_out
                     else self.output_dir / f"{self.case_id}_repair_report.json")
        report = {
            "result":        json.loads(self.ptjsonlib.get_result_json()),
            "repairResults": self._repair_results,
        }
        json_file.write_text(
            json.dumps(report, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8")
        if self.args.json_out:
            ptprint(self.ptjsonlib.get_result_json(), "", True)
        ptprint(f"JSON report: {json_file.name}", "OK", condition=self._out())
        return str(json_file)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def get_help() -> List[Dict]:
    return [
        {"description": [
            "Forensic photo repair tool – ptlibs compliant",
            "Byte-level JPEG repair + PIL resave for PNG",
            "Reads decisions from ptrepairdecision (ATTEMPT_REPAIR only)",
            "Originals are NEVER modified – repairs applied to copies only",
            "",
            "SUPPORTED:   JPEG (byte-level), PNG (PIL resave)",
            "UNSUPPORTED: TIFF, RAW, BMP, WebP",
        ]},
        {"usage": ["ptphotorepair <case-id> [options]"]},
        {"usage_example": [
            "ptphotorepair PHOTORECOVERY-2025-01-26-001",
            "ptphotorepair CASE-001 --dry-run",
            "ptphotorepair CASE-001 --json-out step12.json",
        ]},
        {"options": [
            ["case-id",              "",      "Forensic case identifier – REQUIRED"],
            ["--decisions-file",     "<f>",   "Path to repair_decisions.json"],
            ["-o", "--output-dir",   "<dir>", f"Output directory (default: {DEFAULT_OUTPUT_DIR})"],
            ["-a", "--analyst",      "<n>",   "Analyst name"],
            ["-j", "--json-out",     "<f>",   "Save JSON report to file"],
            ["-q", "--quiet",        "",      "Suppress terminal output"],
            ["--dry-run",            "",      "Simulate without modifying files"],
            ["-h", "--help",         "",      "Show help"],
            ["--version",            "",      "Show version"],
        ]},
        {"notes": [
            "Requires: Pillow (pip install pillow) for truncated JPEG and PNG repair",
            "Reads {case_id}_repair_decisions.json from previous step",
            "Output: {case_id}_repaired/ | {case_id}_repair_failed/",
            "TIFF files with REPAIRABLE status are moved to failed/ with a note",
        ]},
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("case_id")
    parser.add_argument("--decisions-file", default=None)
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
        tool = PtPhotoRepair(args)
        tool.run()
        tool.save_report()
        return 0
    except KeyboardInterrupt:
        ptprint("Interrupted by user.", "WARNING", condition=True)
        return 130
    except Exception as exc:
        ptprint(f"ERROR: {exc}", "ERROR", condition=True)
        return 99


if __name__ == "__main__":
    sys.exit(main())