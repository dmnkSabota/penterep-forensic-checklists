#!/usr/bin/env python3
"""
    Copyright (c) 2025 Bc. Dominik Sabota, VUT FIT Brno

    ptmediareadability - Forensic media readability diagnostic

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License.
    See <https://www.gnu.org/licenses/> for details.
"""

import argparse
import json
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ._version import __version__
from .ptforensictoolbase import ForensicToolBase
from ptlibs import ptjsonlib, ptprinthelper
from ptlibs.ptprinthelper import ptprint


def _custom_sigint_handler(sig, frame):
    raise KeyboardInterrupt


signal.signal(signal.SIGINT, _custom_sigint_handler)

SCRIPTNAME = "ptmediareadability"


class PtMediaReadability(ForensicToolBase):
    """
    On-site media readability diagnostic – ptlibs compliant.

    Runs pre-detection (lsblk, blkid, smartctl, hdparm, mdadm) followed by
    four read tests and classifies the medium as READABLE, PARTIAL, or
    UNREADABLE. All operations are strictly read-only.
    """

    def __init__(self, args: argparse.Namespace) -> None:
        self.ptjsonlib  = ptjsonlib.PtJsonLib()
        self.args       = args
        self.case_id    = args.case_id.strip()
        self.analyst    = args.analyst
        self.dry_run    = args.dry_run
        self.device     = args.device

        self.detection_results: Dict = {}
        self.diagnostic_tests:  List = []
        self.critical_findings: List = []
        self.stats = {"testsRun": 0, "testsPassed": 0, "testsFailed": 0}

        self.media_status:     str           = "UNKNOWN"
        self.recommended_tool: Optional[str] = None
        self.next_step:        Optional[int] = None

        if not self.dry_run:
            if not self.device.startswith("/dev/"):
                self._abort(f"Invalid device path: {self.device}")
            if not os.path.exists(self.device):
                self._abort(f"Device not found: {self.device}")

        self.ptjsonlib.add_properties({
            "caseId":        self.case_id,
            "analyst":       self.analyst,
            "timestamp":     datetime.now(timezone.utc).isoformat(),
            "scriptVersion": __version__,
            "devicePath":    self.device,
            "dryRun":        self.dry_run,
        })

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _abort(self, msg: str) -> None:
        """Hard stop for init-time argument errors."""
        ptprint(f"\nERROR: {msg}", "ERROR", condition=True, colortext=True)
        sys.exit(1)

    def _size(self) -> int:
        """Return device size in bytes, or 0 if unavailable."""
        for cmd in [
            ["blockdev", "--getsize64", self.device],
            ["lsblk", "-b", "-d", "-n", "-o", "SIZE", self.device],
        ]:
            r = self._run_command(cmd, timeout=5)
            if r["success"] and r["stdout"].isdigit():
                return int(r["stdout"])
        return 0

    @staticmethod
    def confirm_write_blocker() -> bool:
        """Interactive write-blocker confirmation required before any test."""
        ptprint("\n" + "!" * 70, "WARNING", condition=True)
        ptprint("CRITICAL: WRITE-BLOCKER MUST BE CONNECTED",
                "WARNING", condition=True, colortext=True)
        ptprint("!" * 70, "WARNING", condition=True)
        for line in [
            "  1. Hardware write-blocker is physically connected",
            "  2. LED indicator shows PROTECTED",
            "  3. No unusual sounds from the drive",
            "  4. Media connected THROUGH the write-blocker",
        ]:
            ptprint(line, "TEXT", condition=True)

        while True:
            resp = input("\nConfirm write-blocker is active [y/N]: ").strip().lower()
            if resp in ("y", "yes"):   ok = True;  break
            if resp in ("n", "no", ""): ok = False; break
            ptprint("Please enter 'y' or 'n'.", "WARNING", condition=True)

        sym = "✓" * 70 if ok else "✗" * 70
        lv  = "OK" if ok else "ERROR"
        ptprint("\n" + sym, lv, condition=True)
        ptprint("CONFIRMED – proceeding" if ok
                else "NOT CONFIRMED – test ABORTED",
                lv, condition=True, colortext=True)
        ptprint(sym, lv, condition=True)
        return ok

    # ------------------------------------------------------------------
    # Phase 0 – pre-detection
    # ------------------------------------------------------------------

    def pre_detect(self) -> bool:
        ptprint("\n" + "=" * 70, "TITLE", condition=self._out())
        ptprint("PHASE 0: Pre-Detection", "TITLE", condition=self._out())
        ptprint("=" * 70,                "TITLE", condition=self._out())

        # lsblk
        ptprint("\n[0a] lsblk – device detection", "SUBTITLE", condition=self._out())
        if not self._check_command("lsblk"):
            self.detection_results["lsblk"] = {"error": "command not found"}
            ptprint("✗ lsblk not installed", "ERROR", condition=self._out())
            return self._fail("preDetection", "lsblk not found")

        r = self._run_command(
            ["lsblk", "-d", "-o", "NAME,SIZE,TYPE,MODEL,SERIAL,TRAN",
             self.device])
        if not r["success"] and not self.dry_run:
            self.detection_results["lsblk"] = {"visible": False,
                                                "error": r["stderr"]}
            return self._fail("preDetection",
                              f"Device not detected: {r['stderr']}")

        lsblk_out = r["stdout"] if r["stdout"] else "(dry-run)"
        ptprint(f"✓ Device detected:\n{lsblk_out}", "OK", condition=self._out())
        size = self._size()
        if size:
            ptprint(f"  Size: {size:,} bytes ({size / (1024**3):.2f} GB)",
                    "TEXT", condition=self._out())
        self.detection_results["lsblk"] = {
            "visible": True, "output": lsblk_out, "sizeBytes": size}

        # blkid – filesystem and encryption
        ptprint("\n[0b] blkid – filesystem & encryption",
                "SUBTITLE", condition=self._out())
        if self._check_command("blkid"):
            r   = self._run_command(["blkid", self.device])
            out = r["stdout"] or r["stderr"] or "(no response)"
            enc = None
            ol  = out.lower()
            if   "crypto_luks" in ol: enc = "LUKS"
            elif "bitlocker"   in ol: enc = "BitLocker"
            elif "veracrypt"   in ol: enc = "VeraCrypt"
            if enc:
                self.critical_findings.append(
                    f"Encryption detected: {enc} – recovery key required")
                ptprint(f"⚠  ENCRYPTION: {enc} detected!",
                        "WARNING", condition=self._out(), colortext=True)
                ptprint("    Recovery key/password REQUIRED for data access",
                        "WARNING", condition=self._out())
            else:
                ptprint(f"✓ {out}", "OK", condition=self._out())
            self.detection_results["blkid"] = {
                "output": out, "encrypted": bool(enc), "encryptionType": enc}
        else:
            ptprint("⚠ blkid not available", "WARNING", condition=self._out())
            self.detection_results["blkid"] = {"error": "command not found"}

        # smartctl – SMART health
        ptprint("\n[0c] smartctl – SMART health", "SUBTITLE", condition=self._out())
        if self._check_command("smartctl"):
            r     = self._run_command(["smartctl", "-a", self.device])
            avail = r["success"] or "SMART support" in r["stdout"]
            warns: List[str] = []
            if avail and r["stdout"]:
                checks = {
                    "reallocated_sector":     ("Reallocated_Sector_Ct",  ">50", 50),
                    "current_pending_sector": ("Current_Pending_Sector", ">0",  0),
                    "uncorrectable":          ("Offline_Uncorrectable",  ">0",  0),
                }
                for line in r["stdout"].splitlines():
                    ll, parts = line.lower(), line.split()
                    for kw, (label, thresh, limit) in checks.items():
                        if kw in ll:
                            for x in parts:
                                if x.isdigit() and int(x) > limit:
                                    warns.append(f"{label} = {x} ({thresh})")
            if warns:
                for w in warns:
                    self.critical_findings.append(f"SMART: {w}")
                    ptprint(f"⚠  SMART WARNING: {w}", "WARNING",
                            condition=self._out())
            else:
                ptprint("✓ SMART data OK" if avail
                        else "✓ Not SMART-capable (normal for flash media)",
                        "OK", condition=self._out())
            self.detection_results["smartctl"] = {
                "smartAvailable": avail, "smartWarnings": warns}
        else:
            ptprint("⚠ smartctl not available", "WARNING", condition=self._out())
            self.detection_results["smartctl"] = {"error": "command not found"}

        # hdparm – TRIM
        ptprint("\n[0d] hdparm – TRIM detection", "SUBTITLE", condition=self._out())
        if self._check_command("hdparm"):
            r    = self._run_command(["hdparm", "-I", self.device])
            trim = any(
                "trim" in line and "supported" in line
                and not line.strip().startswith("*")
                for line in r["stdout"].lower().splitlines()
            )
            if trim:
                self.critical_findings.append(
                    "TRIM active – deleted data may be physically erased")
                ptprint("⚠  TRIM ACTIVE!", "WARNING",
                        condition=self._out(), colortext=True)
                ptprint("    Recovery may be INCOMPLETE – deleted data "
                        "physically removed", "WARNING", condition=self._out())
            else:
                ptprint("✓ TRIM not active or not supported",
                        "OK", condition=self._out())
            self.detection_results["hdparm"] = {"trimActive": trim}
        else:
            ptprint("⚠ hdparm not available", "WARNING", condition=self._out())
            self.detection_results["hdparm"] = {"error": "command not found"}

        # mdadm – RAID membership
        ptprint("\n[0e] mdadm – RAID configuration", "SUBTITLE", condition=self._out())
        if self._check_command("mdadm"):
            r       = self._run_command(["mdadm", "--examine", self.device])
            is_raid = ("MD_LEVEL" in r["stdout"] or "ARRAY" in r["stdout"]
                       or "magic" in r["stdout"].lower())
            if is_raid:
                self.critical_findings.append(
                    "RAID member – full array required for recovery")
                ptprint("⚠  RAID MEMBER DETECTED!", "WARNING",
                        condition=self._out(), colortext=True)
                ptprint("    Full RAID array required for complete recovery",
                        "WARNING", condition=self._out())
            else:
                ptprint("✓ Not a RAID member", "OK", condition=self._out())
            self.detection_results["mdadm"] = {
                "isRaidMember": is_raid,
                "raidInfo": r["stdout"] if is_raid else None}
        else:
            ptprint("⚠ mdadm not available", "WARNING", condition=self._out())
            self.detection_results["mdadm"] = {"error": "command not found"}

        self._add_node("preDetection", True,
                       criticalFindings=len(self.critical_findings),
                       detectionResults=self.detection_results)
        return True

    # ------------------------------------------------------------------
    # Phase 1 – read tests
    # ------------------------------------------------------------------

    def tests(self) -> bool:
        ptprint("\n" + "=" * 70, "TITLE", condition=self._out())
        ptprint("PHASE 1: Diagnostic Tests", "TITLE", condition=self._out())
        ptprint("=" * 70,                   "TITLE", condition=self._out())

        def _record(test_id, name, ok, extra=None):
            entry = {"testId": test_id, "testName": name, "success": ok}
            if extra:
                entry.update(extra)
            self.diagnostic_tests.append(entry)
            if ok: self.stats["testsPassed"] += 1
            else:  self.stats["testsFailed"] += 1
            self.stats["testsRun"] += 1
            return ok

        # Test 1 – first sector (512 B)
        ptprint("\nTest 1/4: First Sector (512 B)", "SUBTITLE", condition=self._out())
        r = self._run_command(
            ["dd", f"if={self.device}", "of=/dev/null",
             "bs=512", "count=1", "status=none"])
        if r["success"]:
            ptprint("✓ First sector readable", "OK", condition=self._out())
        else:
            ptprint("✗ CRITICAL: First sector FAILED – media UNREADABLE",
                    "ERROR", condition=self._out(), colortext=True)
        _record(1, "First Sector", r["success"],
                {"bytesRead": 512 if r["success"] else 0})
        if not r["success"] and not self.dry_run:
            return False

        # Test 2 – sequential 1 MB
        ptprint("\nTest 2/4: Sequential Read (1 MB)", "SUBTITLE", condition=self._out())
        r   = self._run_command(
            ["dd", f"if={self.device}", "of=/dev/null",
             "bs=512", "count=2048", "status=none"], timeout=60)
        seq = r["success"]
        ptprint("✓ Sequential read OK" if r["success"]
                else "✗ Sequential read FAILED",
                "OK" if r["success"] else "ERROR", condition=self._out())
        _record(2, "Sequential Read 1 MB", r["success"],
                {"bytesRead": 1_048_576 if r["success"] else 0})

        # Test 3 – random three positions
        ptprint("\nTest 3/4: Random Read (3 positions)",
                "SUBTITLE", condition=self._out())
        sz  = self._size()
        pos = (
            [("start", 2048), ("middle", sz // 2), ("end", sz - 10 * 1_048_576)]
            if sz > 100 * 1_048_576
            else [("start", 2048), ("middle", 1_048_576), ("end", 10 * 1_048_576)]
        )
        results, all_ok = [], True
        for lbl, off in pos:
            r = self._run_command(
                ["dd", f"if={self.device}", "of=/dev/null",
                 "bs=512", "count=1", f"skip={off // 512}", "status=none"])
            results.append({"position": lbl, "offsetBytes": off,
                             "success": r["success"]})
            ptprint(f"  {'✓' if r['success'] else '✗'} {lbl.capitalize()}",
                    "OK" if r["success"] else "ERROR", condition=self._out())
            if not r["success"]:
                all_ok = False
        _record(3, "Random Read", all_ok, {
            "positions":       results,
            "successfulReads": sum(1 for x in results if x["success"]),
            "totalReads":      len(results),
        })

        # Test 4 – read speed (10 MB); skipped if sequential failed
        if seq or self.dry_run:
            ptprint("\nTest 4/4: Read Speed (10 MB)", "SUBTITLE", condition=self._out())
            t0  = time.time()
            r   = self._run_command(
                ["dd", f"if={self.device}", "of=/dev/null",
                 "bs=512", "count=20480", "status=progress"], timeout=120)
            dur = time.time() - t0
            spd = (10 / dur) if r["success"] and dur > 0 else 0.0
            if r["success"]:
                if spd >= 20:  tag, lv = "GOOD",           "OK"
                elif spd >= 5: tag, lv = "ACCEPTABLE",     "WARNING"
                else:
                    tag, lv = "CRITICALLY LOW", "ERROR"
                    self.critical_findings.append(
                        f"Low read speed: {spd:.1f} MB/s (<5 MB/s)")
                ptprint(f"✓ Speed: {spd:.1f} MB/s ({tag})",
                        lv, condition=self._out())
                if spd < 5:
                    ptprint("    WARNING: Imaging will be very slow or may fail",
                            "WARNING", condition=self._out())
            else:
                tag = "FAILED"
                ptprint("✗ Speed test FAILED", "ERROR", condition=self._out())
            _record(4, "Read Speed", r["success"],
                    {"speedMBps": round(spd, 2), "speedStatus": tag})
        else:
            ptprint("\nTest 4/4: Speed – SKIPPED "
                    "(sequential read failed, medium is PARTIAL)",
                    "WARNING", condition=self._out())

        self._add_node("diagnosticTests", True,
                       testsRun=self.stats["testsRun"],
                       testsPassed=self.stats["testsPassed"],
                       testsFailed=self.stats["testsFailed"],
                       tests=self.diagnostic_tests)
        return True

    # ------------------------------------------------------------------
    # Classification and summary
    # ------------------------------------------------------------------

    def classify(self) -> None:
        t = {test["testId"]: test["success"] for test in self.diagnostic_tests}
        if not t.get(1):
            self.media_status, self.recommended_tool, self.next_step = (
                "UNREADABLE", "Physical repair required", 4)
        elif all(t.values()):
            self.media_status, self.recommended_tool, self.next_step = (
                "READABLE", "dc3dd", 5)
        elif t.get(2):
            self.media_status, self.recommended_tool, self.next_step = (
                "PARTIAL", "ddrescue", 5)
        else:
            self.media_status, self.recommended_tool, self.next_step = (
                "UNREADABLE", "Physical repair required", 4)

        self._add_node("readabilityClassification", True,
                       mediaStatus=self.media_status,
                       recommendedTool=self.recommended_tool,
                       nextStep=self.next_step)

    def _print_summary(self) -> None:
        ptprint("\n" + "=" * 70, "TITLE", condition=self._out())
        ptprint("SUMMARY",       "TITLE", condition=self._out())
        ptprint("=" * 70,        "TITLE", condition=self._out())
        ptprint(f"Device:           {self.device}",
                "TEXT", condition=self._out())
        ptprint(f"Case:             {self.case_id}",
                "TEXT", condition=self._out())
        ptprint(f"Media status:     {self.media_status}",
                "TEXT", condition=self._out())
        ptprint(f"Recommended tool: {self.recommended_tool}",
                "TEXT", condition=self._out())
        ptprint(f"Tests:            "
                f"{self.stats['testsPassed']}/{self.stats['testsRun']} passed",
                "TEXT", condition=self._out())
        if self.critical_findings:
            ptprint(f"\n⚠  CRITICAL FINDINGS ({len(self.critical_findings)}):",
                    "WARNING", colortext=True, condition=self._out())
            ptprint("   INFORM CLIENT BEFORE PROCEEDING:",
                    "WARNING", condition=self._out())
            for c in self.critical_findings:
                ptprint(f"   • {c}", "WARNING", condition=self._out())
        ptprint("=" * 70, "TITLE", condition=self._out())

    # ------------------------------------------------------------------
    # Run and save
    # ------------------------------------------------------------------

    def run(self) -> None:
        ptprint("=" * 70, "TITLE", condition=self._out())
        ptprint(f"MEDIA READABILITY TEST v{__version__}  |  "
                f"Case: {self.case_id}", "TITLE", condition=self._out())
        if self.dry_run:
            ptprint("MODE: DRY-RUN", "WARNING", condition=self._out())
        ptprint("=" * 70, "TITLE", condition=self._out())

        if not self.pre_detect() and not self.dry_run:
            self.media_status, self.recommended_tool, self.next_step = (
                "UNREADABLE", "Physical repair required", 4)
        else:
            self.tests()
            self.classify()
            if not self.dry_run:
                self._print_summary()

        self.ptjsonlib.add_properties({
            "compliance":       ["NIST SP 800-86", "ISO/IEC 27037:2012"],
            "mediaStatus":      self.media_status,
            "recommendedTool":  self.recommended_tool,
            "nextStep":         self.next_step,
            "testsRun":         self.stats["testsRun"],
            "testsPassed":      self.stats["testsPassed"],
            "testsFailed":      self.stats["testsFailed"],
            "criticalFindings": self.critical_findings,
        })
        self.ptjsonlib.add_node(self.ptjsonlib.create_node_object(
            "chainOfCustodyEntry",
            properties={
                "action":       (f"Media readability test – "
                                 f"result: {self.media_status}"),
                "result":       ("SUCCESS"
                                 if self.media_status in ("READABLE", "PARTIAL")
                                 else "UNREADABLE"),
                "analyst":      self.analyst,
                "timestamp":    datetime.now(timezone.utc).isoformat(),
                "selectedTool": self.recommended_tool,
            }
        ))
        self.ptjsonlib.set_status("finished")

    def save_report(self) -> Optional[str]:
        if self.args.json:
            ptprint(self.ptjsonlib.get_result_json(), "", self.args.json)
            return None

        if not self.args.json_out:
            return None

        out = Path(self.args.json_out)
        out.write_text(
            json.dumps({"result": json.loads(self.ptjsonlib.get_result_json())},
                       indent=2, ensure_ascii=False),
            encoding="utf-8")
        ptprint(f"\n✓ JSON saved: {out}", "OK", condition=True)
        return str(out)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def get_help() -> List[Dict]:
    return [
        {"description": [
            "Forensic media readability diagnostic – ptlibs compliant",
            "Classifies media as READABLE / PARTIAL / UNREADABLE via read-only tests",
            "Compliant with NIST SP 800-86 and ISO/IEC 27037:2012",
            "",
            "⚠  WRITE-BLOCKER IS ALWAYS REQUIRED – confirmed at every run",
        ]},
        {"usage": ["ptmediareadability <device> <case-id> [options]"]},
        {"usage_example": [
            "ptmediareadability /dev/sdb PHOTORECOVERY-2025-01-26-001",
            "ptmediareadability /dev/sdb CASE-001 --analyst 'John Doe'",
            "ptmediareadability /dev/sdc CASE-002 --json-out result.json",
        ]},
        {"options": [
            ["device",           "",     "Device path (e.g., /dev/sdb) – REQUIRED"],
            ["case-id",          "",     "Case identifier – REQUIRED"],
            ["-a", "--analyst",  "<n>",  "Analyst name (default: Analyst)"],
            ["-j", "--json-out", "<f>",  "Save JSON report to file"],
            ["-q", "--quiet",    "",     "Suppress terminal output"],
            ["--dry-run",        "",     "Simulate without accessing the device"],
            ["-h", "--help",     "",     "Show help"],
            ["--version",        "",     "Show version"],
        ]},
        {"notes": [
            "Exit 0 = READABLE | Exit 1 = PARTIAL | "
            "Exit 2 = UNREADABLE | Exit 99 = error",
            "All operations are READ-ONLY",
            "Compliant with NIST SP 800-86 and ISO/IEC 27037:2012",
        ]},
    ]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("device")
    p.add_argument("case_id")
    p.add_argument("-a", "--analyst",  default="Analyst")
    p.add_argument("-j", "--json-out", default=None)
    p.add_argument("-q", "--quiet",    action="store_true")
    p.add_argument("--dry-run",        action="store_true")
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
            if not PtMediaReadability.confirm_write_blocker():
                ptprint("\nTest ABORTED – write-blocker is REQUIRED!",
                        "ERROR", condition=True, colortext=True)
                return 99

        tool = PtMediaReadability(args)
        tool.run()
        tool.save_report()

        props  = json.loads(tool.ptjsonlib.get_result_json())["result"]["properties"]
        status = props.get("mediaStatus", "UNKNOWN")
        return {"READABLE": 0, "PARTIAL": 1, "UNREADABLE": 2}.get(status, 99)

    except KeyboardInterrupt:
        ptprint("\nInterrupted by user.", "WARNING", condition=True)
        return 130
    except Exception as exc:
        ptprint(f"\nERROR: {exc}", "ERROR", condition=True, colortext=True)
        return 99


if __name__ == "__main__":
    sys.exit(main())