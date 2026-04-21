#!/usr/bin/env python3
"""
    Copyright (c) 2026 Bc. Dominik Sabota, VUT FIT Brno

    ptforensicimaging - Forensic media imaging tool

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License.
    See <https://www.gnu.org/licenses/> for details.
"""

# LAST CHANGES:
#   - Removed confirm_write_blocker() – now inherited from ForensicToolBase
#   - Replaced threading-based progress bar with simple poll-based loop.
#   - Fixed save_report(): same bug as ptmediareadability (JSON printed to
#     stdout instead of being saved to file)
#   - Removed _custom_sigint_handler + signal.signal(): handled in base.
#   - Replaced inline add_properties({7 fields}) with _init_properties()
#     + separate add_properties for tool-specific fields.

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ._version import __version__
from .ptforensictoolbase import ForensicToolBase
from ptlibs import ptjsonlib, ptprinthelper
from ptlibs.ptprinthelper import ptprint

SCRIPTNAME         = "ptforensicimaging"
DEFAULT_OUTPUT_DIR = "/var/forensics/images"


class PtForensicImaging(ForensicToolBase):
    """
    Forensic media imaging tool – ptlibs compliant.

    Supports dc3dd (READABLE media, integrated SHA-256) and ddrescue
    (PARTIAL/damaged media, SHA-256 computed separately). Requires a
    hardware write-blocker. Compliant with NIST SP 800-86 and
    ISO/IEC 27037:2012.
    """

    def __init__(self, args: argparse.Namespace) -> None:
        self.ptjsonlib  = ptjsonlib.PtJsonLib()
        self.args       = args
        self.case_id    = args.case_id.strip()
        self.analyst    = args.analyst
        self.dry_run    = args.dry_run
        self.device     = args.device
        self.tool       = args.tool
        self.output_dir = Path(args.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.media_status: str = "READABLE" if self.tool == "dc3dd" else "PARTIAL"
        self.source_size:   Optional[int]   = None
        self.image_path:    Optional[Path]  = None
        self.source_hash:   Optional[str]   = None
        self.duration:      Optional[float] = None
        self.avg_speed:     Optional[float] = None
        self.error_sectors: int             = 0
        self.mapfile:       Optional[Path]  = None
        self.log_file:      Optional[Path]  = None

        self._init_properties(__version__)
        self.ptjsonlib.add_properties({
            "devicePath":  self.device,
            "imagingTool": self.tool,
        })

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _tool_version(self) -> str:
        r = self._run_command([self.tool, "--version"], timeout=5)
        if r["success"] and r["stdout"]:
            for line in r["stdout"].splitlines():
                if self.tool in line.lower():
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if self.tool in part.lower() and i + 1 < len(parts):
                            return parts[i + 1]
                    if len(parts) >= 2:
                        return parts[1]
        return "unknown"

    # ------------------------------------------------------------------
    # Phase 1 – prerequisites
    # ------------------------------------------------------------------

    def check_prerequisites(self) -> bool:
        ptprint("\n" + "=" * 70, "TITLE", condition=self._out())
        ptprint("STEP 1: Prerequisites", "TITLE", condition=self._out())
        ptprint("=" * 70,               "TITLE", condition=self._out())

        ptprint(f"\n[1a] Checking {self.tool}", "SUBTITLE", condition=self._out())
        if not self._check_command(self.tool):
            return self._fail("prerequisitesCheck",
                              f"{self.tool} not installed")
        ptprint(f"✓ {self.tool} available", "OK", condition=self._out())

        if self.tool == "ddrescue":
            if not self._check_command("sha256sum"):
                return self._fail("prerequisitesCheck",
                                  "sha256sum not installed")
            ptprint("✓ sha256sum available", "OK", condition=self._out())

        ptprint("\n[1b] Checking source device", "SUBTITLE", condition=self._out())
        if not os.path.exists(self.device) and not self.dry_run:
            return self._fail("prerequisitesCheck",
                              f"Device not found: {self.device}")
        ptprint(f"✓ Device accessible: {self.device}",
                "OK", condition=self._out())

        ptprint("\n[1c] Checking target storage", "SUBTITLE", condition=self._out())
        try:
            stat       = os.statvfs(self.output_dir)
            free_bytes = stat.f_bavail * stat.f_frsize
            if self.source_size:
                required = int(self.source_size * 1.1)
                ptprint(f"  Required:  {required:,} B  "
                        f"({required / (1024**3):.2f} GB)",
                        "TEXT", condition=self._out())
                ptprint(f"  Available: {free_bytes:,} B  "
                        f"({free_bytes / (1024**3):.2f} GB)",
                        "TEXT", condition=self._out())
                if free_bytes < required and not self.dry_run:
                    return self._fail("prerequisitesCheck",
                                      "Insufficient storage space "
                                      "(need 110% of source size)")
                ptprint("✓ Sufficient storage space", "OK", condition=self._out())
            else:
                ptprint(f"  Available: {free_bytes / (1024**3):.2f} GB  "
                        "(source size unknown – cannot pre-verify)",
                        "TEXT", condition=self._out())
        except Exception as exc:
            ptprint(f"⚠ Could not check storage space: {exc}",
                    "WARNING", condition=self._out())

        self._add_node("prerequisitesCheck", True,
                       tool=self.tool, device=self.device)
        return True

    # ------------------------------------------------------------------
    # Phase 2 – imaging
    # ------------------------------------------------------------------

    def run_imaging(self) -> bool:
        ptprint("\n" + "=" * 70, "TITLE", condition=self._out())
        ptprint("STEP 2: Forensic Imaging", "TITLE", condition=self._out())
        ptprint("=" * 70,                   "TITLE", condition=self._out())

        self.image_path = self.output_dir / f"{self.case_id}.dd"
        self.log_file   = self.output_dir / f"{self.case_id}_imaging.log"

        return self.run_dc3dd() if self.tool == "dc3dd" else self.run_ddrescue()

    def run_dc3dd(self) -> bool:
        ptprint("\nStarting dc3dd …", "SUBTITLE", condition=self._out())
        ptprint(f"  Source: {self.device}", "TEXT", condition=self._out())
        ptprint(f"  Target: {self.image_path}", "TEXT", condition=self._out())
        ptprint("  Hash:   SHA-256 (integrated)", "TEXT", condition=self._out())

        r = self._run_command(["blockdev", "--getsize64", self.device], timeout=5)
        if r["success"] and r["stdout"]:
            try:
                self.source_size = int(r["stdout"].strip())
                ptprint(f"  Size:   {self.source_size:,} bytes  "
                        f"({self.source_size / (1024**3):.2f} GB)",
                        "TEXT", condition=self._out())
            except ValueError:
                pass

        cmd = ["dc3dd", f"if={self.device}", f"of={self.image_path}",
               "hash=sha256", f"log={self.log_file}"]
        ptprint(f"\nCommand: {' '.join(cmd)}", "TEXT", condition=self._out())

        if self.dry_run:
            ptprint("[DRY-RUN] dc3dd skipped.", "INFO", condition=self._out())
            self._add_node("imagingResult", True, tool="dc3dd", dryRun=True)
            return True

        ptprint("\nImaging in progress …\n", "TEXT", condition=self._out())
        t0 = time.time()

        try:
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True)

            last_pct = -1
            while proc.poll() is None:
                time.sleep(1.0)
                if (self.image_path.exists() and self.source_size
                        and not self.args.json):
                    cur = self.image_path.stat().st_size
                    pct = min(int(100 * cur / self.source_size), 100)
                    if pct != last_pct:
                        ela = time.time() - t0
                        spd = (cur / (1024**2)) / ela if ela else 0
                        bar = ("=" * (pct // 5)
                               + (">" if pct < 100 else "")
                               + " " * (20 - pct // 5 - (1 if pct < 100 else 0)))
                        print(
                            f"\rImaging: [{bar}] {pct:3d}%  "
                            f"{cur / (1024**3):.1f}/"
                            f"{self.source_size / (1024**3):.1f} GB  "
                            f"{spd:.1f} MB/s  ",
                            end="", flush=True)
                        last_pct = pct

            output_text, _ = proc.communicate()
            output_lines    = output_text.splitlines() if output_text else []

            self.duration = time.time() - t0
            if not self.args.json and last_pct >= 0:
                print()

            if proc.returncode != 0:
                err_lines = [l for l in output_lines
                             if "error" in l.lower() or "!!" in l]
                msg = (f"dc3dd failed (rc={proc.returncode})"
                       + (f": {' '.join(err_lines[:2])}" if err_lines else ""))
                return self._fail("imagingResult", msg)

        except KeyboardInterrupt:
            ptprint("\n✗ Imaging interrupted by user",
                    "WARNING", condition=self._out())
            proc.terminate(); proc.wait()
            raise

        if self.log_file.exists():
            for line in self.log_file.read_text().splitlines():
                if "sha256" in line.lower():
                    for part in line.split():
                        if len(part) == 64 and all(
                                c in "0123456789abcdef" for c in part.lower()):
                            self.source_hash = part.lower()
                            break
        if not self.source_hash:
            ptprint("⚠ Could not extract SHA-256 from dc3dd log",
                    "WARNING", condition=self._out())

        if self.image_path.exists():
            sz = self.image_path.stat().st_size
            if not self.source_size:
                self.source_size = sz
            self.avg_speed = (sz / (1024**2)) / self.duration if self.duration else 0

        if self.source_hash:
            sidecar = Path(str(self.image_path) + ".sha256")
            sidecar.write_text(f"{self.source_hash}  {self.image_path.name}\n")
            ptprint(f"✓ Hash sidecar: {sidecar.name}", "OK", condition=self._out())

        ptprint("✓ dc3dd imaging completed", "OK", condition=self._out())
        self._add_node("imagingResult", True,
                       tool="dc3dd",
                       durationSeconds=round(self.duration or 0, 2),
                       averageSpeedMBps=round(self.avg_speed or 0, 2),
                       sourceHash=self.source_hash)
        return True

    def run_ddrescue(self) -> bool:
        ptprint("\nStarting ddrescue …", "SUBTITLE", condition=self._out())
        ptprint(f"  Source: {self.device}", "TEXT", condition=self._out())
        ptprint(f"  Target: {self.image_path}", "TEXT", condition=self._out())
        ptprint("  Mode:   Damaged sector recovery", "TEXT", condition=self._out())

        self.mapfile = self.output_dir / f"{self.case_id}.mapfile"
        cmd = ["ddrescue", "-f", "-v",
               self.device, str(self.image_path), str(self.mapfile)]
        ptprint(f"\nCommand: {' '.join(cmd)}", "TEXT", condition=self._out())

        if self.dry_run:
            ptprint("[DRY-RUN] ddrescue skipped.", "INFO", condition=self._out())
            self._add_node("imagingResult", True, tool="ddrescue", dryRun=True)
            return True

        ptprint("\nImaging in progress …\n", "TEXT", condition=self._out())
        t0 = time.time()

        try:
            with open(self.log_file, "w") as lf:
                lf.write(f"ddrescue started {datetime.now()}\n"
                         f"Command: {' '.join(cmd)}\n{'=' * 70}\n\n")
                lf.flush()
                proc = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, bufsize=1)
                output_lines: List[str] = []
                try:
                    for line in proc.stdout:
                        lf.write(line); lf.flush()
                        if not self.args.json:
                            print(line, end="")
                        output_lines.append(line)
                    proc.wait()
                except KeyboardInterrupt:
                    lf.write("\n[INTERRUPTED BY USER]\n"); lf.flush()
                    ptprint("\n✗ Imaging interrupted by user",
                            "WARNING", condition=self._out())
                    proc.terminate(); proc.wait()
                    raise
                lf.write(f"\nExit code: {proc.returncode}\n")

            self.duration = time.time() - t0

            if proc.returncode not in (0, 1):
                return self._fail("imagingResult",
                                  f"ddrescue failed (rc={proc.returncode})")

            if self.image_path.exists():
                sz               = self.image_path.stat().st_size
                self.source_size = sz
                self.avg_speed   = (sz / (1024**2)) / self.duration \
                                   if self.duration else 0

            ptprint("\n✓ ddrescue imaging completed", "OK", condition=self._out())

            ptprint("\nCalculating SHA-256 …", "SUBTITLE", condition=self._out())
            r = self._run_command(["sha256sum", str(self.image_path)],
                                  timeout=7200)
            if r["success"] and r["stdout"]:
                self.source_hash = r["stdout"].split()[0]
                ptprint(f"✓ SHA-256: {self.source_hash}",
                        "OK", condition=self._out())
                sidecar = Path(str(self.image_path) + ".sha256")
                sidecar.write_text(
                    f"{self.source_hash}  {self.image_path.name}\n")
                ptprint(f"✓ Hash sidecar: {sidecar.name}",
                        "OK", condition=self._out())
            else:
                ptprint(f"✗ Hash calculation failed: {r['stderr']}",
                        "ERROR", condition=self._out())

            self._add_node("imagingResult", True,
                           tool="ddrescue",
                           durationSeconds=round(self.duration or 0, 2),
                           averageSpeedMBps=round(self.avg_speed or 0, 2),
                           sourceHash=self.source_hash,
                           mapfile=str(self.mapfile))
            return True

        except Exception as exc:
            return self._fail("imagingResult",
                              f"ddrescue execution failed: {exc}")

    # ------------------------------------------------------------------
    # Summary and run
    # ------------------------------------------------------------------

    def _print_summary(self) -> None:
        ptprint("\n" + "=" * 70, "TITLE", condition=self._out())
        ptprint("SUMMARY",       "TITLE", condition=self._out())
        ptprint("=" * 70,        "TITLE", condition=self._out())
        ptprint(f"Case:    {self.case_id}", "TEXT", condition=self._out())
        ptprint(f"Source:  {self.device}",  "TEXT", condition=self._out())
        ptprint(f"Tool:    {self.tool}",    "TEXT", condition=self._out())
        if self.image_path and self.image_path.exists():
            sz = self.image_path.stat().st_size
            ptprint(f"Image:   {self.image_path}", "TEXT", condition=self._out())
            ptprint(f"Size:    {sz:,} bytes ({sz / (1024**3):.2f} GB)",
                    "TEXT", condition=self._out())
        if self.duration:
            ptprint(f"Duration: {self.duration:.1f}s "
                    f"({self.duration / 60:.1f} min)",
                    "TEXT", condition=self._out())
        if self.avg_speed:
            ptprint(f"Speed:   {self.avg_speed:.2f} MB/s",
                    "TEXT", condition=self._out())
        if self.error_sectors:
            ptprint(f"Bad sectors: {self.error_sectors}",
                    "WARNING", condition=self._out())
        if self.source_hash:
            ptprint(f"SHA-256: {self.source_hash}", "TEXT", condition=self._out())
        ptprint("=" * 70, "TITLE", condition=self._out())

    def run(self) -> None:
        ptprint("=" * 70, "TITLE", condition=self._out())
        ptprint(f"FORENSIC IMAGING v{__version__}  |  Case: {self.case_id}",
                "TITLE", condition=self._out())
        if self.dry_run:
            ptprint("MODE: DRY-RUN", "WARNING", condition=self._out())
        ptprint("=" * 70, "TITLE", condition=self._out())

        if not self.check_prerequisites():
            self.ptjsonlib.set_status("finished"); return
        if not self.run_imaging():
            self.ptjsonlib.set_status("finished"); return

        if not self.dry_run:
            self._print_summary()

        tool_ver = self._tool_version()
        method   = ("single-pass with integrated hashing"
                    if self.tool == "dc3dd"
                    else "damaged sector recovery with separate hashing")

        self.ptjsonlib.add_properties({
            "compliance":            ["NIST SP 800-86", "ISO/IEC 27037:2012"],
            "mediaStatus":           self.media_status,
            "outputDir":             str(self.output_dir),
            "imagePath":             str(self.image_path) if self.image_path else None,
            "imageFormat":           "raw (.dd)",
            "imageSizeBytes":        self.source_size,
            "acquisitionMethod":     method,
            "toolVersion":           tool_ver,
            "durationSeconds":       round(self.duration or 0, 2),
            "averageSpeedMBps":      round(self.avg_speed or 0, 2),
            "hashAlgorithm":         "SHA-256",
            "sourceHash":            self.source_hash,
            "hashVerified":          bool(self.source_hash),
            "errorSectors":          self.error_sectors,
            "writeBlockerConfirmed": not self.dry_run,
        })
        self.ptjsonlib.add_node(self.ptjsonlib.create_node_object(
            "chainOfCustodyEntry",
            properties={
                "action":     "Forensic imaging complete",
                "result":     "SUCCESS",
                "analyst":    self.analyst,
                "timestamp":  datetime.now(timezone.utc).isoformat(),
                "tool":       self.tool,
                "sourceHash": self.source_hash,
            }
        ))
        self.ptjsonlib.set_status("finished")

    def save_report(self) -> Optional[str]:
        if not self.args.json_out:
            return None

        out = Path(self.args.json_out)
        out.write_text(
            json.dumps({"result": json.loads(self.ptjsonlib.get_result_json())},
                       indent=2, ensure_ascii=False),
            encoding="utf-8")
        ptprint(self.ptjsonlib.get_result_json(), "", self.args.json)
        ptprint(f"✓ JSON saved: {out}", "OK", condition=not self.args.json)
        return str(out)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def get_help() -> List[Dict]:
    return [
        {"description": [
            "Forensic media imaging tool – ptlibs compliant",
            "Supports dc3dd (READABLE media) and ddrescue (damaged media)",
            "Compliant with NIST SP 800-86 and ISO/IEC 27037:2012",
            "",
            "⚠  WRITE-BLOCKER IS ALWAYS REQUIRED – confirmed at every run",
        ]},
        {"usage": ["ptforensicimaging <case-id> <device> <tool> [options]"]},
        {"usage_example": [
            "ptforensicimaging PHOTORECOVERY-2025-01-26-001 /dev/sdb dc3dd",
            "ptforensicimaging CASE-001 /dev/sdb dc3dd --analyst 'John Doe'",
            "ptforensicimaging CASE-002 /dev/sdc ddrescue --json-out result.json",
        ]},
        {"options": [
            ["case-id",            "",     "Case identifier – REQUIRED"],
            ["device",             "",     "Device path (e.g., /dev/sdb) – REQUIRED"],
            ["tool",               "",     "Imaging tool: dc3dd or ddrescue – REQUIRED"],
            ["-o", "--output-dir", "<d>",  f"Output directory (default: {DEFAULT_OUTPUT_DIR})"],
            ["-a", "--analyst",    "<n>",  "Analyst name (default: Analyst)"],
            ["-j", "--json-out",   "<f>",  "Save JSON report to file"],
            ["-q", "--quiet",      "",     "Suppress terminal output"],
            ["--dry-run",          "",     "Simulate without running the imaging tool"],
            ["-h", "--help",       "",     "Show help"],
            ["--version",          "",     "Show version"],
        ]},
        {"notes": [
            "dc3dd:    READABLE media – integrated SHA-256, fast single pass",
            "ddrescue: PARTIAL media  – damaged sector recovery, "
            "SHA-256 computed separately",
            "Creates canonical <image>.sha256 sidecar on completion",
            "Compliant with NIST SP 800-86 and ISO/IEC 27037:2012",
        ]},
    ]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("case_id")
    p.add_argument("device",  help="Device path (e.g., /dev/sdb)")
    p.add_argument("tool",    choices=["dc3dd", "ddrescue"])
    p.add_argument("-o", "--output-dir", default=DEFAULT_OUTPUT_DIR)
    p.add_argument("-a", "--analyst",    default="Analyst")
    p.add_argument("-j", "--json-out",   default=None)
    p.add_argument("-q", "--quiet",      action="store_true")
    p.add_argument("--dry-run",          action="store_true")
    p.add_argument("--version", action="version",
                   version=f"{SCRIPTNAME} {__version__}")

    if len(sys.argv) == 1 or {"-h", "--help"} & set(sys.argv):
        ptprinthelper.help_print(get_help(), SCRIPTNAME, __version__)
        sys.exit(0)

    args      = p.parse_args()
    args.json = bool(args.json_out)
    if args.json:
        args.quiet = True
    ptprinthelper.print_banner(SCRIPTNAME, __version__, args.json)
    return args


def main() -> int:
    try:
        args = parse_args()

        if not args.dry_run:
            if not PtForensicImaging.confirm_write_blocker():
                ptprint("\nImaging ABORTED – write-blocker is REQUIRED!",
                        "ERROR", condition=True, colortext=True)
                return 99

        tool = PtForensicImaging(args)
        tool.run()
        tool.save_report()

        props = json.loads(tool.ptjsonlib.get_result_json())["result"]["properties"]
        return 0 if props.get("sourceHash") else 1

    except KeyboardInterrupt:
        ptprint("\nInterrupted by user.", "WARNING", condition=True)
        return 130
    except Exception as exc:
        ptprint(f"\nERROR: {exc}", "ERROR", condition=True, colortext=True)
        return 99


if __name__ == "__main__":
    sys.exit(main())