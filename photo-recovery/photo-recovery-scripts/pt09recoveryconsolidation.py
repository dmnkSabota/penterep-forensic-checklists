#!/usr/bin/env python3
"""
    Copyright (c) 2026 Bc. Dominik Sabota, VUT FIT Brno

    ptrecoveryconsolidation - Consolidation of filesystem and carving results

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License.
    See <https://www.gnu.org/licenses/> for details.
"""

# LAST CHANGES:
#   - IMAGE_EXTENSIONS, FORMAT_GROUP_MAP replaced with imports from _constants
#   - Changed --json boolean flag to --json-out <file> for consistency
#
# NOTE (thesis design decision):
#   This step merges outputs of Step 8a (filesystem recovery) and Step 8b
#   (file carving) with deduplication by SHA-256. Filesystem-recovered files
#   take priority over carved files of the same content because they retain
#   original metadata (filename, path, timestamps). This step exists as a
#   separate explicit stage to provide a clear Chain of Custody record of
#   what entered the analysis pipeline, which is forensically important.

import argparse
import hashlib
import json
import shutil
import signal
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from ._version import __version__
from ._constants import IMAGE_EXTENSIONS, FORMAT_GROUP_MAP
from .ptforensictoolbase import ForensicToolBase
from ptlibs import ptjsonlib, ptprinthelper
from ptlibs.ptprinthelper import ptprint


def _custom_sigint_handler(sig, frame):
    raise KeyboardInterrupt


signal.signal(signal.SIGINT, _custom_sigint_handler)

SCRIPTNAME         = "ptrecoveryconsolidation"
DEFAULT_OUTPUT_DIR = "/var/forensics/images"


