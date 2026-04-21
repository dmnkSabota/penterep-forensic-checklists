#!/usr/bin/env python3
"""
    Copyright (c) 2026 Bc. Dominik Sabota, VUT FIT Brno

    ptfilesystemanalysis - Forensic filesystem analysis tool

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License.
    See <https://www.gnu.org/licenses/> for details.
"""

# LAST CHANGES:
#   - IMAGE_EXTENSIONS and FORMAT_GROUPS replaced with imports from _constants
#   - Fixed save_report() JSON-to-stdout bug (consistent with other tools)

import argparse
import json
import re
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ._version import __version__
from ._constants import IMAGE_EXTENSIONS, FORMAT_GROUP_MAP
from .ptforensictoolbase import ForensicToolBase
from ptlibs import ptjsonlib, ptprinthelper
from ptlibs.ptprinthelper import ptprint


def _custom_sigint_handler(sig, frame):
    raise KeyboardInterrupt


signal.signal(signal.SIGINT, _custom_sigint_handler)

SCRIPTNAME         = "ptfilesystemanalysis"
DEFAULT_OUTPUT_DIR = "/var/forensics/images"
MMLS_TIMEOUT       = 60
FSSTAT_TIMEOUT     = 60
FLS_TIMEOUT        = 600

FS_TYPE_MAP: Dict[str, str] = {
    "FAT32": "FAT32", "FAT16": "FAT16", "FAT12": "FAT12",
    "exFAT": "exFAT", "NTFS": "NTFS",
    "Ext4": "ext4", "ext4": "ext4", "Ext3": "ext3", "ext3": "ext3",
    "Ext2": "ext2", "ext2": "ext2", "HFS+": "HFS+", "APFS": "APFS",
    "ISO 9660": "ISO9660",
}

# (filesystem_recognized, directory_readable) → (method, tool, est_minutes, notes)
RECOVERY_STRATEGIES: Dict[Tuple[bool, bool], Tuple[str, str, int, List[str]]] = {
    (True, True): (
        "filesystem_scan", "fls + icat (The Sleuth Kit)", 15,
        ["Filesystem intact – filesystem-based scan recommended.",
         "Original filenames and directory structure preserved.",
         "Fastest recovery method."],
    ),
    (True, False): (
        "hybrid", "fls + photorec", 60,
        ["Filesystem recognised but directory structure damaged.",
         "Hybrid: filesystem scan + file carving on unallocated space.",
         "Some filenames may be lost."],
    ),
    (False, False): (
        "file_carving", "photorec / foremost", 90,
        ["Filesystem not recognised or severely damaged.",
         "File carving required (signature-based recovery).",
         "Original filenames and directory structure will be lost."],
    ),
}


