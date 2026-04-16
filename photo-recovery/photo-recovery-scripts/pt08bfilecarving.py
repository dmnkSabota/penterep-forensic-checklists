#!/usr/bin/env python3
"""
    Copyright (c) 2026 Bc. Dominik Sabota, VUT FIT Brno

    ptfilecarving - Forensic file carving tool (PhotoRec)

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License.
    See <https://www.gnu.org/licenses/> for details.
"""

# LAST CHANGES:
#   - IMAGE_FORMATS, FORMAT_DIRS, IMAGE_FILE_KEYWORDS replaced with imports
#     from _constants (single source of truth)
#   - _validate_file() removed; replaced by self._validate_image_file()
#     inherited from ForensicToolBase (duplicate in ptfilesystemrecovery)
#   - Fixed PhotoRec invocation: removed the .cmd file creation which was
#     dead code (the file was written but never passed to photorec).
#     Using the correct non-interactive syntax on Linux (testdisk 7.1+):
#       photorec /log /d output_dir /cmd image_path search
#     Format filtering is intentionally handled post-carving by
#     validate_and_deduplicate() – this is more reliable across photorec
#     versions than building a comma-separated fileopt command string.
#   - Changed --json boolean flag to --json-out <file> for consistency

import argparse
import hashlib
import json
import re
import shutil
import signal
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from ._version import __version__
from ._constants import IMAGE_EXTENSIONS, FORMAT_GROUP_MAP, FORMAT_DIR_MAP
from .ptforensictoolbase import ForensicToolBase
from ptlibs import ptjsonlib, ptprinthelper
from ptlibs.ptprinthelper import ptprint


def _custom_sigint_handler(sig, frame):
    raise KeyboardInterrupt


signal.signal(signal.SIGINT, _custom_sigint_handler)

SCRIPTNAME         = "ptfilecarving"
DEFAULT_OUTPUT_DIR = "/var/forensics/images"
PHOTOREC_TIMEOUT   = 14400   # 4 hours
VALIDATE_TIMEOUT   = 30      # per file
MIN_FILE_SIZE      = 100     # bytes


