#!/usr/bin/env python3
"""
    Copyright (c) 2025 Bc. Dominik Sabota, VUT FIT Brno

    ptexifanalysis - Forensic EXIF metadata analysis tool

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License.
    See <https://www.gnu.org/licenses/> for details.
"""

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ._version import __version__
from .ptforensictoolbase import ForensicToolBase
from ptlibs import ptjsonlib, ptprinthelper
from ptlibs.ptprinthelper import ptprint

import signal


def _custom_sigint_handler(sig, frame):
    raise KeyboardInterrupt


signal.signal(signal.SIGINT, _custom_sigint_handler)

SCRIPTNAME         = "ptexifanalysis"
DEFAULT_OUTPUT_DIR = "/var/forensics/images"
EXIF_TIMEOUT       = 30
EXIF_BATCH         = 50   # files per exiftool call

EDITING_SOFTWARE = {
    "photoshop", "lightroom", "gimp", "affinity", "capture one",
    "instagram", "snapseed", "vsco", "facetune", "pixelmator",
    "darktable", "rawtherapee", "luminar", "on1", "dxo",
}

QUALITY_THRESHOLDS = {"excellent": 90, "good": 70, "fair": 50}

IMAGE_EXTENSIONS: set = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp",
    ".tiff", ".tif", ".heic", ".heif", ".webp",
    ".cr2", ".cr3", ".nef", ".nrw", ".arw", ".srf", ".sr2",
    ".dng", ".orf", ".raf", ".rw2", ".pef", ".raw",
}


