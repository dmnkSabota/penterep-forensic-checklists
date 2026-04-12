#!/usr/bin/env python3
"""
ptfilesystemanalysis - Step 7: Filesystem Analysis
Analyzes forensic image filesystem structure and recommends recovery strategy.

Part of: Photo Recovery Forensic Toolkit (Scenario 2)
Phase: Analysis (Steps 7-9)
Standards: NIST SP 800-86, ISO/IEC 27037:2012
"""

import sys
import os
import json
import subprocess
import signal
import re
from datetime import datetime, timezone
from pathlib import Path

__version__ = "1.0.0"

# Supported image file extensions
IMAGE_EXTENSIONS = {
    "jpeg": [".jpg", ".jpeg"],
    "png": [".png"],
    "gif": [".gif"],
    "bmp": [".bmp"],
    "tiff": [".tiff", ".tif"],
    "raw": [".raw", ".cr2", ".nef", ".arw", ".dng", ".orf", ".raf"],
    "heic": [".heic", ".heif"],
    "webp": [".webp"],
}

# Filesystem type mapping
FS_TYPE_MAP = {
    "FAT32": "FAT32", "FAT16": "FAT16", "FAT12": "FAT12",
    "exFAT": "exFAT", "NTFS": "NTFS",
    "Ext4": "ext4", "ext4": "ext4",
    "Ext3": "ext3", "ext3": "ext3",
    "Ext2": "ext2", "ext2": "ext2",
    "HFS+": "HFS+", "APFS": "APFS",
    "ISO 9660": "ISO9660",
}

# Recovery strategies: (fs_recognized, dir_readable) → (method, tool, time, notes)
RECOVERY_STRATEGIES = {
    (True, True): (
        "filesystem_scan",
        "fls + icat (The Sleuth Kit)",
        15,
        [
            "Filesystem intact – filesystem-based scan recommended.",
            "Original filenames and directory structure preserved.",
            "Fastest recovery method."
        ]
    ),
    (True, False): (
        "hybrid",
        "fls + photorec",
        60,
        [
            "Filesystem recognised but directory structure damaged.",
            "Hybrid: filesystem scan + file carving on unallocated space.",
            "Some filenames may be lost."
        ]
    ),
    (False, False): (
        "file_carving",
        "photorec / foremost",
        90,
        [
            "Filesystem not recognised or severely damaged.",
            "File carving required (signature-based recovery).",
            "Original filenames and directory structure will be lost."
        ]
    ),
}


