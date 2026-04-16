#!/usr/bin/env python3
"""
    Copyright (c) 2025 Bc. Dominik Sabota, VUT FIT Brno

    ptrepairdecision - Forensic repair decision tool

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License.
    See <https://www.gnu.org/licenses/> for details.
"""

import argparse
import json
import sys
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

SCRIPTNAME         = "ptrepairdecision"
DEFAULT_OUTPUT_DIR = "/var/forensics/images"

# Conservative empirical success rates per corruption type (percent).
# Derived from a review of JPEG/PNG repair tool documentation and
# the forensic literature (Garfinkel 2012, Kessler 2016).
REPAIR_SUCCESS_RATES: Dict[str, float] = {
    "missing_footer":   90.0,  # append EOI – almost always recoverable
    "invalid_header":   85.0,  # SOI reconstruction – reliable when SOS is intact
    "corrupt_segments": 60.0,  # segment stripping – depends on how much is lost
    "truncated":        85.0,  # PIL LOAD_TRUNCATED_IMAGES – good for partial data
    "corrupt_data":     40.0,  # data region damage – highly variable
    "fragmented":       15.0,  # multiple fragments – rarely useful without map
    "unknown":          30.0,  # conservative floor for unclassified cases
}

# R3: when valid files are below this count, repair is always attempted
# regardless of estimated success – recovering even a few extra photos
# is worth the overhead at such low file counts.
FEW_FILES_THRESHOLD = 50

# R4: minimum weighted estimated success rate (percent) required to
# justify running the repair phase.
REPAIR_THRESHOLD = 50.0