class PtRecoveryConsolidation(ForensicToolBase):
    """
    Merges output from filesystem recovery (Step 8a) and file carving (Step 8b)
    into a single deduplicated collection. Filesystem-recovered files take
    priority over carved files of the same SHA-256 (they retain metadata).
    """

    def __init__(self, args: argparse.Namespace) -> None:
        self.ptjsonlib  = ptjsonlib.PtJsonLib()
        self.args       = args
        self.case_id    = args.case_id.strip()
        self.analyst    = getattr(args, "analyst", "Analyst")
        self.dry_run    = args.dry_run
        self.output_dir = Path(args.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Input directories (from previous steps)
        self.fs_recovery_dir = self.output_dir / f"{self.case_id}_recovered"
        self.carved_dir      = self.output_dir / f"{self.case_id}_carved" / "valid"

        # Output directory
        self.consolidated_dir = self.output_dir / f"{self.case_id}_consolidated"

        self._s: Dict[str, Any] = {
            "from_fs":        0,
            "from_carving":   0,
            "deduplicated":   0,
            "total":          0,
            "by_format":      defaultdict(int),
        }
        self._consolidated_files: List[Dict] = []

        self.ptjsonlib.add_properties({
            "caseId":        self.case_id,
            "analyst":       self.analyst,
            "timestamp":     datetime.now(timezone.utc).isoformat(),
            "scriptVersion": __version__,
            "dryRun":        self.dry_run,
        })

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _sha256(path: Path) -> Optional[str]:
        try:
            h = hashlib.sha256()
            with open(path, "rb") as fh:
                for chunk in iter(lambda: fh.read(4 * 1024 * 1024), b""):
                    h.update(chunk)
            return h.hexdigest()
        except Exception:
            return None

    def _collect_dir(self, base: Path, label: str) -> List[Dict]:
        """
        Recursively collect image files from a directory.
        Returns list of {'path': Path, 'sha256': str, 'source': label} dicts.
        """
        if not base.exists():
            ptprint(f"  Directory not found (skip): {base.name}",
                    "WARNING", condition=self._out())
            return []

        files  = [f for f in base.rglob("*")
                  if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS]
        ptprint(f"  {label}: {len(files)} image file(s) in {base.name}",
                "INFO", condition=self._out())

        result = []
        for f in files:
            sha = self._sha256(f)
            result.append({"path": f, "sha256": sha, "source": label})
        return result

    # ------------------------------------------------------------------
    # Phases
    # ------------------------------------------------------------------

    def consolidate(self) -> bool:
        ptprint("\n[1/1] Consolidating recovery results",
                "TITLE", condition=self._out())

        fs_files     = self._collect_dir(self.fs_recovery_dir / "active",  "fs_active")
        fs_files    += self._collect_dir(self.fs_recovery_dir / "deleted", "fs_deleted")
        carved_files = self._collect_dir(self.carved_dir, "carved")

        ptprint(f"\n  FS-recovered: {len(fs_files)}  |  "
                f"Carved: {len(carved_files)}",
                "INFO", condition=self._out())

        if not fs_files and not carved_files:
            ptprint("  No files to consolidate.", "WARNING", condition=self._out())
            self._add_node("consolidation", False, error="No input files found")
            return False

        if not self.dry_run:
            self.consolidated_dir.mkdir(parents=True, exist_ok=True)

        seen_hashes: Set[str] = set()

        def _process(entries: List[Dict]) -> None:
            for entry in entries:
                fp     = entry["path"]
                sha    = entry["sha256"]
                source = entry["source"]
                ext    = fp.suffix.lower()
                group  = FORMAT_GROUP_MAP.get(ext.lstrip("."), "other")

                if sha and sha in seen_hashes:
                    self._s["deduplicated"] += 1
                    continue
                if sha:
                    seen_hashes.add(sha)

                dest_sub = self.consolidated_dir / group
                if not self.dry_run:
                    dest_sub.mkdir(parents=True, exist_ok=True)
                    dest = dest_sub / fp.name
                    # Avoid overwriting if filenames collide
                    if dest.exists():
                        dest = dest_sub / f"{fp.stem}_{sha[:8]}{fp.suffix}"
                    shutil.copy2(str(fp), str(dest))
                else:
                    dest = dest_sub / fp.name

                self._s["total"] += 1
                self._s["by_format"][group] += 1
                if "fs" in source:
                    self._s["from_fs"] += 1
                else:
                    self._s["from_carving"] += 1

                try:
                    st = fp.stat()
                except Exception:
                    st = None

                self._consolidated_files.append({
                    "filename":    fp.name,
                    "sha256":      sha,
                    "source":      source,
                    "group":       group,
                    "sizeBytes":   st.st_size if st else None,
                    "destPath":    str(dest.relative_to(self.consolidated_dir)),
                })

        # FS files first (priority), then carved
        _process(fs_files)
        _process(carved_files)

        s = self._s
        ptprint(f"\n  Consolidated: {s['total']} unique files  |  "
                f"Deduplicated: {s['deduplicated']} duplicates",
                "OK", condition=self._out())
        ptprint(f"  From FS: {s['from_fs']}  |  From carving: {s['from_carving']}",
                "INFO", condition=self._out())
        for fmt, count in sorted(s["by_format"].items()):
            ptprint(f"    {fmt.upper()}: {count}", "INFO", condition=self._out())

        self._add_node("consolidation", True,
                       fromFilesystem=s["from_fs"],
                       fromCarving=s["from_carving"],
                       deduplicated=s["deduplicated"],
                       totalConsolidated=s["total"],
                       byFormat=dict(s["by_format"]))
        return True

    # ------------------------------------------------------------------
    # Run and save
    # ------------------------------------------------------------------

    def run(self) -> None:
        ptprint("=" * 70, "TITLE", condition=self._out())
        ptprint(f"RECOVERY CONSOLIDATION v{__version__}  |  "
                f"Case: {self.case_id}", "TITLE", condition=self._out())
        if self.dry_run:
            ptprint("MODE: DRY-RUN", "WARNING", condition=self._out())
        ptprint("=" * 70, "TITLE", condition=self._out())

        self.consolidate()

        s = self._s
        self.ptjsonlib.add_properties({
            "compliance":         ["NIST SP 800-86", "ISO/IEC 27037:2012"],
            "fromFilesystem":     s["from_fs"],
            "fromCarving":        s["from_carving"],
            "deduplicated":       s["deduplicated"],
            "totalConsolidated":  s["total"],
            "byFormat":           dict(s["by_format"]),
            "consolidatedDir":    str(self.consolidated_dir),
        })
        self.ptjsonlib.add_node(self.ptjsonlib.create_node_object(
            "chainOfCustodyEntry",
            properties={
                "action":    (f"Recovery consolidation complete – "
                              f"{s['total']} unique files "
                              f"({s['deduplicated']} duplicates removed)"),
                "result":    "SUCCESS" if s["total"] > 0 else "NO_FILES",
                "analyst":   self.analyst,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "details":   (f"FS: {s['from_fs']}, "
                              f"Carved: {s['from_carving']}, "
                              f"Deduped: {s['deduplicated']}"),
            }
        ))

        ptprint("\n" + "=" * 70, "TITLE", condition=self._out())
        ptprint("CONSOLIDATION COMPLETE", "OK", condition=self._out())
        ptprint(f"Total: {s['total']}  |  "
                f"FS: {s['from_fs']}  |  "
                f"Carved: {s['from_carving']}  |  "
                f"Deduped: {s['deduplicated']}",
                "INFO", condition=self._out())
        ptprint("Next: Integrity Validation", "INFO", condition=self._out())
        ptprint("=" * 70, "TITLE", condition=self._out())
        self.ptjsonlib.set_status("finished")

    def save_report(self) -> Optional[str]:
        if self.args.json:
            ptprint(self.ptjsonlib.get_result_json(), "", self.args.json)
            return None

        json_file = (Path(self.args.json_out) if self.args.json_out
                     else self.output_dir /
                          f"{self.case_id}_consolidation_report.json")
        report = {
            "result":             json.loads(self.ptjsonlib.get_result_json()),
            "consolidatedFiles":  self._consolidated_files,
            "consolidatedDir":    str(self.consolidated_dir),
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
            "Recovery consolidation – merges filesystem and carving results",
            "Deduplication by SHA-256 with filesystem-recovery priority",
            "Compliant with NIST SP 800-86 and ISO/IEC 27037:2012",
        ]},
        {"usage": ["ptrecoveryconsolidation <case-id> [options]"]},
        {"usage_example": [
            "ptrecoveryconsolidation PHOTORECOVERY-2025-01-26-001",
            "ptrecoveryconsolidation CASE-001 --dry-run",
            "ptrecoveryconsolidation CASE-001 --json-out step9.json",
        ]},
        {"options": [
            ["case-id",            "",      "Forensic case identifier – REQUIRED"],
            ["-o", "--output-dir", "<dir>", f"Output directory (default: {DEFAULT_OUTPUT_DIR})"],
            ["-a", "--analyst",    "<n>",   "Analyst name"],
            ["-j", "--json-out",   "<f>",   "Save JSON report to file"],
            ["-q", "--quiet",      "",      "Suppress terminal output"],
            ["--dry-run",          "",      "Simulate without copying files"],
            ["-h", "--help",       "",      "Show help"],
            ["--version",          "",      "Show version"],
        ]},
        {"notes": [
            "Reads {case_id}_recovered/ (Step 8a) and {case_id}_carved/ (Step 8b)",
            "Output: {case_id}_consolidated/<format_group>/",
            "Filesystem-recovered files take priority over carved duplicates",
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
        tool = PtRecoveryConsolidation(args)
        tool.run()
        tool.save_report()
        props = json.loads(tool.ptjsonlib.get_result_json())["result"]["properties"]
        return 0 if props.get("totalConsolidated", 0) > 0 else 1
    except KeyboardInterrupt:
        ptprint("Interrupted by user.", "WARNING", condition=True)
        return 130
    except Exception as exc:
        ptprint(f"ERROR: {exc}", "ERROR", condition=True)
        return 99


if __name__ == "__main__":
    sys.exit(main())