class PtFilesystemAnalysis(ForensicToolBase):
    """
    Analyses the partition table and filesystem of a forensic image and
    recommends an appropriate recovery strategy (filesystem scan, file
    carving, or hybrid). Read-only on the image.
    """

    def __init__(self, args: argparse.Namespace) -> None:
        self.ptjsonlib  = ptjsonlib.PtJsonLib()
        self.args       = args
        self.case_id    = args.case_id.strip()
        self.analyst    = args.analyst
        self.dry_run    = args.dry_run
        self.image_path = Path(args.image)
        self.output_dir = Path(args.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.image_size:            Optional[int] = None
        self.partition_table_type:  Optional[str] = None
        self.partitions:            List[Dict]     = []
        self.partition_details:     List[Dict]     = []
        self.filesystem_recognized: bool           = False
        self.directory_readable:    bool           = False
        self.total_images:          int            = 0

        self.ptjsonlib.add_properties({
            "caseId":        self.case_id,
            "analyst":       self.analyst,
            "timestamp":     datetime.now(timezone.utc).isoformat(),
            "scriptVersion": __version__,
            "imagePath":     str(self.image_path),
            "dryRun":        self.dry_run,
        })

    # ------------------------------------------------------------------
    # Phases
    # ------------------------------------------------------------------

    def check_tools(self) -> bool:
        ptprint("\n[1/2] Checking Sleuth Kit tools", "TITLE", condition=self._out())
        tools   = {"mmls":   "partition table parser",
                   "fsstat": "filesystem statistics",
                   "fls":    "file listing"}
        missing = []
        for t, desc in tools.items():
            found = self._check_command(t)
            ptprint(f"  [{'OK' if found else 'ERROR'}] {t}: {desc}",
                    "OK" if found else "ERROR", condition=self._out())
            if not found:
                missing.append(t)

        if missing:
            ptprint(f"Missing tools: {', '.join(missing)} – "
                    "sudo apt install sleuthkit",
                    "ERROR", condition=self._out())
            self._add_node("toolsCheck", False, missingTools=missing)
            return False

        self._add_node("toolsCheck", True, toolsChecked=list(tools))
        return True

    def analyse_partitions(self) -> bool:
        ptprint("\n[2/2] Analysing filesystem", "TITLE", condition=self._out())

        r = self._run_command(["mmls", str(self.image_path)], timeout=MMLS_TIMEOUT)

        if not r["success"] or self.dry_run:
            ptprint("  No partition table detected – superfloppy assumed.",
                    "INFO", condition=self._out())
            self.partition_table_type = "superfloppy"
            self.partitions = [{"number": 0, "offset": 0, "sizeSectors": None,
                                 "type": "whole_device",
                                 "description": "Superfloppy – no partition table"}]
            self._add_node("partitionScan", True,
                           tableType=self.partition_table_type, partitionsFound=1)
            return True

        table_type  = "unknown"
        partitions: List[Dict] = []

        for line in r["stdout"].splitlines():
            if "DOS Partition Table" in line or ("DOS" in line and "Partition" in line):
                table_type = "DOS/MBR"
            elif "GUID Partition Table" in line or "GPT" in line:
                table_type = "GPT"

            m = re.match(r"(\d+):\s+(\S+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(.+)", line)
            if m:
                slot, ptype = int(m.group(1)), m.group(2)
                start, size = int(m.group(3)), int(m.group(5))
                desc        = m.group(6).strip()
                if ptype.lower() in ("meta", "-----") or size == 0:
                    continue
                partitions.append({"number": slot, "offset": start,
                                    "sizeSectors": size, "type": ptype,
                                    "description": desc})
                ptprint(f"  Partition {slot}: offset={start}  "
                        f"{size} sectors  {desc}",
                        "INFO", condition=self._out())

        if not partitions:
            partitions = [{"number": 0, "offset": 0, "sizeSectors": None,
                            "type": "whole_device", "description": "Fallback"}]

        self.partition_table_type = table_type
        self.partitions           = partitions
        ptprint(f"  Table type: {table_type}  |  "
                f"{len(partitions)} partition(s) found",
                "OK", condition=self._out())
        self._add_node("partitionScan", True,
                       tableType=table_type, partitionsFound=len(partitions))
        return True

    def analyse_filesystem(self, partition: Dict) -> Dict:
        offset  = partition["offset"]
        ptprint(f"  fsstat (offset={offset}) …",
                "INFO", condition=self._out())

        fs_info: Dict[str, Any] = {
            "offset": offset, "recognized": False, "type": "unknown",
            "label": None, "uuid": None, "sectorSize": None, "clusterSize": None,
        }

        r = self._run_command(
            ["fsstat", "-o", str(offset), str(self.image_path)],
            timeout=FSSTAT_TIMEOUT)

        if not r["success"] or not r["stdout"]:
            if not self.dry_run:
                ptprint(f"  Filesystem not recognised at offset {offset}.",
                        "WARNING", condition=self._out())
            return fs_info

        for keyword, canonical in FS_TYPE_MAP.items():
            if keyword in r["stdout"]:
                fs_info["type"] = canonical
                break

        patterns = {
            "label":       r"(?:Volume Label|Label):\s*(.+)",
            "uuid":        r"(?:Serial Number|UUID):\s*(.+)",
            "sectorSize":  r"(?:Sector Size|sector size):\s*(\d+)",
            "clusterSize": r"(?:Cluster Size|Block Size):\s*(\d+)",
        }
        for field, pattern in patterns.items():
            m = re.search(pattern, r["stdout"])
            if m:
                val = m.group(1).strip()
                fs_info[field] = (int(val) if field not in ("label", "uuid") else val)

        if fs_info["type"] != "unknown":
            fs_info["recognized"]      = True
            self.filesystem_recognized = True
            label_str = f"  |  Label: {fs_info['label']}" if fs_info["label"] else ""
            ptprint(f"  ✓ Type: {fs_info['type']}{label_str}",
                    "OK", condition=self._out())

        return fs_info

    def test_directory_structure(
        self, partition: Dict, fs_info: Dict
    ) -> Tuple[bool, int, int, List[Dict]]:
        offset = partition["offset"]
        ptprint(f"  fls (offset={offset}) …", "INFO", condition=self._out())

        if not fs_info.get("recognized"):
            ptprint("  Skipping fls – filesystem not recognised.",
                    "INFO", condition=self._out())
            return False, 0, 0, []

        r = self._run_command(
            ["fls", "-r", "-o", str(offset), str(self.image_path)],
            timeout=FLS_TIMEOUT)

        if not r["success"] or not r["stdout"]:
            if not self.dry_run:
                ptprint("  Directory structure not readable.",
                        "WARNING", condition=self._out())
            return False, 0, 0, []

        file_list: List[Dict] = []
        active = deleted = 0
        for line in r["stdout"].splitlines():
            if not line.strip():
                continue
            is_deleted = "*" in line
            m = re.search(r":\s*(.+)$", line)
            if m:
                filename = m.group(1).strip()
                file_list.append({"filename": filename, "deleted": is_deleted})
                if is_deleted: deleted += 1
                else:          active  += 1

        self.directory_readable = True
        ptprint(f"  ✓ {active + deleted} entries  "
                f"(active: {active}, deleted: {deleted})",
                "OK", condition=self._out())
        return True, active, deleted, file_list

    def identify_image_files(self, file_list: List[Dict]) -> Dict[str, Any]:
        # Uses IMAGE_EXTENSIONS and FORMAT_GROUP_MAP from _constants
        counts: Dict[str, Any] = {
            "total": 0, "active": 0, "deleted": 0,
            "byFormat": {g: {"active": 0, "deleted": 0}
                         for g in set(FORMAT_GROUP_MAP.values())},
        }
        for entry in file_list:
            ext = Path(entry["filename"]).suffix.lower()
            if ext not in IMAGE_EXTENSIONS:
                continue
            group      = FORMAT_GROUP_MAP.get(ext.lstrip("."), "other")
            counts["total"] += 1
            sk = "deleted" if entry["deleted"] else "active"
            counts[sk] += 1
            counts["byFormat"].setdefault(group, {"active": 0, "deleted": 0})
            counts["byFormat"][group][sk] += 1

        if counts["total"]:
            ptprint(f"  Image files: {counts['total']}  "
                    f"(active: {counts['active']}, deleted: {counts['deleted']})",
                    "INFO", condition=self._out())
            for fmt, c in counts["byFormat"].items():
                total = c["active"] + c["deleted"]
                if total:
                    ptprint(f"    {fmt.upper()}: {total}",
                            "INFO", condition=self._out())
        else:
            ptprint("  No image files found.", "INFO", condition=self._out())

        return counts

    def determine_strategy(self) -> Tuple[str, str, int, List[str]]:
        key = (self.filesystem_recognized, self.directory_readable)
        return RECOVERY_STRATEGIES.get(key, RECOVERY_STRATEGIES[(False, False)])

    # ------------------------------------------------------------------
    # Run and save
    # ------------------------------------------------------------------

    def run(self) -> None:
        ptprint("=" * 70, "TITLE", condition=self._out())
        ptprint(f"FILESYSTEM ANALYSIS v{__version__}  |  Case: {self.case_id}",
                "TITLE", condition=self._out())
        if self.dry_run:
            ptprint("MODE: DRY-RUN", "WARNING", condition=self._out())
        ptprint("=" * 70, "TITLE", condition=self._out())

        if not self.image_path.exists() and not self.dry_run:
            ptprint(f"Image not found: {self.image_path}", "ERROR", condition=True)
            self.ptjsonlib.set_status("finished"); return

        self.image_size = (self.image_path.stat().st_size
                           if not self.dry_run else 0)

        if not self.check_tools():
            self.ptjsonlib.set_status("finished"); return
        if not self.analyse_partitions():
            self.ptjsonlib.set_status("finished"); return

        total_images = 0
        for part in self.partitions:
            ptprint(f"\n  — Partition {part['number']} "
                    f"(offset={part['offset']}) —",
                    "INFO", condition=self._out())
            fs_info  = self.analyse_filesystem(part)
            readable, active, deleted, file_list = \
                self.test_directory_structure(part, fs_info)
            img_counts = (self.identify_image_files(file_list)
                          if readable
                          else {"total": 0, "active": 0, "deleted": 0, "byFormat": {}})
            total_images += img_counts["total"]
            self.partition_details.append({
                "partitionNumber":      part["number"],
                "offset":               part["offset"],
                "filesystemType":       fs_info["type"],
                "filesystemRecognized": fs_info["recognized"],
                "volumeLabel":          fs_info.get("label"),
                "uuid":                 fs_info.get("uuid"),
                "sectorSize":           fs_info.get("sectorSize"),
                "clusterSize":          fs_info.get("clusterSize"),
                "directoryReadable":    readable,
                "imageFiles":           img_counts,
            })

        self.total_images = total_images
        method, tool, est, notes = self.determine_strategy()

        ptprint("\n" + "-" * 70, "TITLE", condition=self._out())
        ptprint("Recovery strategy",  "TITLE", condition=self._out())
        ptprint("-" * 70,             "TITLE", condition=self._out())
        ptprint(f"  Method: {method}  |  Tool: {tool}  |  Est. ~{est} min",
                "OK", condition=self._out())
        for note in notes:
            ptprint(f"  {note}", "INFO", condition=self._out())

        self.ptjsonlib.add_properties({
            "compliance":           ["NIST SP 800-86", "ISO/IEC 27037:2012"],
            "imageSizeBytes":       self.image_size,
            "partitionTableType":   self.partition_table_type,
            "partitionsFound":      len(self.partitions),
            "filesystemRecognized": self.filesystem_recognized,
            "directoryReadable":    self.directory_readable,
            "totalImageFiles":      self.total_images,
            "recommendedMethod":    method,
            "recommendedTool":      tool,
            "estimatedTimeMinutes": est,
        })

        self._add_node("partitionAnalysis", True, partitions=self.partition_details)
        self._add_node("strategyDecision", True,
                       recommendedMethod=method, recommendedTool=tool,
                       estimatedTimeMinutes=est, notes=notes)
        self.ptjsonlib.add_node(self.ptjsonlib.create_node_object(
            "chainOfCustodyEntry",
            properties={
                "action":    (f"Filesystem analysis complete – "
                              f"{self.partition_table_type}, "
                              f"{self.total_images} image files identified"),
                "result":    "SUCCESS",
                "analyst":   self.analyst,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "details":   f"Strategy: {method}, tool: {tool}, est. {est} min",
            }
        ))

        ptprint("\n" + "=" * 70, "TITLE", condition=self._out())
        ptprint("ANALYSIS COMPLETE", "OK", condition=self._out())
        ptprint(f"FS recognised: {self.filesystem_recognized}  |  "
                f"Dir readable: {self.directory_readable}  |  "
                f"Images: {self.total_images}",
                "INFO", condition=self._out())
        next_step = {
            "filesystem_scan": "Filesystem Recovery",
            "file_carving":    "File Carving",
        }.get(method, "Hybrid Recovery")
        ptprint(f"Next: {next_step}", "INFO", condition=self._out())
        ptprint("=" * 70, "TITLE", condition=self._out())
        self.ptjsonlib.set_status("finished")

    def save_report(self) -> Optional[str]:
        if self.args.json:
            ptprint(self.ptjsonlib.get_result_json(), "", self.args.json)
            return None

        json_file = (Path(self.args.json_out) if self.args.json_out
                     else self.output_dir /
                          f"{self.case_id}_filesystem_analysis.json")
        report = {
            "result":     json.loads(self.ptjsonlib.get_result_json()),
            "partitions": self.partition_details,
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
            "Forensic filesystem analysis – ptlibs compliant",
            "Analyses partition table and filesystem structure, recommends recovery strategy",
            "Compliant with NIST SP 800-86 §3.1.2 and ISO/IEC 27037:2012 §7",
        ]},
        {"usage": ["ptfilesystemanalysis <case-id> <image> [options]"]},
        {"usage_example": [
            "ptfilesystemanalysis CASE-001 /var/forensics/images/CASE-001.dd",
            "ptfilesystemanalysis CASE-001 /path/to/image.dd --analyst 'Jane' "
            "--json-out step7.json",
            "ptfilesystemanalysis CASE-001 /path/to/image.dd --dry-run",
        ]},
        {"options": [
            ["case-id",            "",      "Forensic case identifier – REQUIRED"],
            ["image",              "",      "Path to forensic image (.dd) – REQUIRED"],
            ["-a", "--analyst",    "<n>",   "Analyst name (default: Analyst)"],
            ["-o", "--output-dir", "<dir>", f"Output directory (default: {DEFAULT_OUTPUT_DIR})"],
            ["-j", "--json-out",   "<f>",   "Save JSON report to file"],
            ["-q", "--quiet",      "",      "Suppress terminal output"],
            ["--dry-run",          "",      "Simulate without running TSK tools"],
            ["-h", "--help",       "",      "Show help"],
            ["--version",          "",      "Show version"],
        ]},
        {"notes": [
            "Requires: mmls, fsstat, fls  (sudo apt install sleuthkit)",
            "Output: {case_id}_filesystem_analysis.json",
            "Strategy: filesystem_scan | hybrid | file_carving",
            "Compliant with NIST SP 800-86 §3.1.2 and ISO/IEC 27037:2012 §7",
        ]},
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("case_id")
    parser.add_argument("image")
    parser.add_argument("-a", "--analyst",    default="Analyst")
    parser.add_argument("-o", "--output-dir", default=DEFAULT_OUTPUT_DIR)
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
        tool = PtFilesystemAnalysis(args)
        tool.run()
        tool.save_report()
        props = json.loads(tool.ptjsonlib.get_result_json())["result"]["properties"]
        return 0 if props.get("recommendedMethod") is not None else 1
    except KeyboardInterrupt:
        ptprint("Interrupted by user.", "WARNING", condition=True)
        return 130
    except Exception as exc:
        ptprint(f"ERROR: {exc}", "ERROR", condition=True)
        return 99


if __name__ == "__main__":
    sys.exit(main())