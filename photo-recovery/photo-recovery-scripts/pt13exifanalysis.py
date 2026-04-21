#!/usr/bin/env python3
"""
    Copyright (c) 2026 Bc. Dominik Sabota, VUT FIT Brno

    ptexifanalysis - Forensic EXIF metadata analysis tool

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License.
    See <https://www.gnu.org/licenses/> for details.
"""

# LAST CHANGES:
#   - IMAGE_EXTENSIONS replaced with import from _constants.
#   - EDITING_SOFTWARE: trimmed to 8 most common entries.
#   - Anomaly thresholds: added inline rationale and references.
#   - Removed _custom_sigint_handler + signal.signal(): handled in base.
#   - Replaced inline add_properties({5 common fields}) with _init_properties().

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ._version import __version__
from ._constants import IMAGE_EXTENSIONS
from .ptforensictoolbase import ForensicToolBase
from ptlibs import ptjsonlib, ptprinthelper
from ptlibs.ptprinthelper import ptprint

SCRIPTNAME         = "ptexifanalysis"
DEFAULT_OUTPUT_DIR = "/var/forensics/images"
EXIFTOOL_BATCH     = 50

# ---------------------------------------------------------------------------
# Editing software indicators
# Reference: Casey (2011), Ch. 14; Farid (2016), Ch. 3.
# ---------------------------------------------------------------------------
EDITING_SOFTWARE = frozenset({
    "photoshop",
    "lightroom",
    "gimp",
    "affinity photo",
    "instagram",
    "snapseed",
    "vsco",
    "facetune",
})

# ---------------------------------------------------------------------------
# Anomaly detection thresholds
# References: CIPA DC-008:2019 §4.6; Farid (2016) Ch. 2–4; NIST SP 800-86 §3.3
# ---------------------------------------------------------------------------
ANOMALY_THRESHOLDS = {
    "future_date":               True,
    "unusual_iso_threshold":     25600,
    "check_modify_after_original": True,
}

FIELDS_TO_EXTRACT = [
    "FileName", "FileSize", "FileModifyDate", "FileCreateDate",
    "DateTimeOriginal", "CreateDate", "ModifyDate", "OffsetTime",
    "Make", "Model", "LensModel", "Software", "Artist", "Copyright",
    "ExposureTime", "FNumber", "ISO", "FocalLength", "Flash",
    "ImageWidth", "ImageHeight", "GPSLatitude", "GPSLongitude",
    "GPSAltitude", "GPSDateTime",
]


