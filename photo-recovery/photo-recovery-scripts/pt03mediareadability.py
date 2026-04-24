#!/usr/bin/env python3
"""
    Copyright (c) 2026 Bc. Dominik Sabota, VUT FEKT Brno
    
    ptmediareadability - Forensic media readability diagnostic
    License: GNU GPL v3 - See <https://www.gnu.org/licenses/>
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

try:
    from ._version import __version__
except ImportError:
    from _version import __version__

try:
    from .ptforensictoolbase import ForensicToolBase
except ImportError:
    from ptforensictoolbase import ForensicToolBase
from ptlibs import ptjsonlib, ptprinthelper
from ptlibs.ptprinthelper import ptprint

SCRIPTNAME = "ptmediareadability"


class PtMediaReadability(ForensicToolBase):
    """
    On-site media readability diagnostic – ptlibs compliant.
    
    Performs pre-detection (lsblk, blkid, smartctl, hdparm, mdadm) and four
    read-only tests, classifying media as READABLE, PARTIAL, or UNREADABLE.
    """

    SMART_CHECKS = {
        "reallocated_sector": ("Reallocated_Sector_Ct", ">50", 50),
        "current_pending_sector": ("Current_Pending_Sector", ">0", 0),
        "uncorrectable": ("Offline_Uncorrectable", ">0", 0),
    }
    
    ENCRYPTION_MARKERS = {
        "crypto_luks": "LUKS",
        "bitlocker": "BitLocker",
        "veracrypt": "VeraCrypt",
    }

    SPEED_THRESHOLDS = {
        "good": 20.0,
        "acceptable": 5.0,
    }

    def __init__(self, args: argparse.Namespace) -> None:
        self.ptjsonlib = ptjsonlib.PtJsonLib()
        self.args = args
        self.case_id = args.case_id.strip()
        self.analyst = args.analyst
        self.dry_run = args.dry_run
        self.device = args.device

        self.detection_results = {}
        self.diagnostic_tests = []
        self.critical_findings = []
        self.stats = {"testsRun": 0, "testsPassed": 0, "testsFailed": 0}

        self.media_status: str = "UNKNOWN"
        self.recommended_tool: Optional[str] = None
        self.next_step: Optional[int] = None

        if not self.dry_run:
            if not self.device.startswith("/dev/"):
                self._abort(f"Invalid device path: {self.device}")
            if not os.path.exists(self.device):
                self._abort(f"Device not found: {self.device}")

        self._init_properties(__version__)
        self.ptjsonlib.add_properties({"devicePath": self.device})

    def _abort(self, msg: str) -> None:
        """Hard stop for initialization errors."""
        ptprint(f"\nERROR: {msg}", "ERROR", condition=True, colortext=True)
        sys.exit(99)

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

    def _print_header(self, title: str) -> None:
        """Print visual section separator."""
        ptprint("\n" + "=" * 70, "TITLE", condition=self._out())
        ptprint(title, "TITLE", condition=self._out())
        ptprint("=" * 70, "TITLE", condition=self._out())
 
    def _handle_missing_tool(self, tool_name: str) -> None:
        """Record and warn about missing diagnostic tool."""
        ptprint(f"⚠ {tool_name} not available", "WARNING", condition=self._out())
        self.detection_results[tool_name] = {"error": "command not found"}
 
    def _detect_encryption(self, output: str) -> Optional[str]:
        """Detect encryption type from blkid output."""
        output_lower = output.lower()
        for marker, enc_type in self.ENCRYPTION_MARKERS.items():
            if marker in output_lower:
                return enc_type
        return None
 
    def _parse_smart_warnings(self, stdout: str) -> List[str]:
        """Extract SMART warnings from smartctl output."""
        warns = []
        for line in stdout.splitlines():
            line_lower = line.lower()
            parts = line.split()
            
            for keyword, (label, threshold, limit) in self.SMART_CHECKS.items():
                if keyword in line_lower:
                    for part in parts:
                        if part.isdigit() and int(part) > limit:
                            warns.append(f"{label} = {part} ({threshold})")
                            break
                    break
        return warns
 
    def _is_raid_member(self, mdadm_output: str) -> bool:
        """Check if device is part of RAID array."""
        return any(
            keyword in mdadm_output
            for keyword in ["MD_LEVEL", "ARRAY"]
        ) or "magic" in mdadm_output.lower()
 
    def pre_detect(self) -> bool:
        """Run pre-detection diagnostics on device."""
        self._print_header("PHASE 0: Pre-Detection")
        
        if not self._test_lsblk():
            return False
        
        self._test_blkid()
        self._test_smartctl()
        self._test_hdparm()
        self._test_mdadm()
        
        self._add_node("preDetection", True,
                       criticalFindings=len(self.critical_findings),
                       detectionResults=self.detection_results)
        return True
 
    def _test_lsblk(self) -> bool:
        """Test 0a: Device detection with lsblk."""
        ptprint("\n[0a] lsblk – device detection", "SUBTITLE", condition=self._out())
        
        if not self._check_command("lsblk"):
            self.detection_results["lsblk"] = {"error": "command not found"}
            ptprint("✗ lsblk not installed", "ERROR", condition=self._out())
            return self._fail("preDetection", "lsblk not found")
        
        r = self._run_command([
            "lsblk", "-d", "-o", "NAME,SIZE,TYPE,MODEL,SERIAL,TRAN", self.device
        ])
        
        if not r["success"] and not self.dry_run:
            self.detection_results["lsblk"] = {
                "visible": False, "error": r["stderr"]
            }
            return self._fail("preDetection", f"Device not detected: {r['stderr']}")
        
        lsblk_out = r["stdout"] if r["stdout"] else "(dry-run)"
        ptprint(f"✓ Device detected:\n{lsblk_out}", "OK", condition=self._out())
        
        size = self._size()
        if size:
            ptprint(f"  Size: {size:,} bytes ({size / (1024**3):.2f} GB)",
                    "TEXT", condition=self._out())
        
        self.detection_results["lsblk"] = {
            "visible": True, "output": lsblk_out, "sizeBytes": size
        }
        return True
 
    def _test_blkid(self) -> None:
        """Test 0b: Filesystem and encryption detection."""
        ptprint("\n[0b] blkid – filesystem & encryption",
                "SUBTITLE", condition=self._out())
        
        if not self._check_command("blkid"):
            self._handle_missing_tool("blkid")
            return
        
        r = self._run_command(["blkid", self.device])
        out = r["stdout"] or r["stderr"] or "(no response)"
        enc = self._detect_encryption(out)
        
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
            "output": out, "encrypted": bool(enc), "encryptionType": enc
        }
 
    def _test_smartctl(self) -> None:
        """Test 0c: SMART health diagnostics."""
        ptprint("\n[0c] smartctl – SMART health", "SUBTITLE", condition=self._out())
        
        if not self._check_command("smartctl"):
            self._handle_missing_tool("smartctl")
            return
        
        r = self._run_command(["smartctl", "-a", self.device])
        avail = r["success"] or "SMART support" in r["stdout"]
        
        warns = self._parse_smart_warnings(r["stdout"]) if avail and r["stdout"] else []
        
        if warns:
            for warning in warns:
                self.critical_findings.append(f"SMART: {warning}")
                ptprint(f"⚠  SMART WARNING: {warning}", "WARNING",
                        condition=self._out())
        else:
            msg = "✓ SMART data OK" if avail else \
                  "✓ Not SMART-capable (normal for flash media)"
            ptprint(msg, "OK", condition=self._out())
        
        self.detection_results["smartctl"] = {
            "smartAvailable": avail, "smartWarnings": warns
        }
 
    def _test_hdparm(self) -> None:
        """Test 0d: TRIM detection for SSDs."""
        ptprint("\n[0d] hdparm – TRIM detection", "SUBTITLE", condition=self._out())
        
        if not self._check_command("hdparm"):
            self._handle_missing_tool("hdparm")
            return
        
        r = self._run_command(["hdparm", "-I", self.device])
        trim = any(
            "trim" in line and "supported" in line and line.strip().startswith("*")
            for line in r["stdout"].lower().splitlines()
        )
        
        if trim:
            self.critical_findings.append(
                "TRIM active – deleted data may be physically erased")
            ptprint("⚠  TRIM ACTIVE!", "WARNING",
                    condition=self._out(), colortext=True)
            ptprint("    Recovery may be INCOMPLETE – deleted data physically removed",
                    "WARNING", condition=self._out())
        else:
            ptprint("✓ TRIM not active or not supported", "OK", condition=self._out())
        
        self.detection_results["hdparm"] = {"trimActive": trim}
 
    def _test_mdadm(self) -> None:
        """Test 0e: RAID array membership detection."""
        ptprint("\n[0e] mdadm – RAID configuration", "SUBTITLE", condition=self._out())
        
        if not self._check_command("mdadm"):
            self._handle_missing_tool("mdadm")
            return
        
        r = self._run_command(["mdadm", "--examine", self.device])
        is_raid = self._is_raid_member(r["stdout"])
        
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
            "raidInfo": r["stdout"] if is_raid else None
        }

    def _record_test(self, test_id: int, name: str, success: bool, 
                     extra: Optional[Dict] = None) -> bool:
        """Record test result and update statistics."""
        entry = {"testId": test_id, "testName": name, "success": success}
        if extra:
            entry.update(extra)
        self.diagnostic_tests.append(entry)
        
        if success:
            self.stats["testsPassed"] += 1
        else:
            self.stats["testsFailed"] += 1
        self.stats["testsRun"] += 1
        return success
 
    def _calculate_test_positions(self, size: int) -> List[tuple]:
        """Calculate start/middle/end positions for random read test."""
        if size > 100 * 1_048_576:
            return [
                ("start", 2048),
                ("middle", size // 2),
                ("end", size - 10 * 1_048_576)
            ]
        else:
            return [
                ("start", 2048),
                ("middle", 1_048_576),
                ("end", 10 * 1_048_576)
            ]
 
    def _categorize_speed(self, speed: float) -> tuple:
        """Categorize read speed and return (tag, level) tuple."""
        if speed >= self.SPEED_THRESHOLDS["good"]:
            return "GOOD", "OK"
        elif speed >= self.SPEED_THRESHOLDS["acceptable"]:
            return "ACCEPTABLE", "WARNING"
        else:
            return "CRITICALLY LOW", "ERROR"
 
    def tests(self) -> bool:
        """Run diagnostic read tests on device."""
        self._print_header("PHASE 1: Diagnostic Tests")
        
        if not self._test_first_sector():
            return False
        
        seq_ok = self._test_sequential_read()
        self._test_random_positions()
        
        if seq_ok or self.dry_run:
            self._test_read_speed()
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
 
    def _test_first_sector(self) -> bool:
        """Test 1: First sector read (512 bytes)."""
        ptprint("\nTest 1/4: First Sector (512 B)", "SUBTITLE", condition=self._out())
        
        r = self._run_command([
            "dd", f"if={self.device}", "of=/dev/null",
            "bs=512", "count=1", "status=none"
        ])
        
        if r["success"]:
            ptprint("✓ First sector readable", "OK", condition=self._out())
        else:
            ptprint("✗ CRITICAL: First sector FAILED – media UNREADABLE",
                    "ERROR", condition=self._out(), colortext=True)
        
        self._record_test(1, "First Sector", r["success"],
                         {"bytesRead": 512 if r["success"] else 0})
        
        if not r["success"] and not self.dry_run:
            return False
        return True
 
    def _test_sequential_read(self) -> bool:
        """Test 2: Sequential read (1 MB)."""
        ptprint("\nTest 2/4: Sequential Read (1 MB)", "SUBTITLE", condition=self._out())
        
        r = self._run_command([
            "dd", f"if={self.device}", "of=/dev/null",
            "bs=512", "count=2048", "status=none"
        ], timeout=60)
        
        ptprint("✓ Sequential read OK" if r["success"]
                else "✗ Sequential read FAILED",
                "OK" if r["success"] else "ERROR", condition=self._out())
        
        self._record_test(2, "Sequential Read 1 MB", r["success"],
                         {"bytesRead": 1_048_576 if r["success"] else 0})
        return r["success"]
 
    def _test_random_positions(self) -> bool:
        """Test 3: Random read at start/middle/end positions."""
        ptprint("\nTest 3/4: Random Read (3 positions)",
                "SUBTITLE", condition=self._out())
        
        size = self._size()
        positions = self._calculate_test_positions(size)
        results = []
        all_ok = True
        
        for label, offset in positions:
            r = self._run_command([
                "dd", f"if={self.device}", "of=/dev/null",
                "bs=512", "count=1", f"skip={offset // 512}", "status=none"
            ])
            
            results.append({
                "position": label,
                "offsetBytes": offset,
                "success": r["success"]
            })
            
            ptprint(f"  {'✓' if r['success'] else '✗'} {label.capitalize()}",
                    "OK" if r["success"] else "ERROR", condition=self._out())
            
            if not r["success"]:
                all_ok = False
        
        self._record_test(3, "Random Read", all_ok, {
            "positions": results,
            "successfulReads": sum(1 for x in results if x["success"]),
            "totalReads": len(results),
        })
        return all_ok
 
    def _test_read_speed(self) -> None:
        """Test 4: Read speed measurement (10 MB)."""
        ptprint("\nTest 4/4: Read Speed (10 MB)", "SUBTITLE", condition=self._out())
        
        t0 = time.time()
        r = self._run_command([
            "dd", f"if={self.device}", "of=/dev/null",
            "bs=512", "count=20480", "status=progress"
        ], timeout=120)
        dur = time.time() - t0
        
        speed = (10 / dur) if r["success"] and dur > 0 else 0.0
        
        if r["success"]:
            tag, level = self._categorize_speed(speed)
            
            if speed < self.SPEED_THRESHOLDS["acceptable"]:
                self.critical_findings.append(
                    f"Low read speed: {speed:.1f} MB/s (<{self.SPEED_THRESHOLDS['acceptable']} MB/s)")
            
            ptprint(f"✓ Speed: {speed:.1f} MB/s ({tag})", level, condition=self._out())
            
            if speed < self.SPEED_THRESHOLDS["acceptable"]:
                ptprint("    WARNING: Imaging will be very slow or may fail",
                        "WARNING", condition=self._out())
        else:
            tag = "FAILED"
            ptprint("✗ Speed test FAILED", "ERROR", condition=self._out())
        
        self._record_test(4, "Read Speed", r["success"],
                         {"speedMBps": round(speed, 2), "speedStatus": tag})

    def classify(self) -> None:
        """Classify media based on test results."""
        t = {test["testId"]: test["success"] for test in self.diagnostic_tests}
        if not t:
            return
        
        if all(t.values()):
            self.media_status = "READABLE"
            self.recommended_tool = "dc3dd"
            self.next_step = 5
        elif t.get(1) and t.get(2):
            self.media_status = "PARTIAL"
            self.recommended_tool = "ddrescue"
            self.next_step = 5
        else:
            self.media_status = "UNREADABLE"
            self.recommended_tool = "Physical repair required"
            self.next_step = 4
 
        self._add_node("readabilityClassification", True,
                       mediaStatus=self.media_status,
                       recommendedTool=self.recommended_tool,
                       nextStep=self.next_step)
 
    def _print_summary(self) -> None:
        """Display test results summary."""
        self._print_header("SUMMARY")
        
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
            for finding in self.critical_findings:
                ptprint(f"   • {finding}", "WARNING", condition=self._out())
        
        ptprint("=" * 70, "TITLE", condition=self._out())
 
    def run(self) -> None:
        """Main execution workflow."""
        ptprint("=" * 70, "TITLE", condition=self._out())
        ptprint(f"MEDIA READABILITY TEST v{__version__}  |  "
                f"Case: {self.case_id}", "TITLE", condition=self._out())
        if self.dry_run:
            ptprint("MODE: DRY-RUN", "WARNING", condition=self._out())
        ptprint("=" * 70, "TITLE", condition=self._out())
 
        if not self.pre_detect() and not self.dry_run:
            self.media_status = "UNREADABLE"
            self.recommended_tool = "Physical repair required"
            self.next_step = 4
            self.classify()
        else:
            self.tests()
            self.classify()
            if not self.dry_run:
                self._print_summary()
 
        self.ptjsonlib.add_properties({
            "compliance": ["NIST SP 800-86", "ISO/IEC 27037:2012"],
            "mediaStatus": self.media_status,
            "recommendedTool": self.recommended_tool,
            "nextStep": self.next_step,
            "testsRun": self.stats["testsRun"],
            "testsPassed": self.stats["testsPassed"],
            "testsFailed": self.stats["testsFailed"],
            "criticalFindings": self.critical_findings,
        })
        
        self.ptjsonlib.add_node(self.ptjsonlib.create_node_object(
            "chainOfCustodyEntry",
            properties={
                "action": f"Media readability test – result: {self.media_status}",
                "result": ("SUCCESS"
                           if self.media_status in ("READABLE", "PARTIAL")
                           else "UNREADABLE"),
                "analyst": self.analyst,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "selectedTool": self.recommended_tool,
            }
        ))
        self.ptjsonlib.set_status("finished")
 
    def save_report(self) -> Optional[str]:
        """Save JSON report to file."""
        if not self.args.json_out:
            return None
 
        result_data = json.loads(self.ptjsonlib.get_result_json())
        out = Path(self.args.json_out)
        out.write_text(
            json.dumps({"result": result_data}, indent=2, ensure_ascii=False),
            encoding="utf-8")
        
        ptprint(self.ptjsonlib.get_result_json(), "", self.args.json)
        ptprint(f"✓ JSON saved: {out}", "OK", condition=not self.args.json)
        return str(out)

def get_help() -> List[Dict]:
    """Return help information structure for ptprinthelper."""
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
            "Exit 0 = READABLE | Exit 1 = PARTIAL | Exit 2 = UNREADABLE | Exit 99 = error",
            "All operations are READ-ONLY",
            "Compliant with NIST SP 800-86 and ISO/IEC 27037:2012",
        ]},
    ]
 
def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("device")
    parser.add_argument("case_id")
    parser.add_argument("-a", "--analyst",  default="Analyst")
    parser.add_argument("-j", "--json-out", default=None)
    parser.add_argument("-q", "--quiet",    action="store_true")
    parser.add_argument("--dry-run",        action="store_true")
    parser.add_argument("--version", action="version",
                        version=f"{SCRIPTNAME} {__version__}")
    
    if len(sys.argv) == 1 or "-h" in sys.argv or "--help" in sys.argv:
        ptprinthelper.help_print(get_help(), SCRIPTNAME, __version__)
        sys.exit(0)
    
    args = parser.parse_args()
    args.json = bool(args.json_out)
    
    if args.json:
        args.quiet = True
    
    ptprinthelper.print_banner(SCRIPTNAME, __version__, args.json)
    return args

EXIT_CODES = {
        "READABLE": 0,
        "PARTIAL": 1,
        "UNREADABLE": 2,
    }

def main() -> int:
    """Main entry point."""
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
        
        result_data = json.loads(tool.ptjsonlib.get_result_json())
        status = result_data["results"]["properties"].get("mediaStatus", "UNKNOWN")
        
        return EXIT_CODES.get(status, 99)
    
    except KeyboardInterrupt:
        ptprint("\nInterrupted by user.", "WARNING", condition=True)
        return 130
    
    except Exception as exc:
        ptprint(f"\nERROR: {exc}", "ERROR", condition=True, colortext=True)
        return 99
 
 
if __name__ == "__main__":
    sys.exit(main())