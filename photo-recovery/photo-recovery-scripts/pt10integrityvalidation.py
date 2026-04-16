#!/usr/bin/env python3
"""
    Copyright (c) 2025 Bc. Dominik Sabota, VUT FIT Brno

    ptintegrityvalidation - Photo integrity validation tool

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License.
    See <https://www.gnu.org/licenses/> for details.
"""

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ._version import __version__
from .ptforensictoolbase import ForensicToolBase
from ptlibs import ptjsonlib, ptprinthelper
from ptlibs.ptprinthelper import ptprint

import signal


def _custom_sigint_handler(sig, frame):
    raise KeyboardInterrupt


signal.signal(signal.SIGINT, _custom_sigint_handler)

SCRIPTNAME         = "ptintegrityvalidation"
DEFAULT_OUTPUT_DIR = "/var/forensics/images"
VALIDATE_TIMEOUT   = 30

IMAGE_EXTENSIONS: set = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp",
    ".tiff", ".tif", ".heic", ".heif", ".webp",
    ".cr2", ".cr3", ".nef", ".nrw", ".arw", ".srf", ".sr2",
    ".dng", ".orf", ".raf", ".rw2", ".pef", ".raw",
}


class PtIntegrityValidation(ForensicToolBase):
    """
    Three-stage integrity validation (size → file type → format-specific tool)
    for all recovered photos. Classifies each file as VALID, REPAIRABLE, or
    CORRUPTED. Read-only on source directories (copies, never modifies originals).
    """

    def __init__(self, args: argparse.Namespace) -> None:
        self.ptjsonlib  = ptjsonlib.PtJsonLib()
        self.args       = args
        self.case_id    = args.case_id.strip()
        self.analyst    = args.analyst
        self.dry_run    = args.dry_run
        self.output_dir = Path(args.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.consolidated_dir = (
            Path(args.consolidated_dir) if getattr(args, "consolidated_dir", None)
            else self.output_dir / f"{self.case_id}_consolidated")
        self.validation_dir   = self.consolidated_dir / "validation"
        self.valid_dir        = self.validation_dir / "valid"
        self.repairable_dir   = self.validation_dir / "repairable"
        self.corrupted_dir    = self.validation_dir / "corrupted"

        self._s: Dict[str, Any] = {
            "total": 0, "valid": 0, "repairable": 0, "corrupted": 0,
            "by_format": {"valid": {}, "repairable": {}, "corrupted": {}},
        }
        self._results: List[Dict] = []

        self.ptjsonlib.add_properties({
            "caseId":        self.case_id,
            "outputDirectory": str(self.output_dir),
            "timestamp":     datetime.now(timezone.utc).isoformat(),
            "scriptVersion": __version__,
            "dryRun":        self.dry_run,
        })

    # ------------------------------------------------------------------
    # Phases
    # ------------------------------------------------------------------

    def check_source(self) -> bool:
        ptprint("\n[1/3] Checking source directory", "TITLE", condition=self._out())

        if not self.consolidated_dir.exists() and not self.dry_run:
            return self._fail("sourceCheck",
                              f"{self.consolidated_dir.name} not found – "
                              "run Recovery Consolidation first.")
        ptprint(f"  ✓ Source: {self.consolidated_dir.name}",
                "OK", condition=self._out())
        self._add_node("sourceCheck", True,
                       consolidatedDir=str(self.consolidated_dir))
        return True

    def check_tools(self) -> bool:
        ptprint("\n[2/3] Checking validation tools", "TITLE", condition=self._out())
        tools = {
            "file":     ("file type detection",  True),
            "identify": ("ImageMagick",          True),
            "jpeginfo": ("JPEG validation",      False),
            "pngcheck": ("PNG validation",       False),
            "tiffinfo": ("TIFF validation",      False),
            "exiftool": ("EXIF / RAW validation",False),
        }
        missing_critical = []
        for t, (desc, critical) in tools.items():
            found = self._check_command(t)
            ptprint(f"  [{'OK' if found else ('ERROR' if critical else 'WARNING')}] "
                    f"{t}: {desc}",
                    "OK" if found else ("ERROR" if critical else "WARNING"),
                    condition=self._out())
            if not found and critical:
                missing_critical.append(t)

        if missing_critical:
            ptprint(f"Critical tools missing: {', '.join(missing_critical)} – "
                    "sudo apt-get install file imagemagick",
                    "ERROR", condition=self._out())
            self._add_node("toolsCheck", False, missingTools=missing_critical)
            return False

        self._add_node("toolsCheck", True, toolsChecked=list(tools))
        return True

    def collect_files(self) -> List[Path]:
        ptprint("\n[3/3] Scanning for image files", "TITLE", condition=self._out())
        files = []
        for source in ("fs_based", "carved"):
            d = self.consolidated_dir / source
            if d.exists():
                batch = [f for f in d.rglob("*")
                         if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS]
                files.extend(batch)
                ptprint(f"  {source}/: {len(batch)} image files",
                        "INFO", condition=self._out())
        self._s["total"] = len(files)
        ptprint(f"  Total: {len(files)} files to validate",
                "OK", condition=self._out())
        self._add_node("fileScan", True, totalFiles=len(files))
        return files

    def _validate_file(self, filepath: Path) -> Tuple[str, Dict]:
        """Three-stage validation: file size → file(1) → format-specific tool."""
        details: Dict = {"size": 0, "details": ""}

        # Stage 1: minimum size
        try:
            details["size"] = filepath.stat().st_size
        except Exception:
            details["details"] = "Cannot read file"
            return "corrupted", details

        if details["size"] < 100:
            details["details"] = "File too small"
            return "corrupted", details

        # Stage 2: file(1) type check
        r = self._run_command(["file", "-b", str(filepath)], timeout=10)
        if not r["success"] or "image" not in r["stdout"].lower():
            details["details"] = "Not recognised as an image by file(1)"
            return "corrupted", details

        # Stage 3: format-specific validation
        ext = filepath.suffix.lstrip(".").lower()

        if ext in ("jpg", "jpeg"):
            r = self._run_command(["jpeginfo", "-c", str(filepath)],
                                  timeout=VALIDATE_TIMEOUT)
            if r["success"]:
                details["details"] = "OK"
                return "valid", details
            # Fall back to ImageMagick – may still be salvageable
            r = self._run_command(["identify", str(filepath)],
                                  timeout=VALIDATE_TIMEOUT)
            if r["success"]:
                details["details"] = "Minor errors detected (repairable)"
                return "repairable", details
            details["details"] = "JPEG validation failed"
            return "corrupted", details

        if ext == "png":
            r = self._run_command(["pngcheck", str(filepath)],
                                  timeout=VALIDATE_TIMEOUT)
            if r["success"] and "OK" in r["stdout"]:
                details["details"] = "OK"
                return "valid", details
            if "warning" in r["stdout"].lower():
                details["details"] = "PNG warnings (repairable)"
                return "repairable", details
            details["details"] = "PNG validation failed"
            return "corrupted", details

        if ext in ("tif", "tiff"):
            r = self._run_command(["tiffinfo", str(filepath)],
                                  timeout=VALIDATE_TIMEOUT)
            if r["success"]:
                details["details"] = "OK"
                return "valid", details
            details["details"] = "TIFF validation failed"
            return "corrupted", details

        # Generic fallback: ImageMagick identify
        r = self._run_command(["identify", str(filepath)],
                              timeout=VALIDATE_TIMEOUT)
        if r["success"]:
            details["details"] = "OK (generic validation)"
            return "valid", details
        details["details"] = f"{ext.upper()} validation failed"
        return "corrupted", details

    def validate_files(self, files: List[Path]) -> None:
        ptprint("\nValidating integrity …", "TITLE", condition=self._out())
        total = len(files)

        for idx, fp in enumerate(files, 1):
            if idx % 100 == 0 or idx == total:
                ptprint(f"  {idx}/{total} ({idx * 100 // total}%)",
                        "INFO", condition=self._out())

            status, details = self._validate_file(fp)
            ext             = fp.suffix.lstrip(".").lower()

            self._s[status] += 1
            fmt_bucket = self._s["by_format"].get(status, {})
            fmt_bucket[ext] = fmt_bucket.get(ext, 0) + 1

            self._results.append({
                "filename":          fp.name,
                "path":              str(fp.relative_to(self.consolidated_dir)),
                "format":            ext,
                "status":            status,
                "sizeBytes":         details.get("size", 0),
                "validationDetails": details.get("details", ""),
            })

            if not self.dry_run:
                dest_dir = {"valid":      self.valid_dir,
                            "repairable": self.repairable_dir,
                            "corrupted":  self.corrupted_dir}[status]
                shutil.copy2(str(fp), str(dest_dir / fp.name))

        rate = round(self._s["valid"] / total * 100, 1) if total else 0
        ptprint(f"Validation complete  |  Valid: {self._s['valid']}  |  "
                f"Repairable: {self._s['repairable']}  |  "
                f"Corrupted: {self._s['corrupted']}  |  Rate: {rate}%",
                "OK", condition=self._out())
        self._add_node("validation", True,
                       totalFiles=total,
                       validFiles=self._s["valid"],
                       repairableFiles=self._s["repairable"],
                       corruptedFiles=self._s["corrupted"],
                       validationRate=rate)

    # ------------------------------------------------------------------
    # Run and save
    # ------------------------------------------------------------------

    def run(self) -> None:
        ptprint("=" * 70, "TITLE", condition=self._out())
        ptprint(f"PHOTO INTEGRITY VALIDATION v{__version__}  |  "
                f"Case: {self.case_id}", "TITLE", condition=self._out())
        if self.dry_run:
            ptprint("MODE: DRY-RUN", "WARNING", condition=self._out())
        ptprint("=" * 70, "TITLE", condition=self._out())

        if not self.check_source():
            self.ptjsonlib.set_status("finished"); return
        if not self.check_tools():
            self.ptjsonlib.set_status("finished"); return

        if not self.dry_run:
            for path in (self.valid_dir, self.repairable_dir, self.corrupted_dir):
                path.mkdir(parents=True, exist_ok=True)

        files = self.collect_files()
        if not files and not self.dry_run:
            ptprint("No image files found.", "ERROR", condition=self._out())
            self.ptjsonlib.set_status("finished"); return

        self.validate_files(files)

        s    = self._s
        rate = round(s["valid"] / s["total"] * 100, 1) if s["total"] else None
        self.ptjsonlib.add_properties({
            "compliance":       ["NIST SP 800-86", "ISO/IEC 27037:2012"],
            "totalFiles":       s["total"],
            "validFiles":       s["valid"],
            "repairableFiles":  s["repairable"],
            "corruptedFiles":   s["corrupted"],
            "validationRate":   rate,
            "byFormat":         s["by_format"],
            "validationDir":    str(self.validation_dir),
        })
        self.ptjsonlib.add_node(self.ptjsonlib.create_node_object(
            "chainOfCustodyEntry",
            properties={
                "action":    (f"Integrity validation complete – "
                              f"{s['valid']} VALID, {s['repairable']} REPAIRABLE, "
                              f"{s['corrupted']} CORRUPTED"),
                "result":    "SUCCESS" if s["total"] > 0 else "NO_FILES",
                "analyst":   self.analyst,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ))

        ptprint("\n" + "=" * 70, "TITLE", condition=self._out())
        ptprint("VALIDATION COMPLETE", "OK", condition=self._out())
        ptprint(f"Total: {s['total']}  |  Valid: {s['valid']}  |  "
                f"Repairable: {s['repairable']}  |  Corrupted: {s['corrupted']}"
                + (f"  |  Rate: {rate}%" if rate else ""),
                "INFO", condition=self._out())
        ptprint("Next: Repair Decision Point", "INFO", condition=self._out())
        ptprint("=" * 70, "TITLE", condition=self._out())
        self.ptjsonlib.set_status("finished")

    def _write_text_report(self, props: Dict) -> Path:
        txt = self.validation_dir / "VALIDATION_REPORT.txt"
        self.validation_dir.mkdir(parents=True, exist_ok=True)
        sep   = "=" * 70
        lines = [sep, "PHOTO INTEGRITY VALIDATION REPORT", sep, "",
                 f"Case ID:   {self.case_id}",
                 f"Timestamp: {props.get('timestamp', '')}", "",
                 "STATISTICS:",
                 f"  Total files:     {props.get('totalFiles', 0)}",
                 f"  VALID:           {props.get('validFiles', 0)}",
                 f"  REPAIRABLE:      {props.get('repairableFiles', 0)}",
                 f"  CORRUPTED:       {props.get('corruptedFiles', 0)}",
                 *([] if props.get("validationRate") is None
                   else [f"  Validation rate: {props['validationRate']}%"]),
                 "", "BY FORMAT (VALID):"]
        lines += [f"  {k.upper():8s}: {v}"
                  for k, v in sorted(
                      props.get("byFormat", {}).get("valid", {}).items())]
        lines += ["", "BY FORMAT (REPAIRABLE):"]
        lines += [f"  {k.upper():8s}: {v}"
                  for k, v in sorted(
                      props.get("byFormat", {}).get("repairable", {}).items())]
        txt.write_text("\n".join(lines), encoding="utf-8")
        return txt

    def save_report(self) -> Optional[str]:
        if self.args.json:
            ptprint(self.ptjsonlib.get_result_json(), "", self.args.json)
            return None

        json_file = self.output_dir / f"{self.case_id}_validation_report.json"
        report    = {
            "result":         json.loads(self.ptjsonlib.get_result_json()),
            "validatedFiles": self._results,
        }
        json_file.write_text(
            json.dumps(report, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8")
        ptprint(f"JSON report: {json_file}", "OK", condition=self._out())

        props = json.loads(self.ptjsonlib.get_result_json())["result"]["properties"]
        txt   = self._write_text_report(props)
        ptprint(f"Text report: {txt}", "OK", condition=self._out())
        return str(json_file)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def get_help() -> List[Dict]:
    return [
        {"description": [
            "Photo integrity validation – ptlibs compliant",
            "Three-stage validation: size → file(1) → format-specific tool",
            "Compliant with NIST SP 800-86 and ISO/IEC 27037:2012",
        ]},
        {"usage": ["ptintegrityvalidation <case-id> [options]"]},
        {"usage_example": [
            "ptintegrityvalidation PHOTORECOVERY-2025-01-26-001",
            "ptintegrityvalidation PHOTORECOVERY-2025-01-26-001 --dry-run",
        ]},
        {"options": [
            ["case-id",            "",      "Forensic case identifier – REQUIRED"],
            ["--consolidated-dir", "<dir>", "Consolidated dir (optional; auto-discovered)"],
            ["-a", "--analyst",    "<n>",   "Analyst name (default: Analyst)"],
            ["-o", "--output-dir", "<dir>", f"Output directory (default: {DEFAULT_OUTPUT_DIR})"],
            ["--dry-run",          "",      "Simulate without copying files"],
            ["-j", "--json",       "",      "JSON output for platform integration"],
            ["-q", "--quiet",      "",      "Suppress terminal output"],
            ["-h", "--help",       "",      "Show help"],
            ["--version",          "",      "Show version"],
        ]},
        {"notes": [
            "VALID: passes all checks  |  REPAIRABLE: minor errors  |  "
            "CORRUPTED: severe damage",
            "JPEG: jpeginfo → identify (fallback)  |  PNG: pngcheck  |  "
            "TIFF: tiffinfo  |  Other: identify",
            "Output: valid/ | repairable/ | corrupted/ | VALIDATION_REPORT.txt",
            "Compliant with NIST SP 800-86 and ISO/IEC 27037:2012",
        ]},
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("case_id")
    parser.add_argument("--consolidated-dir", default=None,
                        help="Path to consolidated dir (optional; auto-discovered if omitted)")
    parser.add_argument("-a", "--analyst",    default="Analyst")
    parser.add_argument("-o", "--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("-q", "--quiet",      action="store_true")
    parser.add_argument("--dry-run",          action="store_true")
    parser.add_argument("-j", "--json",       action="store_true")
    parser.add_argument("--version", action="version",
                        version=f"{SCRIPTNAME} {__version__}")

    if len(sys.argv) == 1 or {"-h", "--help"} & set(sys.argv):
        ptprinthelper.help_print(get_help(), SCRIPTNAME, __version__)
        sys.exit(0)

    args = parser.parse_args()
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