#!/usr/bin/env python3
"""
    Copyright (c) 2026 Bc. Dominik Sabota, VUT FIT Brno

    ptfilesystemrecovery - Forensic filesystem-based photo recovery tool

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License.
    See <https://www.gnu.org/licenses/> for details.
"""

# LAST CHANGES:
#   - IMAGE_EXTENSIONS, IMAGE_FILE_KEYWORDS, FORMAT_GROUPS replaced with
#     imports from _constants (single source of truth)
#   - _validate_image() removed; replaced by self._validate_image_file()
#     inherited from ForensicToolBase (was duplicated in ptfilecarving too)
#   - Changed --json boolean flag to --json-out <file> for consistency with
#     all other tools in the scenario

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ._version import __version__
from ._constants import IMAGE_EXTENSIONS, FORMAT_GROUP_MAP
from .ptforensictoolbase import ForensicToolBase
from ptlibs import ptjsonlib, ptprinthelper
from ptlibs.ptprinthelper import ptprint

import signal


def _custom_sigint_handler(sig, frame):
    raise KeyboardInterrupt


signal.signal(signal.SIGINT, _custom_sigint_handler)

SCRIPTNAME         = "ptfilesystemrecovery"
DEFAULT_OUTPUT_DIR = "/var/forensics/images"
FLS_TIMEOUT        = 1800
ICAT_TIMEOUT       = 60
EXIF_TIMEOUT       = 30

# Matches fls output lines: "r/r [* ]inode[-alloc]: path"
_FLS_LINE = re.compile(r"^\S+\s+\*?\s*(\d+)(?:-\d+)?:\s+(.+)$")