class PtExifAnalysis(ForensicToolBase):
    """
    Batch-extracts EXIF metadata from all valid and repaired photos, builds
    a photographic timeline, detects GPS locations, identifies edited files,
    and flags anomalies. Read-only on source files.
    """

    def __init__(self, args: argparse.Namespace) -> None:
        self.ptjsonlib  = ptjsonlib.PtJsonLib()
        self.args       = args
        self.case_id    = args.case_id.strip()
        self.analyst    = args.analyst
        self.dry_run    = args.dry_run
        self.output_dir = Path(args.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.valid_dir    = Path(args.valid_dir)
        self.repaired_dir = Path(args.repaired_dir) if args.repaired_dir else None
        self.analysis_dir = self.output_dir / f"{self.case_id}_exif_analysis"

        self._image_files: List[Dict]       = []
        self._exif_db:     List[Dict]       = []
        self._timeline:    Dict[str, List]  = defaultdict(list)
        self._gps_locations: List[Dict]     = []
        self._edited:      List[Dict]       = []
        self._anomalies:   List[Dict]       = []

        self._s: Dict[str, Any] = {
            "total": 0, "with_exif": 0, "without_exif": 0,
            "with_datetime": 0, "with_gps": 0, "edited": 0, "anomalies": 0,
            "iso": [], "aperture": [], "focal": [],
        }
        self._cameras: Counter        = Counter()
        self._dates:   List[datetime] = []

        self.ptjsonlib.add_properties({
            "caseId":        self.case_id,
            "analyst":       self.analyst,
            "timestamp":     datetime.now(timezone.utc).isoformat(),
            "scriptVersion": __version__,
            "validDir":      str(self.valid_dir),
            "repairedDir":   str(self.repaired_dir) if self.repaired_dir else None,
            "dryRun":        self.dry_run,
        })

    # ------------------------------------------------------------------
    # Phases
    # ------------------------------------------------------------------

    def validate_inputs(self) -> bool:
        ptprint("\n[1/4] Validating inputs", "TITLE", condition=self._out())

        if self.dry_run:
            ptprint("  [DRY-RUN] Input validation skipped.",
                    "INFO", condition=self._out())
            self._add_node("inputValidation", True, dryRun=True)
            return True

        if not self.valid_dir.exists():
            return self._fail("inputValidation",
                              f"Valid dir not found: {self.valid_dir}")
        if not self.valid_dir.is_dir():
            return self._fail("inputValidation",
                              f"Not a directory: {self.valid_dir}")

        ptprint(f"  ✓ Valid dir:    {self.valid_dir}", "OK", condition=self._out())

        if self.repaired_dir:
            if not self.repaired_dir.exists():
                ptprint(f"  ⚠ Repaired dir not found: {self.repaired_dir} – skipping",
                        "WARNING", condition=self._out())
                self.repaired_dir = None
            else:
                ptprint(f"  ✓ Repaired dir: {self.repaired_dir}",
                        "OK", condition=self._out())

        self._add_node("inputValidation", True,
                       validDir=str(self.valid_dir),
                       repairedDir=str(self.repaired_dir) if self.repaired_dir else None)
        return True

    def collect_files(self) -> bool:
        ptprint("\n[2/4] Collecting image files", "TITLE", condition=self._out())
        idx = 1

        valid_count = 0
        if not self.dry_run:
            for p in sorted(self.valid_dir.rglob("*")):
                if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS:
                    self._image_files.append(
                        {"id": idx, "filename": p.name,
                         "path": str(p), "source": "valid"})
                    idx         += 1
                    valid_count += 1
        else:
            for i in range(6):
                self._image_files.append(
                    {"id": i + 1, "filename": f"TEST_{i+1:04d}.jpg",
                     "path": str(self.valid_dir / f"TEST_{i+1:04d}.jpg"),
                     "source": "valid"})
            valid_count = 6

        ptprint(f"  Valid files:    {valid_count}", "OK", condition=self._out())

        repaired_count = 0
        if self.repaired_dir and (self.repaired_dir.exists() or self.dry_run):
            if not self.dry_run:
                for p in sorted(self.repaired_dir.rglob("*")):
                    if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS:
                        self._image_files.append(
                            {"id": idx, "filename": p.name,
                             "path": str(p), "source": "repaired"})
                        idx            += 1
                        repaired_count += 1
            ptprint(f"  Repaired files: {repaired_count}", "OK", condition=self._out())

        self._s["total"] = len(self._image_files)
        if self._s["total"] == 0:
            return self._fail("collectFiles",
                              "No image files found in input directories.")

        ptprint(f"  Total: {self._s['total']} "
                f"({valid_count} valid + {repaired_count} repaired)",
                "OK", condition=self._out())
        self.ptjsonlib.add_properties({
            "totalFiles":        self._s["total"],
            "validFilesCount":   valid_count,
            "repairedFilesCount": repaired_count,
        })
        self._add_node("collectFiles", True,
                       totalFiles=self._s["total"],
                       validFiles=valid_count,
                       repairedFiles=repaired_count)
        return True

    def check_exiftool(self) -> bool:
        ptprint("\n[3/4] Checking ExifTool", "TITLE", condition=self._out())

        if not self._run_command(["which", "exiftool"], timeout=5)["success"]:
            return self._fail("toolsCheck",
                              "exiftool not found – "
                              "sudo apt-get install libimage-exiftool-perl")
        ver = self._run_command(["exiftool", "-ver"], timeout=5)["stdout"] or "?"
        ptprint(f"  ✓ exiftool v{ver}", "OK", condition=self._out())
        self._add_node("toolsCheck", True, exiftoolVersion=ver)
        return True

    def _parse_single(self, raw: Dict, fi: Dict) -> Dict:
        """Extract forensically relevant fields from one raw exiftool record."""
        def get(*keys):
            for k in keys:
                v = raw.get(k)
                if v not in (None, "", "0000:00:00 00:00:00"):
                    return v
            return None

        return {
            "fileId":           fi.get("id"),
            "filename":         fi["filename"],
            "path":             fi["path"],
            "source":           fi.get("source", ""),
            "make":             get("EXIF:Make",            "IFD0:Make"),
            "model":            get("EXIF:Model",           "IFD0:Model"),
            "serialNumber":     get("EXIF:SerialNumber",    "MakerNotes:SerialNumber"),
            "datetimeOriginal": get("EXIF:DateTimeOriginal"),
            "createDate":       get("EXIF:CreateDate"),
            "modifyDate":       get("EXIF:ModifyDate",      "IFD0:ModifyDate"),
            "iso":              get("EXIF:ISO"),
            "fNumber":          get("EXIF:FNumber",         "EXIF:ApertureValue"),
            "exposureTime":     get("EXIF:ExposureTime"),
            "focalLength":      get("EXIF:FocalLength"),
            "flash":            get("EXIF:Flash"),
            "width":            get("EXIF:ExifImageWidth",  "File:ImageWidth"),
            "height":           get("EXIF:ExifImageHeight", "File:ImageHeight"),
            "gpsLatitude":      get("EXIF:GPSLatitude"),
            "gpsLongitude":     get("EXIF:GPSLongitude"),
            "gpsAltitude":      get("EXIF:GPSAltitude"),
            "software":         get("EXIF:Software",        "IFD0:Software"),
            "edited":           False,
            "possiblyEdited":   False,
        }

    def extract_exif(self) -> bool:
        ptprint(f"\n[4/4] Extracting EXIF "
                f"({self._s['total']} files, batches of {EXIF_BATCH})",
                "TITLE", condition=self._out())

        MEANINGFUL = {"datetimeOriginal", "make", "model",
                      "iso", "gpsLatitude", "software"}

        for start in range(0, len(self._image_files), EXIF_BATCH):
            batch    = self._image_files[start: start + EXIF_BATCH]
            existing = [(fi, Path(fi["path"]))
                        for fi in batch
                        if Path(fi["path"]).exists() or self.dry_run]
            if not existing:
                continue

            cmd      = (["exiftool", "-j", "-G", "-a", "-s", "-n"]
                        + [str(p) for _, p in existing])
            r        = self._run_command(
                cmd, timeout=EXIF_TIMEOUT * len(existing))
            raw_list = (json.loads(r["stdout"])
                        if r["success"] and r["stdout"] else [])

            for idx, (fi, _) in enumerate(existing):
                raw    = raw_list[idx] if idx < len(raw_list) else {}
                parsed = self._parse_single(raw, fi)
                if any(parsed.get(k) for k in MEANINGFUL):
                    self._exif_db.append(parsed)
                    self._s["with_exif"] += 1
                else:
                    self._s["without_exif"] += 1

            done = min(start + EXIF_BATCH, len(self._image_files))
            ptprint(f"  {done}/{len(self._image_files)} "
                    f"({done * 100 // len(self._image_files)}%)",
                    "INFO", condition=self._out())

        ptprint(f"  With EXIF: {self._s['with_exif']}  |  "
                f"Without: {self._s['without_exif']}",
                "OK", condition=self._out())
        self._add_node("exifExtraction", True,
                       filesWithExif=self._s["with_exif"],
                       filesWithoutExif=self._s["without_exif"])
        return self._s["with_exif"] > 0

    # ------------------------------------------------------------------
    # Analysis helpers (called per EXIF entry)
    # ------------------------------------------------------------------

    def _process_datetime(self, exif: Dict, now: datetime) -> Optional[datetime]:
        """Parse DateTimeOriginal or CreateDate; update timeline and date list."""
        dt_str = exif.get("datetimeOriginal") or exif.get("createDate")
        if not dt_str:
            return None
        try:
            dt = datetime.strptime(str(dt_str), "%Y:%m:%d %H:%M:%S")
            self._dates.append(dt)
            exif["parsedDatetime"] = dt.isoformat()
            self._timeline[dt.strftime("%Y-%m-%d")].append({
                "filename": exif["filename"],
                "time":     dt.strftime("%H:%M:%S"),
                "camera":   (f"{exif.get('make') or '?'} "
                             f"{exif.get('model') or ''}").strip(),
            })
            self._s["with_datetime"] += 1
            return dt
        except (ValueError, TypeError):
            return None

    def _process_camera(self, exif: Dict) -> None:
        """Update camera counter."""
        cam = (f"{exif.get('make') or 'Unknown'} "
               f"{exif.get('model') or 'Unknown'}").strip()
        self._cameras[cam] += 1

    def _process_settings(self, exif: Dict) -> None:
        """Accumulate ISO, aperture, and focal length lists."""
        for field, store in (("iso", "iso"), ("fNumber", "aperture"),
                              ("focalLength", "focal")):
            if exif.get(field):
                try:
                    self._s[store].append(
                        float(str(exif[field]).replace("mm", "").strip()))
                except (ValueError, TypeError):
                    pass

    def _process_gps(self, exif: Dict) -> None:
        """Extract GPS coordinates if present."""
        if exif.get("gpsLatitude") and exif.get("gpsLongitude"):
            try:
                self._gps_locations.append({
                    "filename":  exif["filename"],
                    "latitude":  float(exif["gpsLatitude"]),
                    "longitude": float(exif["gpsLongitude"]),
                    "altitude":  exif.get("gpsAltitude"),
                })
                self._s["with_gps"] += 1
            except (ValueError, TypeError):
                pass

    def _detect_edit(self, exif: Dict) -> None:
        """Check the Software field for known editing applications."""
        sw = (exif.get("software") or "").lower()
        if sw and any(e in sw for e in EDITING_SOFTWARE):
            exif["edited"] = True
            self._edited.append({"filename": exif["filename"],
                                  "software": exif["software"]})
            self._s["edited"] += 1

    def _detect_anomaly(self, exif: Dict,
                         dt: Optional[datetime], now: datetime) -> None:
        """Flag future dates, unusual ISO, and modify-after-original cases."""
        # Future DateTimeOriginal
        if dt and dt > now:
            self._anomalies.append({
                "filename": exif["filename"], "type": "future_date",
                "detail":   f"DateTimeOriginal in future: {dt.date()}"})
            self._s["anomalies"] += 1

        # Unusually high ISO
        if exif.get("iso"):
            try:
                if int(float(exif["iso"])) > 25600:
                    self._anomalies.append({
                        "filename": exif["filename"], "type": "unusual_iso",
                        "detail":   f"ISO {exif['iso']} (>25600)"})
                    self._s["anomalies"] += 1
            except (ValueError, TypeError):
                pass

        # ModifyDate newer than DateTimeOriginal without Software tag
        if exif.get("modifyDate") and exif.get("datetimeOriginal"):
            try:
                orig   = datetime.strptime(str(exif["datetimeOriginal"]),
                                            "%Y:%m:%d %H:%M:%S")
                modify = datetime.strptime(str(exif["modifyDate"]),
                                            "%Y:%m:%d %H:%M:%S")
                if modify > orig and not exif.get("edited"):
                    exif["possiblyEdited"] = True
                    self._anomalies.append({
                        "filename": exif["filename"],
                        "type":     "modify_after_original",
                        "detail":   (f"ModifyDate {modify.date()} > "
                                     f"DateTimeOriginal {orig.date()}")})
                    self._s["anomalies"] += 1
            except (ValueError, TypeError):
                pass

    def analyse(self) -> None:
        """Iterate over all EXIF records and apply the five analysis helpers."""
        ptprint("\nAnalysing EXIF data …", "TITLE", condition=self._out())
        now = datetime.now()

        for exif in self._exif_db:
            dt = self._process_datetime(exif, now)
            self._process_camera(exif)
            self._process_settings(exif)
            self._process_gps(exif)
            self._detect_edit(exif)
            self._detect_anomaly(exif, dt, now)

        ptprint(f"  Cameras: {len(self._cameras)}  |  "
                f"GPS: {self._s['with_gps']}  |  "
                f"Edited: {self._s['edited']}  |  "
                f"Anomalies: {self._s['anomalies']}",
                "OK", condition=self._out())

    # ------------------------------------------------------------------
    # Run and save
    # ------------------------------------------------------------------

    def _range_stats(self, vals: List[float]) -> Optional[Dict]:
        if not vals:
            return None
        return {"min": round(min(vals), 2),
                "max": round(max(vals), 2),
                "avg": round(sum(vals) / len(vals), 2)}

    def run(self) -> None:
        ptprint("=" * 70, "TITLE", condition=self._out())
        ptprint(f"EXIF METADATA ANALYSIS v{__version__}  |  "
                f"Case: {self.case_id}", "TITLE", condition=self._out())
        if self.dry_run:
            ptprint("MODE: DRY-RUN", "WARNING", condition=self._out())
        ptprint("=" * 70, "TITLE", condition=self._out())

        if not self.validate_inputs():
            self.ptjsonlib.set_status("finished"); return
        if not self.collect_files():
            self.ptjsonlib.set_status("finished"); return
        if not self.check_exiftool():
            self.ptjsonlib.set_status("finished"); return
        if not self.extract_exif():
            ptprint("No EXIF data extracted.", "ERROR", condition=self._out())
            self.ptjsonlib.set_status("finished"); return

        self.analyse()

        s             = self._s
        quality_pct   = round(s["with_datetime"] / max(s["total"], 1) * 100, 1)
        quality_label = next((lbl for lbl, thr in QUALITY_THRESHOLDS.items()
                               if quality_pct >= thr), "poor")

        date_range: Dict = {}
        if self._dates:
            date_range = {
                "earliest": min(self._dates).strftime("%Y-%m-%d %H:%M:%S"),
                "latest":   max(self._dates).strftime("%Y-%m-%d %H:%M:%S"),
                "spanDays": (max(self._dates) - min(self._dates)).days,
            }

        settings_range = {
            "iso":         self._range_stats(s["iso"]),
            "aperture":    self._range_stats(s["aperture"]),
            "focalLength": self._range_stats(s["focal"]),
        }

        self.ptjsonlib.add_properties({
            "compliance":       ["NIST SP 800-86", "EXIF 2.32", "CIPA DC-008-2019"],
            "filesWithExif":    s["with_exif"],
            "filesWithoutExif": s["without_exif"],
            "withDatetime":     s["with_datetime"],
            "withGps":          s["with_gps"],
            "editedPhotos":     s["edited"],
            "anomalies":        s["anomalies"],
            "uniqueCameras":    len(self._cameras),
            "dateRange":        date_range,
            "qualityScore":     quality_label,
            "qualityPct":       quality_pct,
            "settingsRange":    settings_range,
            "byCamera":         dict(self._cameras.most_common(10)),
        })
        self.ptjsonlib.add_node(self.ptjsonlib.create_node_object(
            "chainOfCustodyEntry",
            properties={
                "action":    (f"EXIF analysis complete – "
                              f"{s['with_exif']} files with EXIF, "
                              f"quality: {quality_label}"),
                "result":    "SUCCESS" if s["with_exif"] > 0 else "NO_EXIF",
                "analyst":   self.analyst,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ))
        self._add_node("analysisSummary", True,
                       qualityScore=quality_label, qualityPct=quality_pct,
                       uniqueCameras=len(self._cameras),
                       withGps=s["with_gps"], editedPhotos=s["edited"],
                       anomalies=s["anomalies"], dateRange=date_range)

        ptprint("\n" + "=" * 70, "TITLE", condition=self._out())
        ptprint("EXIF ANALYSIS COMPLETE", "OK", condition=self._out())
        ptprint(f"EXIF: {s['with_exif']}/{s['total']}  |  "
                f"Datetime: {s['with_datetime']}  |  GPS: {s['with_gps']}  |  "
                f"Edited: {s['edited']}  |  "
                f"Quality: {quality_label.upper()} ({quality_pct}%)",
                "INFO", condition=self._out())
        ptprint("Next: Final report", "INFO", condition=self._out())
        ptprint("=" * 70, "TITLE", condition=self._out())
        self.ptjsonlib.set_status("finished")

    def _write_text_report(self, props: Dict) -> Path:
        sep   = "=" * 70
        lines = [sep, "EXIF METADATA ANALYSIS REPORT", sep, "",
                 f"Case ID:   {self.case_id}",
                 f"Analyst:   {self.analyst}",
                 f"Timestamp: {props.get('timestamp', '')}", "",
                 "SUMMARY:",
                 f"  Total files:         {props.get('totalFiles', 0)}",
                 f"  Files with EXIF:     {props.get('filesWithExif', 0)}",
                 f"  Files with datetime: {props.get('withDatetime', 0)}",
                 f"  Files with GPS:      {props.get('withGps', 0)}",
                 f"  Edited photos:       {props.get('editedPhotos', 0)}",
                 f"  Anomalies:           {props.get('anomalies', 0)}",
                 f"\nQUALITY SCORE: "
                 f"{(props.get('qualityScore') or '?').upper()} "
                 f"({props.get('qualityPct', 0)}%)"]

        dr = props.get("dateRange", {})
        if dr:
            lines += ["", "DATE RANGE:",
                      f"  Earliest: {dr.get('earliest', '?')}",
                      f"  Latest:   {dr.get('latest', '?')}",
                      f"  Span:     {dr.get('spanDays', 0)} days"]

        lines += ["", f"UNIQUE CAMERAS: {props.get('uniqueCameras', 0)}"]
        for cam, cnt in list(props.get("byCamera", {}).items())[:10]:
            pct = cnt / max(self._s["with_exif"], 1) * 100
            lines.append(f"  {cam}: {cnt} ({pct:.1f}%)")

        sr = props.get("settingsRange", {})
        if sr.get("iso"):
            i = sr["iso"]
            lines.append(f"\nISO:          {i['min']} – {i['max']} "
                         f"(avg {i['avg']})")
        if sr.get("aperture"):
            a = sr["aperture"]
            lines.append(f"Aperture:     f/{a['min']} – f/{a['max']} "
                         f"(avg f/{a['avg']})")
        if sr.get("focalLength"):
            f_ = sr["focalLength"]
            lines.append(f"Focal length: {f_['min']} – {f_['max']} mm "
                         f"(avg {f_['avg']} mm)")

        if self._timeline:
            lines += ["", "TIMELINE (first 20 days):"]
            lines += [f"  {d}: {len(v)} photos"
                      for d, v in sorted(self._timeline.items())[:20]]

        if self._gps_locations:
            lines += ["", f"GPS LOCATIONS ({len(self._gps_locations)} photos):"]
            lines += [f"  {loc['filename']}: "
                      f"{loc['latitude']:.6f}, {loc['longitude']:.6f}"
                      for loc in self._gps_locations[:10]]

        if self._edited:
            lines += ["", f"EDITED PHOTOS ({len(self._edited)}):"]
            lines += [f"  {e['filename']}: {e['software']}"
                      for e in self._edited[:20]]

        if self._anomalies:
            lines += ["", f"ANOMALIES ({len(self._anomalies)}):"]
            lines += [f"  [{a['type']}] {a['filename']}: {a['detail']}"
                      for a in self._anomalies[:20]]

        txt = self.analysis_dir / f"{self.case_id}_EXIF_REPORT.txt"
        txt.write_text("\n".join(lines), encoding="utf-8")
        return txt

    def save_report(self) -> Optional[str]:
        if self.args.json:
            ptprint(self.ptjsonlib.get_result_json(), "", self.args.json)
            return None

        if not self.dry_run:
            self.analysis_dir.mkdir(parents=True, exist_ok=True)

        props     = json.loads(self.ptjsonlib.get_result_json())["result"]["properties"]
        json_file = (Path(self.args.json_out) if self.args.json_out
                     else self.analysis_dir / f"{self.case_id}_exif_database.json")
        database  = {
            "caseId":       self.case_id,
            "analyst":      self.analyst,
            "timestamp":    props.get("timestamp"),
            "statistics":   props,
            "exifData":     self._exif_db,
            "timeline":     dict(self._timeline),
            "gpsLocations": self._gps_locations,
            "editedPhotos": self._edited,
            "anomalies":    self._anomalies,
        }
        if not self.dry_run:
            json_file.write_text(
                json.dumps(database, indent=2, ensure_ascii=False, default=str),
                encoding="utf-8")
        ptprint(f"JSON database: {json_file.name}", "OK", condition=self._out())

        csv_file = self.analysis_dir / f"{self.case_id}_exif_data.csv"
        if self._exif_db and not self.dry_run:
            all_keys = sorted({k for rec in self._exif_db for k in rec})
            with open(csv_file, "w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=all_keys)
                writer.writeheader()
                writer.writerows(self._exif_db)
        ptprint(f"CSV export:    {csv_file.name}", "OK", condition=self._out())

        if not self.dry_run:
            txt = self._write_text_report(props)
            ptprint(f"Text report:   {txt.name}", "OK", condition=self._out())

        return str(json_file)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def get_help() -> List[Dict]:
    return [
        {"description": [
            "Forensic EXIF metadata analysis – ptlibs compliant",
            "Batch-extracts EXIF, builds timeline, detects edits and anomalies",
            "Read-only on source files",
            "Compliant with EXIF 2.32 / CIPA DC-008-2019 and NIST SP 800-86",
        ]},
        {"usage": [
            "ptexifanalysis <case-id> --valid-dir <dir> "
            "[--repaired-dir <dir>] [options]"
        ]},
        {"usage_example": [
            "ptexifanalysis CASE-001 "
            "--valid-dir .../CASE-001_validation/valid",
            "ptexifanalysis CASE-001 "
            "--valid-dir .../valid "
            "--repaired-dir .../repaired "
            "--analyst 'Jane' --json-out result.json",
            "ptexifanalysis CASE-001 --valid-dir ./valid --dry-run",
        ]},
        {"options": [
            ["case-id",              "",      "Forensic case identifier – REQUIRED"],
            ["-v", "--valid-dir",    "<dir>", "Directory with valid files – REQUIRED"],
            ["-r", "--repaired-dir", "<dir>", "Directory with repaired files (optional)"],
            ["-o", "--output-dir",   "<dir>", f"Output directory (default: {DEFAULT_OUTPUT_DIR})"],
            ["-a", "--analyst",      "<n>",   "Analyst name (default: Analyst)"],
            ["-j", "--json-out",     "<f>",   "Save JSON output to file"],
            ["-q", "--quiet",        "",      "Suppress terminal output"],
            ["--dry-run",            "",      "Simulate without running exiftool"],
            ["-h", "--help",         "",      "Show help"],
            ["--version",            "",      "Show version"],
        ]},
        {"notes": [
            "Quality: excellent >90% | good 70–90% | fair 50–70% | poor <50% "
            "(DateTimeOriginal coverage)",
            "Edit detection: photoshop, lightroom, gimp, instagram, snapseed, vsco, …",
            "Anomaly detection: future_date | unusual_iso (>25600) | "
            "modify_after_original",
            "Output: {case_id}_exif_database.json | {case_id}_exif_data.csv | "
            "{case_id}_EXIF_REPORT.txt",
            "Compliant with EXIF 2.32 / CIPA DC-008-2019 and NIST SP 800-86",
        ]},
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("case_id")
    parser.add_argument("-v", "--valid-dir",    required=True)
    parser.add_argument("-r", "--repaired-dir", default=None)
    parser.add_argument("-o", "--output-dir",   default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("-a", "--analyst",      default="Analyst")
    parser.add_argument("-j", "--json-out",     default=None)
    parser.add_argument("-q", "--quiet",        action="store_true")
    parser.add_argument("--dry-run",            action="store_true")
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
        tool = PtExifAnalysis(args)
        tool.run()
        tool.save_report()
        props = json.loads(tool.ptjsonlib.get_result_json())["result"]["properties"]
        return 0 if props.get("filesWithExif", 0) > 0 else 1
    except KeyboardInterrupt:
        ptprint("Interrupted by user.", "WARNING", condition=True)
        return 130
    except Exception as exc:
        ptprint(f"ERROR: {exc}", "ERROR", condition=True)
        return 99


if __name__ == "__main__":
    sys.exit(main())