#!/usr/bin/env python3
"""
    Copyright (c) 2025 Bc. Dominik Sabota, VUT FIT Brno

    ptphotorepair - Forensic photo repair tool

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License.
    See <https://www.gnu.org/licenses/> for details.
"""

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from PIL import Image, ImageFile
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from ._version import __version__

from ptlibs import ptjsonlib, ptprinthelper
from ptlibs.ptprinthelper import ptprint

# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------

SCRIPTNAME         = "ptphotorepair"
DEFAULT_OUTPUT_DIR = "/var/forensics/images"
VALIDATE_TIMEOUT   = 30

SOI  = b"\xff\xd8"
EOI  = b"\xff\xd9"
SOS  = b"\xff\xda"
SOF0 = b"\xff\xc0"
DQT  = b"\xff\xdb"
DHT  = b"\xff\xc4"

JFIF_APP0        = b"\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
MARKER_PREFIX    = b"\xff"
CRITICAL_MARKERS = {SOF0, DQT, DHT}

# Empirical success rate ranges per repair technique
EXPECTED_SUCCESS: Dict[str, Tuple[int, int]] = {
    "repair_missing_footer":   (85, 95),
    "repair_invalid_header":   (90, 95),
    "repair_invalid_segments": (80, 85),
    "repair_truncated_file":   (50, 70),
}

# ---------------------------------------------------------------------------
# MAIN CLASS
# ---------------------------------------------------------------------------