class PtRepairDecision(ForensicToolBase):
    """
    Applies five priority rules to the integrity validation report and
    decides whether running photo repair is worthwhile. Read-only;
    no files are copied or modified.
    """

    def __init__(self, args: argparse.Namespace) -> None:
        self.ptjsonlib  = ptjsonlib.PtJsonLib()
        self.args       = args
        self.case_id    = args.case_id.strip()
        self.analyst    = args.analyst
        self.dry_run    = args.dry_run
        self.output_dir = Path(args.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.validation_report = (
            Path(args.validation_report) if getattr(args, "validation_report", None)
            else self.output_dir / f"{self.case_id}_validation_report.json")
        self.decision_file = \
            self.output_dir / f"{self.case_id}_repair_decision.json"

        self.ptjsonlib.add_properties({
            "caseId":        self.case_id,
            "outputDirectory": str(self.output_dir),
            "timestamp":     datetime.now(timezone.utc).isoformat(),
            "scriptVersion": __version__,
            "dryRun":        self.dry_run,
        })

    # ------------------------------------------------------------------
    # Phases
    # ------------------------------------------------------------------

    def load_report(self) -> Optional[Dict]:
        ptprint("\n[1/2] Loading validation report", "TITLE", condition=self._out())

        if self.dry_run:
            mock = {
                "result": {"properties": {
                    "validFiles": 341, "corruptedFiles": 29,
                }},
                "filesNeedingRepair": [
                    {"filename": f"FILE_{i:04d}.jpg", "corruptionType": ct}
                    for i, ct in enumerate(
                        ["truncated"] * 10 + ["corrupt_segments"] * 12 +
                        ["corrupt_data"] * 4 + ["fragmented"] * 3, 1)
                ],
            }
            ptprint("  [DRY-RUN] Using synthetic validation data.",
                    "WARNING", condition=self._out())
            return mock

        if not self.validation_report.exists():
            self._fail("reportLoad",
                       f"{self.validation_report.name} not found – "
                       "run Photo Integrity Validation first.")
            return None
        try:
            data = json.loads(self.validation_report.read_text(encoding="utf-8"))
        except Exception as exc:
            self._fail("reportLoad", f"Cannot read report: {exc}")
            return None

        self._add_node("reportLoad", True,
                       sourceFile=str(self.validation_report))
        return data

    def decide(self, report: Dict) -> Dict[str, Any]:
        ptprint("\n[2/2] Applying decision rules", "TITLE", condition=self._out())

        props       = report.get("result", {}).get("properties", report)
        valid       = (props.get("validFiles")       or props.get("valid_files",    0))
        corrupted   = (props.get("corruptedFiles")   or props.get("corrupted_files", 0))
        repairable  = (report.get("filesNeedingRepair")
                       or report.get("files_needing_repair") or [])
        n_rep       = len(repairable)

        # R1: nothing to repair
        if corrupted == 0:
            return self._build(
                "skip_repair", "high", "R1",
                "No corrupted files detected – skipping repair phase.",
                n_rep, 0.0, valid)

        # R2: nothing repairable
        if n_rep == 0:
            return self._build(
                "skip_repair", "high", "R2",
                "No repairable files in validation report "
                "(all corrupted files are unrecoverable).",
                n_rep, 0.0, valid)

        # Weighted estimated success rate across all repairable files
        estimate = round(
            sum(REPAIR_SUCCESS_RATES.get(
                    fi.get("corruptionType") or fi.get("corruption_type", "unknown"),
                    REPAIR_SUCCESS_RATES["unknown"])
                for fi in repairable) / n_rep, 1)

        # R3: very few valid files – repair regardless of estimate
        if valid < FEW_FILES_THRESHOLD:
            return self._build(
                "perform_repair", "medium", "R3",
                f"Only {valid} valid files recovered "
                f"(below threshold of {FEW_FILES_THRESHOLD}) – "
                f"repair attempted regardless of estimated success ({estimate}%).",
                n_rep, estimate, valid)

        # R4: estimate meets threshold
        if estimate >= REPAIR_THRESHOLD:
            return self._build(
                "perform_repair", "high", "R4",
                f"Estimated success rate {estimate}% "
                f"meets the {REPAIR_THRESHOLD}% threshold.",
                n_rep, estimate, valid)

        # R5: below threshold – not cost-effective
        return self._build(
            "skip_repair", "high", "R5",
            f"Estimated success rate {estimate}% is below the "
            f"{REPAIR_THRESHOLD}% threshold – repair not cost-effective.",
            n_rep, estimate, valid)

    def _build(self, strategy: str, confidence: str, rule: str,
               reasoning: str, n_repairable: int,
               estimate: float, valid: int) -> Dict[str, Any]:
        expected_add = (round(n_repairable * estimate / 100)
                        if strategy == "perform_repair" else 0)
        final_count  = valid + expected_add
        improvement  = round(expected_add / max(valid, 1) * 100, 1)

        expected_outcome = {
            "expectedAdditionalFiles": expected_add,
            "finalExpectedCount":      final_count,
            "improvementPct":          improvement,
        }

        ptprint(f"  Rule: {rule}  |  Strategy: {strategy}  |  "
                f"Confidence: {confidence}",
                "OK", condition=self._out())
        ptprint(f"  {reasoning}", "INFO", condition=self._out())
        if strategy == "perform_repair":
            ptprint(f"  Expected: +{expected_add} files → total {final_count}",
                    "INFO", condition=self._out())

        return {"strategy": strategy, "confidence": confidence,
                "rule": rule, "reasoning": reasoning,
                "repairableFiles": n_repairable,
                "estimatedSuccessRate": estimate,
                "expectedOutcome": expected_outcome}

    # ------------------------------------------------------------------
    # Run and save
    # ------------------------------------------------------------------

    def run(self) -> None:
        ptprint("=" * 70, "TITLE", condition=self._out())
        ptprint(f"REPAIR DECISION v{__version__}  |  Case: {self.case_id}",
                "TITLE", condition=self._out())
        if self.dry_run:
            ptprint("MODE: DRY-RUN", "WARNING", condition=self._out())
        ptprint("=" * 70, "TITLE", condition=self._out())

        report = self.load_report()
        if report is None:
            self.ptjsonlib.set_status("finished"); return

        d = self.decide(report)

        self.ptjsonlib.add_properties({
            "compliance":           ["NIST SP 800-86", "ISO/IEC 27037:2012"],
            "strategy":             d["strategy"],
            "confidence":           d["confidence"],
            "reasoning":            d["reasoning"],
            "estimatedSuccessRate": d["estimatedSuccessRate"],
            "repairableFiles":      d["repairableFiles"],
            "expectedOutcome":      d["expectedOutcome"],
        })
        self._add_node("repairDecision", True,
                       **{k: v for k, v in d.items() if k != "expectedOutcome"},
                       **d["expectedOutcome"])
        self.ptjsonlib.add_node(self.ptjsonlib.create_node_object(
            "chainOfCustodyEntry",
            properties={
                "action":    (f"Repair decision: {d['strategy']} – "
                              f"rule {d['rule']}, "
                              f"estimated success {d['estimatedSuccessRate']}%"),
                "result":    "SUCCESS",
                "analyst":   self.analyst,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ))

        ptprint("\n" + "=" * 70, "TITLE", condition=self._out())
        ptprint("REPAIR DECISION COMPLETE", "OK", condition=self._out())
        if d["strategy"] == "perform_repair":
            ptprint(f"  → PERFORM REPAIR  (confidence: {d['confidence']})",
                    "OK", condition=self._out())
            ptprint("  Next: Photo Repair", "INFO", condition=self._out())
        else:
            ptprint(f"  → SKIP REPAIR  (confidence: {d['confidence']})",
                    "INFO", condition=self._out())
            ptprint("  Next: EXIF Analysis", "INFO", condition=self._out())
        ptprint("=" * 70, "TITLE", condition=self._out())
        self.ptjsonlib.set_status("finished")

    def save_report(self) -> Optional[str]:
        if self.args.json:
            ptprint(self.ptjsonlib.get_result_json(), "", self.args.json)
            return None

        props    = json.loads(self.ptjsonlib.get_result_json())["result"]["properties"]
        decision = {
            "caseId":               self.case_id,
            "timestamp":            props.get("timestamp"),
            "strategy":             props.get("strategy"),
            "confidence":           props.get("confidence"),
            "reasoning":            props.get("reasoning"),
            "estimatedSuccessRate": props.get("estimatedSuccessRate"),
            "repairableFiles":      props.get("repairableFiles"),
            "expectedOutcome":      props.get("expectedOutcome"),
        }
        if not self.dry_run:
            self.decision_file.write_text(
                json.dumps(decision, indent=2, ensure_ascii=False),
                encoding="utf-8")
        ptprint(f"Decision saved: {self.decision_file.name}",
                "OK", condition=self._out())
        return str(self.decision_file)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def get_help() -> List[Dict]:
    return [
        {"description": [
            "Forensic repair decision – ptlibs compliant",
            "Applies five priority rules to decide whether photo repair is worthwhile",
            "Read-only: no files are copied or modified",
            "Compliant with ISO/IEC 27037:2012 §7.6 and NIST SP 800-86 §3.2",
        ]},
        {"usage": ["ptrepairdecision <case-id> [options]"]},
        {"usage_example": [
            "ptrepairdecision PHOTORECOVERY-2025-01-26-001",
            "ptrepairdecision PHOTORECOVERY-2025-01-26-001 --dry-run",
        ]},
        {"options": [
            ["case-id",            "",      "Forensic case identifier – REQUIRED"],
            ["-r", "--validation-report", "<f>", "Path to validation_report.json (optional; auto-discovered)"],
            ["-a", "--analyst",    "<n>",   "Analyst name (default: Analyst)"],
            ["-o", "--output-dir", "<dir>", f"Output directory (default: {DEFAULT_OUTPUT_DIR})"],
            ["--dry-run",          "",      "Simulate with synthetic validation data"],
            ["-j", "--json",       "",      "JSON output for platform integration"],
            ["-q", "--quiet",      "",      "Suppress terminal output"],
            ["-h", "--help",       "",      "Show help"],
            ["--version",          "",      "Show version"],
        ]},
        {"notes": [
            "R1: no corrupted files → skip",
            "R2: no repairable files → skip",
            f"R3: valid < {FEW_FILES_THRESHOLD} → repair (regardless of estimate)",
            f"R4: estimate ≥ {REPAIR_THRESHOLD}% → repair",
            "R5: estimate below threshold → skip",
            "Success rates: missing_footer 90% | invalid_header 85% | "
            "truncated 85% | corrupt_segments 60% | corrupt_data 40%",
            "Compliant with ISO/IEC 27037:2012 §7.6 and NIST SP 800-86 §3.2",
        ]},
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("case_id")
    parser.add_argument("-r", "--validation-report", default=None,
                        help="Path to validation_report.json (optional; auto-discovered if omitted)")
    parser.add_argument("-a", "--analyst",    default="Analyst")
    parser.add_argument("-o", "--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("-q", "--quiet",      action="store_true")
    parser.add_argument("--dry-run",          action="store_true")
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
        tool = PtRepairDecision(args)
        tool.run()
        tool.save_report()
        props = json.loads(tool.ptjsonlib.get_result_json())["result"]["properties"]
        return 0 if props.get("strategy") is not None else 1
    except KeyboardInterrupt:
        ptprint("Interrupted by user.", "WARNING", condition=True)
        return 130
    except Exception as exc:
        ptprint(f"ERROR: {exc}", "ERROR", condition=True)
        return 99


if __name__ == "__main__":
    sys.exit(main())