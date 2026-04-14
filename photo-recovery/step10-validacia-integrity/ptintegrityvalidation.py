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
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ._version import __version__

from ptlibs import ptjsonlib, ptprinthelper
from ptlibs.ptprinthelper import ptprint

# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------

SCRIPTNAME         = "ptintegrityvalidation"
DEFAULT_OUTPUT_DIR = "/var/forensics/images"
VALIDATE_TIMEOUT   = 30   # per file (identify, jpeginfo, etc.)

IMAGE_EXTENSIONS: set = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp",
    ".tiff", ".tif", ".heic", ".heif", ".webp",
    ".cr2", ".cr3", ".nef", ".nrw", ".arw", ".srf", ".sr2",
    ".dng", ".orf", ".raf", ".rw2", ".pef", ".raw",
}

FORMAT_VALIDATORS: Dict[str, str] = {
    "jpg": "jpeginfo", "jpeg": "jpeginfo",
    "png": "pngcheck",
    "tif": "tiffinfo", "tiff": "tiffinfo",
}

# ---------------------------------------------------------------------------
# MAIN CLASS
# ---------------------------------------------------------------------------

class PtIntegrityValidation:
    """
    Photo integrity validation – ptlibs compliant.

    Pipeline: scan consolidated → 3-stage validation (size → file → format) →
              classify (VALID / REPAIRABLE / CORRUPTED) → organise → report.

    READ-ONLY on source directories (copies, never modifies originals).
    Compliant with NIST SP 800-86 and ISO/IEC 27037:2012.
    """

    def __init__(self, args: argparse.Namespace) -> None:
        self.ptjsonlib  = ptjsonlib.PtJsonLib()
        self.args       = args
        self.case_id    = args.case_id.strip()
        self.dry_run    = args.dry_run
        self.output_dir = Path(args.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Source directory
        self.consolidated_dir = self.output_dir / f"{self.case_id}_consolidated"

        # Output directories
        self.validation_dir = self.consolidated_dir / "validation"
        self.valid_dir      = self.validation_dir / "valid"
        self.repairable_dir = self.validation_dir / "repairable"
        self.corrupted_dir  = self.validation_dir / "corrupted"

        # All counters in one dict
        self._s: Dict[str, Any] = {
            "total": 0, "valid": 0, "repairable": 0, "corrupted": 0,
            "by_format": {"valid": {}, "repairable": {}, "corrupted": {}},
        }
        self._results: List[Dict] = []

        self.ptjsonlib.add_properties({
            "caseId": self.case_id,
            "outputDirectory": str(self.output_dir),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "scriptVersion": __version__,
            "compliance": ["NIST SP 800-86", "ISO/IEC 27037:2012"],
            "totalFiles": 0, "validFiles": 0, "repairableFiles": 0,
            "corruptedFiles": 0, "validationRate": None,
            "byFormat": {"valid": {}, "repairable": {}, "corrupted": {}},
            "validationDir": str(self.validation_dir),
            "dryRun": self.dry_run,
        })
        ptprint(f"Initialized: case={self.case_id}", "INFO", condition=not self.args.json)

    # --- helpers ------------------------------------------------------------

    def _add_node(self, node_type: str, success: bool, **kwargs) -> None:
        self.ptjsonlib.add_node(self.ptjsonlib.create_node_object(
            node_type, properties={"success": success, **kwargs}
        ))

    def _fail(self, node_type: str, msg: str) -> bool:
        ptprint(msg, "ERROR", condition=not self.args.json)
        self._add_node(node_type, False, error=msg)
        return False

    def _check_command(self, cmd: str) -> bool:
        try:
            subprocess.run(["which", cmd], capture_output=True, check=True, timeout=5)
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return False

    def _run_command(self, cmd: List[str], timeout: int = 30) -> Dict[str, Any]:
        if self.dry_run:
            return {"success": True, "stdout": "[DRY-RUN]", "stderr": "", "returncode": 0}
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True,
                                  timeout=timeout, check=False)
            return {"success": proc.returncode == 0, "stdout": proc.stdout.strip(),
                    "stderr": proc.stderr.strip(), "returncode": proc.returncode}
        except subprocess.TimeoutExpired:
            return {"success": False, "stdout": "", "stderr": f"Timeout after {timeout}s",
                    "returncode": -1}
        except Exception as exc:
            return {"success": False, "stdout": "", "stderr": str(exc), "returncode": -1}

    # --- phases -------------------------------------------------------------

    def check_source(self) -> bool:
        """Verify consolidated directory exists."""
        ptprint("\n[1/3] Checking Source Directory", "TITLE", condition=not self.args.json)

        if not self.consolidated_dir.exists() and not self.dry_run:
            return self._fail("sourceCheck",
                              f"Consolidated directory not found: {self.consolidated_dir.name} – "
                              "run Recovery Consolidation first.")

        ptprint(f"[OK] Source: {self.consolidated_dir.name}",
                "OK", condition=not self.args.json)
        self._add_node("sourceCheck", True, consolidatedDir=str(self.consolidated_dir))
        return True

    def check_tools(self) -> bool:
        """Verify validation tools are installed."""
        ptprint("\n[2/3] Checking Validation Tools", "TITLE", condition=not self.args.json)

        tools = {"file": "file type detection", "identify": "ImageMagick validation",
                 "jpeginfo": "JPEG validation", "pngcheck": "PNG validation",
                 "tiffinfo": "TIFF validation", "exiftool": "EXIF/RAW validation"}
        missing = []
        for t, desc in tools.items():
            found = self._check_command(t)
            ptprint(f"  [{'OK' if found else 'WARNING'}] {t}: {desc}",
                    "OK" if found else "WARNING", condition=not self.args.json)
            if not found and t in ("file", "identify"):
                missing.append(t)

        if missing:
            ptprint(f"Critical tools missing: {', '.join(missing)} – "
                    "sudo apt-get install file imagemagick",
                    "ERROR", condition=not self.args.json)
            self._add_node("toolsCheck", False, missingTools=missing)
            return False

        self._add_node("toolsCheck", True, toolsChecked=list(tools.keys()))
        return True

    def collect_files(self) -> List[Path]:
        """Collect all image files from consolidated directory."""
        ptprint("\n[3/3] Scanning for Image Files", "TITLE", condition=not self.args.json)

        files = []
        for source in ("fs_based", "carved"):
            source_dir = self.consolidated_dir / source
            if source_dir.exists():
                batch = [f for f in source_dir.rglob("*")
                         if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS]
                files.extend(batch)
                ptprint(f"  {source}/: {len(batch)} image files",
                        "INFO", condition=not self.args.json)

        self._s["total"] = len(files)
        ptprint(f"Total: {len(files)} files to validate",
                "OK", condition=not self.args.json)
        self._add_node("fileScan", True, totalFiles=len(files))
        return files

    def validate_files(self, files: List[Path]) -> None:
        """Three-stage validation: size → file → format."""
        ptprint("\nValidating integrity …", "TITLE", condition=not self.args.json)

        total = len(files)
        for idx, fp in enumerate(files, 1):
            if idx % 100 == 0 or idx == total:
                ptprint(f"  {idx}/{total} ({idx*100//total}%)",
                        "INFO", condition=not self.args.json)

            status, details = self._validate_file(fp)
            ext = fp.suffix.lstrip(".").lower()

            self._s[status] += 1
            if status in self._s["by_format"]:
                self._s["by_format"][status][ext] = \
                    self._s["by_format"][status].get(ext, 0) + 1

            self._results.append({
                "filename": fp.name,
                "path": str(fp.relative_to(self.consolidated_dir)),
                "format": ext,
                "status": status,
                "sizeBytes": details.get("size", 0),
                "validationDetails": details.get("details", ""),
            })

            # Copy to appropriate directory
            if not self.dry_run:
                if status == "valid":
                    shutil.copy2(str(fp), str(self.valid_dir / fp.name))
                elif status == "repairable":
                    shutil.copy2(str(fp), str(self.repairable_dir / fp.name))
                else:
                    shutil.copy2(str(fp), str(self.corrupted_dir / fp.name))

        rate = round(self._s["valid"] / total * 100, 1) if total else 0
        ptprint(f"Validation complete | Valid: {self._s['valid']} | "
                f"Repairable: {self._s['repairable']} | "
                f"Corrupted: {self._s['corrupted']} | Rate: {rate}%",
                "OK", condition=not self.args.json)
        self._add_node("validation", True,
                       totalFiles=total, validFiles=self._s["valid"],
                       repairableFiles=self._s["repairable"],
                       corruptedFiles=self._s["corrupted"], validationRate=rate)

    def _validate_file(self, filepath: Path) -> Tuple[str, Dict]:
        """Three-stage validation: size → file → format. Returns (status, details)."""
        details: Dict = {"size": 0, "details": ""}

        # Stage 1: Size
        try:
            details["size"] = filepath.stat().st_size
        except Exception:
            details["details"] = "Cannot read file"
            return "corrupted", details

        if details["size"] < 100:
            details["details"] = "File too small"
            return "corrupted", details

        # Stage 2: File type
        r = self._run_command(["file", "-b", str(filepath)], timeout=10)
        if not r["success"] or "image" not in r["stdout"].lower():
            details["details"] = "Not an image file"
            return "corrupted", details

        # Stage 3: Format validation
        ext = filepath.suffix.lstrip(".").lower()

        if ext in ("jpg", "jpeg"):
            r = self._run_command(["jpeginfo", "-c", str(filepath)],
                                  timeout=VALIDATE_TIMEOUT)
            if r["success"]:
                details["details"] = "OK"
                return "valid", details
            # Try ImageMagick as fallback
            r = self._run_command(["identify", str(filepath)],
                                  timeout=VALIDATE_TIMEOUT)
            if r["success"]:
                details["details"] = "Minor errors (repairable)"
                return "repairable", details
            details["details"] = "JPEG validation failed"
            return "corrupted", details

        elif ext == "png":
            r = self._run_command(["pngcheck", str(filepath)],
                                  timeout=VALIDATE_TIMEOUT)
            if r["success"] and "OK" in r["stdout"]:
                details["details"] = "OK"
                return "valid", details
            elif "warning" in r["stdout"].lower():
                details["details"] = "PNG warnings (repairable)"
                return "repairable", details
            details["details"] = "PNG validation failed"
            return "corrupted", details

        elif ext in ("tif", "tiff"):
            r = self._run_command(["tiffinfo", str(filepath)],
                                  timeout=VALIDATE_TIMEOUT)
            if r["success"]:
                details["details"] = "OK"
                return "valid", details
            details["details"] = "TIFF validation failed"
            return "corrupted", details

        else:
            # Generic ImageMagick validation for other formats
            r = self._run_command(["identify", str(filepath)],
                                  timeout=VALIDATE_TIMEOUT)
            if r["success"]:
                details["details"] = "OK (generic validation)"
                return "valid", details
            details["details"] = f"{ext.upper()} validation failed"
            return "corrupted", details

    # --- run & save ---------------------------------------------------------

    def run(self) -> None:
        """Orchestrate the full validation pipeline."""
        ptprint("=" * 70, "TITLE", condition=not self.args.json)
        ptprint(f"PHOTO INTEGRITY VALIDATION v{__version__} | Case: {self.case_id}",
                "TITLE", condition=not self.args.json)
        if self.dry_run:
            ptprint("MODE: DRY-RUN", "WARNING", condition=not self.args.json)
        ptprint("=" * 70, "TITLE", condition=not self.args.json)

        if not self.check_source():
            self.ptjsonlib.set_status("finished"); return
        if not self.check_tools():
            self.ptjsonlib.set_status("finished"); return

        # Create directory tree
        if not self.dry_run:
            for path in (self.valid_dir, self.repairable_dir, self.corrupted_dir):
                path.mkdir(parents=True, exist_ok=True)

        files = self.collect_files()
        if not files and not self.dry_run:
            ptprint("No image files found.", "ERROR", condition=not self.args.json)
            self.ptjsonlib.set_status("finished"); return

        self.validate_files(files)

        s = self._s
        rate = round(s["valid"] / s["total"] * 100, 1) if s["total"] else None
        self.ptjsonlib.add_properties({
            "totalFiles": s["total"], "validFiles": s["valid"],
            "repairableFiles": s["repairable"], "corruptedFiles": s["corrupted"],
            "validationRate": rate, "byFormat": s["by_format"],
        })

        # Add Chain of Custody entry
        self.ptjsonlib.add_node(self.ptjsonlib.create_node_object(
            "chainOfCustodyEntry",
            properties={
                "action": f"Validácia integrity dokončená – {s['valid']} VALID, {s['repairable']} REPAIRABLE, {s['corrupted']} CORRUPTED",
                "result": "SUCCESS" if s["total"] > 0 else "NO_FILES",
                "analyst": self.args.analyst if hasattr(self.args, 'analyst') else "System",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ))

        ptprint("\n" + "=" * 70, "TITLE", condition=not self.args.json)
        ptprint("VALIDATION COMPLETED", "OK", condition=not self.args.json)
        ptprint(f"Total: {s['total']} | Valid: {s['valid']} | "
                f"Repairable: {s['repairable']} | Corrupted: {s['corrupted']}"
                + (f" | Rate: {rate}%" if rate else ""),
                "INFO", condition=not self.args.json)
        ptprint("Next: Repair Decision Point", "INFO", condition=not self.args.json)
        ptprint("=" * 70, "TITLE", condition=not self.args.json)
        self.ptjsonlib.set_status("finished")

    def _write_text_report(self, props: Dict) -> Path:
        """Write VALIDATION_REPORT.txt to validation_dir."""
        txt = self.validation_dir / "VALIDATION_REPORT.txt"
        self.validation_dir.mkdir(parents=True, exist_ok=True)
        sep = "=" * 70
        lines = [sep, "PHOTO INTEGRITY VALIDATION REPORT", sep, "",
                 f"Case ID:   {self.case_id}",
                 f"Timestamp: {props.get('timestamp','')}", "",
                 "STATISTICS:",
                 f"  Total files:     {props.get('totalFiles',0)}",
                 f"  VALID:           {props.get('validFiles',0)}",
                 f"  REPAIRABLE:      {props.get('repairableFiles',0)}",
                 f"  CORRUPTED:       {props.get('corruptedFiles',0)}",
                 *([] if props.get("validationRate") is None
                   else [f"  Validation rate: {props['validationRate']}%"]),
                 "", "BY FORMAT (VALID):"]
        lines += [f"  {k.upper():8s}: {v}"
                  for k, v in sorted(props.get("byFormat", {}).get("valid", {}).items())]
        lines += ["", "BY FORMAT (REPAIRABLE):"]
        lines += [f"  {k.upper():8s}: {v}"
                  for k, v in sorted(props.get("byFormat", {}).get("repairable", {}).items())]
        txt.write_text("\n".join(lines), encoding="utf-8")
        return txt

    def save_report(self) -> Optional[str]:
        """Save JSON report and VALIDATION_REPORT.txt."""
        if self.args.json:
            ptprint(self.ptjsonlib.get_result_json(), "", self.args.json)
            return None

        json_file = self.output_dir / f"{self.case_id}_validation_report.json"
        report = {
            "result": json.loads(self.ptjsonlib.get_result_json()),
            "validatedFiles": self._results,
        }
        json_file.write_text(
            json.dumps(report, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8")
        ptprint(f"JSON report: {json_file}", "OK", condition=not self.args.json)

        props = json.loads(self.ptjsonlib.get_result_json())["result"]["properties"]
        txt = self._write_text_report(props)
        ptprint(f"Text report: {txt}", "OK", condition=not self.args.json)
        return str(json_file)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def get_help() -> List[Dict]:
    return [
        {"description": [
            "Photo integrity validation – ptlibs compliant",
            "3-stage validation: size → file → format-specific tools",
            "Compliant with NIST SP 800-86 and ISO/IEC 27037:2012",
        ]},
        {"usage": ["ptintegrityvalidation <case-id> [options]"]},
        {"usage_example": [
            "ptintegrityvalidation PHOTORECOVERY-2025-01-26-001",
            "ptintegrityvalidation PHOTORECOVERY-2025-01-26-001 --json",
            "ptintegrityvalidation PHOTORECOVERY-2025-01-26-001 --dry-run",
        ]},
        {"options": [
            ["case-id",            "",      "Forensic case identifier – REQUIRED"],
            ["-o", "--output-dir", "<dir>", f"Output directory (default: {DEFAULT_OUTPUT_DIR})"],
            ["-v", "--verbose",    "",      "Verbose logging"],
            ["--dry-run",          "",      "Simulate without copying files"],
            ["-j", "--json",       "",      "JSON output for Penterep platform"],
            ["-q", "--quiet",      "",      "Suppress progress output"],
            ["-h", "--help",       "",      "Show help"],
            ["--version",          "",      "Show version"],
        ]},
        {"notes": [
            "Pipeline: source check → tools → scan → validate → classify → report",
            "Output:   valid/ | repairable/ | corrupted/ | VALIDATION_REPORT.txt",
            "Categories: VALID (OK) | REPAIRABLE (minor errors) | CORRUPTED (severe damage)",
            "READ-ONLY on source directories (copies, never modifies originals)",
            "Compliant with NIST SP 800-86 and ISO/IEC 27037:2012",
        ]},
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("case_id")
    parser.add_argument("-o", "--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("-v", "--verbose",    action="store_true")
    parser.add_argument("-q", "--quiet",      action="store_true")
    parser.add_argument("--dry-run",          action="store_true")
    parser.add_argument("-j", "--json",       action="store_true")
    parser.add_argument("--version", action="version", version=f"{SCRIPTNAME} {__version__}")
    parser.add_argument("--socket-address",   default=None)
    parser.add_argument("--socket-port",      default=None)
    parser.add_argument("--process-ident",    default=None)

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