class PtPhotoRepair:
    """
    Forensic photo repair – ptlibs compliant.

    Pipeline: validate inputs → check tools → load filesNeedingRepair →
              per-file repair (technique routing) → post-repair validation →
              organise (repaired / failed) → JSON + text report.

    Repair techniques:
      missing_footer    → repair_missing_footer()    85–95 %
      invalid_header    → repair_invalid_header()    90–95 %
      corrupt_segments  → repair_invalid_segments()  80–85 %
      truncated / other → repair_truncated_file()    50–70 %

    READ-ONLY on source files. Repair works on shutil.copy2 working copies.
    Compliant with ISO/IEC 10918-1, JFIF 1.02, NIST SP 800-86 §3.1.4.
    """

    def __init__(self, args: argparse.Namespace) -> None:
        self.ptjsonlib  = ptjsonlib.PtJsonLib()
        self.args       = args
        self.case_id    = args.case_id.strip()
        self.analyst    = args.analyst
        self.dry_run    = args.dry_run
        self.output_dir = Path(args.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.corrupted_dir     = Path(args.corrupted_dir)
        self.validation_report = Path(args.validation_report)
        self.repair_base       = self.output_dir / f"{self.case_id}_repair"
        self.repaired_dir      = self.repair_base / "repaired"
        self.failed_dir        = self.repair_base / "failed"

        self._tools:           Dict[str, bool] = {}
        self._files_to_repair: List[Dict]      = []
        self._results:         List[Dict]      = []
        self._by_type:         Dict[str, Dict] = {}
        self._s = {"attempted": 0, "repaired": 0, "failed": 0, "skipped": 0}

        if PIL_AVAILABLE:
            ImageFile.LOAD_TRUNCATED_IMAGES = True

        self.ptjsonlib.add_properties({
            "caseId":            self.case_id,
            "analyst":           self.analyst,
            "timestamp":         datetime.now(timezone.utc).isoformat(),
            "scriptVersion":     __version__,
            "compliance":        ["NIST SP 800-86", "ISO/IEC 10918-1", "JFIF 1.02"],
            "corruptedDir":      str(self.corrupted_dir),
            "validationReport":  str(self.validation_report),
            "outputDirectory":   str(self.output_dir),
            "totalAttempted":    0,
            "successfulRepairs": 0,
            "failedRepairs":     0,
            "skippedFiles":      0,
            "successRate":       0.0,
            "byCorruptionType":  {},
            "dryRun":            self.dry_run,
        })
        ptprint(f"Initialized: case={self.case_id}", "INFO", condition=not self.args.json)

    # --- helpers ------------------------------------------------------------

    def _add_node(self, node_type: str, success: bool, **kwargs) -> None:
        self.ptjsonlib.add_node(self.ptjsonlib.create_node_object(
            node_type, properties={"success": success, **kwargs}
        ))

    def _fail(self, node_type: str, msg: str) -> bool:
        ptprint(msg, "ERROR", condition=not self.args.json)
        self._add_node(node_type, False, error=msg)
        return False

    def _run(self, cmd: List[str], timeout: int = VALIDATE_TIMEOUT) -> Dict[str, Any]:
        if self.dry_run:
            return {"success": True, "stdout": "[DRY-RUN]", "stderr": "", "returncode": 0}
        try:
            p = subprocess.run(cmd, capture_output=True, text=True,
                               timeout=timeout, check=False)
            return {"success": p.returncode == 0, "stdout": p.stdout.strip(),
                    "stderr": p.stderr.strip(), "returncode": p.returncode}
        except subprocess.TimeoutExpired:
            return {"success": False, "stdout": "",
                    "stderr": f"Timeout {timeout}s", "returncode": -1}
        except Exception as exc:
            return {"success": False, "stdout": "", "stderr": str(exc), "returncode": -1}

    def _rb(self, path: Path) -> Optional[bytes]:
        try:
            return path.read_bytes()
        except Exception:
            return None

    def _wb(self, path: Path, data: bytes) -> bool:
        try:
            path.write_bytes(data)
            return True
        except Exception:
            return False

    # --- phases -------------------------------------------------------------

    def validate_inputs(self) -> bool:
        """Verify corrupted_dir and validation_report exist before doing anything."""
        ptprint("\n[1/3] Validating Inputs", "TITLE", condition=not self.args.json)

        if self.dry_run:
            ptprint("[DRY-RUN] Input validation skipped.",
                    "INFO", condition=not self.args.json)
            self._add_node("inputValidation", True, dryRun=True)
            return True

        if not self.corrupted_dir.exists():
            return self._fail("inputValidation",
                              f"Corrupted dir not found: {self.corrupted_dir}")
        if not self.corrupted_dir.is_dir():
            return self._fail("inputValidation",
                              f"Not a directory: {self.corrupted_dir}")
        if not self.validation_report.exists():
            return self._fail("inputValidation",
                              f"Validation report not found: {self.validation_report}")

        ptprint(f"  ✓ Corrupted dir:      {self.corrupted_dir}", "OK",
                condition=not self.args.json)
        ptprint(f"  ✓ Validation report:  {self.validation_report.name}", "OK",
                condition=not self.args.json)
        self._add_node("inputValidation", True,
                       corruptedDir=str(self.corrupted_dir),
                       validationReport=str(self.validation_report))
        return True

    def check_tools(self) -> bool:
        """Verify PIL (required) and optional tool jpeginfo."""
        ptprint("\n[2/3] Checking Repair Tools", "TITLE", condition=not self.args.json)

        self._tools["pil"] = PIL_AVAILABLE or self.dry_run
        ptprint(
            f"  {'✓' if self._tools['pil'] else '✗'} PIL/Pillow"
            + ("" if self._tools["pil"]
               else " – pip install Pillow --break-system-packages"),
            "OK" if self._tools["pil"] else "ERROR",
            condition=not self.args.json
        )

        found = self._run(["which", "jpeginfo"], timeout=5)["success"]
        self._tools["jpeginfo"] = found
        ptprint(f"  {'✓' if found else '⚠'} jpeginfo"
                + ("" if found else " – sudo apt-get install jpeginfo"),
                "OK" if found else "WARNING", condition=not self.args.json)

        if not self._tools["pil"]:
            ptprint("PIL/Pillow is required – install with: "
                    "pip install Pillow --break-system-packages",
                    "ERROR", condition=not self.args.json)

        self._add_node("toolsCheck", self._tools["pil"], tools=self._tools)
        return self._tools["pil"]

    def load_report(self) -> bool:
        """Load filesNeedingRepair list from validation_report.json."""
        ptprint("\n[3/3] Loading Files to Repair", "TITLE", condition=not self.args.json)

        if self.dry_run:
            self._files_to_repair = [
                {"filename": f"TEST_{i:04d}.jpg", "corruptionType": ct}
                for i, ct in enumerate(
                    ["missing_footer", "missing_footer",
                     "invalid_header", "corrupt_segments",
                     "truncated", "truncated"], 1)
            ]
        else:
            try:
                raw = json.loads(self.validation_report.read_text(encoding="utf-8"))
            except Exception as exc:
                return self._fail("reportLoad", f"Cannot read validation report: {exc}")
            self._files_to_repair = (raw.get("filesNeedingRepair") or
                                     raw.get("files_needing_repair") or [])

        if not self._files_to_repair:
            ptprint("No files listed for repair in validation report.",
                    "WARNING", condition=not self.args.json)

        ptprint(f"Files to repair: {len(self._files_to_repair)}",
                "OK", condition=not self.args.json)
        self._add_node("reportLoad", True, filesToRepair=len(self._files_to_repair))
        return True

    # --- repair techniques --------------------------------------------------

    def repair_missing_footer(self, path: Path) -> Tuple[bool, str]:
        """Append missing JPEG EOI (FF D9) marker."""
        data = self._rb(path)
        if data is None:
            return False, "Cannot read file"
        if data.endswith(EOI):
            return False, "EOI already present – file may have different corruption"
        if data.endswith(MARKER_PREFIX):
            return self._wb(path, data[:-1] + EOI), "Replaced incomplete trailing marker with EOI"
        return self._wb(path, data + EOI), "Appended missing EOI marker"

    def repair_invalid_header(self, path: Path) -> Tuple[bool, str]:
        """Fix corrupt/missing JPEG SOI header."""
        data = self._rb(path)
        if data is None:
            return False, "Cannot read file"
        soi_pos = data.find(SOI)
        if soi_pos > 0:
            return self._wb(path, data[soi_pos:]), f"Removed {soi_pos} leading garbage bytes"
        if soi_pos == 0:
            return False, "SOI already at offset 0 – file may have different corruption"
        sos_pos = data.find(SOS)
        if sos_pos < 0:
            return False, "No SOI or SOS marker found – file unrecoverable"
        return (self._wb(path, SOI + JFIF_APP0 + data[sos_pos:]),
                "Inserted synthetic SOI + JFIF APP0 before SOS")

    def repair_invalid_segments(self, path: Path) -> Tuple[bool, str]:
        """Remove corrupt APP segments, preserve critical markers SOF0/DQT/DHT."""
        data = self._rb(path)
        if data is None:
            return False, "Cannot read file"
        sos_pos = data.find(SOS)
        if sos_pos < 0:
            return False, "No SOS marker found – cannot locate image data"
        critical = b""
        i = 2
        while i < sos_pos - 1:
            if data[i:i+1] != MARKER_PREFIX:
                i += 1
                continue
            marker  = data[i:i+2]
            if i + 4 > len(data):
                break
            seg_len = int.from_bytes(data[i+2:i+4], "big")
            seg_end = i + 2 + seg_len
            if seg_end > len(data):
                break
            if marker in CRITICAL_MARKERS:
                critical += data[i:seg_end]
            i = seg_end
        removed = sos_pos - 2 - len(JFIF_APP0) - len(critical)
        return (self._wb(path, SOI + JFIF_APP0 + critical + data[sos_pos:]),
                f"Removed {removed} bytes of corrupt segment data")

    def repair_truncated_file(self, path: Path) -> Tuple[bool, str]:
        """Partial recovery via PIL LOAD_TRUNCATED_IMAGES."""
        if self.dry_run:
            return True, "[DRY-RUN] truncated repair simulated"
        tmp = path.parent / (path.stem + "_tmp.jpg")
        try:
            img = Image.open(path)
            img.load()
            w, h = img.size
            if w == 0 or h == 0:
                return False, "Zero dimensions after truncated load"
            img.save(tmp, "JPEG", quality=95, optimize=True, progressive=False)
            shutil.move(str(tmp), str(path))
            return True, f"Partial recovery succeeded: {w}×{h} px"
        except Exception as exc:
            if tmp.exists():
                tmp.unlink(missing_ok=True)
            return False, str(exc)

    _STRATEGY_MAP: Dict[str, str] = {
        "missing_footer":   "repair_missing_footer",
        "invalid_header":   "repair_invalid_header",
        "corrupt_segments": "repair_invalid_segments",
        "corrupt_segment":  "repair_invalid_segments",
        "invalid_segment":  "repair_invalid_segments",
        "corrupt_data":     "repair_truncated_file",
        "truncated":        "repair_truncated_file",
        "unknown":          "repair_invalid_header",
    }

    # --- post-repair validation ---------------------------------------------

    def _validate_repaired(self, path: Path) -> Dict[str, Any]:
        """PIL + optional jpeginfo validation after repair."""
        if self.dry_run:
            return {"valid": True, "toolsPassed": 2, "toolsTotal": 2}

        passed = total = 0
        d: Dict[str, Any] = {}

        # PIL – works for all formats
        total += 1
        try:
            img = Image.open(path)
            img.verify()
            img = Image.open(path)
            img.load()
            w, h = img.size
            if w > 0 and h > 0:
                d.update({"pil": True, "width": w, "height": h, "mode": img.mode})
                passed += 1
            else:
                d["pil"] = False
                d["pilError"] = "zero dimensions after load"
        except Exception as exc:
            d["pil"]      = False
            d["pilError"] = str(exc)[:120]

        # jpeginfo – JPEG only, optional
        if self._tools.get("jpeginfo") and path.suffix.lower() in (".jpg", ".jpeg"):
            total += 1
            r = self._run(["jpeginfo", "-c", str(path)])
            d["jpeginfo"] = r["success"]
            if r["success"]:
                passed += 1
            else:
                d["jpeginfError"] = (r["stdout"] + " " + r["stderr"]).strip()[:120]

        d.update({"toolsPassed": passed, "toolsTotal": total, "valid": passed > 0})
        return d

    # --- repair loop --------------------------------------------------------

    def repair_all_files(self) -> None:
        """Route each file to the correct technique and validate the result."""
        ptprint("\nRepairing files …", "TITLE", condition=not self.args.json)

        total = len(self._files_to_repair)
        self._s["attempted"] = total

        if total == 0:
            ptprint("No files to repair.", "INFO", condition=not self.args.json)
            self._add_node("repairPhase", True, totalAttempted=0)
            return

        for idx, fi in enumerate(self._files_to_repair, 1):
            filename = fi.get("filename") or fi.get("file_name", "unknown")
            ctype    = fi.get("corruptionType") or fi.get("corruption_type") or "unknown"
            ptprint(f"  [{idx}/{total}] {filename}  [{ctype}]",
                    "INFO", condition=not self.args.json)

            src = self.corrupted_dir / filename
            if not src.exists() and not self.dry_run:
                self._results.append({
                    "filename":       filename,
                    "corruptionType": ctype,
                    "attempted":      False,
                    "finalStatus":    "skipped",
                    "error":          f"Source file not found in {self.corrupted_dir}",
                })
                self._s["skipped"] += 1
                ptprint(f"    ⚠ Skipped – file not found in corrupted dir",
                        "WARNING", condition=not self.args.json)
                continue

            work        = self.repair_base / filename
            method_name = self._STRATEGY_MAP.get(ctype, "repair_invalid_header")
            repair_func = getattr(self, method_name)
            exp_lo, exp_hi = EXPECTED_SUCCESS.get(method_name, (50, 80))

            if not self.dry_run:
                shutil.copy2(src, work)

            entry: Dict[str, Any] = {
                "filename":        filename,
                "corruptionType":  ctype,
                "attempted":       True,
                "repairTechnique": method_name,
                "expectedSuccess": f"{exp_lo}–{exp_hi} %",
            }

            ok, msg = repair_func(work) if not self.dry_run else (True, "[DRY-RUN]")
            entry["repairMessage"] = msg

            if ok:
                v = self._validate_repaired(work)
                entry["validation"] = v
                if v["valid"]:
                    dst = self.repaired_dir / filename
                    if not self.dry_run:
                        if dst.exists():
                            stem, sfx, n = dst.stem, dst.suffix, 1
                            while dst.exists():
                                dst = self.repaired_dir / f"{stem}_{n}{sfx}"
                                n += 1
                        shutil.move(str(work), str(dst))
                    entry["finalStatus"] = "fully_repaired"
                    self._s["repaired"] += 1
                    ptprint(f"    ✓ REPAIRED  ({msg})", "OK", condition=not self.args.json)
                else:
                    if not self.dry_run:
                        shutil.move(str(work), str(self.failed_dir / filename))
                    entry["finalStatus"] = "repair_failed_validation"
                    self._s["failed"] += 1
                    ptprint("    ✗ Repair applied but post-repair validation failed",
                            "WARNING", condition=not self.args.json)
            else:
                if not self.dry_run:
                    shutil.copy2(src, self.failed_dir / filename)
                    if work.exists():
                        work.unlink(missing_ok=True)
                entry["finalStatus"] = "repair_failed"
                self._s["failed"] += 1
                ptprint(f"    ✗ Failed  ({msg})", "WARNING", condition=not self.args.json)

            # Per-type statistics
            if ctype not in self._by_type:
                self._by_type[ctype] = {"attempted": 0, "successful": 0, "failed": 0}
            self._by_type[ctype]["attempted"] += 1
            if entry["finalStatus"] == "fully_repaired":
                self._by_type[ctype]["successful"] += 1
            else:
                self._by_type[ctype]["failed"] += 1

            self._results.append(entry)

        rate = round(self._s["repaired"] / max(total, 1) * 100, 2)
        ptprint(
            f"\nRepaired: {self._s['repaired']}/{total} "
            f"| Failed: {self._s['failed']} "
            f"| Skipped: {self._s['skipped']} "
            f"| Rate: {rate}%",
            "OK", condition=not self.args.json
        )
        self._add_node("repairPhase", True,
                       totalAttempted=total,
                       successfulRepairs=self._s["repaired"],
                       failedRepairs=self._s["failed"],
                       skippedFiles=self._s["skipped"],
                       successRate=rate,
                       byCorruptionType=self._by_type)

    # --- run & save ---------------------------------------------------------

    def run(self) -> None:
        """Orchestrate the full repair pipeline."""
        ptprint("=" * 70, "TITLE", condition=not self.args.json)
        ptprint(f"PHOTO REPAIR v{__version__} | Case: {self.case_id}",
                "TITLE", condition=not self.args.json)
        if self.dry_run:
            ptprint("MODE: DRY-RUN", "WARNING", condition=not self.args.json)
        ptprint("=" * 70, "TITLE", condition=not self.args.json)

        if not self.validate_inputs():
            self.ptjsonlib.set_status("finished"); return
        if not self.check_tools():
            self.ptjsonlib.set_status("finished"); return
        if not self.load_report():
            self.ptjsonlib.set_status("finished"); return

        if not self.dry_run:
            for d in (self.repaired_dir, self.failed_dir):
                d.mkdir(parents=True, exist_ok=True)

        self.repair_all_files()

        rate = round(self._s["repaired"] / max(self._s["attempted"], 1) * 100, 2)
        self.ptjsonlib.add_properties({
            "totalAttempted":    self._s["attempted"],
            "successfulRepairs": self._s["repaired"],
            "failedRepairs":     self._s["failed"],
            "skippedFiles":      self._s["skipped"],
            "successRate":       rate,
            "byCorruptionType":  self._by_type,
        })

        # Chain of Custody entry
        self.ptjsonlib.add_node(self.ptjsonlib.create_node_object(
            "chainOfCustodyEntry",
            properties={
                "action":    f"Oprava fotografií dokončená – "
                             f"{self._s['repaired']} úspešných, "
                             f"{self._s['failed']} neúspešných",
                "result":    "SUCCESS" if self._s["repaired"] > 0 else "NO_REPAIRS",
                "analyst":   self.analyst,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ))

        ptprint("\n" + "=" * 70, "TITLE", condition=not self.args.json)
        ptprint(
            f"REPAIR COMPLETED | "
            f"{self._s['repaired']}/{self._s['attempted']} successful ({rate}%)",
            "OK", condition=not self.args.json
        )
        ptprint("Next: EXIF Analysis (ptexifanalysis)", "INFO", condition=not self.args.json)
        ptprint("=" * 70, "TITLE", condition=not self.args.json)
        self.ptjsonlib.set_status("finished")

    def _write_text_report(self, json_path: Path) -> Path:
        """Write {case_id}_REPAIR_REPORT.txt alongside the JSON report."""
        rate = round(self._s["repaired"] / max(self._s["attempted"], 1) * 100, 2)
        sep  = "=" * 70
        lines = [
            sep, "PHOTO REPAIR REPORT", sep, "",
            f"Case ID:   {self.case_id}",
            f"Analyst:   {self.analyst}",
            f"Timestamp: {datetime.now(timezone.utc).isoformat()}", "",
            "SUMMARY:",
            f"  Total attempted:  {self._s['attempted']}",
            f"  Successful:       {self._s['repaired']}",
            f"  Failed:           {self._s['failed']}",
            f"  Skipped:          {self._s['skipped']}",
            f"  Success rate:     {rate}%", "",
            "BY CORRUPTION TYPE:",
        ]
        for ct, d in sorted(self._by_type.items()):
            r      = d["successful"] / max(d["attempted"], 1) * 100
            fn     = self._STRATEGY_MAP.get(ct, "repair_invalid_header")
            lo, hi = EXPECTED_SUCCESS.get(fn, (50, 80))
            lines.append(
                f"  {ct}: {d['successful']}/{d['attempted']} ({r:.1f}%)  "
                f"[expected {lo}–{hi}%]"
            )
        lines += ["", "REPAIR DETAILS:"]
        for e in self._results:
            v = e.get("validation", {})
            lines += [
                f"\n  {e['filename']}",
                f"    Corruption: {e['corruptionType']}",
                f"    Technique:  {e.get('repairTechnique', 'N/A')}",
                f"    Status:     {e.get('finalStatus', 'N/A')}",
                f"    Message:    {e.get('repairMessage', '')}",
            ]
            if v:
                dim = f"  {v.get('width')}×{v.get('height')} px" if v.get("width") else ""
                lines.append(
                    f"    Validation: {v.get('toolsPassed', 0)}/{v.get('toolsTotal', 0)} "
                    f"tools passed{dim}"
                )

        txt = json_path.with_suffix(".txt").with_stem(json_path.stem.replace(
            "_repair_report", "_REPAIR_REPORT"))
        txt.write_text("\n".join(lines), encoding="utf-8")
        return txt

    def save_report(self) -> Optional[str]:
        """Save JSON report and plain-text summary."""
        if self.args.json:
            ptprint(self.ptjsonlib.get_result_json(), "", self.args.json)
            return None

        json_path = (Path(self.args.json_out) if self.args.json_out
                     else self.output_dir / f"{self.case_id}_repair_report.json")

        report = {
            "result":        json.loads(self.ptjsonlib.get_result_json()),
            "repairResults": self._results,
        }

        if not self.dry_run:
            json_path.parent.mkdir(parents=True, exist_ok=True)
            json_path.write_text(
                json.dumps(report, indent=2, ensure_ascii=False, default=str),
                encoding="utf-8"
            )
            ptprint(f"JSON report: {json_path.name}", "OK", condition=not self.args.json)
            txt = self._write_text_report(json_path)
            ptprint(f"Text report: {txt.name}", "OK", condition=not self.args.json)

        return str(json_path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def get_help() -> List:
    return [
        {"description": [
            "Forensic photo repair – ptlibs compliant",
            "Techniques: missing_footer | invalid_header | corrupt_segments | truncated",
            "Post-repair validation: PIL + jpeginfo",
            "READ-ONLY on source files – repair works on working copies",
            "Compliant with ISO/IEC 10918-1, JFIF 1.02, NIST SP 800-86 §3.1.4",
        ]},
        {"usage": [
            "ptphotorepair <case-id> --corrupted-dir <dir> --validation-report <file> [options]"
        ]},
        {"usage_example": [
            "ptphotorepair PHOTORECOVERY-2025-01-26-001 "
            "--corrupted-dir /var/forensics/images/PHOTORECOVERY-2025-01-26-001_validation/corrupted "
            "--validation-report /var/forensics/images/PHOTORECOVERY-2025-01-26-001_validation_report.json",
            "ptphotorepair PHOTORECOVERY-2025-01-26-001 "
            "--corrupted-dir ./corrupted "
            "--validation-report ./validation_report.json "
            "--analyst 'John Doe' --json-out result.json",
            "ptphotorepair PHOTORECOVERY-2025-01-26-001 "
            "--corrupted-dir ./corrupted "
            "--validation-report ./validation_report.json --dry-run",
        ]},
        {"options": [
            ["case-id",                   "",      "Forensic case identifier – REQUIRED"],
            ["-c", "--corrupted-dir",     "<dir>", "Directory with corrupted source files – REQUIRED"],
            ["-r", "--validation-report", "<f>",   "Path to validation_report.json – REQUIRED"],
            ["-o", "--output-dir",        "<dir>", f"Output directory (default: {DEFAULT_OUTPUT_DIR})"],
            ["-a", "--analyst",           "<n>",   "Analyst name (default: Analyst)"],
            ["-j", "--json-out",          "<f>",   "Save JSON output to file (optional)"],
            ["--dry-run",                 "",      "Simulate repairs with synthetic data"],
            ["-h", "--help",              "",      "Show help"],
            ["--version",                 "",      "Show version"],
        ]},
        {"notes": [
            "missing_footer   → repair_missing_footer()    (85–95 %)",
            "invalid_header   → repair_invalid_header()    (90–95 %)",
            "corrupt_segments → repair_invalid_segments()  (80–85 %)",
            "truncated        → repair_truncated_file()    (50–70 %)",
            "unknown          → repair_invalid_header()    (fallback)",
            "PIL LOAD_TRUNCATED_IMAGES=True enables partial pixel recovery",
        ]},
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("case_id")
    parser.add_argument("-c", "--corrupted-dir",     required=True)
    parser.add_argument("-r", "--validation-report", required=True)
    parser.add_argument("-o", "--output-dir",        default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("-a", "--analyst",           default="Analyst")
    parser.add_argument("-j", "--json-out",          default=None)
    parser.add_argument("-q", "--quiet",             action="store_true")
    parser.add_argument("--dry-run",                 action="store_true")
    parser.add_argument("--version", action="version", version=f"{SCRIPTNAME} {__version__}")
    parser.add_argument("--socket-address",          default=None)
    parser.add_argument("--socket-port",             default=None)
    parser.add_argument("--process-ident",           default=None)

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
        args  = parse_args()
        tool  = PtPhotoRepair(args)
        tool.run()
        tool.save_report()
        props = json.loads(tool.ptjsonlib.get_result_json())["result"]["properties"]
        return 0 if props.get("successfulRepairs", 0) > 0 else 1
    except KeyboardInterrupt:
        ptprint("Interrupted by user.", "WARNING", condition=True)
        return 130
    except Exception as exc:
        ptprint(f"ERROR: {exc}", "ERROR", condition=True)
        return 99


if __name__ == "__main__":
    sys.exit(main())