class PtFilesystemRecovery(ForensicToolBase):
    """
    Recovers image files from a forensic image using fls and icat (The Sleuth
    Kit). Reads the filesystem analysis JSON from the previous step to obtain
    the image path and partition layout. Read-only on the forensic image.
    """

    def __init__(self, args: argparse.Namespace) -> None:
        self.ptjsonlib  = ptjsonlib.PtJsonLib()
        self.args       = args
        self.case_id    = args.case_id.strip()
        self.dry_run    = args.dry_run
        self.force      = args.force
        self.output_dir = Path(args.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.image_path:  Optional[Path] = None
        self.fs_analysis: Optional[Dict] = None

        self.recovery_base = self.output_dir / f"{self.case_id}_recovered"
        self.active_dir    = self.recovery_base / "active"
        self.deleted_dir   = self.recovery_base / "deleted"
        self.corrupted_dir = self.recovery_base / "corrupted"
        self.metadata_dir  = self.recovery_base / "metadata"

        self._s: Dict[str, Any] = {
            "scanned": 0, "active": 0, "deleted": 0,
            "extracted": 0, "valid": 0, "corrupted": 0, "invalid": 0,
            "exif": 0, "by_format": {},
        }
        self._recovered_files: List[Dict] = []

        self.ptjsonlib.add_properties({
            "caseId":          self.case_id,
            "outputDirectory": str(self.output_dir),
            "timestamp":       datetime.now(timezone.utc).isoformat(),
            "scriptVersion":   __version__,
            "dryRun":          self.dry_run,
        })

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _format_group(self, ext: str) -> str:
        return FORMAT_GROUP_MAP.get(ext.lstrip(".").lower(), "other")

    # ------------------------------------------------------------------
    # Phases
    # ------------------------------------------------------------------

    def load_fs_analysis(self) -> bool:
        ptprint("\n[1/3] Loading filesystem analysis",
                "TITLE", condition=self._out())

        f = (Path(self.args.analysis_file)
             if getattr(self.args, "analysis_file", None)
             else self.output_dir / f"{self.case_id}_filesystem_analysis.json")
        if not f.exists():
            return self._fail("fsAnalysisLoad",
                              f"{f.name} not found – run Filesystem Analysis first.")
        try:
            raw = json.loads(f.read_text(encoding="utf-8"))
        except Exception as exc:
            return self._fail("fsAnalysisLoad", f"Cannot read analysis file: {exc}")

        if "result" in raw and "properties" in raw["result"]:
            p          = raw["result"]["properties"]
            partitions = next(
                (n.get("properties", {}).get("partitions", [])
                 for n in raw["result"].get("nodes", [])
                 if n.get("type") == "partitionAnalysis"), [])
            self.fs_analysis = {
                "recommended_method": p.get("recommendedMethod"),
                "image_file":         p.get("imagePath"),
                "partitions":         partitions,
            }
        else:
            self.fs_analysis = raw

        recommended  = (self.fs_analysis.get("recommended_method")
                        or self.fs_analysis.get("recommendedMethod"))
        image_path_s = (self.fs_analysis.get("image_file")
                        or self.fs_analysis.get("imagePath"))

        if not image_path_s:
            return self._fail("fsAnalysisLoad", "imagePath missing in analysis file.")

        self.image_path = Path(image_path_s)
        if not self.image_path.exists() and not self.dry_run:
            return self._fail("fsAnalysisLoad",
                              f"Forensic image not found: {self.image_path}")

        if recommended == "file_carving" and not self.force:
            return self._fail("fsAnalysisLoad",
                              "Analysis recommends file_carving – "
                              "use File Carving or pass --force to override.")
        if recommended == "hybrid":
            ptprint("Hybrid strategy – also run File Carving after this step.",
                    "WARNING", condition=self._out())

        partitions = self.fs_analysis.get("partitions", [])
        ptprint(f"Loaded: method={recommended}  |  "
                f"partitions={len(partitions)}  |  "
                f"image={self.image_path.name}",
                "OK", condition=self._out())
        self.ptjsonlib.add_properties({"imagePath": str(self.image_path)})
        self._add_node("fsAnalysisLoad", True, recommendedMethod=recommended,
                       imagePath=str(self.image_path), partitionsFound=len(partitions))
        return True

    def check_tools(self) -> bool:
        ptprint("\n[2/3] Checking required tools", "TITLE", condition=self._out())
        tools   = {"fls":      "TSK file listing",
                   "icat":     "TSK inode extraction",
                   "file":     "file type detection",
                   "identify": "ImageMagick validation",
                   "exiftool": "EXIF extraction"}
        missing = []
        for t, desc in tools.items():
            found = self._check_command(t)
            ptprint(f"  [{'OK' if found else 'ERROR'}] {t}: {desc}",
                    "OK" if found else "ERROR", condition=self._out())
            if not found:
                missing.append(t)

        if missing:
            ptprint(f"Missing: {', '.join(missing)} – "
                    "sudo apt-get install sleuthkit imagemagick libimage-exiftool-perl",
                    "ERROR", condition=self._out())
            self._add_node("toolsCheck", False, missingTools=missing)
            return False

        self._add_node("toolsCheck", True, toolsChecked=list(tools))
        return True

    def scan_and_filter(self, partition: Dict) -> Tuple[List[Dict], List[Dict]]:
        offset   = partition.get("offset", 0)
        part_num = partition.get("number", 0)
        ptprint(f"  fls: partition {part_num} (offset={offset}) …",
                "INFO", condition=self._out())

        r = self._run_command(
            ["fls", "-r", "-d", "-p", "-o", str(offset), str(self.image_path)],
            timeout=FLS_TIMEOUT)
        if not r["success"]:
            ptprint(f"  fls failed: {r['stderr']}", "ERROR", condition=self._out())
            return [], []

        active, deleted = [], []
        for line in r["stdout"].splitlines():
            line = line.strip()
            if not line or line.startswith("d/d"):
                continue
            self._s["scanned"] += 1

            m = _FLS_LINE.match(line)
            if not m:
                continue

            inode    = int(m.group(1))
            filepath = m.group(2).strip()
            ext      = Path(filepath).suffix.lower()
            if ext not in IMAGE_EXTENSIONS:
                continue

            is_deleted = line.split(":")[0].count("*") > 0
            group      = self._format_group(ext)
            self._s["by_format"][group] = self._s["by_format"].get(group, 0) + 1

            entry = {"inode": inode, "path": filepath,
                     "filename": Path(filepath).name, "deleted": is_deleted}
            if is_deleted: deleted.append(entry); self._s["deleted"] += 1
            else:          active.append(entry);  self._s["active"]  += 1

        ptprint(f"  Images: {len(active) + len(deleted)}  "
                f"(active={len(active)}, deleted={len(deleted)})",
                "OK", condition=self._out())
        return active, deleted

    def _extract_single(self, entry: Dict, offset: int, out_base: Path) -> Optional[Path]:
        dest = out_base / entry["path"].lstrip("/")
        dest.parent.mkdir(parents=True, exist_ok=True)
        cmd = ["icat", "-o", str(offset), str(self.image_path), str(entry["inode"])]

        if self.dry_run:
            return dest
        try:
            with open(dest, "wb") as fh:
                proc = subprocess.run(cmd, stdout=fh, stderr=subprocess.PIPE,
                                      timeout=ICAT_TIMEOUT, check=False)
            if proc.returncode == 0:
                return dest
            ptprint(f"    icat {entry['inode']}: "
                    f"{proc.stderr.decode(errors='replace').strip()}",
                    "WARNING", condition=self._out())
        except Exception as exc:
            ptprint(f"    icat {entry['inode']}: {exc}",
                    "WARNING", condition=self._out())
        if dest.exists():
            dest.unlink()
        return None

    def _extract_metadata(self, filepath: Path, entry: Dict) -> Dict:
        meta: Dict = {
            "filename": filepath.name, "originalPath": entry["path"],
            "inode": entry["inode"], "deleted": entry["deleted"],
            "fsMetadata": {}, "exifMetadata": {}, "hasExif": False,
        }
        try:
            st = filepath.stat()
            meta["fsMetadata"] = {
                "sizeBytes":    st.st_size,
                "modifiedTime": datetime.fromtimestamp(
                    st.st_mtime, tz=timezone.utc).isoformat(),
                "accessedTime": datetime.fromtimestamp(
                    st.st_atime, tz=timezone.utc).isoformat(),
                "createdTime":  datetime.fromtimestamp(
                    st.st_ctime, tz=timezone.utc).isoformat(),
            }
        except Exception as exc:
            meta["fsMetadata"]["error"] = str(exc)

        r = self._run_command(
            ["exiftool", "-json", "-charset", "utf8", str(filepath)],
            timeout=EXIF_TIMEOUT)
        if r["success"]:
            try:
                data = json.loads(r["stdout"])
                if data:
                    meta["exifMetadata"] = data[0]
                    if ({"DateTimeOriginal", "CreateDate", "GPSLatitude",
                         "Make", "Model"} & set(data[0])):
                        meta["hasExif"] = True
                        self._s["exif"] += 1
            except Exception as exc:
                meta["exifMetadata"] = {"parseError": str(exc)}
        return meta

    def process_partition(self, partition: Dict) -> None:
        part_num = partition.get("number", 0)
        offset   = partition.get("offset", 0)
        ptprint(f"\n  Partition {part_num} (offset={offset})",
                "TITLE", condition=self._out())

        active_imgs, deleted_imgs = self.scan_and_filter(partition)
        all_targets = ([(e, self.active_dir,  "active")  for e in active_imgs] +
                       [(e, self.deleted_dir, "deleted") for e in deleted_imgs])

        if not all_targets:
            ptprint("  No image files found.", "WARNING", condition=self._out())
            return

        total = len(all_targets)
        ptprint(f"  Extracting {total} image files …", "INFO", condition=self._out())
        self._add_node("partitionRecovery", True,
                       partitionNumber=part_num, offset=offset, totalImages=total)

        for idx, (entry, out_base, label) in enumerate(all_targets, 1):
            if idx % 50 == 0 or idx == total:
                ptprint(f"    {idx}/{total} ({idx * 100 // total}%)",
                        "INFO", condition=self._out())

            extracted = self._extract_single(entry, offset, out_base)
            if extracted is None:
                self._s["invalid"] += 1; continue
            self._s["extracted"] += 1

            # _validate_image_file() is now defined in ForensicToolBase
            status, vinfo = self._validate_image_file(extracted)

            if status == "valid":
                self._s["valid"] += 1
                meta = self._extract_metadata(extracted, entry)
                if not self.dry_run:
                    (self.metadata_dir / f"{extracted.name}_metadata.json").write_text(
                        json.dumps(meta, indent=2, ensure_ascii=False, default=str),
                        encoding="utf-8")
                self._recovered_files.append({
                    "filename":      extracted.name,
                    "originalPath":  entry["path"],
                    "recoveredPath": str(extracted.relative_to(self.recovery_base)),
                    "inode":         entry["inode"],
                    "status":        label,
                    "sizeBytes":     vinfo["size"],
                    "format":        vinfo.get("imageFormat"),
                    "dimensions":    vinfo.get("dimensions"),
                    "hasExif":       meta.get("hasExif", False),
                })
            elif status == "corrupted":
                self._s["corrupted"] += 1
                if not self.dry_run:
                    shutil.move(str(extracted),
                                str(self.corrupted_dir / extracted.name))
            else:
                self._s["invalid"] += 1
                if not self.dry_run and extracted.exists():
                    extracted.unlink()

        ptprint(f"  Partition {part_num} done.", "OK", condition=self._out())

    # ------------------------------------------------------------------
    # Run and save
    # ------------------------------------------------------------------

    def run(self) -> None:
        ptprint("=" * 70, "TITLE", condition=self._out())
        ptprint(f"FILESYSTEM-BASED PHOTO RECOVERY v{__version__}  |  "
                f"Case: {self.case_id}", "TITLE", condition=self._out())
        if self.dry_run:
            ptprint("MODE: DRY-RUN", "WARNING", condition=self._out())
        ptprint("=" * 70, "TITLE", condition=self._out())

        if not self.load_fs_analysis():
            self.ptjsonlib.set_status("finished"); return
        if not self.check_tools():
            self.ptjsonlib.set_status("finished"); return

        for path in (self.active_dir, self.deleted_dir,
                     self.corrupted_dir, self.metadata_dir):
            if not self.dry_run:
                path.mkdir(parents=True, exist_ok=True)
        ptprint("[3/3] Output directories ready.", "OK", condition=self._out())

        partitions = self.fs_analysis.get("partitions", [])
        for partition in partitions:
            self.process_partition(partition)

        s            = self._s
        total_images = s["active"] + s["deleted"]
        success_rate = (round(s["valid"] / s["extracted"] * 100, 1)
                        if s["extracted"] else None)

        self.ptjsonlib.add_properties({
            "compliance":          ["NIST SP 800-86", "ISO/IEC 27037:2012"],
            "method":              "filesystem_scan",
            "partitionsProcessed": len(partitions),
            "totalFilesScanned":   s["scanned"],
            "imageFilesFound":     total_images,
            "activeImages":        s["active"],
            "deletedImages":       s["deleted"],
            "imagesExtracted":     s["extracted"],
            "validImages":         s["valid"],
            "corruptedImages":     s["corrupted"],
            "invalidImages":       s["invalid"],
            "withExif":            s["exif"],
            "byFormat":            s["by_format"],
            "successRate":         success_rate,
            "recoveryBaseDir":     str(self.recovery_base),
        })
        self._add_node("recoverySummary", True,
                       imageFilesFound=total_images, imagesExtracted=s["extracted"],
                       validImages=s["valid"], corruptedImages=s["corrupted"],
                       withExif=s["exif"], byFormat=s["by_format"],
                       successRate=success_rate)
        self.ptjsonlib.add_node(self.ptjsonlib.create_node_object(
            "chainOfCustodyEntry",
            properties={
                "action":    (f"Filesystem-based photo recovery complete – "
                              f"{s['valid']} valid files recovered"),
                "result":    "SUCCESS" if s["valid"] > 0 else "NO_FILES",
                "analyst":   self.args.analyst,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ))

        ptprint("\n" + "=" * 70, "TITLE", condition=self._out())
        ptprint("RECOVERY COMPLETE", "OK", condition=self._out())
        ptprint(f"Images: {total_images} (active={s['active']}, "
                f"deleted={s['deleted']})  |  Valid: {s['valid']}  |  "
                f"Corrupted: {s['corrupted']}  |  Invalid: {s['invalid']}",
                "INFO", condition=self._out())
        if success_rate is not None:
            ptprint(f"Success rate: {success_rate}%", "OK", condition=self._out())
        ptprint("Next: Photo Cataloging", "INFO", condition=self._out())
        ptprint("=" * 70, "TITLE", condition=self._out())
        self.ptjsonlib.set_status("finished")

    def _write_text_report(self, props: Dict) -> Path:
        txt = self.recovery_base / "RECOVERY_REPORT.txt"
        self.recovery_base.mkdir(parents=True, exist_ok=True)
        sep   = "=" * 70
        lines = [sep, "FILESYSTEM-BASED PHOTO RECOVERY REPORT", sep, "",
                 f"Case ID:   {self.case_id}",
                 f"Timestamp: {props.get('timestamp', '')}",
                 f"Method:    {props.get('method', 'filesystem_scan')}", "",
                 "STATISTICS:",
                 f"  Images found:   {props.get('imageFilesFound', 0)} "
                 f"(active={props.get('activeImages', 0)}, "
                 f"deleted={props.get('deletedImages', 0)})",
                 f"  Extracted:      {props.get('imagesExtracted', 0)}",
                 f"  Valid:          {props.get('validImages', 0)}",
                 f"  Corrupted:      {props.get('corruptedImages', 0)}",
                 f"  With EXIF:      {props.get('withExif', 0)}",
                 *([] if props.get("successRate") is None
                   else [f"  Success rate:   {props['successRate']}%"]),
                 "", "BY FORMAT:"]
        lines += [f"  {k.upper():8s}: {v}"
                  for k, v in sorted(props.get("byFormat", {}).items())]
        lines += ["", sep,
                  f"RECOVERED FILES (first 100 of {len(self._recovered_files)}):",
                  sep, ""]
        for rec in self._recovered_files[:100]:
            dim = f"  |  {rec['dimensions']}" if rec.get("dimensions") else ""
            lines += [rec["filename"],
                      f"  {rec['originalPath']}  →  {rec['recoveredPath']}",
                      f"  {rec['sizeBytes']} B{dim}  |  "
                      f"EXIF: {'Yes' if rec.get('hasExif') else 'No'}", ""]
        if len(self._recovered_files) > 100:
            lines.append(f"… and {len(self._recovered_files) - 100} more files")
        txt.write_text("\n".join(lines), encoding="utf-8")
        return txt

    def save_report(self) -> Optional[str]:
        if self.args.json:
            ptprint(self.ptjsonlib.get_result_json(), "", self.args.json)
            return None

        json_file = self.output_dir / f"{self.case_id}_recovery_report.json"
        report    = {
            "result": json.loads(self.ptjsonlib.get_result_json()),
            "recoveredFiles": self._recovered_files,
            "outputDirectories": {
                "active":    str(self.active_dir),
                "deleted":   str(self.deleted_dir),
                "corrupted": str(self.corrupted_dir),
                "metadata":  str(self.metadata_dir),
            },
        }
        json_file.write_text(
            json.dumps(report, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8")
        ptprint(f"JSON report: {json_file}", "OK", condition=self._out())

        props = json.loads(self.ptjsonlib.get_result_json())["result"]["properties"]
        txt   = self._write_text_report(props)
        ptprint(f"Text report: {txt}", "OK", condition=self._out())
        return str(json_file)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def get_help() -> List[Dict]:
    return [
        {"description": [
            "Forensic filesystem-based photo recovery – ptlibs compliant",
            "Recovers images via fls + icat, preserving filenames, paths, and EXIF",
            "Compliant with ISO/IEC 27037:2012 and NIST SP 800-86",
        ]},
        {"usage": ["ptfilesystemrecovery <case-id> [options]"]},
        {"usage_example": [
            "ptfilesystemrecovery PHOTORECOVERY-2025-01-26-001",
            "ptfilesystemrecovery PHOTORECOVERY-2025-01-26-001 --dry-run",
            "ptfilesystemrecovery PHOTORECOVERY-2025-01-26-001 --force",
        ]},
        {"options": [
            ["case-id",            "",      "Forensic case identifier – REQUIRED"],
            ["--analysis-file",    "<f>",   "Path to filesystem_analysis.json (optional)"],
            ["-a", "--analyst",    "<n>",   "Analyst name (default: Analyst)"],
            ["-o", "--output-dir", "<dir>", f"Output directory (default: {DEFAULT_OUTPUT_DIR})"],
            ["--dry-run",          "",      "Simulate without running external commands"],
            ["--force",            "",      "Override file_carving recommendation"],
            ["-j", "--json-out",   "<f>",   "Save JSON report to file"],
            ["-q", "--quiet",      "",      "Suppress terminal output"],
            ["-h", "--help",       "",      "Show help"],
            ["--version",          "",      "Show version"],
        ]},
        {"notes": [
            "Requires: fls, icat (sleuthkit) + identify (imagemagick) + exiftool",
            "Output: active/ | deleted/ | corrupted/ | metadata/ | RECOVERY_REPORT.txt",
            "Reads {case_id}_filesystem_analysis.json from the previous step",
            "Compliant with ISO/IEC 27037:2012 and NIST SP 800-86",
        ]},
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("case_id")
    parser.add_argument("--analysis-file", default=None)
    parser.add_argument("-a", "--analyst",    default="Analyst")
    parser.add_argument("-o", "--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("-q", "--quiet",      action="store_true")
    parser.add_argument("--dry-run",          action="store_true")
    parser.add_argument("--force",            action="store_true")
    parser.add_argument("-j", "--json-out",   default=None)
    parser.add_argument("--version", action="version",
                        version=f"{SCRIPTNAME} {__version__}")

    if len(sys.argv) == 1 or {"-h", "--help"} & set(sys.argv):
        ptprinthelper.help_print(get_help(), SCRIPTNAME, __version__)
        sys.exit(0)

    args = parser.parse_args()
    args.json = bool(args.json_out)
    if args.json:
        args.quiet = True
    ptprinthelper.print_banner(SCRIPTNAME, __version__, args.json)
    return args


def main() -> int:
    try:
        args = parse_args()
        tool = PtFilesystemRecovery(args)
        tool.run()
        tool.save_report()
        props = json.loads(tool.ptjsonlib.get_result_json())["result"]["properties"]
        return 0 if props.get("validImages", 0) > 0 else 1
    except KeyboardInterrupt:
        ptprint("Interrupted by user.", "WARNING", condition=True)
        return 130
    except Exception as exc:
        ptprint(f"ERROR: {exc}", "ERROR", condition=True)
        return 99


if __name__ == "__main__":
    sys.exit(main())