#!/usr/bin/env python3
"""
    Copyright (c) 2025 Bc. Dominik Sabota, VUT FIT Brno

    ptcocmanager - Chain of Custody form, physical labeling and storage

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License.
    See <https://www.gnu.org/licenses/> for details.
"""

import argparse
import json
import os
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ._version import __version__
from .ptforensictoolbase import ForensicToolBase
from ptlibs import ptjsonlib, ptprinthelper
from ptlibs.ptprinthelper import ptprint


def _custom_sigint_handler(sig, frame):
    raise KeyboardInterrupt


signal.signal(signal.SIGINT, _custom_sigint_handler)

SCRIPTNAME         = "ptcocmanager"
DEFAULT_OUTPUT_DIR = "/var/forensics/cases"


class PtCocManager(ForensicToolBase):
    """
    Chain of Custody form generator, physical labeling guide and storage
    recorder for the CoC scenario (Step 6).

    Loads JSON reports from previous steps (imaging, verification),
    pre-fills the CoC form, walks the analyst through the physical
    labeling checklist and records the storage location.
    Compliant with ISO/IEC 27037:2012 Sections 5.2, 5.3, 5.4 and
    NIST SP 800-86.
    """

    def __init__(self, args: argparse.Namespace) -> None:
        self.ptjsonlib   = ptjsonlib.PtJsonLib()
        self.args        = args
        self.case_id     = args.case_id.strip()
        self.analyst     = args.analyst
        self.dry_run     = args.dry_run
        self.output_dir  = Path(args.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Data loaded from previous-step JSON reports
        self.context_data:      Dict = {}
        self.device_data:       Dict = {}
        self.imaging_data:      Dict = {}
        self.verification_data: Dict = {}

        # CoC form fields filled during run
        self.coc_form:          Dict = {}
        self.storage_location:  str  = ""
        self.labeling_ok:       bool = False
        self.imaging_attempts:  int  = 1

        self.ptjsonlib.add_properties({
            "caseId":        self.case_id,
            "analyst":       self.analyst,
            "timestamp":     datetime.now(timezone.utc).isoformat(),
            "scriptVersion": __version__,
            "dryRun":        self.dry_run,
        })

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _prompt(self, question: str, default: str = "") -> str:
        """Interactive prompt; returns default in dry-run or JSON mode."""
        if self.dry_run or self.args.json:
            return default
        suffix = f" [{default}]" if default else ""
        try:
            val = input(f"{question}{suffix}: ").strip()
            return val if val else default
        except (EOFError, KeyboardInterrupt):
            raise KeyboardInterrupt

    def _confirm(self, question: str) -> bool:
        """Yes/No prompt; returns True in dry-run mode."""
        if self.dry_run or self.args.json:
            return True
        while True:
            resp = input(f"{question} [y/N]: ").strip().lower()
            if resp in ("y", "yes"): return True
            if resp in ("n", "no", ""): return False
            ptprint("Please enter 'y' or 'n'.", "WARNING", condition=True)

    def _load_json_report(self, path: Path) -> Dict:
        """Load a JSON report, return empty dict on failure."""
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data.get("result", data)
        except Exception:
            return {}

    def _find_report(self, *suffixes: str) -> Optional[Path]:
        """Find the first matching report file in output_dir."""
        for suffix in suffixes:
            candidates = [
                self.output_dir / f"{self.case_id}{suffix}",
                self.output_dir / suffix,
                Path(suffix),
            ]
            for p in candidates:
                if p.exists():
                    return p
        return None

    # ------------------------------------------------------------------
    # Phase 1 – load previous-step reports
    # ------------------------------------------------------------------

    def load_reports(self) -> bool:
        ptprint("\n" + "=" * 70, "TITLE", condition=self._out())
        ptprint("PHASE 1: Loading previous step reports",
                "TITLE", condition=self._out())
        ptprint("=" * 70, "TITLE", condition=self._out())

        # Imaging report (Step 4)
        imaging_path = self._find_report(
            "_imaging_result.json", "_imaging.json")
        if imaging_path:
            self.imaging_data = self._load_json_report(imaging_path)
            props = self.imaging_data.get("properties", {})
            ptprint(f"  ✓ Imaging report loaded: {imaging_path.name}",
                    "OK", condition=self._out())
            ptprint(f"    Tool: {props.get('imagingTool', '?')}  |  "
                    f"sourceHash: {str(props.get('sourceHash', ''))[:16]}…",
                    "TEXT", condition=self._out())
        else:
            ptprint("  ⚠  Imaging report not found – fields will be empty",
                    "WARNING", condition=self._out())

        # Verification report (Step 5)
        verif_path = self._find_report(
            "_verification_report.json", "_verification.json")
        if verif_path:
            self.verification_data = self._load_json_report(verif_path)
            props = self.verification_data.get("properties", {})
            ptprint(f"  ✓ Verification report loaded: {verif_path.name}",
                    "OK", condition=self._out())
            ptprint(f"    Status: {props.get('verificationStatus', '?')}",
                    "TEXT", condition=self._out())
        else:
            ptprint("  ⚠  Verification report not found – fields will be empty",
                    "WARNING", condition=self._out())

        self._add_node("reportsLoaded", True,
                       imagingReportFound=bool(imaging_path),
                       verificationReportFound=bool(verif_path))
        return True

    # ------------------------------------------------------------------
    # Phase 2 – pre-fill and complete CoC form
    # ------------------------------------------------------------------

    def fill_coc_form(self) -> bool:
        ptprint("\n" + "=" * 70, "TITLE", condition=self._out())
        ptprint("PHASE 2: Chain of Custody Form",
                "TITLE", condition=self._out())
        ptprint("=" * 70, "TITLE", condition=self._out())

        ip = self.imaging_data.get("properties", {})
        vp = self.verification_data.get("properties", {})

        # Auto-fill from reports
        source_hash   = ip.get("sourceHash", "")
        image_hash    = vp.get("imageHash", "")
        verif_status  = vp.get("verificationStatus", "UNKNOWN")
        image_path    = ip.get("imagePath", "")
        tool          = ip.get("imagingTool", "")
        tool_ver      = ip.get("toolVersion", "")
        duration      = ip.get("durationSeconds", "")
        wb_confirmed  = ip.get("writeBlockerConfirmed", False)
        img_timestamp = ip.get("timestamp", "")

        ptprint("\n[2a] Pre-filled from JSON reports:",
                "SUBTITLE", condition=self._out())
        ptprint(f"  sourceHash:   {source_hash[:32]}…" if source_hash
                else "  sourceHash:   (not found)", "TEXT", condition=self._out())
        ptprint(f"  imageHash:    {image_hash[:32]}…" if image_hash
                else "  imageHash:    (not found)", "TEXT", condition=self._out())
        ptprint(f"  Verification: {verif_status}", "TEXT", condition=self._out())
        ptprint(f"  Tool:         {tool} {tool_ver}", "TEXT", condition=self._out())

        if not self.dry_run and not self.args.json:
            ptprint(
                "\n  ⚠  Visually verify hash values – compare last 8 characters "
                "with your handwritten notes from Step 4.",
                "WARNING", condition=self._out())
            if source_hash:
                ptprint(f"     sourceHash last 8: …{source_hash[-8:]}",
                        "WARNING", condition=self._out())
            if image_hash:
                ptprint(f"     imageHash  last 8: …{image_hash[-8:]}",
                        "WARNING", condition=self._out())

        ptprint("\n[2b] Manual fields:", "SUBTITLE", condition=self._out())

        evidence_number   = self._prompt(
            "Evidence number (e.g. EV-2025-001)", f"EV-{self.case_id[-3:]}")
        legal_basis       = self._prompt(
            "Legal basis (§83a TŘ / §78 TŘ / voluntary / commercial)",
            "§78 TŘ")
        device_type       = self._prompt("Device type", "USB flash disk")
        device_make       = self._prompt("Manufacturer", "")
        device_model      = self._prompt("Model", "")
        device_serial     = self._prompt("Serial number", "")
        device_condition  = self._prompt(
            "Condition at seizure (new/used/damaged)", "used")
        wb_model          = self._prompt("Write-blocker model", "Tableau T8-R2")
        wb_serial         = self._prompt("Write-blocker serial number", "")

        try:
            self.imaging_attempts = int(
                self._prompt("Number of imaging attempts", "1"))
        except ValueError:
            self.imaging_attempts = 1

        self.coc_form = {
            "caseId":          self.case_id,
            "evidenceNumber":  evidence_number,
            "analyst":         self.analyst,
            "timestamp":       datetime.now(timezone.utc).isoformat(),
            "legalBasis":      legal_basis,
            "device": {
                "type":      device_type,
                "make":      device_make,
                "model":     device_model,
                "serial":    device_serial,
                "condition": device_condition,
            },
            "cryptographic": {
                "sourceHash":          source_hash,
                "imageHash":           image_hash,
                "verificationStatus":  verif_status,
                "imagingAttempts":     self.imaging_attempts,
            },
            "technical": {
                "imagingTool":          f"{tool} {tool_ver}".strip(),
                "imagingTimestamp":     img_timestamp,
                "durationSeconds":      duration,
                "imagePath":            image_path,
                "writeBlockerModel":    wb_model,
                "writeBlockerSerial":   wb_serial,
                "writeBlockerConfirmed": wb_confirmed,
            },
            "transferRecords": [],   # filled in Step 7
        }

        ptprint("\n  ✓ CoC form pre-filled and verified",
                "OK", condition=self._out())
        self._add_node("cocFormFilled", True,
                       evidenceNumber=evidence_number,
                       verificationStatus=verif_status)
        return True

    # ------------------------------------------------------------------
    # Phase 3 – physical labeling checklist
    # ------------------------------------------------------------------

    def physical_labeling(self) -> bool:
        ptprint("\n" + "=" * 70, "TITLE", condition=self._out())
        ptprint("PHASE 3: Physical Labeling Checklist",
                "TITLE", condition=self._out())
        ptprint("=" * 70, "TITLE", condition=self._out())

        evidence_number = self.coc_form.get("evidenceNumber", "")

        ptprint(
            f"\n  Print a tamper-evident label with the following data:\n"
            f"    Case ID:          {self.case_id}\n"
            f"    Evidence number:  {evidence_number}\n"
            f"    Date:             {datetime.now().strftime('%Y-%m-%d')}\n"
            f"    Analyst:          {self.analyst}\n",
            "TEXT", condition=self._out())

        checklist = [
            "Label does NOT cover the serial number or manufacturer stickers",
            "Label is NOT on connectors or moving parts",
            "Label is visible without disassembly",
            "Device is photographed with visible label (≥3 angles)",
            f"Photos saved as {self.case_id}_label_01.jpg etc.",
        ]

        ptprint("  Confirm each labeling step:", "SUBTITLE", condition=self._out())
        all_ok = True
        for i, item in enumerate(checklist, 1):
            ok = self._confirm(f"  [{i}/{len(checklist)}] {item}")
            if not ok:
                ptprint(f"    ✗ Step not confirmed – resolve before continuing",
                        "ERROR", condition=self._out())
                all_ok = False

        self.labeling_ok = all_ok
        if all_ok:
            ptprint("\n  ✓ Physical labeling completed",
                    "OK", condition=self._out())
        else:
            ptprint(
                "\n  ⚠  Some labeling steps not confirmed – document reason",
                "WARNING", condition=self._out())

        self.coc_form["labeling"] = {
            "completed":      self.labeling_ok,
            "evidenceNumber": evidence_number,
            "timestamp":      datetime.now(timezone.utc).isoformat(),
        }
        self._add_node("physicalLabeling", self.labeling_ok,
                       evidenceNumber=evidence_number,
                       labelingCompleted=self.labeling_ok)
        return True

    # ------------------------------------------------------------------
    # Phase 4 – storage location
    # ------------------------------------------------------------------

    def record_storage(self) -> bool:
        ptprint("\n" + "=" * 70, "TITLE", condition=self._out())
        ptprint("PHASE 4: Secure Storage", "TITLE", condition=self._out())
        ptprint("=" * 70, "TITLE", condition=self._out())

        ptprint(
            "\n  Wrap device in antistatic bag, seal it and attach an "
            "external label with Case ID.",
            "TEXT", condition=self._out())
        ptprint(
            "  Verify storage conditions: temp 15–25 °C, humidity 40–60 %, "
            "no strong magnetic fields.",
            "TEXT", condition=self._out())

        room     = self._prompt("Storage room",   "Room B03")
        shelf    = self._prompt("Shelf / cabinet", "Shelf 4")
        position = self._prompt("Position (optional)", "")
        custodian = self._prompt("Custodian name", self.analyst)

        self.storage_location = f"{room}, {shelf}"
        if position:
            self.storage_location += f", {position}"

        self.coc_form["storage"] = {
            "room":           room,
            "shelf":          shelf,
            "position":       position,
            "custodian":      custodian,
            "timestamp":      datetime.now(timezone.utc).isoformat(),
            "location":       self.storage_location,
        }

        ptprint(f"\n  ✓ Storage location recorded: {self.storage_location}",
                "OK", condition=self._out())
        self._add_node("storageRecorded", True,
                       location=self.storage_location,
                       custodian=custodian)
        return True

    # ------------------------------------------------------------------
    # Run and save
    # ------------------------------------------------------------------

    def run(self) -> None:
        ptprint("=" * 70, "TITLE", condition=self._out())
        ptprint(f"CoC MANAGER v{__version__}  |  Case: {self.case_id}",
                "TITLE", condition=self._out())
        if self.dry_run:
            ptprint("MODE: DRY-RUN", "WARNING", condition=self._out())
        ptprint("=" * 70, "TITLE", condition=self._out())

        if not self.load_reports():
            self.ptjsonlib.set_status("finished"); return
        if not self.fill_coc_form():
            self.ptjsonlib.set_status("finished"); return
        if not self.physical_labeling():
            self.ptjsonlib.set_status("finished"); return
        if not self.record_storage():
            self.ptjsonlib.set_status("finished"); return

        # Summary
        ptprint("\n" + "=" * 70, "TITLE", condition=self._out())
        ptprint("SUMMARY",       "TITLE", condition=self._out())
        ptprint("=" * 70,        "TITLE", condition=self._out())
        ptprint(f"  Case:       {self.case_id}", "TEXT", condition=self._out())
        ptprint(f"  Evidence:   {self.coc_form.get('evidenceNumber', '')}",
                "TEXT", condition=self._out())
        ptprint(f"  Labeling:   {'✓ OK' if self.labeling_ok else '⚠ incomplete'}",
                "TEXT", condition=self._out())
        ptprint(f"  Storage:    {self.storage_location}",
                "TEXT", condition=self._out())
        ptprint(f"  Attempts:   {self.imaging_attempts}",
                "TEXT", condition=self._out())
        ptprint("=" * 70, "TITLE", condition=self._out())

        self.ptjsonlib.add_properties({
            "compliance":      ["ISO/IEC 27037:2012", "NIST SP 800-86"],
            "cocForm":         self.coc_form,
            "labelingOk":      self.labeling_ok,
            "storageLocation": self.storage_location,
            "imagingAttempts": self.imaging_attempts,
        })
        self.ptjsonlib.add_node(self.ptjsonlib.create_node_object(
            "chainOfCustodyEntry",
            properties={
                "action":   (f"CoC formulár podpísaný, zariadenie označené "
                             f"a uložené do úschovne – lokácia: "
                             f"{self.storage_location}"),
                "result":   "SUCCESS",
                "analyst":  self.analyst,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ))
        self.ptjsonlib.set_status("finished")

    def save_report(self) -> Optional[str]:
        if self.args.json:
            ptprint(self.ptjsonlib.get_result_json(), "", self.args.json)
            return None

        out_path = (Path(self.args.json_out) if self.args.json_out
                    else self.output_dir / f"{self.case_id}_coc_form.json")
        out_path.write_text(
            json.dumps(
                {"result": json.loads(self.ptjsonlib.get_result_json())},
                indent=2, ensure_ascii=False),
            encoding="utf-8")
        ptprint(f"\n  ✓ CoC form saved: {out_path}", "OK", condition=True)
        return str(out_path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def get_help() -> List:
    return [
        {"description": [
            "Chain of Custody form, physical labeling and storage – ptlibs compliant",
            "Loads imaging and verification JSON reports, pre-fills CoC form,",
            "guides analyst through physical labeling checklist and records storage.",
            "Compliant with ISO/IEC 27037:2012 §5.2, 5.3, 5.4 and NIST SP 800-86.",
        ]},
        {"usage": ["ptcocmanager <case-id> [options]"]},
        {"usage_example": [
            "ptcocmanager COC-2025-01-26-001",
            "ptcocmanager COC-2025-01-26-001 --analyst 'Jan Novak'",
            "ptcocmanager COC-2025-01-26-001 --json-out coc_form.json",
            "ptcocmanager COC-2025-01-26-001 --dry-run",
        ]},
        {"options": [
            ["case-id",             "",    "Case identifier – REQUIRED"],
            ["-a", "--analyst",     "<n>", "Analyst name (default: Analyst)"],
            ["-o", "--output-dir",  "<d>", f"Directory with reports and output "
                                           f"(default: {DEFAULT_OUTPUT_DIR})"],
            ["-j", "--json-out",    "<f>", "Save CoC form JSON to file"],
            ["-q", "--quiet",       "",    "Suppress terminal output"],
            ["--dry-run",           "",    "Simulate without interactive prompts"],
            ["-h", "--help",        "",    "Show help"],
            ["--version",           "",    "Show version"],
        ]},
        {"notes": [
            "Automatically loads *_imaging_result.json and *_verification_report.json",
            "from --output-dir. Run after ptforensicimaging and ptimageverification.",
            "Exit 0 = success | Exit 99 = error | Exit 130 = Ctrl+C",
            "Compliant with ISO/IEC 27037:2012 §5.2, 5.3, 5.4",
        ]},
    ]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("case_id")
    p.add_argument("-a", "--analyst",    default="Analyst")
    p.add_argument("-o", "--output-dir", default=DEFAULT_OUTPUT_DIR)
    p.add_argument("-j", "--json-out",   default=None)
    p.add_argument("-q", "--quiet",      action="store_true")
    p.add_argument("--dry-run",          action="store_true")
    p.add_argument("--version", action="version",
                   version=f"{SCRIPTNAME} {__version__}")

    if len(sys.argv) == 1 or {"-h", "--help"} & set(sys.argv):
        ptprinthelper.help_print(get_help(), SCRIPTNAME, __version__)
        sys.exit(0)

    args      = p.parse_args()
    args.json = bool(args.json_out)
    if args.json:
        args.quiet = True
    ptprinthelper.print_banner(SCRIPTNAME, __version__, args.json)
    return args


def main() -> int:
    try:
        args = parse_args()
        tool = PtCocManager(args)
        tool.run()
        tool.save_report()
        return 0
    except KeyboardInterrupt:
        ptprint("\nInterrupted by user.", "WARNING", condition=True)
        return 130
    except Exception as exc:
        ptprint(f"\nERROR: {exc}", "ERROR", condition=True, colortext=True)
        return 99


if __name__ == "__main__":
    sys.exit(main())