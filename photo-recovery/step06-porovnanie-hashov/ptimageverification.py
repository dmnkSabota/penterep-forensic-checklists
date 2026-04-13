#!/usr/bin/env python3
"""
ptimageverification - Step 6: Hash Verification
Calculates image_hash and compares with source_hash to verify integrity.

Part of: Photo Recovery Forensic Toolkit (Scenario 2)
Phase: Collection (Steps 1-6)
Standards: NIST SP 800-86, ISO/IEC 27037:2012
"""

import sys
import os
import json
import hashlib
import subprocess
import signal
import time
from datetime import datetime, timezone
from pathlib import Path

__version__ = "1.0.0"

HASH_BLOCK_SIZE = 4 * 1024 * 1024  # 4 MB chunks


class ImageVerificationTool:
    """Step 6: Calculate image_hash and verify against source_hash."""
    
    def __init__(self):
        self.case_id = None
        self.analyst = "Analyst"
        self.image_path = None
        self.source_hash = None
        self.output_file = None
        
        # Results storage
        self.image_format = None
        self.image_size = None
        self.image_hash = None
        self.calculation_time = None
        self.hash_match = None
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.error_message = None
        self.success = False
        
        # Signal handler
        signal.signal(signal.SIGINT, self._custom_sigint_handler)
    
    def _custom_sigint_handler(self, sig, frame):
        """Handle Ctrl+C gracefully."""
        raise KeyboardInterrupt
    
    def _cmd(self, cmd, timeout=30):
        """Execute command and return (stdout, stderr, returncode)."""
        try:
            result = subprocess.run(
                cmd if isinstance(cmd, list) else cmd.split(),
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.stdout.strip(), result.stderr.strip(), result.returncode
        except subprocess.TimeoutExpired:
            return None, f"Timeout after {timeout}s", -1
        except Exception as e:
            return None, str(e), -1
    
    def _has(self, cmd):
        """Check if command exists."""
        stdout, _, ret = self._cmd(["which", cmd], timeout=5)
        return ret == 0
    
    def _fail(self, msg):
        """Fail with error message."""
        self.error_message = msg
        self.success = False
        print(f"\n[ERROR] ERROR: {msg}\n", file=sys.stderr)
    
    def validate_source_hash(self):
        """Validate source_hash format."""
        print("\n[1/3] Validating Source Hash")
        
        if not self.source_hash:
            self._fail("Source hash is required")
            return False
        
        # Validate format: 64 lowercase hex chars
        if len(self.source_hash) != 64:
            self._fail(f"Invalid hash length: {len(self.source_hash)} (expected 64)")
            return False
        
        if not all(c in '0123456789abcdef' for c in self.source_hash.lower()):
            self._fail("Invalid hash format (must be 64 hexadecimal characters)")
            return False
        
        self.source_hash = self.source_hash.lower()
        print(f"[OK] Source hash valid: {self.source_hash[:16]}...")
        return True
    
    def find_image(self):
        """Locate and validate forensic image file."""
        print("\n[2/3] Locating Forensic Image")
        
        if not self.image_path.exists():
            self._fail(f"Image file not found: {self.image_path}")
            return False
        
        self.image_format = self.image_path.suffix.lower()
        self.image_size = self.image_path.stat().st_size
        
        print(f"[OK] Image found: {self.image_path.name}")
        print(f"  Format: {self.image_format}")
        print(f"  Size: {self.image_size:,} bytes ({self.image_size/(1024**3):.2f} GB)")
        return True
    
    def calculate_hash(self):
        """Calculate SHA-256 hash of image file."""
        print("\n[3/3] Calculating Image Hash")
        
        if self.image_format in ('.dd', '.raw'):
            return self._hash_raw()
        elif self.image_format in ('.e01',):
            return self._hash_e01()
        else:
            self._fail(f"Unsupported image format: {self.image_format}")
            return False
    
    def _hash_raw(self):
        """Calculate SHA-256 for RAW images."""
        print(f"\nCalculating SHA-256 hash (4 MB chunks)...")
        
        size_gb = self.image_size / (1024**3)
        est_time_min = size_gb * 1024 / (200 * 60)  # Assuming 200 MB/s
        print(f"Estimated time: ~{est_time_min:.1f} min (assuming 200 MB/s)")
        
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
                        print(f"Progress: {current_gb:.1f} GB | {speed:.0f} MB/s")
                        last_gb = current_gb
            
            self.calculation_time = time.time() - t0
            self.image_hash = sha.hexdigest()
            avg_speed = (self.image_size / (1024**2)) / self.calculation_time if self.calculation_time > 0 else 0
            
            print(f"\n[OK] Hash calculation completed")
            print(f"  Duration: {self.calculation_time:.0f}s ({self.calculation_time/60:.1f} min)")
            print(f"  Average speed: {avg_speed:.0f} MB/s")
            print(f"  Image hash: {self.image_hash}")
            return True
            
        except Exception as e:
            self._fail(f"Hash calculation failed: {str(e)}")
            return False
    
    def _hash_e01(self):
        """Calculate hash for E01 images using ewfverify."""
        print(f"\nUsing ewfverify for E01 format...")
        
        if not self._has("ewfverify"):
            self._fail("ewfverify not installed (sudo apt install libewf-tools)")
            return False
        
        t0 = time.time()
        try:
            stdout, stderr, ret = self._cmd(
                ["ewfverify", "-d", "sha256", str(self.image_path)],
                timeout=7200
            )
            self.calculation_time = time.time() - t0
            
            if ret != 0:
                self._fail(f"ewfverify failed: {stderr}")
                return False
            
            # Parse hash from output
            for line in stdout.splitlines():
                if 'sha256' in line.lower() and ':' in line:
                    self.image_hash = line.split(':')[-1].strip()
                    break
            
            if not self.image_hash:
                self._fail("Could not parse hash from ewfverify output")
                return False
            
            print(f"[OK] Hash calculation completed in {self.calculation_time:.0f}s")
            print(f"  Image hash: {self.image_hash}")
            return True
            
        except subprocess.TimeoutExpired:
            self._fail("ewfverify timeout (2 hours)")
            return False
        except Exception as e:
            self._fail(f"Hash calculation failed: {str(e)}")
            return False
    
    def verify_match(self):
        """Compare source_hash with image_hash."""
        print("\n" + "="*70)
        print("HASH VERIFICATION")
        print("="*70)
        
        if not self.source_hash or not self.image_hash:
            self._fail("Missing hash values for comparison")
            return False
        
        print(f"\nSource hash (imaging): {self.source_hash}")
        print(f"Image hash  (file):   {self.image_hash}")
        
        self.hash_match = (self.source_hash == self.image_hash)
        
        if self.hash_match:
            print("\n" + "[OK]" * 70)
            print("HASH MATCH - Image integrity VERIFIED")
            print("[OK]" * 70)
            print("\nImage is bit-for-bit identical to source media.")
            return True
        else:
            print("\n" + "[ERROR]" * 70)
            print("HASH MISMATCH - CRITICAL ERROR")
            print("[ERROR]" * 70)
            print("\nPossible causes:")
            print("  • I/O error during imaging")
            print("  • File corrupted on disk")
            print("  • Image modified after creation")
            print("  • Media degraded during imaging")
            print("\nAction required: Repeat imaging")
            self._fail("Hash mismatch - imaging must be repeated")
            return False
    
    def save_json(self):
        """Save results to JSON."""
        data = {
            "hashVerification": {
                "version": __version__,
                "compliance": ["NIST SP 800-86", "ISO/IEC 27037:2012"],
                "caseId": self.case_id,
                "timestamp": self.timestamp,
                "analyst": self.analyst,
                "image": {
                    "imagePath": str(self.image_path),
                    "imageFormat": self.image_format,
                    "imageSizeBytes": self.image_size
                }
            }
        }
        
        if self.success:
            data["hashVerification"]["verification"] = {
                "algorithm": "SHA-256",
                "sourceHash": self.source_hash,
                "imageHash": self.image_hash,
                "hashMatch": self.hash_match,
                "verificationStatus": "VERIFIED" if self.hash_match else "MISMATCH",
                "calculationTimeSeconds": round(self.calculation_time, 2) if self.calculation_time else None
            }
            
            data["chainOfCustodyEntry"] = {
                "action": f"Verifikácia integrity obrazu – výsledok: {'VERIFIED' if self.hash_match else 'MISMATCH'}",
                "result": "SUCCESS" if self.hash_match else "ERROR",
                "analyst": self.analyst,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            if not self.hash_match:
                data["chainOfCustodyEntry"]["errorDetails"] = "Hash mismatch - imaging must be repeated"
        else:
            if self.error_message:
                data["hashVerification"]["errorMessage"] = self.error_message
            
            if self.source_hash:
                data["hashVerification"]["verification"] = {
                    "algorithm": "SHA-256",
                    "sourceHash": self.source_hash,
                    "imageHash": self.image_hash,
                    "verificationStatus": "ERROR"
                }
            
            data["chainOfCustodyEntry"] = {
                "action": "Verifikácia integrity obrazu – zlyhanie",
                "result": "ERROR",
                "analyst": self.analyst,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            if self.error_message:
                data["chainOfCustodyEntry"]["errorDetails"] = self.error_message
        
        if self.output_file:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.write('\n')
            print(f"\n[OK] Report saved: {Path(self.output_file).name}")
        else:
            print("\n" + "="*70)
            print(" JSON OUTPUT")
            print("="*70)
            print(json.dumps(data, indent=2))
        
        # Create canonical hash file if we have image_hash
        if self.image_hash and self.image_path:
            hash_file = Path(str(self.image_path) + ".sha256")
            hash_file.write_text(f"{self.image_hash}  {self.image_path.name}\n")
            print(f"[OK] Hash file saved: {hash_file.name}")
        
        self.success = True
    
    def run(self):
        """Main execution flow."""
        try:
            print("\n" + "="*70)
            print(" STEP 6: HASH VERIFICATION")
            print("="*70)
            print(f"Version: {__version__}")
            print(f"Case ID: {self.case_id}")
            print(f"Image: {self.image_path}")
            print("="*70)
            
            if not self.validate_source_hash():
                return 1
            if not self.find_image():
                return 1
            if not self.calculate_hash():
                return 1
            if not self.verify_match():
                return 1
            
            self.success = True
            self.save_json()
            
            print("\n" + "="*70)
            print(" VERIFICATION COMPLETED")
            print("="*70)
            print(f"Status: {'VERIFIED' if self.hash_match else 'MISMATCH'}")
            print(f"Next: {'Filesystem Analysis' if self.hash_match else 'Repeat Imaging'}")
            print("="*70)
            
            return 0 if self.hash_match else 1
            
        except KeyboardInterrupt:
            print("\n\n[WARNING]  Operation interrupted by user (Ctrl+C)", file=sys.stderr)
            return 130
        except Exception as e:
            self._fail(f"Unexpected error: {e}")
            return 99


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Step 6: Hash Verification - Calculate image_hash and verify integrity",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  ptimageverification CASE-001 /var/forensics/images/CASE-001.dd SOURCE_HASH --analyst "John Doe"
  
  # With JSON output file
  ptimageverification CASE-001 /path/to/image.dd a3f5e8c9... --output result.json

Exit Codes:
  0   - VERIFIED (hash match)
  1   - MISMATCH (hash mismatch - repeat imaging)
  99  - ERROR (image not found, calculation failed)
  130 - Interrupted (Ctrl+C)

Standards:
  NIST SP 800-86 Section 3.1.2
  ISO/IEC 27037:2012 Section 7.2
        """
    )
    
    parser.add_argument("case_id", help="Case ID (e.g., CASE-2025-001)")
    parser.add_argument("image", help="Path to forensic image file (.dd)")
    parser.add_argument("source_hash", help="SHA-256 hash from forensic imaging (64 hex chars)")
    parser.add_argument("--analyst", "-a", default="Analyst",
                        help="Analyst name for Chain of Custody")
    parser.add_argument("--output", "-o", dest="output",
                        help="JSON output file path")
    parser.add_argument("--version", action="version", version=f"ptimageverification {__version__}")
    
    args = parser.parse_args()
    
    tool = ImageVerificationTool()
    tool.case_id = args.case_id
    tool.analyst = args.analyst
    tool.image_path = Path(args.image)
    tool.source_hash = args.source_hash
    tool.output_file = args.output if args.output else None
    
    exit_code = tool.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()