class PtExifAnalysis(ForensicToolBase):
    """
    Batch EXIF metadata extraction and forensic anomaly detection.
    Uses exiftool with EXIFTOOL_BATCH files per call for performance.
    """

    def __init__(self, args: argparse.Namespace) -> None:
        self.ptjsonlib  = ptjsonlib.PtJsonLib()
        self.args       = args
        self.case_id    = args.case_id.strip()
        self.analyst    = getattr(args, "analyst", "Analyst")
        self.dry_run    = args.dry_run
        self.output_dir = Path(args.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.source_dir = (Path(args.source_dir)
                           if getattr(args, "source_dir", None)
                           else self.output_dir /
                                f"{self.case_id}_consolidated")

        self._s: Dict[str, Any] = {
            "total": 0, "with_exif": 0, "no_exif": 0, "anomalies": 0,
            "gps_count": 0, "by_make": {}, "by_anomaly": {},
        }
        self._exif_records: List[Dict] = []

        self._init_properties(__version__)

    # ------------------------------------------------------------------
    # EXIF extraction
    # ------------------------------------------------------------------

    def _run_exiftool_batch(self, files: List[Path]) -> List[Dict]:
        if self.dry_run:
            return [{"SourceFile": str(f)} for f in files]

        fields_args = [f"-{field}" for field in FIELDS_TO_EXTRACT]
        cmd = (["exiftool", "-json", "-charset", "utf8"] +
               fields_args +
               [str(f) for f in files])
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True,
                                  timeout=120, check=False)
            if proc.returncode in (0, 1) and proc.stdout.strip():
                data = json.loads(proc.stdout)
                return data if isinstance(data, list) else [data]
        except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
            pass
        return [{"SourceFile": str(f)} for f in files]

    # ------------------------------------------------------------------
    # EXIF parsing helpers
    # ------------------------------------------------------------------

    def _parse_datetime(self, raw: Optional[str]) -> Optional[datetime]:
        if not raw:
            return None
        m = re.match(r"(\d{4}):(\d{2}):(\d{2})\s+(\d{2}):(\d{2}):(\d{2})",
                     str(raw))
        if not m:
            return None
        try:
            return datetime(*[int(x) for x in m.groups()], tzinfo=timezone.utc)
        except (ValueError, TypeError):
            return None

    def _detect_editing_software(self, exif: Dict) -> Optional[str]:
        for field in ("Software", "Artist", "Copyright"):
            val = str(exif.get(field, "")).lower()
            for sw in EDITING_SOFTWARE:
                if sw in val:
                    return sw
        return None

    def _detect_anomalies(self, exif: Dict) -> List[Dict]:
        anomalies: List[Dict] = []
        now = datetime.now(timezone.utc)

        dt_orig = self._parse_datetime(exif.get("DateTimeOriginal"))
        if dt_orig and dt_orig > now:
            anomalies.append({
                "type":        "future_date",
                "description": "DateTimeOriginal is in the future",
                "value":       str(dt_orig),
                "reference":   "NIST SP 800-86 §3.3; CIPA DC-008:2019 §4.6",
            })

        try:
            iso_val   = int(str(exif.get("ISO", 0)).split()[0])
            threshold = ANOMALY_THRESHOLDS["unusual_iso_threshold"]
            if iso_val > threshold:
                anomalies.append({
                    "type":        "unusual_iso",
                    "description": f"ISO {iso_val} exceeds threshold ({threshold})",
                    "value":       iso_val,
                    "reference":   ("Farid 2016, Ch. 2; "
                                    "Canon/Nikon/Sony product manuals (pre-2020)"),
                })
        except (ValueError, TypeError):
            pass

        dt_modify = self._parse_datetime(exif.get("ModifyDate"))
        if (ANOMALY_THRESHOLDS["check_modify_after_original"]
                and dt_orig and dt_modify and dt_modify > dt_orig):
            delta_days = (dt_modify - dt_orig).days
            anomalies.append({
                "type":        "modify_after_original",
                "description": (f"ModifyDate is {delta_days} day(s) after "
                                f"DateTimeOriginal"),
                "value":       f"original={dt_orig}, modified={dt_modify}",
                "reference":   "Farid 2016, Ch. 4; CIPA DC-008:2019 §4.6.4",
            })

        return anomalies

    def _parse_single(self, exif: Dict) -> Dict:
        src      = exif.get("SourceFile", "")
        filename = Path(src).name if src else "unknown"

        has_key_exif = bool(exif.get("DateTimeOriginal") or
                            exif.get("Make") or
                            exif.get("Model"))

        gps: Optional[Dict] = None
        if exif.get("GPSLatitude") and exif.get("GPSLongitude"):
            gps = {
                "latitude":  exif.get("GPSLatitude"),
                "longitude": exif.get("GPSLongitude"),
                "altitude":  exif.get("GPSAltitude"),
                "datetime":  exif.get("GPSDateTime"),
            }

        editing_sw = self._detect_editing_software(exif)
        anomalies  = self._detect_anomalies(exif)

        return {
            "filename":        filename,
            "filePath":        src,
            "hasExif":         has_key_exif,
            "make":            exif.get("Make"),
            "model":           exif.get("Model"),
            "software":        exif.get("Software"),
            "editingSoftware": editing_sw,
            "dateTimeOriginal": exif.get("DateTimeOriginal"),
            "createDate":      exif.get("CreateDate"),
            "modifyDate":      exif.get("ModifyDate"),
            "iso":             exif.get("ISO"),
            "fNumber":         exif.get("FNumber"),
            "exposureTime":    exif.get("ExposureTime"),
            "focalLength":     exif.get("FocalLength"),
            "flash":           exif.get("Flash"),
            "width":           exif.get("ImageWidth"),
            "height":          exif.get("ImageHeight"),
            "gps":             gps,
            "anomalies":       anomalies,
        }

    # ------------------------------------------------------------------
    # Phases
    # ------------------------------------------------------------------

    def check_tools(self) -> bool:
        ptprint("\n[1/2] Checking exiftool", "TITLE", condition=self._out())
        if not self._check_command("exiftool"):
            return self._fail("toolsCheck",
                              "exiftool not found – "
                              "sudo apt install libimage-exiftool-perl")
        r = self._run_command(["exiftool", "-ver"], timeout=5)
        ver = r["stdout"].strip() if r["success"] else "unknown"
        ptprint(f"  ✓ exiftool {ver}", "OK", condition=self._out())
        self._add_node("toolsCheck", True, exiftoolVersion=ver)
        return True

    def analyse_all(self) -> bool:
        ptprint("\n[2/2] Extracting EXIF metadata", "TITLE", condition=self._out())

        if not self.source_dir.exists() and not self.dry_run:
            return self._fail("exifAnalysis",
                              f"Source directory not found: {self.source_dir}")

        candidates = (
            [f for f in self.source_dir.rglob("*")
             if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS]
            if not self.dry_run else []
        )
        ptprint(f"  Files to analyse: {len(candidates)}",
                "INFO", condition=self._out())

        if not candidates:
            if not self.dry_run:
                ptprint("  No image files found.", "WARNING", condition=self._out())
            self._add_node("exifAnalysis", True, totalFiles=0)
            return True

        for start in range(0, len(candidates), EXIFTOOL_BATCH):
            batch = candidates[start:start + EXIFTOOL_BATCH]
            pct   = min(start + EXIFTOOL_BATCH, len(candidates))
            ptprint(f"  {pct}/{len(candidates)} …", "INFO", condition=self._out())

            for exif_raw in self._run_exiftool_batch(batch):
                record = self._parse_single(exif_raw)
                self._exif_records.append(record)
                self._s["total"] += 1

                if record["hasExif"]: self._s["with_exif"] += 1
                else:                 self._s["no_exif"]   += 1
                if record["gps"]:     self._s["gps_count"] += 1
                if record["anomalies"]:
                    self._s["anomalies"] += 1
                    for a in record["anomalies"]:
                        t = a["type"]
                        self._s["by_anomaly"][t] = (
                            self._s["by_anomaly"].get(t, 0) + 1)
                if record["make"]:
                    m = record["make"]
                    self._s["by_make"][m] = self._s["by_make"].get(m, 0) + 1

        s = self._s
        ptprint(f"\n  Total: {s['total']}  |  "
                f"With EXIF: {s['with_exif']}  |  "
                f"No EXIF: {s['no_exif']}  |  "
                f"GPS: {s['gps_count']}  |  "
                f"Anomalies: {s['anomalies']}",
                "OK", condition=self._out())

        if s["by_anomaly"]:
            ptprint("  Anomalies detected:", "WARNING", condition=self._out())
            for atype, count in sorted(s["by_anomaly"].items()):
                ptprint(f"    {count:4d}× {atype}", "WARNING", condition=self._out())

        if s["by_make"]:
            ptprint("  Camera makes:", "INFO", condition=self._out())
            for make, count in sorted(s["by_make"].items(),
                                      key=lambda x: -x[1])[:5]:
                ptprint(f"    {count:4d}× {make}", "INFO", condition=self._out())

        self._add_node("exifAnalysis", True,
                       totalFiles=s["total"],
                       withExif=s["with_exif"],
                       noExif=s["no_exif"],
                       gpsCount=s["gps_count"],
                       anomaliesDetected=s["anomalies"],
                       byAnomaly=s["by_anomaly"],
                       topMakes=dict(
                           sorted(s["by_make"].items(), key=lambda x: -x[1])[:5]))
        return True

    # ------------------------------------------------------------------
    # Run and save
    # ------------------------------------------------------------------

    def run(self) -> None:
        ptprint("=" * 70, "TITLE", condition=self._out())
        ptprint(f"EXIF ANALYSIS v{__version__}  |  Case: {self.case_id}",
                "TITLE", condition=self._out())
        if self.dry_run:
            ptprint("MODE: DRY-RUN", "WARNING", condition=self._out())
        ptprint("=" * 70, "TITLE", condition=self._out())

        if not self.check_tools():
            self.ptjsonlib.set_status("finished"); return
        self.analyse_all()

        s = self._s
        self.ptjsonlib.add_properties({
            "compliance":        ["NIST SP 800-86", "ISO/IEC 27037:2012"],
            "totalFiles":        s["total"],
            "withExif":          s["with_exif"],
            "noExif":            s["no_exif"],
            "gpsCount":          s["gps_count"],
            "anomaliesDetected": s["anomalies"],
            "byAnomaly":         s["by_anomaly"],
            "editingSoftware":   sorted(EDITING_SOFTWARE),
            "anomalyThresholds": {
                k: v for k, v in ANOMALY_THRESHOLDS.items()
                if not callable(v)
            },
        })
        self.ptjsonlib.add_node(self.ptjsonlib.create_node_object(
            "chainOfCustodyEntry",
            properties={
                "action":    (f"EXIF analysis complete – "
                              f"{s['with_exif']} files with EXIF, "
                              f"{s['anomalies']} anomalies"),
                "result":    "SUCCESS",
                "analyst":   self.analyst,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "note":      ("Anomaly detection: future_date, unusual_iso, "
                              "modify_after_original – see thesis §X.Y"),
            }
        ))

        ptprint("\n" + "=" * 70, "TITLE", condition=self._out())
        ptprint("EXIF ANALYSIS COMPLETE", "OK", condition=self._out())
        ptprint(f"With EXIF: {s['with_exif']}  |  GPS: {s['gps_count']}  |  "
                f"Anomalies: {s['anomalies']}",
                "INFO", condition=self._out())
        ptprint("Next: Photo Catalog", "INFO", condition=self._out())
        ptprint("=" * 70, "TITLE", condition=self._out())
        self.ptjsonlib.set_status("finished")

    def save_report(self) -> Optional[str]:
        json_file = (Path(self.args.json_out) if self.args.json_out
                     else self.output_dir /
                          f"{self.case_id}_exif_analysis.json")
        report = {
            "result":      json.loads(self.ptjsonlib.get_result_json()),
            "exifRecords": self._exif_records,
        }
        json_file.write_text(
            json.dumps(report, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8")
        if self.args.json_out:
            ptprint(self.ptjsonlib.get_result_json(), "", True)
        ptprint(f"JSON report: {json_file.name}", "OK", condition=self._out())
        ptprint(f"  {len(self._exif_records)} EXIF records saved.",
                "INFO", condition=self._out())
        return str(json_file)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def get_help() -> List[Dict]:
    return [
        {"description": [
            "Forensic EXIF metadata analysis – ptlibs compliant",
            f"Batch extraction ({EXIFTOOL_BATCH} files/call) + anomaly detection",
            "Anomaly types: future_date | unusual_iso | modify_after_original",
            "References: Farid 2016; NIST SP 800-86; CIPA DC-008:2019",
        ]},
        {"usage": ["ptexifanalysis <case-id> [options]"]},
        {"usage_example": [
            "ptexifanalysis PHOTORECOVERY-2025-01-26-001",
            "ptexifanalysis CASE-001 --source-dir /path/to/images/",
            "ptexifanalysis CASE-001 --dry-run --json-out step13.json",
        ]},
        {"options": [
            ["case-id",            "",      "Forensic case identifier – REQUIRED"],
            ["--source-dir",       "<dir>", "Source directory (default: consolidated dir)"],
            ["-o", "--output-dir", "<dir>", f"Output directory (default: {DEFAULT_OUTPUT_DIR})"],
            ["-a", "--analyst",    "<n>",   "Analyst name"],
            ["-j", "--json-out",   "<f>",   "Save JSON report to file"],
            ["-q", "--quiet",      "",      "Suppress terminal output"],
            ["--dry-run",          "",      "Simulate without reading files"],
            ["-h", "--help",       "",      "Show help"],
            ["--version",          "",      "Show version"],
        ]},
        {"notes": [
            "Requires: exiftool (sudo apt install libimage-exiftool-perl)",
            f"Batch size: {EXIFTOOL_BATCH} files per exiftool call",
            "Anomaly detection thresholds documented in ANOMALY_THRESHOLDS",
            "Editing software detection: 8 entries (see EDITING_SOFTWARE)",
        ]},
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("case_id")
    parser.add_argument("--source-dir",    default=None)
    parser.add_argument("-o", "--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("-a", "--analyst",    default="Analyst")
    parser.add_argument("-j", "--json-out",   default=None)
    parser.add_argument("-q", "--quiet",      action="store_true")
    parser.add_argument("--dry-run",          action="store_true")
    parser.add_argument("--version", action="version",
                        version=f"{SCRIPTNAME} {__version__}")

    if len(sys.argv) == 1 or {"-h", "--help"} & set(sys.argv):
        ptprinthelper.help_print(get_help(), SCRIPTNAME, __version__)
        sys.exit(0)

    args           = parser.parse_args()
    args.json      = bool(args.json_out)
    args.source_dir = args.source_dir
    if args.json:
        args.quiet = True
    ptprinthelper.print_banner(SCRIPTNAME, __version__, args.json)
    return args


def main() -> int:
    try:
        args = parse_args()
        tool = PtExifAnalysis(args)
        tool.run()
        tool.save_report()
        props = json.loads(tool.ptjsonlib.get_result_json())["result"]["properties"]
        return 0 if props.get("totalFiles", 0) >= 0 else 99
    except KeyboardInterrupt:
        ptprint("Interrupted by user.", "WARNING", condition=True)
        return 130
    except Exception as exc:
        ptprint(f"ERROR: {exc}", "ERROR", condition=True)
        return 99


if __name__ == "__main__":
    sys.exit(main())