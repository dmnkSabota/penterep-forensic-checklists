#!/usr/bin/env python3
"""
    Copyright (c) 2025 Bc. Dominik Sabota, VUT FIT Brno

    ptfilecarving - Forensic file carving photo recovery tool

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License.
    See <https://www.gnu.org/licenses/> for details.
"""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ._version import __version__
from .ptforensictoolbase import ForensicToolBase
from ptlibs import ptjsonlib, ptprinthelper
from ptlibs.ptprinthelper import ptprint

import signal


def _custom_sigint_handler(sig, frame):
    raise KeyboardInterrupt


signal.signal(signal.SIGINT, _custom_sigint_handler)

SCRIPTNAME         = "ptfilecarving"
DEFAULT_OUTPUT_DIR = "/var/forensics/images"
PHOTOREC_TIMEOUT   = 86400   # 24 h absolute ceiling
VALIDATE_TIMEOUT   = 30
EXIF_TIMEOUT       = 30
HASH_CHUNK         = 65536   # 64 KB

IMAGE_FORMATS: Dict[str, str] = {
    "jpg": "JPEG", "png": "PNG", "gif": "GIF", "bmp": "BMP",
    "tiff": "TIFF", "heic": "HEIC/HEIF", "webp": "WebP",
    "cr2": "Canon RAW", "cr3": "Canon RAW3", "nef": "Nikon RAW",
    "arw": "Sony RAW", "dng": "Adobe DNG", "orf": "Olympus RAW",
    "raf": "Fuji RAW", "rw2": "Panasonic RAW",
}

FORMAT_DIRS: Dict[str, str] = {
    "jpg": "jpg", "jpeg": "jpg", "png": "png",
    "tif": "tiff", "tiff": "tiff",
    "cr2": "raw", "cr3": "raw", "nef": "raw", "nrw": "raw",
    "arw": "raw", "srf": "raw", "sr2": "raw", "dng": "raw",
    "orf": "raw", "raf": "raw", "rw2": "raw", "pef": "raw", "raw": "raw",
    "heic": "other", "heif": "other", "webp": "other",
    "gif": "other", "bmp": "other",
}

IMAGE_FILE_KEYWORDS = {"image", "jpeg", "png", "tiff", "gif", "bitmap",
                       "raw", "canon", "nikon", "exif", "riff webp", "heic"}


