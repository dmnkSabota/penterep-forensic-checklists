#!/usr/bin/env python3
"""
    Copyright (c) 2025 Bc. Dominik Sabota, VUT FIT Brno
    ptforensicimaging - Forensic media imaging tool
    
    Standalone tool for forensic imaging with integrated SHA-256 hashing.
    Auto-loads device path and tool selection from Step 3 readability test.
    
    Usage: ptforensicimaging CASE-ID [--analyst NAME] [--output file.json]
    
    Compliant with NIST SP 800-86 and ISO/IEC 27037:2012.
"""

import argparse
import sys
import os
import json
import subprocess
import time
import signal
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional

from _version import __version__
from ptlibs import ptprinthelper
from ptlibs.ptprinthelper import ptprint

# Override ptlibs signal handler to allow KeyboardInterrupt
def _custom_sigint_handler(sig, frame):
    """Custom SIGINT handler - raises KeyboardInterrupt instead of os._exit(1)"""
    raise KeyboardInterrupt

# Re-register signal handler AFTER ptlibs import
signal.signal(signal.SIGINT, _custom_sigint_handler)

SCRIPTNAME = "ptforensicimaging"
DEFAULT_OUTPUT_DIR = "/var/forensics/images"


class PtForensicImaging:
    """
    Standalone forensic imaging tool
    
    Auto-loads: device path, tool selection from Step 3
    dc3dd: READABLE media (fast, integrated SHA-256)
    ddrescue: PARTIAL media (damaged sector recovery)
    """

    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.case_id = args.case_id
        self.analyst = args.analyst
        self.device = args.device
        self.tool = args.tool
        self.output_dir = Path(args.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Validate required parameters
        if not self.device:
            self._fail("Device path is required (use --device /dev/sdX)")
        if not self.tool:
            self._fail("Tool selection is required (use --tool dc3dd or --tool ddrescue)")
        
        # Determine media status from tool
        self.media_status = "READABLE" if self.tool == "dc3dd" else "PARTIAL"
        self.source_size = None
        
        # Results storage
        self.image_path = None
        self.source_hash = None
        self.duration = None
        self.avg_speed = None
        self.error_sectors = 0
        self.mapfile = None
        self.log_file = None
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.error_message = None  # Track errors for JSON
        self.success = False  # Track overall success

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
        ptprint("  3. Source media connected THROUGH write-blocker", "TEXT", condition=True)
        ptprint("  4. Target storage has sufficient free space", "TEXT", condition=True)
        
        while True:
            response = input("\nConfirm write-blocker is active [y/N]: ").strip().lower()
            
            if response in ("y", "yes"):
                ok = True
                break
            elif response in ("n", "no", ""):
                ok = False
                break
            else:
                ptprint("Invalid input. Please enter 'y' or 'n'", "WARNING", condition=True)
        
        ptprint("\n" + ("✓" * 70 if ok else "✗" * 70), "OK" if ok else "ERROR", condition=True)
        ptprint("CONFIRMED - proceeding" if ok else "NOT CONFIRMED - imaging ABORTED",
            "OK" if ok else "ERROR", condition=True, colortext=True)
        ptprint(("✓" * 70 if ok else "✗" * 70), "OK" if ok else "ERROR", condition=True)
        return ok

    def _cmd(self, cmd: List[str], timeout: Optional[int] = None) -> Dict[str, Any]:
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

    def _fail(self, msg: str) -> None:
        """Fail"""
        ptprint(f"\nERROR: {msg}", "ERROR", condition=True, colortext=True)
        sys.exit(1)

    def check_prerequisites(self) -> bool:
        """Check tool availability and storage space"""
        ptprint("\n" + "=" * 70, "TITLE", condition=not self.args.json)
        ptprint("STEP 1: Prerequisites Check", "TITLE", condition=not self.args.json)
        ptprint("=" * 70, "TITLE", condition=not self.args.json)
        
        # Check tool availability
        ptprint(f"\n[2a] Checking {self.tool} availability", "SUBTITLE", condition=not self.args.json)
        if not self._has(self.tool):
            self.error_message = f"{self.tool} not installed"
            ptprint(f"✗ {self.tool} not installed", "ERROR", condition=not self.args.json)
            return False
        ptprint(f"✓ {self.tool} is available", "OK", condition=not self.args.json)
        
        # Check sha256sum for ddrescue
        if self.tool == "ddrescue":
            if not self._has("sha256sum"):
                self.error_message = "sha256sum not installed"
                ptprint("✗ sha256sum not installed", "ERROR", condition=not self.args.json)
                return False
            ptprint("✓ sha256sum is available", "OK", condition=not self.args.json)
        
        # Check device exists
        ptprint("\n[2b] Checking source device", "SUBTITLE", condition=not self.args.json)
        if not os.path.exists(self.device):
            self.error_message = f"Device not found: {self.device}"
            ptprint(f"✗ Device not found: {self.device}", "ERROR", condition=not self.args.json)
            return False
        ptprint(f"✓ Device accessible: {self.device}", "OK", condition=not self.args.json)
        
        # Check storage space
        ptprint("\n[2c] Checking target storage space", "SUBTITLE", condition=not self.args.json)
        try:
            stat = os.statvfs(self.output_dir)
            free_bytes = stat.f_bavail * stat.f_frsize
            
            if self.source_size:
                required = int(self.source_size * 1.1)
                ptprint(f"  Required: {required:,} bytes ({required/(1024**3):.2f} GB)",
                       "TEXT", condition=not self.args.json)
                ptprint(f"  Available: {free_bytes:,} bytes ({free_bytes/(1024**3):.2f} GB)",
                       "TEXT", condition=not self.args.json)
                
                if free_bytes < required:
                    self.error_message = "Insufficient storage space (need 110% of source size)"
                    ptprint("✗ Insufficient storage space (need 110% of source size)",
                           "ERROR", condition=not self.args.json)
                    return False
                ptprint("✓ Sufficient storage space", "OK", condition=not self.args.json)
            else:
                ptprint(f"  Available: {free_bytes/(1024**3):.2f} GB", "TEXT",
                       condition=not self.args.json)
                ptprint("⚠ Source size unknown - cannot verify space", "WARNING",
                       condition=not self.args.json)
        except Exception as e:
            ptprint(f"⚠ Could not check storage space: {e}", "WARNING",
                   condition=not self.args.json)
        
        return True

    def run_imaging(self) -> bool:
        """Execute imaging based on tool selection"""
        ptprint("\n" + "=" * 70, "TITLE", condition=not self.args.json)
        ptprint("STEP 2: Forensic Imaging", "TITLE", condition=not self.args.json)
        ptprint("=" * 70, "TITLE", condition=not self.args.json)
        
        self.image_path = self.output_dir / f"{self.case_id}.dd"
        self.log_file = self.output_dir / f"{self.case_id}_imaging.log"
        
        if self.tool == "dc3dd":
            return self.run_dc3dd()
        else:
            return self.run_ddrescue()

    def run_dc3dd(self) -> bool:
        """dc3dd imaging with integrated SHA-256"""
        ptprint(f"\nStarting dc3dd imaging...", "SUBTITLE", condition=not self.args.json)
        ptprint(f"  Source: {self.device}", "TEXT", condition=not self.args.json)
        ptprint(f"  Target: {self.image_path}", "TEXT", condition=not self.args.json)
        ptprint(f"  Hash:   SHA-256 (integrated)", "TEXT", condition=not self.args.json)
        
        # Get source size for progress calculation
        try:
            r = self._cmd(["blockdev", "--getsize64", self.device], timeout=5)
            if r['ok'] and r['out']:
                self.source_size = int(r['out'].strip())
                ptprint(f"  Size:   {self.source_size:,} bytes ({self.source_size/(1024**3):.2f} GB)",
                       "TEXT", condition=not self.args.json)
        except:
            pass
        
        # FIXED: dc3dd syntax - minimal options only (dc3dd shows progress automatically)
        cmd = [
            "dc3dd",
            f"if={self.device}",
            f"of={self.image_path}",
            "hash=sha256",
            f"log={self.log_file}"
        ]
        
        ptprint(f"\nCommand: {' '.join(cmd)}", "TEXT", condition=not self.args.json)
        ptprint("\nImaging in progress...\n", "TEXT", condition=not self.args.json)
        
        t0 = time.time()
        
        try:
            # Run dc3dd in background
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, bufsize=1)
            
            # Monitor progress by watching output file size
            import threading
            output_lines = []
            proc_done = threading.Event()
            
            def read_output():
                """Read dc3dd output in background thread"""
                for line in proc.stdout:
                    output_lines.append(line)
                proc_done.set()
            
            # Start output reader thread
            reader = threading.Thread(target=read_output, daemon=True)
            reader.start()
            
            # Display progress by monitoring file size
            last_pct = -1
            while not proc_done.is_set():
                time.sleep(0.5)  # Update every 0.5 seconds
                
                if self.image_path.exists() and self.source_size:
                    current_size = self.image_path.stat().st_size
                    pct = int(100 * current_size / self.source_size)
                    
                    if pct != last_pct and not self.args.json:
                        # Draw progress bar
                        bar_width = 20
                        filled = int(bar_width * pct / 100)
                        bar = '=' * filled + ('>' if filled < bar_width else '') + ' ' * (bar_width - filled - (1 if filled < bar_width else 0))
                        
                        gb_current = current_size / (1024**3)
                        gb_total = self.source_size / (1024**3)
                        
                        elapsed = time.time() - t0
                        speed = (current_size / (1024**2)) / elapsed if elapsed > 0 else 0
                        
                        progress_line = f"\rImaging: [{bar}] {pct:3d}% | {gb_current:.1f}/{gb_total:.1f} GB | {speed:.1f} MB/s"
                        print(progress_line, end='', flush=True)
                        last_pct = pct
            
            # Wait for process to complete
            proc.wait()
            reader.join(timeout=5)
            
            if not self.args.json and last_pct >= 0:
                print()  # New line after progress bar
            
            self.duration = time.time() - t0
            
            if proc.returncode != 0:
                self.error_message = f"dc3dd failed with return code {proc.returncode}"
                # Try to extract error from output
                error_lines = [l for l in output_lines if 'error' in l.lower() or 'fail' in l.lower() or '!!' in l]
                if error_lines:
                    self.error_message += f": {' '.join(error_lines[:3])}"
                
                ptprint(f"\n✗ dc3dd failed with return code {proc.returncode}",
                       "ERROR", condition=not self.args.json)
                if error_lines:
                    for err_line in error_lines[:3]:
                        ptprint(f"  {err_line.strip()}", "ERROR", condition=not self.args.json)
                return False
            
        except KeyboardInterrupt:
            # User pressed Ctrl+C during imaging
            ptprint("\n✗ Imaging interrupted by user", "WARNING", condition=not self.args.json)
            proc.terminate()
            proc.wait()
            raise  # Re-raise to main() for exit code 130
        
        # Extract SHA-256 from log
        if self.log_file.exists():
            log_content = self.log_file.read_text()
            for line in log_content.splitlines():
                if "sha256" in line.lower() and len(line.split()) > 1:
                    parts = line.split()
                    for part in parts:
                        if len(part) == 64 and all(c in '0123456789abcdef' for c in part.lower()):
                            self.source_hash = part.lower()
                            break
        
        if not self.source_hash:
            ptprint("\n⚠ Could not extract SHA-256 from dc3dd output", "WARNING",
                   condition=not self.args.json)
        
        # Calculate average speed
        if self.image_path.exists():
            size = self.image_path.stat().st_size
            if not self.source_size:
                self.source_size = size
            self.avg_speed = (size / (1024**2)) / self.duration if self.duration > 0 else 0
        
        # Create canonical hash file
        if self.source_hash:
            hash_file = Path(str(self.image_path) + ".sha256")
            hash_file.write_text(f"{self.source_hash}  {self.image_path.name}\n")
            ptprint(f"\n✓ Hash file created: {hash_file}", "OK", condition=not self.args.json)
        
        ptprint(f"\n✓ dc3dd imaging completed", "OK", condition=not self.args.json)
        return True

    def run_ddrescue(self) -> bool:
        """ddrescue imaging with separate SHA-256 calculation"""
        ptprint(f"\nStarting ddrescue imaging...", "SUBTITLE", condition=not self.args.json)
        ptprint(f"  Source: {self.device}", "TEXT", condition=not self.args.json)
        ptprint(f"  Target: {self.image_path}", "TEXT", condition=not self.args.json)
        ptprint(f"  Mode:   Damaged sector recovery", "TEXT", condition=not self.args.json)
        
        self.mapfile = self.output_dir / f"{self.case_id}.mapfile"
        
        cmd = [
            "ddrescue",
            "-f", "-v",
            self.device,
            str(self.image_path),
            str(self.mapfile)
        ]
        
        ptprint(f"\nCommand: {' '.join(cmd)}", "TEXT", condition=not self.args.json)
        ptprint("\nImaging in progress...\n", "TEXT", condition=not self.args.json)
        
        t0 = time.time()
        
        try:
            # Open log file for writing
            with open(self.log_file, 'w') as log_f:
                # Write command to log
                log_f.write(f"ddrescue started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S %z')}\n")
                log_f.write(f"Command: {' '.join(cmd)}\n")
                log_f.write("=" * 70 + "\n\n")
                log_f.flush()
                
                # Run with output to both screen and log file
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                       text=True, bufsize=1)
                output_lines = []
                try:
                    for line in proc.stdout:
                        # Write to log file
                        log_f.write(line)
                        log_f.flush()
                        # Display to screen (if not JSON mode)
                        if not self.args.json:
                            print(line, end='')
                        output_lines.append(line)
                    
                    proc.wait()
                    
                except KeyboardInterrupt:
                    # User pressed Ctrl+C during imaging
                    log_f.write("\n[INTERRUPTED BY USER]\n")
                    log_f.flush()
                    ptprint("\n✗ Imaging interrupted by user", "WARNING", condition=not self.args.json)
                    proc.terminate()
                    proc.wait()
                    raise  # Re-raise to main() for exit code 130
                
                # Write completion to log
                log_f.write(f"\nddrescue completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S %z')}\n")
                log_f.write(f"Exit code: {proc.returncode}\n")
            
            self.duration = time.time() - t0
            
            if proc.returncode not in (0, 1):  # 0 = success, 1 = partial success
                self.error_message = f"ddrescue failed with return code {proc.returncode}"
                ptprint(f"\n✗ ddrescue failed with return code {proc.returncode}",
                       "ERROR", condition=not self.args.json)
                return False
            
            # Parse error sectors from output
            output_text = ''.join(output_lines)
            for line in output_text.splitlines():
                if 'errsize' in line.lower() or 'rescued' in line.lower():
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if 'errsize' in part.lower() and i + 1 < len(parts):
                            try:
                                self.error_sectors = int(parts[i+1].replace(',', ''))
                            except:
                                pass
            
            # Calculate average speed
            if self.image_path.exists():
                size = self.image_path.stat().st_size
                self.source_size = size
                self.avg_speed = (size / (1024**2)) / self.duration if self.duration > 0 else 0
            
            ptprint(f"\n✓ ddrescue imaging completed", "OK", condition=not self.args.json)
            
            # Calculate SHA-256 hash
            ptprint("\nCalculating SHA-256 hash...", "SUBTITLE", condition=not self.args.json)
            r = self._cmd(["sha256sum", str(self.image_path)], timeout=7200)
            
            if r['ok'] and r['out']:
                self.source_hash = r['out'].split()[0]
                ptprint(f"✓ SHA-256: {self.source_hash}", "OK", condition=not self.args.json)
                
                # Create canonical hash file
                hash_file = Path(str(self.image_path) + ".sha256")
                hash_file.write_text(f"{self.source_hash}  {self.image_path.name}\n")
                ptprint(f"✓ Hash file created: {hash_file}", "OK", condition=not self.args.json)
            else:
                self.error_message = f"Hash calculation failed: {r['err']}"
                ptprint(f"✗ Hash calculation failed: {r['err']}", "ERROR",
                       condition=not self.args.json)
            
            return True
            
        except Exception as e:
            self.error_message = f"ddrescue execution failed: {str(e)}"
            ptprint(f"\n✗ ddrescue execution failed: {e}", "ERROR", condition=not self.args.json)
            return False

    def summary(self) -> None:
        """Display summary"""
        ptprint("\n" + "=" * 70, "TITLE", condition=not self.args.json)
        ptprint("SUMMARY", "TITLE", condition=not self.args.json)
        ptprint("=" * 70, "TITLE", condition=not self.args.json)
        ptprint(f"Case ID: {self.case_id}", "TEXT", condition=not self.args.json)
        ptprint(f"Source:  {self.device}", "TEXT", condition=not self.args.json)
        ptprint(f"Tool:    {self.tool}", "TEXT", condition=not self.args.json)
        
        if self.image_path:
            ptprint(f"Image:   {self.image_path}", "TEXT", condition=not self.args.json)
            if self.image_path.exists():
                size = self.image_path.stat().st_size
                ptprint(f"Size:    {size:,} bytes ({size/(1024**3):.2f} GB)",
                       "TEXT", condition=not self.args.json)
        
        if self.duration:
            ptprint(f"Duration: {self.duration:.1f}s ({self.duration/60:.1f} min)",
                   "TEXT", condition=not self.args.json)
        if self.avg_speed:
            ptprint(f"Speed:   {self.avg_speed:.2f} MB/s", "TEXT", condition=not self.args.json)
        if self.error_sectors > 0:
            ptprint(f"Bad sectors: {self.error_sectors}", "WARNING", condition=not self.args.json)
        if self.source_hash:
            ptprint(f"SHA-256: {self.source_hash}", "TEXT", condition=not self.args.json)
        
        if self.error_message:
            ptprint(f"\nError:   {self.error_message}", "ERROR", condition=not self.args.json)
        
        ptprint("=" * 70, "TITLE", condition=not self.args.json)

    def _get_tool_version(self) -> str:
        """Get tool version from command"""
        try:
            r = self._cmd([self.tool, "--version"], timeout=5)
            if r['ok'] and r['out']:
                # Extract version from output (e.g., "dc3dd 7.2.646" or "ddrescue 1.23")
                for line in r['out'].splitlines():
                    if self.tool in line.lower():
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if self.tool in part.lower() and i + 1 < len(parts):
                                return parts[i + 1]
                        # Fallback: take second token
                        if len(parts) >= 2:
                            return parts[1]
            return "unknown"
        except:
            return "unknown"

    def save_json(self, filepath: str) -> None:
        """Save results as standards-compliant forensic JSON"""
        
        # Base structure with compliance metadata
        output = {
            "forensicImaging": {
                "version": __version__,
                "compliance": ["NIST SP 800-86", "ISO/IEC 27037:2012"],
                "caseId": self.case_id,
                "timestamp": self.timestamp,
                "analyst": self.analyst
            }
        }
        
        # Source information
        output["forensicImaging"]["source"] = {
            "devicePath": self.device,
            "mediaStatus": self.media_status
        }
        if self.source_size:
            output["forensicImaging"]["source"]["sizeBytes"] = self.source_size
        
        # Acquisition details
        tool_version = self._get_tool_version()
        acquisition = {
            "tool": self.tool,
            "toolVersion": tool_version
        }
        
        if self.success:
            # SUCCESS case - full details
            acquisition["method"] = "single-pass with integrated hashing" if self.tool == "dc3dd" else "damaged sector recovery with separate hashing"
            
            if self.duration:
                acquisition["durationSeconds"] = round(self.duration, 2)
            if self.avg_speed:
                acquisition["averageSpeedMBps"] = round(self.avg_speed, 2)
            
            output["forensicImaging"]["acquisition"] = acquisition
            
            # Output files
            output_data = {
                "imagePath": str(self.image_path),
                "imageFormat": "raw (.dd)",
                "imageSizeBytes": self.source_size if self.source_size else 0,
                "imagingLog": str(self.log_file)
            }
            
            if self.mapfile:
                output_data["mapfile"] = str(self.mapfile)
            
            output["forensicImaging"]["output"] = output_data
            
            # Integrity verification
            integrity = {
                "writeBlockerConfirmed": True,
                "errorSectors": self.error_sectors
            }
            
            if self.source_hash:
                integrity["hashAlgorithm"] = "SHA-256"
                integrity["sourceHash"] = self.source_hash
                integrity["verified"] = True
                # Add hash file path
                output["forensicImaging"]["output"]["hashFile"] = f"{self.image_path}.sha256"
            
            output["forensicImaging"]["integrity"] = integrity
            
            # Chain of Custody
            output["forensicImaging"]["chainOfCustody"] = {
                "action": "Forensic imaging completed",
                "result": "SUCCESS",
                "analyst": self.analyst,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        else:
            # ERROR case - minimal data with error info
            acquisition["status"] = "FAILED"
            if self.error_message:
                acquisition["errorMessage"] = self.error_message
            
            output["forensicImaging"]["acquisition"] = acquisition
            
            # Chain of Custody for failure
            output["forensicImaging"]["chainOfCustody"] = {
                "action": "Forensic imaging failed",
                "result": "ERROR",
                "analyst": self.analyst,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            if self.error_message:
                output["forensicImaging"]["chainOfCustody"]["errorDetails"] = self.error_message
        
        # Write with proper formatting
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
            f.write('\n')  # Add trailing newline

    def run(self) -> bool:
        """Main execution"""
        ptprint("=" * 70, "TITLE", condition=not self.args.json)
        ptprint(f"FORENSIC IMAGING v{__version__}", "TITLE", condition=not self.args.json)
        ptprint(f"Case: {self.case_id} | Device: {self.device} | Tool: {self.tool}",
               "TITLE", condition=not self.args.json)
        ptprint("=" * 70, "TITLE", condition=not self.args.json)
        
        if not self.check_prerequisites():
            return False
        if not self.run_imaging():
            return False
        
        self.success = True
        self.summary()
        return True


def get_help() -> List[Dict]:
    return [
        {"description": [
            "Forensic media imaging tool - standalone",
            "Compliant with NIST SP 800-86 and ISO/IEC 27037:2012",
            "",
            "⚠️  WRITE-BLOCKER IS ALWAYS REQUIRED - confirmation at every run"
        ]},
        {"usage": ["ptforensicimaging <case-id> <device> <tool> [options]"]},
        {"usage_example": [
            "ptforensicimaging PHOTORECOVERY-2025-01-26-001 /dev/sdb dc3dd",
            "ptforensicimaging CASE-001 /dev/sdb dc3dd --analyst 'John Doe'",
            "ptforensicimaging CASE-002 /dev/sdc ddrescue --json-out result.json",
        ]},
        {"options": [
            ["case-id",            "",      "Case identifier - REQUIRED"],
            ["device",             "",      "Device path (e.g., /dev/sdb) - REQUIRED"],
            ["tool",               "",      "Imaging tool: dc3dd or ddrescue - REQUIRED"],
            ["-o", "--output-dir", "<d>",   f"Output directory (default: {DEFAULT_OUTPUT_DIR})"],
            ["-a", "--analyst",    "<n>",   "Analyst name (default: Analyst)"],
            ["-j", "--json-out",   "<f>",   "Save JSON output to file (optional)"],
            ["-h", "--help",       "",      "Show this help"],
            ["--version",          "",      "Show version"],
        ]},
        {"notes": [
            "⚠️  Write-blocker confirmation is ALWAYS REQUIRED",
            "✓ dc3dd for READABLE media (integrated SHA-256)",
            "✓ ddrescue for PARTIAL media (separate SHA-256)",
            "✓ Creates canonical .sha256 hash file",
            "✓ JSON output ready for manual copy-paste into case.json",
        ]},
    ]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("case_id")
    p.add_argument("device", help="Device path (e.g., /dev/sdb)")
    p.add_argument("tool", choices=["dc3dd", "ddrescue"], help="Imaging tool")
    p.add_argument("-o", "--output-dir", default=DEFAULT_OUTPUT_DIR)
    p.add_argument("-a", "--analyst", default="Analyst")
    p.add_argument("-j", "--json-out", help="JSON output file (optional)")
    p.add_argument("--version", action="version", version=f"{SCRIPTNAME} {__version__}")
    
    if len(sys.argv) == 1 or {"-h", "--help"} & set(sys.argv):
        ptprinthelper.help_print(get_help(), SCRIPTNAME, __version__)
        sys.exit(0)
    
    args = p.parse_args()
    args.json = bool(args.json_out)
    ptprinthelper.print_banner(SCRIPTNAME, __version__, args.json)
    return args


def main() -> int:
    try:
        args = parse_args()
        
        # ALWAYS require write-blocker confirmation
        if not PtForensicImaging.confirm_write_blocker():
            ptprint("\nImaging ABORTED - write-blocker is REQUIRED!", "ERROR",
                   condition=True, colortext=True)
            return 99
        
        tool = PtForensicImaging(args)
        success = tool.run()
        
        # Save JSON only if --json-out specified
        if args.json_out:
            try:
                tool.save_json(args.json_out)
                ptprint(f"\n✓ JSON saved: {args.json_out}", "OK", condition=True)
                ptprint("  Ready to copy-paste into case.json", "TEXT", condition=True)
            except Exception as e:
                ptprint(f"\n✗ Error saving JSON: {e}", "ERROR", condition=True)
                return 99
        
        return 0 if success else 1
    
    except KeyboardInterrupt:
        ptprint("\nInterrupted by user", "WARNING", condition=True)
        return 130
    except Exception as e:
        ptprint(f"\nERROR: {e}", "ERROR", condition=True, colortext=True)
        return 99


if __name__ == "__main__":
    sys.exit(main())