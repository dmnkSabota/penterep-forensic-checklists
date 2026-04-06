#!/usr/bin/env python3
"""
    Copyright (c) 2025 Bc. Dominik Sabota, VUT FIT Brno
    ptmediareadability - Forensic media readability diagnostic
    
    Standalone tool for on-site media readability testing.
    Analyst identifies device path (e.g., /dev/sdb) and runs test directly.
    
    Usage: ptmediareadability /dev/sdb CASE-ID [--analyst NAME] [--output file.json]
    
    Compliant with NIST SP 800-86 and ISO/IEC 27037:2012.
"""

import argparse
import sys
import os
import json
import subprocess
from datetime import datetime, timezone
from typing import Dict, List, Any

from ._version import __version__
from ptlibs import ptprinthelper
from ptlibs.ptprinthelper import ptprint

SCRIPTNAME = "ptmediareadability"


class PtMediaReadability:
    """
    Standalone media readability diagnostic
    
    Pre-detection: lsblk, blkid, smartctl, hdparm, mdadm
    Tests: first sector, sequential 1MB, random 3-pos, speed 10MB
    Result: READABLE (dc3dd) / PARTIAL (ddrescue) / UNREADABLE (repair)
    """

    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.device = args.device
        self.case_id = args.case_id
        self.analyst = args.analyst
        
        # Results storage
        self.detection_results = {}
        self.diagnostic_tests = []
        self.critical_findings = []
        self.stats = {'testsRun': 0, 'testsPassed': 0, 'testsFailed': 0}
        self.media_status = "UNKNOWN"
        self.recommended_tool = None
        self.next_step = None
        self.timestamp = datetime.now(timezone.utc).isoformat()
        
        # Validate
        if not self.device.startswith("/dev/"):
            self._fail(f"Invalid device path: {self.device}")
        if not os.path.exists(self.device):
            self._fail(f"Device not found: {self.device}")

    @staticmethod
    def confirm_write_blocker() -> bool:
        """Write-blocker confirmation"""
        ptprint("\n" + "!" * 70, "WARNING", condition=True)
        ptprint("CRITICAL: WRITE-BLOCKER MUST BE CONNECTED", "WARNING",
               condition=True, colortext=True)
        ptprint("!" * 70, "WARNING", condition=True)
        ptprint("\nVerify before proceeding:", "TEXT", condition=True)
        ptprint("  1. Hardware write-blocker is physically connected", "TEXT", condition=True)
        ptprint("  2. LED indicator shows PROTECTED", "TEXT", condition=True)
        ptprint("  3. No unusual sounds from HDD", "TEXT", condition=True)
        ptprint("  4. Media connected THROUGH write-blocker, not directly", "TEXT", condition=True)
        
        ok = input("\nConfirm write-blocker is active [yes/NO]: ").strip().lower() in ("yes", "y")
        ptprint("\n" + ("✓" * 70 if ok else "✗" * 70), "OK" if ok else "ERROR", condition=True)
        ptprint("CONFIRMED - proceeding" if ok else "NOT CONFIRMED - test ABORTED",
               "OK" if ok else "ERROR", condition=True, colortext=True)
        ptprint(("✓" * 70 if ok else "✗" * 70), "OK" if ok else "ERROR", condition=True)
        return ok

    def _cmd(self, cmd: List[str], timeout: int = 30) -> Dict[str, Any]:
        """Execute command"""
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
            return {'ok': r.returncode == 0, 'out': r.stdout.strip(), 'err': r.stderr.strip()}
        except subprocess.TimeoutExpired:
            return {'ok': False, 'out': '', 'err': f'Timeout {timeout}s'}
        except Exception as e:
            return {'ok': False, 'out': '', 'err': str(e)}

    def _has(self, cmd: str) -> bool:
        """Check command exists"""
        try:
            subprocess.run(["which", cmd], capture_output=True, check=True, timeout=5)
            return True
        except:
            return False

    def _size(self) -> int:
        """Device size in bytes"""
        for cmd in [["blockdev", "--getsize64", self.device],
                    ["lsblk", "-b", "-d", "-n", "-o", "SIZE", self.device]]:
            r = self._cmd(cmd)
            if r['ok'] and r['out'].isdigit():
                return int(r['out'])
        return 0

    def _add_critical(self, msg: str) -> None:
        """Add critical finding"""
        self.critical_findings.append(msg)

    def _fail(self, msg: str) -> None:
        """Fail"""
        ptprint(f"\nERROR: {msg}", "ERROR", condition=True, colortext=True)
        sys.exit(1)

    def pre_detect(self) -> bool:
        """Pre-detection phase"""
        ptprint("\n" + "=" * 70, "TITLE", condition=not self.args.json)
        ptprint("PHASE 0: Pre-Detection", "TITLE", condition=not self.args.json)
        ptprint("=" * 70, "TITLE", condition=not self.args.json)

        # lsblk
        ptprint("\n[0a] lsblk - Device detection", "SUBTITLE", condition=not self.args.json)
        if not self._has("lsblk"):
            self.detection_results['lsblk'] = {"error": "command not found"}
            ptprint("✗ lsblk not installed", "ERROR", condition=not self.args.json)
            return False
        
        r = self._cmd(["lsblk", "-d", "-o", "NAME,SIZE,TYPE,MODEL,SERIAL,TRAN", self.device])
        if not r['ok']:
            self.detection_results['lsblk'] = {"visible": False, "error": r['err']}
            ptprint(f"✗ Device not detected: {r['err']}", "ERROR", condition=not self.args.json)
            return False
        
        ptprint(f"✓ Device detected:\n{r['out']}", "OK", condition=not self.args.json)
        size = self._size()
        if size:
            ptprint(f"  Size: {size:,} bytes ({size/(1024**3):.2f} GB)", "TEXT",
                   condition=not self.args.json)
        self.detection_results['lsblk'] = {
            "visible": True,
            "output": r['out'],
            "sizeBytes": size
        }

        # blkid
        ptprint("\n[0b] blkid - Filesystem & encryption", "SUBTITLE", condition=not self.args.json)
        if self._has("blkid"):
            r = self._cmd(["blkid", self.device])
            out = r['out'] or r['err'] or "(no response)"
            enc = None
            ol = out.lower()
            if "crypto_luks" in ol:
                enc = "LUKS"
            elif "bitlocker" in ol:
                enc = "BitLocker"
            elif "veracrypt" in ol:
                enc = "VeraCrypt"
            
            if enc:
                self._add_critical(f"Encryption detected: {enc} - recovery key required")
                ptprint(f"⚠️  ENCRYPTION: {enc} detected!", "WARNING",
                       condition=not self.args.json, colortext=True)
                ptprint("    Recovery key/password REQUIRED for data access", "WARNING",
                       condition=not self.args.json)
            else:
                ptprint(f"✓ {out}", "OK", condition=not self.args.json)
            
            self.detection_results['blkid'] = {
                "output": out,
                "encrypted": bool(enc),
                "encryptionType": enc
            }
        else:
            ptprint("⚠ blkid not available", "WARNING", condition=not self.args.json)
            self.detection_results['blkid'] = {"error": "command not found"}

        # smartctl
        ptprint("\n[0c] smartctl - SMART health data", "SUBTITLE", condition=not self.args.json)
        if self._has("smartctl"):
            r = self._cmd(["smartctl", "-a", self.device])
            ok = r['ok'] or "SMART support" in r['out']
            warns = []
            if ok and r['out']:
                for line in r['out'].splitlines():
                    ll, p = line.lower(), line.split()
                    if "reallocated_sector" in ll:
                        for x in p:
                            if x.isdigit() and int(x) > 50:
                                warns.append(f"Reallocated_Sector_Ct = {x} (>50 - critically damaged)")
                    if "current_pending_sector" in ll:
                        for x in p:
                            if x.isdigit() and int(x) > 0:
                                warns.append(f"Current_Pending_Sector = {x} (>0 - actively failing)")
                    if "uncorrectable" in ll:
                        for x in p:
                            if x.isdigit() and int(x) > 0:
                                warns.append(f"Offline_Uncorrectable = {x} (>0 - uncorrectable errors)")
            if warns:
                for w in warns:
                    self._add_critical(f"SMART: {w}")
                    ptprint(f"⚠️  SMART WARNING: {w}", "WARNING", condition=not self.args.json)
            else:
                ptprint("✓ SMART data OK" if ok else "✓ Not SMART-capable (normal for flash media)",
                       "OK", condition=not self.args.json)
            
            self.detection_results['smartctl'] = {
                "smartAvailable": ok,
                "smartWarnings": warns
            }
        else:
            ptprint("⚠ smartctl not available", "WARNING", condition=not self.args.json)
            self.detection_results['smartctl'] = {"error": "command not found"}

        # hdparm
        ptprint("\n[0d] hdparm - TRIM support detection", "SUBTITLE", condition=not self.args.json)
        if self._has("hdparm"):
            r = self._cmd(["hdparm", "-I", self.device])
            trim = False
            if r['out']:
                for line in r['out'].lower().splitlines():
                    if "trim" in line and "supported" in line:
                        if not line.strip().startswith("*"):
                            trim = True
                            break
            if trim:
                self._add_critical("TRIM active - deleted data may be physically erased")
                ptprint("⚠️  TRIM ACTIVE!", "WARNING", condition=not self.args.json, colortext=True)
                ptprint("    Recovery may be INCOMPLETE - deleted data physically removed",
                       "WARNING", condition=not self.args.json)
            else:
                ptprint("✓ TRIM not active or not supported", "OK", condition=not self.args.json)
            
            self.detection_results['hdparm'] = {"trimActive": trim}
        else:
            ptprint("⚠ hdparm not available", "WARNING", condition=not self.args.json)
            self.detection_results['hdparm'] = {"error": "command not found"}

        # mdadm
        ptprint("\n[0e] mdadm - RAID configuration", "SUBTITLE", condition=not self.args.json)
        if self._has("mdadm"):
            r = self._cmd(["mdadm", "--examine", self.device])
            is_raid = "MD_LEVEL" in r['out'] or "ARRAY" in r['out'] or "magic" in r['out'].lower()
            raid_info = None
            
            if is_raid:
                self._add_critical("RAID member detected - full array required for recovery")
                ptprint("⚠️  RAID MEMBER DETECTED!", "WARNING",
                       condition=not self.args.json, colortext=True)
                ptprint("    Full RAID array required for complete recovery", "WARNING",
                       condition=not self.args.json)
                raid_info = r['out']
            else:
                ptprint("✓ Not a RAID member", "OK", condition=not self.args.json)
            
            self.detection_results['mdadm'] = {
                "isRaidMember": is_raid,
                "raidInfo": raid_info
            }
        else:
            ptprint("⚠ mdadm not available", "WARNING", condition=not self.args.json)
            self.detection_results['mdadm'] = {"error": "command not found"}

        return True

    def tests(self) -> bool:
        """Diagnostic tests"""
        ptprint("\n" + "=" * 70, "TITLE", condition=not self.args.json)
        ptprint("PHASE 1: Diagnostic Tests", "TITLE", condition=not self.args.json)
        ptprint("=" * 70, "TITLE", condition=not self.args.json)

        # Test 1: First sector
        self.stats['testsRun'] += 1
        ptprint("\nTest 1/4: First Sector (512 B)", "SUBTITLE", condition=not self.args.json)
        r = self._cmd(["dd", f"if={self.device}", "of=/dev/null", "bs=512", "count=1",
                      "status=none"])
        if r['ok']:
            self.stats['testsPassed'] += 1
            ptprint("✓ First sector readable", "OK", condition=not self.args.json)
        else:
            self.stats['testsFailed'] += 1
            ptprint("✗ CRITICAL: First sector FAILED - media UNREADABLE", "ERROR",
                   condition=not self.args.json, colortext=True)
        
        self.diagnostic_tests.append({
            "testId": 1,
            "testName": "First Sector",
            "success": r['ok'],
            "bytesRead": 512 if r['ok'] else 0
        })
        
        if not r['ok']:
            return False

        # Test 2: Sequential 1MB
        self.stats['testsRun'] += 1
        ptprint("\nTest 2/4: Sequential Read (1 MB)", "SUBTITLE", condition=not self.args.json)
        r = self._cmd(["dd", f"if={self.device}", "of=/dev/null", "bs=512", "count=2048",
                      "status=none"], timeout=60)
        seq = r['ok']
        if r['ok']:
            self.stats['testsPassed'] += 1
            ptprint("✓ Sequential read OK", "OK", condition=not self.args.json)
        else:
            self.stats['testsFailed'] += 1
            ptprint("✗ Sequential read FAILED", "ERROR", condition=not self.args.json)
        
        self.diagnostic_tests.append({
            "testId": 2,
            "testName": "Sequential Read 1MB",
            "success": r['ok'],
            "bytesRead": 1024*1024 if r['ok'] else 0
        })

        # Test 3: Random 3-pos
        self.stats['testsRun'] += 1
        ptprint("\nTest 3/4: Random Read (3 positions)", "SUBTITLE", condition=not self.args.json)
        sz = self._size()
        pos = ([("start", 2048), ("middle", sz//2), ("end", sz-10*1024*1024)] if sz > 100*1024*1024
               else [("start", 2048), ("middle", 1024*1024), ("end", 10*1024*1024)])
        res, all_ok = [], True
        for lbl, off in pos:
            r = self._cmd(["dd", f"if={self.device}", "of=/dev/null", "bs=512", "count=1",
                          f"skip={off//512}", "status=none"])
            res.append({"position": lbl, "offsetBytes": off, "success": r['ok']})
            ptprint(f"  {'✓' if r['ok'] else '✗'} {lbl.capitalize()}", "OK" if r['ok'] else "ERROR",
                   condition=not self.args.json)
            if not r['ok']:
                all_ok = False
        
        if all_ok:
            self.stats['testsPassed'] += 1
        else:
            self.stats['testsFailed'] += 1
        
        self.diagnostic_tests.append({
            "testId": 3,
            "testName": "Random Read",
            "success": all_ok,
            "positions": res,
            "successfulReads": sum(1 for x in res if x['success']),
            "totalReads": len(res)
        })

        # Test 4: Speed
        if seq:
            self.stats['testsRun'] += 1
            ptprint("\nTest 4/4: Read Speed (10 MB)", "SUBTITLE", condition=not self.args.json)
            t0 = datetime.now()
            r = self._cmd(["dd", f"if={self.device}", "of=/dev/null", "bs=512",
                          "count=20480", "status=progress"], timeout=120)
            dur = (datetime.now() - t0).total_seconds()
            spd = (10 / dur) if r['ok'] and dur > 0 else 0.0
            if r['ok']:
                self.stats['testsPassed'] += 1
                if spd >= 20:
                    tag, level = "GOOD", "OK"
                elif spd >= 5:
                    tag, level = "ACCEPTABLE", "WARNING"
                else:
                    tag, level = "CRITICALLY LOW", "ERROR"
                    self._add_critical(f"Low read speed: {spd:.1f} MB/s (<5 MB/s)")
                
                ptprint(f"✓ Speed: {spd:.1f} MB/s ({tag})", level, condition=not self.args.json)
                if spd < 5:
                    ptprint("    WARNING: Imaging will be extremely slow or may fail",
                           "WARNING", condition=not self.args.json)
            else:
                self.stats['testsFailed'] += 1
                ptprint("✗ Speed test FAILED", "ERROR", condition=not self.args.json)
            
            self.diagnostic_tests.append({
                "testId": 4,
                "testName": "Read Speed",
                "success": r['ok'],
                "speedMBps": round(spd, 2) if r['ok'] else 0,
                "speedStatus": tag if r['ok'] else "FAILED"
            })
        else:
            ptprint("\nTest 4/4: Speed - SKIPPED (sequential read failed, medium is PARTIAL)",
                   "WARNING", condition=not self.args.json)
        
        return True

    def classify(self) -> None:
        """Classification"""
        t = {test['testId']: test['success'] for test in self.diagnostic_tests}
        
        if not t.get(1):
            self.media_status = "UNREADABLE"
            self.recommended_tool = "Physical repair required"
            self.next_step = 4
        elif all(t.values()):
            self.media_status = "READABLE"
            self.recommended_tool = "dc3dd"
            self.next_step = 5
        elif t.get(2):
            self.media_status = "PARTIAL"
            self.recommended_tool = "ddrescue"
            self.next_step = 5
        else:
            self.media_status = "UNREADABLE"
            self.recommended_tool = "Physical repair required"
            self.next_step = 4

    def summary(self) -> None:
        """Summary"""
        ptprint("\n" + "=" * 70, "TITLE", condition=not self.args.json)
        ptprint("SUMMARY", "TITLE", condition=not self.args.json)
        ptprint("=" * 70, "TITLE", condition=not self.args.json)
        ptprint(f"Device: {self.device}", "TEXT", condition=not self.args.json)
        ptprint(f"Case: {self.case_id}", "TEXT", condition=not self.args.json)
        ptprint(f"Media Status: {self.media_status}", "TEXT", condition=not self.args.json)
        ptprint(f"Recommended Tool: {self.recommended_tool}", "TEXT", condition=not self.args.json)
        ptprint(f"Tests: {self.stats['testsPassed']}/{self.stats['testsRun']} passed", "TEXT",
               condition=not self.args.json)
        
        if self.critical_findings:
            ptprint(f"\n⚠️  CRITICAL FINDINGS ({len(self.critical_findings)}):", "WARNING",
                   colortext=True, condition=not self.args.json)
            ptprint("INFORM CLIENT BEFORE PROCEEDING:", "WARNING", condition=not self.args.json)
            for c in self.critical_findings:
                ptprint(f"  • {c}", "WARNING", condition=not self.args.json)
        
        ptprint("=" * 70, "TITLE", condition=not self.args.json)

    def save_json(self, filepath: str) -> None:
        """Save results as case.json-ready JSON"""
        output = {
            "readabilityTest": {
                "devicePath": self.device,
                "timestamp": self.timestamp,
                "mediaStatus": self.media_status,
                "recommendedTool": self.recommended_tool,
                "nextStep": self.next_step,
                "criticalFindings": self.critical_findings,
                "statistics": self.stats,
                "detectionResults": self.detection_results,
                "diagnosticTests": self.diagnostic_tests
            },
            "chainOfCustodyEntry": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "analyst": self.analyst,
                "action": f"Test čitateľnosti média – výsledok: {self.media_status}",
                "selectedTool": self.recommended_tool
            }
        }
        
        with open(filepath, 'w') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

    def run(self) -> None:
        """Main execution"""
        ptprint("=" * 70, "TITLE", condition=not self.args.json)
        ptprint(f"MEDIA READABILITY TEST v{__version__}", "TITLE", condition=not self.args.json)
        ptprint(f"Device: {self.device} | Case: {self.case_id}", "TITLE",
               condition=not self.args.json)
        ptprint("=" * 70, "TITLE", condition=not self.args.json)
        
        if not self.pre_detect():
            self.media_status = "UNREADABLE"
            self.recommended_tool = "Physical repair required"
            self.next_step = 4
            return
        
        self.tests()
        self.classify()
        self.summary()


def get_help() -> List[Dict]:
    return [
        {"description": [
            "Forensic media readability diagnostic - standalone tool",
            "READ-ONLY tests classify media as READABLE/PARTIAL/UNREADABLE",
            "Compliant with NIST SP 800-86 and ISO/IEC 27037:2012",
            "",
            "⚠️  WRITE-BLOCKER IS ALWAYS REQUIRED - confirmation at every run"
        ]},
        {"usage": ["ptmediareadability <device> <case-id> [options]"]},
        {"usage_example": [
            "ptmediareadability /dev/sdb PHOTORECOVERY-2025-01-26-001",
            "ptmediareadability /dev/sdb CASE-001 --analyst 'John Doe'",
            "ptmediareadability /dev/sdc CASE-002 --output result.json",
        ]},
        {"options": [
            ["device",           "",      "Device path (e.g., /dev/sdb) - REQUIRED"],
            ["case-id",          "",      "Case identifier - REQUIRED"],
            ["-a", "--analyst",  "<n>",   "Analyst name (default: Analyst)"],
            ["-o", "--output",   "<f>",   "Save JSON output to file (optional)"],
            ["-h", "--help",     "",      "Show this help"],
            ["--version",        "",      "Show version"],
        ]},
        {"notes": [
            "⚠️  Write-blocker confirmation is ALWAYS REQUIRED",
            "✓ All operations are READ-ONLY",
            "✓ Terminal output by default, JSON only if --output specified",
            "✓ JSON output ready for manual copy-paste into case.json",
        ]},
    ]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("device")
    p.add_argument("case_id")
    p.add_argument("-a", "--analyst", default="Analyst")
    p.add_argument("-o", "--output", help="JSON output file (optional)")
    p.add_argument("--version", action="version", version=f"{SCRIPTNAME} {__version__}")
    if len(sys.argv) == 1 or {"-h", "--help"} & set(sys.argv):
        ptprinthelper.help_print(get_help(), SCRIPTNAME, __version__)
        sys.exit(0)
    args = p.parse_args()
    args.json = bool(args.output)
    ptprinthelper.print_banner(SCRIPTNAME, __version__, args.json)
    return args


def main() -> int:
    try:
        args = parse_args()
        
        # ALWAYS require write-blocker confirmation
        if not PtMediaReadability.confirm_write_blocker():
            ptprint("\nTest ABORTED - write-blocker is REQUIRED!", "ERROR",
                   condition=True, colortext=True)
            return 99
        
        tool = PtMediaReadability(args)
        tool.run()
        
        # Save JSON only if --output specified
        if args.output:
            try:
                tool.save_json(args.output)
                ptprint(f"\n✓ JSON saved: {args.output}", "OK", condition=True)
                ptprint("  Ready to copy-paste into case.json", "TEXT", condition=True)
            except Exception as e:
                ptprint(f"\n✗ Error saving JSON: {e}", "ERROR", condition=True)
                return 99
        
        return {"READABLE": 0, "PARTIAL": 1, "UNREADABLE": 2}.get(tool.media_status, 99)
    
    except KeyboardInterrupt:
        ptprint("\nInterrupted by user", "WARNING", condition=True)
        return 130
    except Exception as e:
        ptprint(f"\nERROR: {e}", "ERROR", condition=True, colortext=True)
        return 99


if __name__ == "__main__":
    sys.exit(main())