class PtFileCarving(ForensicToolBase):
    """
    Recovers image files from a forensic image using PhotoRec file carving.
    Filenames and directory structure are not preserved; recovered files are
    renamed to {case_id}_{type}_{seq:06d}.{ext}. Read-only on the forensic image.
    """

    def __init__(self, args: argparse.Namespace) -> None:
        self.ptjsonlib  = ptjsonlib.PtJsonLib()
        self.args       = args
        self.case_id    = args.case_id.strip()
        self.analyst    = args.analyst
        self.dry_run    = args.dry_run
        self.force      = args.force
        self.output_dir = Path(args.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.image_path: Optional[Path] = None

        self.carving_base   = self.output_dir / f"{self.case_id}_carved"
        self.photorec_work  = self.carving_base / "photorec_work"
        self.organized_dir  = self.carving_base / "organized"
        self.corrupted_dir  = self.carving_base / "corrupted"
        self.quarantine_dir = self.carving_base / "quarantine"
        self.duplicates_dir = self.carving_base / "duplicates"
        self.metadata_dir   = self.carving_base / "metadata"

        self._s: Dict[str, Any] = {
            "carved": 0, "valid": 0, "corrupted": 0, "invalid": 0,
            "dupes": 0, "unique": 0, "exif": 0, "gps": 0,
            "by_format": {}, "carving_sec": 0.0, "validate_sec": 0.0,
        }
        self._hash_db:      Dict[str, str] = {}
        self._unique_files: List[Dict]     = []

        self.ptjsonlib.add_properties({
            "caseId":        self.case_id,
            "outputDirectory": str(self.output_dir),
            "timestamp":     datetime.now(timezone.utc).isoformat(),
            "scriptVersion": __version__,
            "dryRun":        self.dry_run,
        })

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _sha256(self, filepath: Path) -> Optional[str]:
        h = hashlib.sha256()
        try:
            with open(filepath, "rb") as fh:
                for chunk in iter(lambda: fh.read(HASH_CHUNK), b""):
                    h.update(chunk)
            return h.hexdigest()
        except Exception:
            return None

    def _run_streaming(self, cmd: List[str], timeout: int) -> bool:
        if self.dry_run:
            return True
        try:
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, bufsize=1)
            for line in proc.stdout:
                if not self.args.json:
                    print(line, end="", flush=True)
            proc.wait(timeout=timeout)
            return proc.returncode == 0
        except Exception as exc:
            ptprint(f"PhotoRec error: {exc}", "ERROR", condition=self._out())
            return False

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
            p            = raw["result"]["properties"]
            recommended  = p.get("recommendedMethod")
            image_path_s = p.get("imagePath")
        else:
            recommended  = raw.get("recommended_method") or raw.get("recommendedMethod")
            image_path_s = raw.get("image_file") or raw.get("imagePath")

        if recommended == "filesystem_scan" and not self.force:
            return self._fail("fsAnalysisLoad",
                              "Analysis recommends filesystem_scan – "
                              "use Filesystem Recovery or pass --force to override.")
        if recommended == "hybrid":
            ptprint("Hybrid strategy – file carving will complement "
                    "Filesystem Recovery.", "WARNING", condition=self._out())

        if not image_path_s:
            return self._fail("fsAnalysisLoad", "imagePath missing in analysis file.")

        self.image_path = Path(image_path_s)
        if not self.image_path.exists() and not self.dry_run:
            return self._fail("fsAnalysisLoad",
                              f"Forensic image not found: {self.image_path}")

        ptprint(f"Loaded: method={recommended}  |  image={self.image_path.name}",
                "OK", condition=self._out())
        self.ptjsonlib.add_properties({"imagePath": str(self.image_path)})
        self._add_node("fsAnalysisLoad", True,
                       recommendedMethod=recommended,
                       imagePath=str(self.image_path))
        return True

    def check_tools(self) -> bool:
        ptprint("\n[2/3] Checking required tools", "TITLE", condition=self._out())
        tools   = {"photorec": "PhotoRec file carving",
                   "file": "file type detection",
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
                    "sudo apt-get install testdisk imagemagick "
                    "libimage-exiftool-perl",
                    "ERROR", condition=self._out())
            self._add_node("toolsCheck", False, missingTools=missing)
            return False

        self._add_node("toolsCheck", True, toolsChecked=list(tools))
        return True

    def run_photorec(self) -> bool:
        ptprint("\n[3/3] Running PhotoRec", "TITLE", condition=self._out())
        ptprint("  Scan time depends on media size – flash: 5–30 min, "
                "HDD (500 GB+): 2–8 h.  Do not interrupt.",
                "WARNING", condition=self._out())

        if not self.dry_run:
            lines = ["fileopt,everything,disable"]
            lines += [f"fileopt,{fmt},enable" for fmt in IMAGE_FORMATS]
            lines += ["options,paranoid,enable", "options,expert,enable", "search"]
            self.photorec_work.mkdir(parents=True, exist_ok=True)
            (self.photorec_work / "photorec.cmd").write_text(
                "\n".join(lines) + "\n", encoding="utf-8")

        ptprint(f"  Config: {len(IMAGE_FORMATS)} formats enabled "
                "(paranoid + expert mode).", "INFO", condition=self._out())

        cmd   = ["photorec", "/log", "/d", str(self.photorec_work),
                 "/cmd", str(self.image_path), "search"]
        start = datetime.now()
        ok    = self._run_streaming(cmd, timeout=PHOTOREC_TIMEOUT)
        self._s["carving_sec"] = (datetime.now() - start).total_seconds()

        ptprint(f"{'✓ PhotoRec completed' if ok else '✗ PhotoRec failed'} "
                f"in {self._s['carving_sec'] / 60:.1f} min",
                "OK" if ok else "ERROR", condition=self._out())
        self._add_node("photorec", ok,
                       carvingSeconds=round(self._s["carving_sec"], 1))
        return ok

    def collect_carved_files(self) -> List[Path]:
        recup_dirs = sorted(self.photorec_work.glob("recup_dir.*"))
        if not recup_dirs and not self.dry_run:
            ptprint("No recup_dir folders found.", "ERROR", condition=self._out())
            return []
        files              = [f for rd in recup_dirs for f in rd.glob("f*.*")]
        self._s["carved"]  = len(files)
        ptprint(f"  {len(recup_dirs)} recup_dir(s)  |  {len(files)} raw carved files.",
                "OK", condition=self._out())
        return files

    def _validate_file(self, filepath: Path) -> Tuple[str, Dict]:
        info: Dict = {"size": 0, "format": None, "dimensions": None}
        try:
            info["size"] = filepath.stat().st_size
        except Exception:
            return "invalid", info
        if info["size"] < 100:
            return "invalid", info

        r = self._run_command(["file", "-b", str(filepath)], timeout=10)
        if r["success"] and not any(kw in r["stdout"].lower()
                                    for kw in IMAGE_FILE_KEYWORDS):
            return "invalid", info

        r = self._run_command(["identify", str(filepath)], timeout=VALIDATE_TIMEOUT)
        if r["success"]:
            m = re.search(r"(\w+)\s+(\d+)x(\d+)", r["stdout"])
            if m:
                info["format"]     = m.group(1)
                info["dimensions"] = f"{m.group(2)}x{m.group(3)}"
            return "valid", info

        return ("corrupted" if info["size"] > 10240 else "invalid"), info

    def validate_and_deduplicate(self, carved_files: List[Path]) -> List[Dict]:
        ptprint("\nValidating and deduplicating …", "TITLE", condition=self._out())
        total       = len(carved_files)
        valid_files: List[Dict] = []
        start       = datetime.now()

        for idx, fp in enumerate(carved_files, 1):
            if idx % 100 == 0 or idx == total:
                ptprint(f"  {idx}/{total} ({idx * 100 // total}%)",
                        "INFO", condition=self._out())

            status, vinfo = self._validate_file(fp)

            if status == "valid":
                digest = self._sha256(fp)
                if digest:
                    if digest in self._hash_db:
                        if not self.dry_run:
                            shutil.move(str(fp),
                                        str(self.duplicates_dir / fp.name))
                        self._s["dupes"] += 1
                    else:
                        self._hash_db[digest] = str(fp)
                        ext = fp.suffix.lstrip(".").lower()
                        self._s["by_format"][ext] = \
                            self._s["by_format"].get(ext, 0) + 1
                        self._s["valid"] += 1
                        valid_files.append({"path": fp, "hash": digest,
                                            "size": vinfo["size"],
                                            "format": vinfo.get("format"),
                                            "dimensions": vinfo.get("dimensions")})
            elif status == "corrupted":
                self._s["corrupted"] += 1
                if not self.dry_run:
                    shutil.move(str(fp), str(self.corrupted_dir / fp.name))
            else:
                self._s["invalid"] += 1
                if not self.dry_run:
                    shutil.move(str(fp), str(self.quarantine_dir / fp.name))

        self._s["validate_sec"] = (datetime.now() - start).total_seconds()
        self._s["unique"]       = len(valid_files)

        ptprint(f"Done in {self._s['validate_sec']:.0f}s  |  "
                f"unique={self._s['unique']}  |  dupes={self._s['dupes']}  |  "
                f"corrupted={self._s['corrupted']}  |  invalid={self._s['invalid']}",
                "OK", condition=self._out())
        self._add_node("validationDedup", True,
                       totalCarvedRaw=self._s["carved"],
                       validUnique=self._s["unique"],
                       duplicatesRemoved=self._s["dupes"],
                       corrupted=self._s["corrupted"],
                       invalid=self._s["invalid"],
                       validationSeconds=round(self._s["validate_sec"], 1))
        return valid_files

    def _extract_exif(self, filepath: Path) -> Optional[Dict]:
        r = self._run_command(
            ["exiftool", "-json", "-charset", "utf8", str(filepath)],
            timeout=EXIF_TIMEOUT)
        if not r["success"]:
            return None
        try:
            data = json.loads(r["stdout"])
            if data:
                exif = data[0]
                if {"DateTimeOriginal", "CreateDate", "GPSLatitude",
                    "Make", "Model"} & set(exif):
                    self._s["exif"] += 1
                    if "GPSLatitude" in exif:
                        self._s["gps"] += 1
                    return exif
        except Exception:
            pass
        return None

    def organise_and_rename(self, valid_files: List[Dict]) -> None:
        ptprint("\nOrganising and renaming files …", "TITLE", condition=self._out())
        fmt_counters: Dict[str, int] = defaultdict(int)

        for fi in valid_files:
            fp       = fi["path"]
            ext      = fp.suffix.lstrip(".").lower()
            subdir   = FORMAT_DIRS.get(ext, "other")
            fmt_counters[subdir] += 1
            seq      = fmt_counters[subdir]
            new_name = f"{self.case_id}_{subdir}_{seq:06d}.{ext}"
            new_path = self.organized_dir / subdir / new_name

            if not self.dry_run:
                shutil.move(str(fp), str(new_path))

            exif_data = self._extract_exif(new_path if not self.dry_run else fp)
            if exif_data and not self.dry_run:
                (self.metadata_dir / f"{new_name}_metadata.json").write_text(
                    json.dumps(exif_data, indent=2, ensure_ascii=False, default=str),
                    encoding="utf-8")

            self._unique_files.append({
                "newFilename":      new_name,
                "originalPhotorec": fp.name,
                "recoveredPath":    str((self.organized_dir / subdir / new_name)
                                        .relative_to(self.carving_base)),
                "hash":             fi["hash"],
                "sizeBytes":        fi["size"],
                "formatGroup":      subdir,
                "dimensions":       fi.get("dimensions"),
                "hasExif":          exif_data is not None,
                "hasGps":           bool(exif_data and exif_data.get("GPSLatitude")),
            })

        ptprint(f"{len(self._unique_files)} files organised.",
                "OK", condition=self._out())

    # ------------------------------------------------------------------
    # Run and save
    # ------------------------------------------------------------------

    def run(self) -> None:
        ptprint("=" * 70, "TITLE", condition=self._out())
        ptprint(f"FILE CARVING PHOTO RECOVERY v{__version__}  |  "
                f"Case: {self.case_id}", "TITLE", condition=self._out())
        if self.dry_run:
            ptprint("MODE: DRY-RUN", "WARNING", condition=self._out())
        ptprint("=" * 70, "TITLE", condition=self._out())

        if not self.load_fs_analysis():
            self.ptjsonlib.set_status("finished"); return
        if not self.check_tools():
            self.ptjsonlib.set_status("finished"); return

        if not self.dry_run:
            for path in (self.photorec_work, self.organized_dir,
                         self.corrupted_dir, self.quarantine_dir,
                         self.duplicates_dir, self.metadata_dir):
                path.mkdir(parents=True, exist_ok=True)
            for sub in ("jpg", "png", "tiff", "raw", "other"):
                (self.organized_dir / sub).mkdir(exist_ok=True)

        if not self.run_photorec():
            self.ptjsonlib.set_status("finished"); return

        carved = self.collect_carved_files()
        if not carved and not self.dry_run:
            ptprint("No carved files found.", "ERROR", condition=self._out())
            self.ptjsonlib.set_status("finished"); return

        valid_files = self.validate_and_deduplicate(carved)
        if not valid_files and not self.dry_run:
            ptprint("No valid files after validation.",
                    "ERROR", condition=self._out())
            self.ptjsonlib.set_status("finished"); return

        self.organise_and_rename(valid_files)

        s            = self._s
        success_rate = (round(s["unique"] / s["carved"] * 100, 1)
                        if s["carved"] else None)

        self.ptjsonlib.add_properties({
            "compliance":          ["NIST SP 800-86", "ISO/IEC 27037:2012"],
            "method":              "file_carving",
            "tool":                "PhotoRec",
            "totalCarvedRaw":      s["carved"],
            "validAfterValidation": s["valid"],
            "corruptedFiles":      s["corrupted"],
            "invalidFiles":        s["invalid"],
            "duplicatesRemoved":   s["dupes"],
            "finalUniqueFiles":    s["unique"],
            "withExif":            s["exif"],
            "withGps":             s["gps"],
            "byFormat":            s["by_format"],
            "carvingSeconds":      round(s["carving_sec"], 1),
            "validationSeconds":   round(s["validate_sec"], 1),
            "successRate":         success_rate,
            "carvingBaseDir":      str(self.carving_base),
        })
        self._add_node("carvingSummary", True,
                       totalCarvedRaw=s["carved"], finalUniqueFiles=s["unique"],
                       duplicatesRemoved=s["dupes"], withExif=s["exif"],
                       withGps=s["gps"], successRate=success_rate)
        self.ptjsonlib.add_node(self.ptjsonlib.create_node_object(
            "chainOfCustodyEntry",
            properties={
                "action":    f"File carving complete – {s['unique']} files recovered",
                "result":    "SUCCESS" if s["unique"] > 0 else "NO_FILES",
                "analyst":   self.analyst,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ))

        ptprint("\n" + "=" * 70, "TITLE", condition=self._out())
        ptprint("FILE CARVING COMPLETE", "OK", condition=self._out())
        ptprint(f"Carved: {s['carved']}  |  Valid: {s['valid']}  |  "
                f"Dupes: {s['dupes']}  |  Unique: {s['unique']}"
                + (f"  |  Rate: {success_rate}%" if success_rate else ""),
                "INFO", condition=self._out())
        ptprint(f"Carving time: {s['carving_sec'] / 60:.1f} min",
                "INFO", condition=self._out())
        ptprint("Next: Photo Cataloging", "INFO", condition=self._out())
        ptprint("=" * 70, "TITLE", condition=self._out())
        self.ptjsonlib.set_status("finished")

    def _write_text_report(self, props: Dict) -> Path:
        txt = self.carving_base / "CARVING_REPORT.txt"
        self.carving_base.mkdir(parents=True, exist_ok=True)
        sep   = "=" * 70
        lines = [sep, "FILE CARVING PHOTO RECOVERY REPORT", sep, "",
                 f"Case ID:   {self.case_id}",
                 f"Timestamp: {props.get('timestamp', '')}",
                 f"Method:    {props.get('method', 'file_carving')}",
                 f"Tool:      {props.get('tool', 'PhotoRec')}", "",
                 "STATISTICS:",
                 f"  Total carved (raw):     {props.get('totalCarvedRaw', 0)}",
                 f"  Valid after validation:  {props.get('validAfterValidation', 0)}",
                 f"  Duplicates removed:     {props.get('duplicatesRemoved', 0)}",
                 f"  Final unique files:     {props.get('finalUniqueFiles', 0)}",
                 f"  Corrupted:              {props.get('corruptedFiles', 0)}",
                 f"  With EXIF:              {props.get('withExif', 0)}",
                 f"  With GPS:               {props.get('withGps', 0)}",
                 *([] if props.get("successRate") is None
                   else [f"  Success rate:           {props['successRate']}%"]),
                 "", "TIMING:",
                 f"  Carving:    {props.get('carvingSeconds', 0) / 60:.1f} min",
                 f"  Validation: {props.get('validationSeconds', 0) / 60:.1f} min",
                 "", "BY FORMAT:"]
        lines += [f"  {k.upper():8s}: {v}"
                  for k, v in sorted(props.get("byFormat", {}).items())]
        lines += ["", sep,
                  f"RECOVERED FILES (first 100 of {len(self._unique_files)}):",
                  sep, ""]
        for rec in self._unique_files[:100]:
            dim = f"  |  {rec['dimensions']}" if rec.get("dimensions") else ""
            gps = "  |  GPS: Yes" if rec.get("hasGps") else ""
            lines += [rec["newFilename"],
                      f"  {rec['recoveredPath']}  |  {rec['sizeBytes']} B{dim}",
                      f"  EXIF: {'Yes' if rec.get('hasExif') else 'No'}{gps}", ""]
        if len(self._unique_files) > 100:
            lines.append(f"… and {len(self._unique_files) - 100} more files")
        txt.write_text("\n".join(lines), encoding="utf-8")
        return txt

    def save_report(self) -> Optional[str]:
        if self.args.json:
            ptprint(self.ptjsonlib.get_result_json(), "", self.args.json)
            return None

        json_file = self.output_dir / f"{self.case_id}_carving_report.json"
        report    = {
            "result": json.loads(self.ptjsonlib.get_result_json()),
            "recoveredFiles": self._unique_files,
            "hashDatabase":   self._hash_db,
            "outputDirectories": {
                "organized":  str(self.organized_dir),
                "corrupted":  str(self.corrupted_dir),
                "quarantine": str(self.quarantine_dir),
                "duplicates": str(self.duplicates_dir),
                "metadata":   str(self.metadata_dir),
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
            "Forensic file carving photo recovery – ptlibs compliant",
            "Recovers images via PhotoRec byte-signature search (filesystem not required)",
            "Compliant with NIST SP 800-86 §3.1.2.3 and ISO/IEC 27037:2012",
        ]},
        {"usage": ["ptfilecarving <case-id> [options]"]},
        {"usage_example": [
            "ptfilecarving PHOTORECOVERY-2025-01-26-001",
            "ptfilecarving PHOTORECOVERY-2025-01-26-001 --dry-run",
            "ptfilecarving PHOTORECOVERY-2025-01-26-001 --force",
        ]},
        {"options": [
            ["case-id",            "",      "Forensic case identifier – REQUIRED"],
            ["--analysis-file",    "<f>",   "Path to filesystem_analysis.json (optional)"],
            ["-a", "--analyst",    "<n>",   "Analyst name (default: Analyst)"],
            ["-o", "--output-dir", "<dir>", f"Output directory (default: {DEFAULT_OUTPUT_DIR})"],
            ["--dry-run",          "",      "Simulate without running PhotoRec"],
            ["--force",            "",      "Override filesystem_scan recommendation"],
            ["-j", "--json",       "",      "JSON output for platform integration"],
            ["-q", "--quiet",      "",      "Suppress terminal output"],
            ["-h", "--help",       "",      "Show help"],
            ["--version",          "",      "Show version"],
        ]},
        {"notes": [
            "Filenames NOT preserved – renamed to {case_id}_{type}_{seq:06d}.{ext}",
            "Flash media (8–64 GB): 5–30 min | HDD (500 GB+): 2–8 h",
            "Typical success rate: 50–65% of carved files",
            "Output: organized/ | corrupted/ | quarantine/ | duplicates/ | metadata/",
            "Compliant with NIST SP 800-86 §3.1.2.3 and ISO/IEC 27037:2012",
        ]},
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("case_id")
    parser.add_argument("--analysis-file", default=None,
                        help="Path to filesystem_analysis.json (optional; auto-discovered from --output-dir if omitted)")
    parser.add_argument("-a", "--analyst",    default="Analyst")
    parser.add_argument("-o", "--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("-q", "--quiet",      action="store_true")
    parser.add_argument("--dry-run",          action="store_true")
    parser.add_argument("--force",            action="store_true")
    parser.add_argument("-j", "--json",       action="store_true")
    parser.add_argument("--version", action="version",
                        version=f"{SCRIPTNAME} {__version__}")

    if len(sys.argv) == 1 or {"-h", "--help"} & set(sys.argv):
        ptprinthelper.help_print(get_help(), SCRIPTNAME, __version__)
        sys.exit(0)

    args = parser.parse_args()
    if args.json:
        args.quiet = True
    ptprinthelper.print_banner(SCRIPTNAME, __version__, args.json)
    return args


def main() -> int:
    try:
        args = parse_args()
        tool = PtFileCarving(args)
        tool.run()
        tool.save_report()
        props = json.loads(tool.ptjsonlib.get_result_json())["result"]["properties"]
        return 0 if props.get("finalUniqueFiles", 0) > 0 else 1
    except KeyboardInterrupt:
        ptprint("Interrupted by user.", "WARNING", condition=True)
        return 130
    except Exception as exc:
        ptprint(f"ERROR: {exc}", "ERROR", condition=True)
        return 99


if __name__ == "__main__":
    sys.exit(main())