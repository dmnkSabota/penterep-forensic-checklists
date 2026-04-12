#!/usr/bin/env python3
"""
    Copyright (c) 2025 Bc. Dominik Sabota, VUT FIT Brno
    ptimageverification - Forensic image hash verification tool
    
    Standalone tool for forensic image integrity verification.
    Compares source_hash (Step 5) with image_hash (calculated from file).
    
    Usage: ptimageverification CASE-ID [--analyst NAME] [--output file.json]
    
    Compliant with NIST SP 800-86 and ISO/IEC 27037:2012.
"""

import argparse
import sys
import os
import json
import hashlib
import subprocess
import signal
import time
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

SCRIPTNAME = "ptimageverification"
DEFAULT_OUTPUT_DIR = "/var/forensics/images"
HASH_BLOCK_SIZE = 4 * 1024 * 1024  # 4 MB chunks


class PtImageVerification:
    """
    Standalone forensic image verification tool
    
    Two-phase integrity verification:
      Phase 1 (Step 5): source_hash from imaging
      Phase 2 (Step 6): image_hash from file on disk
    
    Hash match proves bit-for-bit forensic integrity.
    """

    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.case_id = args.case_id
        self.analyst = args.analyst
        self.output_dir = Path(args.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Results storage
        self.image_path = None
        self.image_format = None
        self.image_size = None
        self.source_hash = None
        self.image_hash = None
        self.calculation_time = None
        self.hash_match = None
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.error_message = None
        self.success = False

    def _cmd(self, cmd: List[str], timeout: Optional[int] = 30) -> Dict[str, Any]:
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

    def load_source_hash(self) -> bool:
        """Step 1: Load source_hash from Step 5 imaging results"""
        ptprint("\n" + "=" * 70, "TITLE", condition=not self.args.json)
        ptprint("STEP 1: Load Source Hash from Step 5", "TITLE", condition=not self.args.json)
        ptprint("=" * 70, "TITLE", condition=not self.args.json)
        
        # Find Step 5 imaging JSON
        pattern = f"{self.case_id}*.json"
        candidates = sorted(self.output_dir.glob(pattern), reverse=True)
        
        if not candidates:
            self.error_message = f"Step 5 imaging results not found in {self.output_dir}"
            ptprint(f"✗ Imaging results not found: {pattern}", "ERROR", condition=not self.args.json)
            ptprint("  Run Step 5 (ptforensicimaging) first", "ERROR", condition=not self.args.json)
            return False
        
        # Try to load from first matching file
        for json_file in candidates:
            try:
                data = json.loads(json_file.read_text(encoding='utf-8'))
                
                # Try new format first (Step 5 updated)
                if 'forensicImaging' in data:
                    self.source_hash = data['forensicImaging'].get('integrity', {}).get('sourceHash')
                # Fallback to old ptlibs format
                elif 'result' in data:
                    self.source_hash = data['result'].get('properties', {}).get('sourceHash')
                
                if self.source_hash:
                    break
            except Exception as e:
                ptprint(f"⚠ Error reading {json_file.name}: {e}", "WARNING", condition=not self.args.json)
                continue
        
        if not self.source_hash:
            self.error_message = "Source hash not found in imaging results"
            ptprint("✗ Source hash not found", "ERROR", condition=not self.args.json)
            ptprint("  Step 5 may not have completed successfully", "ERROR", condition=not self.args.json)
            return False
        
        # Validate format: 64 lowercase hex chars
        if len(self.source_hash) != 64 or not all(c in '0123456789abcdef' for c in self.source_hash.lower()):
            self.error_message = f"Invalid source hash format: {self.source_hash}"
            ptprint(f"✗ Invalid hash format: {self.source_hash}", "ERROR", condition=not self.args.json)
            return False
        
        ptprint(f"✓ Source hash loaded: {self.source_hash[:16]}...", "OK", condition=not self.args.json)
        return True

    def find_image(self) -> bool:
        """Step 2: Locate forensic image file"""
        ptprint("\n" + "=" * 70, "TITLE", condition=not self.args.json)
        ptprint("STEP 2: Locate Forensic Image", "TITLE", condition=not self.args.json)
        ptprint("=" * 70, "TITLE", condition=not self.args.json)
        
        # Try common image formats
        for suffix in ('.dd', '.raw', '.E01', '.e01'):
            path = self.output_dir / f"{self.case_id}{suffix}"
            if path.exists():
                self.image_path = path
                self.image_format = suffix.lower()
                self.image_size = path.stat().st_size
                
                ptprint(f"✓ Image found: {path.name}", "OK", condition=not self.args.json)
                ptprint(f"  Format: {self.image_format}", "TEXT", condition=not self.args.json)
                ptprint(f"  Size: {self.image_size:,} bytes ({self.image_size/(1024**3):.2f} GB)",
                       "TEXT", condition=not self.args.json)
                return True
        
        self.error_message = f"Image file not found for case {self.case_id}"
        ptprint(f"✗ No image file found: {self.case_id}.dd/.raw/.E01", "ERROR",
               condition=not self.args.json)
        ptprint("  Run Step 5 (ptforensicimaging) first", "ERROR", condition=not self.args.json)
        return False

    def calculate_hash(self) -> bool:
        """Step 3: Calculate SHA-256 hash of image file"""
        ptprint("\n" + "=" * 70, "TITLE", condition=not self.args.json)
        ptprint("STEP 3: Calculate Image Hash", "TITLE", condition=not self.args.json)
        ptprint("=" * 70, "TITLE", condition=not self.args.json)
        
        if self.image_format in ('.dd', '.raw'):
            return self._hash_raw()
        elif self.image_format in ('.e01',):
            return self._hash_e01()
        else:
            self.error_message = f"Unsupported image format: {self.image_format}"
            ptprint(f"✗ Unsupported format: {self.image_format}", "ERROR", condition=not self.args.json)
            return False

    def _hash_raw(self) -> bool:
        """Calculate SHA-256 for RAW images"""
        ptprint(f"\nCalculating SHA-256 hash (hashlib, 4 MB chunks)...", "SUBTITLE",
               condition=not self.args.json)
        
        size_gb = self.image_size / (1024**3)
        est_time_min = size_gb * 1024 / (200 * 60)  # Assuming 200 MB/s
        ptprint(f"Estimated time: ~{est_time_min:.1f} min (assuming 200 MB/s)",
               "TEXT", condition=not self.args.json)
        
        sha = hashlib.sha256()
        read = 0
        last_gb = 0.0
        t0 = time.time()
        
        try:
            with open(self.image_path, 'rb') as f:
                while chunk := f.read(HASH_BLOCK_SIZE):
                    sha.update(chunk)
                    read += len(chunk)
                    
                    # Progress every 1 GB
                    current_gb = read / (1024**3)
                    if current_gb - last_gb >= 1.0:
                        elapsed = time.time() - t0
                        speed = (read / (1024**2)) / elapsed if elapsed > 0 else 0
                        ptprint(f"Progress: {current_gb:.1f} GB | {speed:.0f} MB/s",
                               "TEXT", condition=not self.args.json)
                        last_gb = current_gb
            
            self.calculation_time = time.time() - t0
            self.image_hash = sha.hexdigest()
            avg_speed = (self.image_size / (1024**2)) / self.calculation_time if self.calculation_time > 0 else 0
            
            ptprint(f"\n✓ Hash calculation completed", "OK", condition=not self.args.json)
            ptprint(f"  Duration: {self.calculation_time:.0f}s ({self.calculation_time/60:.1f} min)",
                   "TEXT", condition=not self.args.json)
            ptprint(f"  Average speed: {avg_speed:.0f} MB/s", "TEXT", condition=not self.args.json)
            ptprint(f"  Image hash: {self.image_hash}", "TEXT", condition=not self.args.json)
            return True
            
        except Exception as e:
            self.error_message = f"Hash calculation failed: {str(e)}"
            ptprint(f"\n✗ Hash calculation failed: {e}", "ERROR", condition=not self.args.json)
            return False

    def _hash_e01(self) -> bool:
        """Calculate hash for E01 images using ewfverify"""
        ptprint(f"\nUsing ewfverify for E01 format...", "SUBTITLE", condition=not self.args.json)
        
        if not self._has("ewfverify"):
            self.error_message = "ewfverify not installed"
            ptprint("✗ ewfverify not found", "ERROR", condition=not self.args.json)
            ptprint("  Install: sudo apt install libewf-tools", "ERROR", condition=not self.args.json)
            return False
        
        t0 = time.time()
        try:
            r = subprocess.run(
                ["ewfverify", "-d", "sha256", str(self.image_path)],
                capture_output=True, text=True, timeout=7200
            )
            self.calculation_time = time.time() - t0
            
            if r.returncode != 0:
                self.error_message = f"ewfverify failed: {r.stderr}"
                ptprint(f"✗ ewfverify failed: {r.stderr}", "ERROR", condition=not self.args.json)
                return False
            
            # Parse hash from output
            for line in r.stdout.splitlines():
                if 'sha256' in line.lower() and ':' in line:
                    self.image_hash = line.split(':')[-1].strip()
                    break
            
            if not self.image_hash:
                self.error_message = "Could not parse hash from ewfverify output"
                ptprint("✗ Hash parsing failed", "ERROR", condition=not self.args.json)
                return False
            
            ptprint(f"✓ Hash calculation completed in {self.calculation_time:.0f}s",
                   "OK", condition=not self.args.json)
            ptprint(f"  Image hash: {self.image_hash}", "TEXT", condition=not self.args.json)
            return True
            
        except subprocess.TimeoutExpired:
            self.error_message = "ewfverify timeout (2 hours)"
            ptprint("✗ ewfverify timeout", "ERROR", condition=not self.args.json)
            return False
        except Exception as e:
            self.error_message = f"Hash calculation failed: {str(e)}"
            ptprint(f"✗ Hash calculation failed: {e}", "ERROR", condition=not self.args.json)
            return False

    def verify_match(self) -> bool:
        """Step 4: Compare source_hash with image_hash"""
        ptprint("\n" + "=" * 70, "TITLE", condition=not self.args.json)
        ptprint("STEP 4: Verify Hash Match", "TITLE", condition=not self.args.json)
        ptprint("=" * 70, "TITLE", condition=not self.args.json)
        
        if not self.source_hash or not self.image_hash:
            self.error_message = "Missing hash values for comparison"
            ptprint("✗ Missing hash values", "ERROR", condition=not self.args.json)
            return False
        
        ptprint(f"\nSource hash (Step 5): {self.source_hash}", "TEXT", condition=not self.args.json)
        ptprint(f"Image hash  (file):   {self.image_hash}", "TEXT", condition=not self.args.json)
        
        self.hash_match = (self.source_hash == self.image_hash)
        
        if self.hash_match:
            ptprint("\n" + "✓" * 70, "OK", condition=not self.args.json)
            ptprint("HASH MATCH - Image integrity VERIFIED", "OK",
                   condition=not self.args.json, colortext=True)
            ptprint("✓" * 70, "OK", condition=not self.args.json)
            ptprint("\nImage is bit-for-bit identical to source media.", "OK",
                   condition=not self.args.json)
            return True
        else:
            ptprint("\n" + "✗" * 70, "ERROR", condition=not self.args.json)
            ptprint("HASH MISMATCH - CRITICAL ERROR", "ERROR",
                   condition=not self.args.json, colortext=True)
            ptprint("✗" * 70, "ERROR", condition=not self.args.json)
            ptprint("\nPossible causes:", "ERROR", condition=not self.args.json)
            ptprint("  • I/O error during imaging", "ERROR", condition=not self.args.json)
            ptprint("  • File corrupted on disk", "ERROR", condition=not self.args.json)
            ptprint("  • Image modified after creation", "ERROR", condition=not self.args.json)
            ptprint("  • Media degraded during imaging", "ERROR", condition=not self.args.json)
            ptprint("\nAction required: Repeat Step 5 (imaging)", "ERROR",
                   condition=not self.args.json)
            self.error_message = "Hash mismatch - imaging must be repeated"
            return False

    def summary(self) -> None:
        """Display summary"""
        ptprint("\n" + "=" * 70, "TITLE", condition=not self.args.json)
        ptprint("SUMMARY", "TITLE", condition=not self.args.json)
        ptprint("=" * 70, "TITLE", condition=not self.args.json)
        ptprint(f"Case ID: {self.case_id}", "TEXT", condition=not self.args.json)
        ptprint(f"Image:   {self.image_path.name if self.image_path else 'N/A'}", "TEXT",
               condition=not self.args.json)
        ptprint(f"Status:  {'VERIFIED' if self.hash_match else 'MISMATCH'}", "TEXT",
               condition=not self.args.json)
        
        if self.error_message:
            ptprint(f"\nError:   {self.error_message}", "ERROR", condition=not self.args.json)
        
        ptprint("=" * 70, "TITLE", condition=not self.args.json)

    def save_json(self, filepath: str) -> None:
        """Save results as standards-compliant forensic JSON"""
        
        # Base structure with compliance metadata
        output = {
            "hashVerification": {
                "version": __version__,
                "compliance": ["NIST SP 800-86", "ISO/IEC 27037:2012"],
                "caseId": self.case_id,
                "timestamp": self.timestamp,
                "analyst": self.analyst
            }
        }
        
        # Image information
        output["hashVerification"]["image"] = {
            "imagePath": str(self.image_path) if self.image_path else None,
            "imageFormat": self.image_format,
            "imageSizeBytes": self.image_size
        }
        
        if self.success:
            # SUCCESS case - full verification details
            output["hashVerification"]["verification"] = {
                "algorithm": "SHA-256",
                "sourceHash": self.source_hash,
                "imageHash": self.image_hash,
                "hashMatch": self.hash_match,
                "verificationStatus": "VERIFIED" if self.hash_match else "MISMATCH",
                "calculationTimeSeconds": round(self.calculation_time, 2) if self.calculation_time else None
            }
            
            # Chain of Custody
            output["chainOfCustodyEntry"] = {
                "action": f"Verifikácia integrity obrazu – výsledok: {'VERIFIED' if self.hash_match else 'MISMATCH'}",
                "result": "SUCCESS" if self.hash_match else "ERROR",
                "analyst": self.analyst,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            if not self.hash_match:
                output["chainOfCustodyEntry"]["errorDetails"] = "Hash mismatch - imaging must be repeated"
        else:
            # ERROR case - minimal data with error info
            if self.error_message:
                output["hashVerification"]["errorMessage"] = self.error_message
            
            # Partial verification data if available
            if self.source_hash:
                output["hashVerification"]["verification"] = {
                    "algorithm": "SHA-256",
                    "sourceHash": self.source_hash,
                    "imageHash": self.image_hash,
                    "verificationStatus": "ERROR"
                }
            
            # Chain of Custody for failure
            output["chainOfCustodyEntry"] = {
                "action": "Verifikácia integrity obrazu – zlyhanie",
                "result": "ERROR",
                "analyst": self.analyst,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            if self.error_message:
                output["chainOfCustodyEntry"]["errorDetails"] = self.error_message
        
        # Write with proper formatting
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
            f.write('\n')
        
        # Create canonical hash file if we have image_hash
        if self.image_hash and self.image_path:
            hash_file = Path(str(self.image_path) + ".sha256")
            hash_file.write_text(f"{self.image_hash}  {self.image_path.name}\n")

    def run(self) -> bool:
        """Main execution"""
        ptprint("=" * 70, "TITLE", condition=not self.args.json)
        ptprint(f"IMAGE VERIFICATION v{__version__}", "TITLE", condition=not self.args.json)
        ptprint(f"Case: {self.case_id}", "TITLE", condition=not self.args.json)
        ptprint("=" * 70, "TITLE", condition=not self.args.json)
        
        if not self.load_source_hash():
            return False
        if not self.find_image():
            return False
        if not self.calculate_hash():
            return False
        if not self.verify_match():
            return False
        
        self.success = True
        self.summary()
        return True


def get_help() -> List[Dict]:
    return [
        {"description": [
            "Forensic image hash verification tool - standalone",
            "Compares source_hash (Step 5) with image_hash (file)",
            "Compliant with NIST SP 800-86 and ISO/IEC 27037:2012",
        ]},
        {"usage": ["ptimageverification <case-id> [options]"]},
        {"usage_example": [
            "ptimageverification PHOTORECOVERY-2025-01-26-001",
            "ptimageverification CASE-001 --analyst 'John Doe'",
            "ptimageverification CASE-002 --output result.json",
        ]},
        {"options": [
            ["case-id",            "",      "Case identifier - REQUIRED"],
            ["-o", "--output-dir", "<d>",   f"Output directory (default: {DEFAULT_OUTPUT_DIR})"],
            ["-a", "--analyst",    "<n>",   "Analyst name (default: Analyst)"],
            ["-j", "--json-out",   "<f>",   "Save JSON output to file (optional)"],
            ["-h", "--help",       "",      "Show this help"],
            ["--version",          "",      "Show version"],
        ]},
        {"notes": [
            "✓ Requires Step 5 (ptforensicimaging) results",
            "✓ Hash match proves bit-for-bit integrity",
            "✓ Supports RAW (.dd, .raw) and E01 formats",
            "✓ MISMATCH = repeat Step 5 imaging",
        ]},
    ]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("case_id")
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
        
        tool = PtImageVerification(args)
        success = tool.run()
        
        # Save JSON only if --json-out specified
        if args.json_out:
            try:
                tool.save_json(args.json_out)
                ptprint(f"\n✓ JSON saved: {args.json_out}", "OK", condition=True)
                ptprint("  Ready to copy-paste into case.json", "TEXT", condition=True)
                
                if tool.image_hash and tool.image_path:
                    hash_file = Path(str(tool.image_path) + ".sha256")
                    ptprint(f"✓ Hash file saved: {hash_file}", "OK", condition=True)
            except Exception as e:
                ptprint(f"\n✗ Error saving JSON: {e}", "ERROR", condition=True)
                return 99
        
        # Return codes: 0 = VERIFIED, 1 = MISMATCH, 99 = ERROR
        if success and tool.hash_match:
            return 0
        elif success and not tool.hash_match:
            return 1
        else:
            return 99
    
    except KeyboardInterrupt:
        ptprint("\nInterrupted by user", "WARNING", condition=True)
        return 130
    except Exception as e:
        ptprint(f"\nERROR: {e}", "ERROR", condition=True, colortext=True)
        return 99


if __name__ == "__main__":
    sys.exit(main())