class PtFileCarving(ForensicToolBase):
    """
    Recovers image files from a forensic image using PhotoRec (file carving).
    Validates and deduplicates recovered files. Read-only on the forensic image.

    NOTE: This step uses a non-interactive PhotoRec invocation. Format filtering
    is applied post-carving – PhotoRec will recover all file types and
    validate_and_deduplicate() retains only valid image files.
    """

    def __init__(self, args: argparse.Namespace) -> None:
        self.ptjsonlib  = ptjsonlib.PtJsonLib()
        self.args       = args
        self.case_id    = args.case_id.strip()
        self.analyst    = getattr(args, "analyst", "Analyst")
        self.dry_run    = args.dry_run
        self.output_dir = Path(args.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.image_path:     Optional[Path] = None
        self.photorec_work:  Path = self.output_dir / f"{self.case_id}_photorec"
        self.carved_out:     Path = self.output_dir / f"{self.case_id}_carved"
        self.carved_valid:   Path = self.carved_out / "valid"
        self.carved_corrupt: Path = self.carved_out / "corrupted"
        self.carved_dupes:   Path = self.carved_out / "duplicates"

        self._s: Dict[str, Any] = {
            "carved": 0, "image_files": 0, "valid": 0, "corrupted": 0,
            "duplicates": 0, "invalid": 0, "by_format": defaultdict(int),
        }
        self._valid_files: List[Dict] = []

        self.ptjsonlib.add_properties({
            "caseId":        self.case_id,
            "analyst":       self.analyst,
            "timestamp":     datetime.now(timezone.utc).isoformat(),
            "scriptVersion": __version__,
            "dryRun":        self.dry_run,
        })

    # ------------------------------------------------------------------
    # Phases
    # ------------------------------------------------------------------

    def load_image(self) -> bool:
        ptprint("\n[1/4] Locating forensic image", "TITLE", condition=self._out())

        f = (Path(self.args.analysis_file)
             if getattr(self.args, "analysis_file", None)
             else self.output_dir / f"{self.case_id}_filesystem_analysis.json")

        if f.exists():
            try:
                data       = json.loads(f.read_text(encoding="utf-8"))
                props      = data.get("result", data).get("properties", data)
                image_path = props.get("imagePath") or props.get("image_file")
                if image_path:
                    self.image_path = Path(image_path)
                    ptprint(f"  Loaded from analysis file: {self.image_path.name}",
                            "OK", condition=self._out())
            except Exception as exc:
                ptprint(f"  Cannot parse analysis file: {exc}",
                        "WARNING", condition=self._out())

        if not self.image_path and getattr(self.args, "image", None):
            self.image_path = Path(self.args.image)

        if not self.image_path:
            return self._fail("imageLookup",
                              "No forensic image found. "
                              "Provide --image or run Filesystem Analysis first.")
        if not self.image_path.exists() and not self.dry_run:
            return self._fail("imageLookup",
                              f"Image not found: {self.image_path}")

        ptprint(f"  Image: {self.image_path}", "OK", condition=self._out())
        self.ptjsonlib.add_properties({"imagePath": str(self.image_path)})
        self._add_node("imageLookup", True, imagePath=str(self.image_path))
        return True

    def check_tools(self) -> bool:
        ptprint("\n[2/4] Checking required tools", "TITLE", condition=self._out())
        tools   = {"photorec": "file carving engine",
                   "file":     "file type detection",
                   "identify": "ImageMagick validation"}
        missing = []
        for t, desc in tools.items():
            found = self._check_command(t)
            ptprint(f"  [{'OK' if found else 'ERROR'}] {t}: {desc}",
                    "OK" if found else "ERROR", condition=self._out())
            if not found:
                missing.append(t)

        if "photorec" in missing:
            ptprint("  Install: sudo apt install testdisk",
                    "ERROR", condition=self._out())
        if {"file", "identify"} & set(missing):
            ptprint("  Install: sudo apt install file imagemagick",
                    "ERROR", condition=self._out())
        if missing:
            self._add_node("toolsCheck", False, missingTools=missing)
            return False

        self._add_node("toolsCheck", True, toolsChecked=list(tools))
        return True

    def run_photorec(self) -> bool:
        ptprint("\n[3/4] Running PhotoRec", "TITLE", condition=self._out())

        if not self.dry_run:
            self.photorec_work.mkdir(parents=True, exist_ok=True)

        # Non-interactive PhotoRec batch mode (testdisk 7.1+, Ubuntu 22.04).
        #
        # Syntax:  photorec /log /d output_dir /cmd image_path command
        #
        # Format filtering is NOT applied here via fileopt commands because
        # the comma-separated fileopt string varies across PhotoRec versions.
        # Instead, validate_and_deduplicate() (step 3/4) retains only files
        # whose extensions appear in IMAGE_EXTENSIONS and that pass
        # ImageMagick identify validation.
        cmd = ["photorec", "/log", "/d", str(self.photorec_work),
               "/cmd", str(self.image_path), "search"]

        ptprint(f"  Command: {' '.join(cmd)}", "INFO", condition=self._out())
        ptprint(f"  Output:  {self.photorec_work}",
                "INFO", condition=self._out())

        if self.dry_run:
            ptprint("  [DRY-RUN] PhotoRec skipped.", "INFO", condition=self._out())
            self._add_node("photorecRun", True, dryRun=True)
            return True

        ptprint("  Running PhotoRec (this may take a while) …",
                "INFO", condition=self._out())
        log_file = self.output_dir / f"{self.case_id}_photorec.log"

        try:
            with open(log_file, "w") as lf:
                lf.write(f"PhotoRec started: {datetime.now()}\n"
                         f"Command: {' '.join(cmd)}\n{'=' * 70}\n\n")
                lf.flush()
                proc = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, bufsize=1)
                for line in proc.stdout:
                    lf.write(line); lf.flush()
                    if not self.args.json:
                        print(line, end="", flush=True)
                proc.wait()
                lf.write(f"\nExit code: {proc.returncode}\n")

            if proc.returncode not in (0, 1):
                return self._fail("photorecRun",
                                  f"PhotoRec exited with code {proc.returncode}. "
                                  f"Check {log_file.name} for details.")

        except subprocess.TimeoutExpired:
            proc.kill(); proc.wait()
            return self._fail("photorecRun",
                              f"PhotoRec timed out after "
                              f"{PHOTOREC_TIMEOUT // 3600}h")
        except KeyboardInterrupt:
            proc.terminate(); proc.wait()
            ptprint("\n  Interrupted by user.", "WARNING", condition=self._out())
            raise

        # Count how many files PhotoRec recovered (all types)
        carved_all = list(self.photorec_work.rglob("*"))
        total      = sum(1 for f in carved_all if f.is_file())
        ptprint(f"  ✓ PhotoRec done. {total} file(s) in work directory.",
                "OK", condition=self._out())
        self._s["carved"] = total
        self._add_node("photorecRun", True, filesRecovered=total,
                       logFile=str(log_file))
        return True

    def validate_and_deduplicate(self) -> bool:
        ptprint("\n[4/4] Validating and deduplicating", "TITLE", condition=self._out())

        for d in (self.carved_valid, self.carved_corrupt, self.carved_dupes):
            if not self.dry_run:
                d.mkdir(parents=True, exist_ok=True)

        # Collect candidate files: extension must be in IMAGE_EXTENSIONS
        candidates: List[Path] = []
        src = self.photorec_work if not self.dry_run else Path("/dev/null")
        if src.exists():
            for f in src.rglob("*"):
                if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS:
                    candidates.append(f)
        else:
            ptprint("  [DRY-RUN] Skipping file collection.",
                    "INFO", condition=self._out())
            self._add_node("validationDedup", True, dryRun=True)
            return True

        ptprint(f"  Candidate image files: {len(candidates)}",
                "INFO", condition=self._out())
        self._s["image_files"] = len(candidates)

        seen_hashes: Set[str] = set()
        counters    = defaultdict(int)

        for idx, fp in enumerate(candidates, 1):
            if idx % 100 == 0:
                ptprint(f"  {idx}/{len(candidates)} …",
                        "INFO", condition=self._out())

            # Deduplication by SHA-256
            try:
                sha    = hashlib.sha256(fp.read_bytes()).hexdigest()
                is_dup = sha in seen_hashes
            except Exception:
                sha    = ""
                is_dup = False

            if is_dup:
                self._s["duplicates"] += 1
                counters["dup"] += 1
                if not self.dry_run:
                    shutil.move(str(fp), str(self.carved_dupes / fp.name))
                continue
            if sha:
                seen_hashes.add(sha)

            # _validate_image_file() is now in ForensicToolBase – no local copy needed
            status, vinfo = self._validate_image_file(fp)
            ext   = fp.suffix.lower().lstrip(".")
            group = FORMAT_GROUP_MAP.get(ext, "other")
            dest_dir = FORMAT_DIR_MAP.get(ext, "other")

            if status == "valid":
                self._s["valid"] += 1
                self._s["by_format"][group] += 1
                counters["valid"] += 1
                dest = self.carved_valid / dest_dir
                if not self.dry_run:
                    dest.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(fp), str(dest / fp.name))
                self._valid_files.append({
                    "filename":   fp.name,
                    "sha256":     sha,
                    "sizeBytes":  vinfo["size"],
                    "format":     vinfo.get("imageFormat"),
                    "dimensions": vinfo.get("dimensions"),
                    "group":      group,
                    "destDir":    dest_dir,
                })
            elif status == "corrupted":
                self._s["corrupted"] += 1
                counters["corrupt"] += 1
                if not self.dry_run:
                    shutil.move(str(fp), str(self.carved_corrupt / fp.name))
            else:
                self._s["invalid"] += 1
                counters["invalid"] += 1
                if not self.dry_run and fp.exists():
                    fp.unlink()

        s = self._s
        ptprint(f"  Total candidates: {s['image_files']}  |  "
                f"Valid: {s['valid']}  |  Corrupted: {s['corrupted']}  |  "
                f"Duplicates: {s['duplicates']}  |  Invalid: {s['invalid']}",
                "OK", condition=self._out())
        for group, count in sorted(s["by_format"].items()):
            ptprint(f"    {group.upper()}: {count}", "INFO", condition=self._out())

        self._add_node("validationDedup", True,
                       imageCandidates=s["image_files"],
                       validImages=s["valid"],
                       corruptedImages=s["corrupted"],
                       duplicates=s["duplicates"],
                       invalidFiles=s["invalid"],
                       byFormat=dict(s["by_format"]))
        return True

    # ------------------------------------------------------------------
    # Run and save
    # ------------------------------------------------------------------

    def run(self) -> None:
        ptprint("=" * 70, "TITLE", condition=self._out())
        ptprint(f"FILE CARVING (PHOTORECOVERY) v{__version__}  |  "
                f"Case: {self.case_id}", "TITLE", condition=self._out())
        if self.dry_run:
            ptprint("MODE: DRY-RUN", "WARNING", condition=self._out())
        ptprint("=" * 70, "TITLE", condition=self._out())

        if not self.load_image():
            self.ptjsonlib.set_status("finished"); return
        if not self.check_tools():
            self.ptjsonlib.set_status("finished"); return
        if not self.run_photorec():
            self.ptjsonlib.set_status("finished"); return
        self.validate_and_deduplicate()

        s            = self._s
        success_rate = (round(s["valid"] / max(s["image_files"], 1) * 100, 1)
                        if s["image_files"] else None)

        self.ptjsonlib.add_properties({
            "compliance":        ["NIST SP 800-86", "ISO/IEC 27037:2012"],
            "method":            "file_carving",
            "carvingTool":       "photorec",
            "totalCarvedFiles":  s["carved"],
            "imageCandidates":   s["image_files"],
            "validImages":       s["valid"],
            "corruptedImages":   s["corrupted"],
            "duplicates":        s["duplicates"],
            "invalidFiles":      s["invalid"],
            "byFormat":          dict(s["by_format"]),
            "successRate":       success_rate,
            "outputDir":         str(self.carved_out),
        })
        self.ptjsonlib.add_node(self.ptjsonlib.create_node_object(
            "chainOfCustodyEntry",
            properties={
                "action":    f"File carving complete – {s['valid']} valid images",
                "result":    "SUCCESS" if s["valid"] > 0 else "NO_FILES",
                "analyst":   self.analyst,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "tool":      "photorec",
            }
        ))

        ptprint("\n" + "=" * 70, "TITLE", condition=self._out())
        ptprint("FILE CARVING COMPLETE", "OK", condition=self._out())
        ptprint(f"Carved: {s['carved']}  |  Valid images: {s['valid']}  |  "
                f"Corrupted: {s['corrupted']}  |  Duplicates: {s['duplicates']}",
                "INFO", condition=self._out())
        if success_rate is not None:
            ptprint(f"Success rate: {success_rate}%", "OK", condition=self._out())
        ptprint("Next: Recovery Consolidation", "INFO", condition=self._out())
        ptprint("=" * 70, "TITLE", condition=self._out())
        self.ptjsonlib.set_status("finished")

    def save_report(self) -> Optional[str]:
        if self.args.json:
            ptprint(self.ptjsonlib.get_result_json(), "", self.args.json)
            return None

        json_file = (Path(self.args.json_out) if self.args.json_out
                     else self.output_dir / f"{self.case_id}_carving_report.json")
        report = {
            "result":      json.loads(self.ptjsonlib.get_result_json()),
            "validFiles":  self._valid_files,
            "directories": {
                "valid":      str(self.carved_valid),
                "corrupted":  str(self.carved_corrupt),
                "duplicates": str(self.carved_dupes),
            },
        }
        json_file.write_text(
            json.dumps(report, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8")
        ptprint(f"JSON report: {json_file.name}", "OK", condition=self._out())
        return str(json_file)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def get_help() -> List[Dict]:
    return [
        {"description": [
            "Forensic file carving tool – ptlibs compliant",
            "Recovers image files using PhotoRec (testdisk package)",
            "Post-carving: extension filter + ImageMagick validation + SHA-256 dedup",
            "Compliant with NIST SP 800-86 and ISO/IEC 27037:2012",
        ]},
        {"usage": ["ptfilecarving <case-id> [options]"]},
        {"usage_example": [
            "ptfilecarving PHOTORECOVERY-2025-01-26-001",
            "ptfilecarving CASE-001 --image /var/forensics/images/CASE-001.dd",
            "ptfilecarving CASE-001 --dry-run --json-out carving.json",
        ]},
        {"options": [
            ["case-id",            "",      "Forensic case identifier – REQUIRED"],
            ["--image",            "<f>",   "Path to forensic image (overrides analysis file)"],
            ["--analysis-file",    "<f>",   "Path to filesystem_analysis.json"],
            ["-o", "--output-dir", "<dir>", f"Output directory (default: {DEFAULT_OUTPUT_DIR})"],
            ["-a", "--analyst",    "<n>",   "Analyst name"],
            ["-j", "--json-out",   "<f>",   "Save JSON report to file"],
            ["-q", "--quiet",      "",      "Suppress terminal output"],
            ["--dry-run",          "",      "Simulate without running PhotoRec"],
            ["-h", "--help",       "",      "Show help"],
            ["--version",          "",      "Show version"],
        ]},
        {"notes": [
            "Requires: photorec (sudo apt install testdisk)",
            "Requires: identify (sudo apt install imagemagick)",
            "Output: carved/valid/<format>/ | carved/corrupted/ | carved/duplicates/",
            "NOTE: PhotoRec recovers all file types; image filter applied post-carving",
            "NOTE: Original filenames are not preserved by PhotoRec",
        ]},
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("case_id")
    parser.add_argument("--image",         default=None)
    parser.add_argument("--analysis-file", default=None)
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
        tool = PtFileCarving(args)
        tool.run()
        tool.save_report()
        props = json.loads(tool.ptjsonlib.get_result_json())["result"]["properties"]
        return 0 if props.get("validImages", 0) > 0 else 1
    except KeyboardInterrupt:
        ptprint("Interrupted by user.", "WARNING", condition=True)
        return 130
    except Exception as exc:
        ptprint(f"ERROR: {exc}", "ERROR", condition=True)
        return 99


if __name__ == "__main__":
    sys.exit(main())