class FilesystemAnalysisTool:
    """Step 7: Analyze filesystem and recommend recovery strategy."""
    
    def __init__(self):
        self.case_id = None
        self.analyst = "Analyst"
        self.output_dir = Path("/var/forensics/images")
        self.output_file = None
        
        # Image info
        self.image_path = None
        self.image_size = None
        
        # Analysis results
        self.partition_table_type = None
        self.partitions = []
        self.filesystem_recognized = False
        self.directory_readable = False
        self.total_images = 0
        
        # Strategy
        self.recommended_method = None
        self.recommended_tool = None
        self.estimated_time = None
        self.strategy_notes = []
        
        # Error tracking
        self.error_message = None
        self.success = False
        
        # Signal handler
        signal.signal(signal.SIGINT, self._custom_sigint_handler)
    
    def _custom_sigint_handler(self, sig, frame):
        """Handle Ctrl+C gracefully."""
        raise KeyboardInterrupt
    
    def _cmd(self, cmd, timeout=300):
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
        print(f"\n✗ ERROR: {msg}\n", file=sys.stderr)
    
    def load_image_path(self):
        """Load forensic image path from Step 6 verification JSON."""
        print("\n[1/3] Loading Image Path from Step 6")
        
        # Find Step 6 verification JSON
        candidates = sorted(
            self.output_dir.glob(f"{self.case_id}*verification*.json"),
            reverse=True
        )
        
        for candidate in candidates:
            try:
                with open(candidate, 'r') as f:
                    data = json.load(f)
                
                # Try different JSON structures
                image_path = None
                if "hashVerification" in data:
                    image_path = data["hashVerification"].get("image", {}).get("imagePath")
                elif "result" in data and "properties" in data["result"]:
                    image_path = data["result"]["properties"].get("imagePath")
                
                if image_path and Path(image_path).exists():
                    self.image_path = Path(image_path)
                    self.image_size = self.image_path.stat().st_size
                    print(f"✓ Image path loaded: {self.image_path.name}")
                    return True
            except Exception as e:
                print(f"  Warning: Could not read {candidate.name}: {e}")
                continue
        
        # Fallback: default image location
        fallback = self.output_dir / f"{self.case_id}.dd"
        if fallback.exists():
            self.image_path = fallback
            self.image_size = fallback.stat().st_size
            print(f"✓ Image found at default location: {fallback.name}")
            return True
        
        self._fail("Cannot find forensic image – run Steps 5 and 6 first")
        return False
    
    def check_tools(self):
        """Verify The Sleuth Kit tools are available."""
        print("\n[2/3] Checking The Sleuth Kit Tools")
        
        missing = [t for t in ("mmls", "fsstat", "fls") if not self._has(t)]
        
        if missing:
            self._fail(f"Missing tools: {', '.join(missing)} – install with: sudo apt install sleuthkit")
            return False
        
        print("✓ All TSK tools available (mmls, fsstat, fls)")
        return True
    
    def analyze_partitions(self):
        """Detect partition table and partitions using mmls."""
        print("\n[3/3] Analyzing Filesystem\n")
        
        stdout, stderr, ret = self._cmd(["mmls", str(self.image_path)])
        
        if ret != 0:
            # No partition table – superfloppy
            print("No partition table detected – superfloppy format assumed")
            self.partition_table_type = "superfloppy"
            self.partitions = [{
                "number": 0,
                "offset": 0,
                "sizeSectors": None,
                "type": "whole_device",
                "description": "Superfloppy – no partition table"
            }]
            return True
        
        # Parse mmls output
        table_type = "unknown"
        partitions = []
        
        for line in stdout.splitlines():
            if "DOS Partition Table" in line or ("DOS" in line and "Partition" in line):
                table_type = "DOS/MBR"
            elif "GUID Partition Table" in line or "GPT" in line:
                table_type = "GPT"
            
            # Parse partition entries: 002:  00:00  00001  62521343  62521343  Linux (0x83)
            m = re.match(r"(\d+):\s+(\S+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(.+)", line)
            if m:
                slot, ptype, start, _end, size, desc = (
                    int(m.group(1)), m.group(2),
                    int(m.group(3)), m.group(4),
                    int(m.group(5)), m.group(6).strip()
                )
                if ptype.lower() in ("meta", "-----") or size == 0:
                    continue
                partitions.append({
                    "number": slot,
                    "offset": start,
                    "sizeSectors": size,
                    "type": ptype,
                    "description": desc
                })
                print(f"  Partition {slot}: offset={start} | size={size} sectors | {desc}")
        
        self.partition_table_type = table_type
        self.partitions = partitions if partitions else [{
            "number": 0, "offset": 0, "sizeSectors": None,
            "type": "whole_device", "description": "Fallback"
        }]
        
        print(f"\nPartition Table: {table_type} | {len(self.partitions)} partition(s) found")
        return True
    
    def analyze_filesystem(self, partition):
        """Identify filesystem type and metadata using fsstat."""
        offset = partition["offset"]
        print(f"\n  fsstat (offset={offset})")
        
        fs_info = {
            "offset": offset,
            "recognized": False,
            "type": "unknown",
            "label": None,
            "uuid": None,
            "sectorSize": None,
            "clusterSize": None
        }
        
        stdout, stderr, ret = self._cmd(["fsstat", "-o", str(offset), str(self.image_path)])
        
        if ret != 0:
            print(f"  Filesystem not recognised at offset {offset}")
            return fs_info
        
        # Identify FS type
        for keyword, canonical in FS_TYPE_MAP.items():
            if keyword in stdout:
                fs_info["type"] = canonical
                break
        
        # Extract metadata
        patterns = {
            "label": r"(?:Volume Label|Label):\s*(.+)",
            "uuid": r"(?:Serial Number|UUID):\s*(.+)",
            "sectorSize": r"(?:Sector Size|sector size):\s*(\d+)",
            "clusterSize": r"(?:Cluster Size|Block Size):\s*(\d+)",
        }
        
        for field, pattern in patterns.items():
            m = re.search(pattern, stdout)
            if m:
                val = m.group(1).strip()
                fs_info[field] = int(val) if field not in ("label", "uuid") else val
        
        if fs_info["type"] != "unknown":
            fs_info["recognized"] = True
            self.filesystem_recognized = True
            label_str = f" | Label: {fs_info['label']}" if fs_info['label'] else ""
            print(f"  Type: {fs_info['type']}{label_str}")
            print(f"  ✓ Filesystem recognized")
        else:
            print(f"  Could not identify filesystem type")
        
        return fs_info
    
    def test_directory_structure(self, partition, fs_info):
        """Test directory readability using fls."""
        offset = partition["offset"]
        print(f"\n  fls (offset={offset})")
        
        if not fs_info.get("recognized"):
            print("  Skipping fls – filesystem not recognised")
            return False, 0, 0, []
        
        stdout, stderr, ret = self._cmd(
            ["fls", "-r", "-o", str(offset), str(self.image_path)],
            timeout=600
        )
        
        if ret != 0 or not stdout:
            print("  Directory structure not readable")
            return False, 0, 0, []
        
        # Parse file list
        file_list = []
        active = 0
        deleted = 0
        
        for line in stdout.splitlines():
            if not line.strip():
                continue
            is_deleted = "*" in line
            m = re.search(r":\s*(.+)$", line)
            if m:
                filename = m.group(1).strip()
                file_list.append({"filename": filename, "deleted": is_deleted})
                if is_deleted:
                    deleted += 1
                else:
                    active += 1
        
        self.directory_readable = True
        print(f"  ✓ Directory readable: {active + deleted} entries (active: {active}, deleted: {deleted})")
        return True, active, deleted, file_list
    
    def identify_image_files(self, file_list):
        """Count image files by format and status."""
        counts = {
            "total": 0,
            "active": 0,
            "deleted": 0,
            "byFormat": {fmt: {"active": 0, "deleted": 0} for fmt in IMAGE_EXTENSIONS}
        }
        
        for entry in file_list:
            name = entry["filename"].lower()
            for fmt, exts in IMAGE_EXTENSIONS.items():
                if any(name.endswith(e) for e in exts):
                    counts["total"] += 1
                    key = "deleted" if entry["deleted"] else "active"
                    counts[key] += 1
                    counts["byFormat"][fmt][key] += 1
                    break
        
        if counts["total"] > 0:
            print(f"\n  Image files: {counts['total']} (active: {counts['active']}, deleted: {counts['deleted']})")
            for fmt, c in counts["byFormat"].items():
                total = c["active"] + c["deleted"]
                if total > 0:
                    print(f"    {fmt.upper()}: {total}")
        else:
            print(f"\n  No image files found")
        
        return counts
    
    def determine_strategy(self):
        """Select optimal recovery strategy."""
        key = (self.filesystem_recognized, self.directory_readable)
        method, tool, est, notes = RECOVERY_STRATEGIES.get(
            key, RECOVERY_STRATEGIES[(False, False)]
        )
        
        self.recommended_method = method
        self.recommended_tool = tool
        self.estimated_time = est
        self.strategy_notes = notes
        
        return method, tool, est, notes
    
    def save_json(self):
        """Save analysis results to JSON."""
        method, tool, est, notes = self.determine_strategy()
        
        data = {
            "filesystemAnalysis": {
                "version": __version__,
                "compliance": ["NIST SP 800-86", "ISO/IEC 27037:2012"],
                "caseId": self.case_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "analyst": self.analyst,
                "image": {
                    "imagePath": str(self.image_path),
                    "imageSizeBytes": self.image_size,
                    "imageFormat": self.image_path.suffix.lstrip('.')
                },
                "partitionTable": {
                    "tableType": self.partition_table_type,
                    "partitionsFound": len(self.partitions)
                },
                "partitions": self.partitions,
                "recoveryStrategy": {
                    "recommendedMethod": method,
                    "recommendedTool": tool,
                    "estimatedTimeMinutes": est,
                    "notes": notes,
                    "filesystemRecognized": self.filesystem_recognized,
                    "directoryReadable": self.directory_readable,
                    "totalImageFiles": self.total_images
                }
            },
            "chainOfCustodyEntry": {
                "action": f"Filesystem analysis completed - {self.partition_table_type}, {self.total_images} photos identified",
                "result": "SUCCESS",
                "analyst": self.analyst,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "details": f"Strategy: {method}, Tool: {tool}, Est. time: {est} min"
            }
        }
        
        # Add partition-level details if analyzed
        if hasattr(self, 'partition_details'):
            data["filesystemAnalysis"]["partitions"] = self.partition_details
        
        if self.output_file:
            with open(self.output_file, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"\n✓ Report saved: {Path(self.output_file).name}")
        else:
            # Print to stdout
            print("\n" + "="*70)
            print(" JSON OUTPUT")
            print("="*70)
            print(json.dumps(data, indent=2))
        
        self.success = True
    
    def run(self):
        """Main execution flow."""
        try:
            print("\n" + "="*70)
            print(" STEP 7: FILESYSTEM ANALYSIS")
            print("="*70)
            print(f"Version: {__version__}")
            print(f"Case ID: {self.case_id}")
            print("="*70)
            
            # Load image
            if not self.load_image_path():
                return 1
            
            # Check tools
            if not self.check_tools():
                return 1
            
            # Analyze partitions
            if not self.analyze_partitions():
                return 1
            
            # Analyze each partition
            partition_details = []
            total_images = 0
            
            for part in self.partitions:
                fs_info = self.analyze_filesystem(part)
                readable, active, deleted, file_list = self.test_directory_structure(part, fs_info)
                img_counts = self.identify_image_files(file_list) if readable else {
                    "total": 0, "active": 0, "deleted": 0, "byFormat": {}
                }
                
                total_images += img_counts["total"]
                
                partition_details.append({
                    "partitionNumber": part["number"],
                    "offset": part["offset"],
                    "filesystemType": fs_info["type"],
                    "filesystemRecognized": fs_info["recognized"],
                    "volumeLabel": fs_info.get("label"),
                    "uuid": fs_info.get("uuid"),
                    "sectorSize": fs_info.get("sectorSize"),
                    "clusterSize": fs_info.get("clusterSize"),
                    "directoryReadable": readable,
                    "imageFiles": img_counts
                })
            
            self.partition_details = partition_details
            self.total_images = total_images
            
            # Determine strategy
            print("\n" + "-"*70)
            print("Recovery Strategy")
            print("-"*70)
            method, tool, est, notes = self.determine_strategy()
            print(f"Method: {method} | Tool: {tool} | Est. time: ~{est} min")
            for note in notes:
                print(f"  {note}")
            
            # Save results
            self.save_json()
            
            # Summary
            print("\n" + "="*70)
            print(" ANALYSIS COMPLETED")
            print("="*70)
            print(f"FS recognised: {self.filesystem_recognized} | "
                  f"Directory readable: {self.directory_readable} | "
                  f"Images: {total_images}")
            print(f"Method: {method}")
            
            if method == "filesystem_scan":
                print("Next: Step 8a (Filesystem Recovery)")
            elif method == "file_carving":
                print("Next: Step 8b (File Carving)")
            else:  # hybrid
                print("Next: Step 8a and 8b (Hybrid Recovery)")
            
            print("="*70)
            
            return 0
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Operation interrupted by user (Ctrl+C)", file=sys.stderr)
            return 130
        except Exception as e:
            self._fail(f"Unexpected error: {e}")
            return 1


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Step 7: Filesystem Analysis - Analyze FS structure and recommend recovery strategy",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  ptfilesystemanalysis CASE-001 --analyst "John Doe"
  
  # With custom output directory
  ptfilesystemanalysis CASE-001 --output-dir /mnt/forensics --analyst "Jane Smith"
  
  # With JSON output file
  ptfilesystemanalysis CASE-001 --output step7_analysis.json

Exit Codes:
  0   - Success (analysis completed)
  1   - Error (image not found, tools missing)
  130 - Interrupted (Ctrl+C)

Standards:
  NIST SP 800-86 Section 3.1.2
  ISO/IEC 27037:2012 Section 7
        """
    )
    
    parser.add_argument("case_id", help="Case ID (e.g., CASE-2025-001)")
    parser.add_argument("--output-dir", "-d", default="/var/forensics/images",
                        help="Forensic images directory (default: /var/forensics/images)")
    parser.add_argument("--analyst", "-a", default="Analyst",
                        help="Analyst name for Chain of Custody")
    parser.add_argument("--output", "-o", dest="output",
                        help="JSON output file path")
    parser.add_argument("--version", action="version", version=f"ptfilesystemanalysis {__version__}")
    
    args = parser.parse_args()
    
    tool = FilesystemAnalysisTool()
    tool.case_id = args.case_id
    tool.analyst = args.analyst
    tool.output_dir = Path(args.output_dir)
    tool.output_file = args.output if args.output else None
    
    exit_code = tool.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()