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

from ptlibs import ptjsonlib, ptprinthelper
from ptlibs.ptprinthelper import ptprint

# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------

SCRIPTNAME         = "ptrepairdecision"
DEFAULT_OUTPUT_DIR = "/var/forensics/images"

# Conservative empirical success rates per corruption type (percent)
REPAIR_SUCCESS_RATES: Dict[str, float] = {
    "missing_footer":   90.0,
    "invalid_header":   85.0,
    "corrupt_segments": 60.0,
    "truncated":        85.0,
    "corrupt_data":     40.0,
    "fragmented":       15.0,
    "unknown":          30.0,
}

# R3: always repair when valid count is below this threshold
FEW_FILES_THRESHOLD = 50

# R4: repair when weighted estimate meets or exceeds this threshold
REPAIR_THRESHOLD = 50.0

# ---------------------------------------------------------------------------
# MAIN CLASS
# ---------------------------------------------------------------------------

class PtRepairDecision:
    """
    Forensic repair decision – ptlibs compliant.

    Pipeline: load validation_report.json → estimate repair success →
              apply 5 priority rules → save repair_decision.json.

    Rules (priority order):
      R1: no corrupted files           → skip_repair  (high)
      R2: no repairable files          → skip_repair  (high)
      R3: valid count < threshold      → perform_repair (medium)
      R4: estimated success ≥ 50%      → perform_repair (high)
      R5: otherwise                    → skip_repair  (high)

    READ-ONLY. No files are copied or modified.
    Compliant with ISO/IEC 27037:2012 §7.6, NIST SP 800-86 §3.2.
    """

    def __init__(self, args: argparse.Namespace) -> None:
        self.ptjsonlib  = ptjsonlib.PtJsonLib()
        self.args       = args
        self.case_id    = args.case_id.strip()
        self.dry_run    = args.dry_run
        self.output_dir = Path(args.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.validation_report = self.output_dir / f"{self.case_id}_validation_report.json"
        self.decision_file     = self.output_dir / f"{self.case_id}_repair_decision.json"

        self.ptjsonlib.add_properties({
            "caseId": self.case_id,
            "outputDirectory": str(self.output_dir),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "scriptVersion": __version__,
            "compliance": ["NIST SP 800-86", "ISO/IEC 27037:2012"],
            "strategy": None, "confidence": None,
            "reasoning": None, "estimatedSuccessRate": 0.0,
            "repairableFiles": 0, "expectedOutcome": {},
            "dryRun": self.dry_run,
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

    # --- phases -------------------------------------------------------------

    def load_report(self) -> Optional[Dict]:
        """Load validation_report.json and return its contents."""
        ptprint("\n[1/2] Loading Validation Report", "TITLE", condition=not self.args.json)

        if self.dry_run:
            mock = {
                "result": {"properties": {
                    "validFiles": 341, "corruptedFiles": 29, "unrecoverableFiles": 12,
                    "integrityScore": 89.3,
                }},
                "filesNeedingRepair": [
                    {"filename": f"FILE_{i:04d}.jpg",
                     "corruptionType": ct}
                    for i, ct in enumerate(
                        ["truncated"] * 10 + ["corrupt_segments"] * 12 +
                        ["corrupt_data"] * 4 + ["fragmented"] * 3, 1)
                ],
            }
            ptprint("DRY-RUN: using synthetic data", "WARNING", condition=not self.args.json)
            return mock

        if not self.validation_report.exists():
            self._fail("reportLoad",
                       f"{self.validation_report.name} not found – run Photo Integrity Validation first.")
            return None
        try:
            data = json.loads(self.validation_report.read_text(encoding="utf-8"))
        except Exception as exc:
            self._fail("reportLoad", f"Cannot read report: {exc}")
            return None

        self._add_node("reportLoad", True, sourceFile=str(self.validation_report))
        return data

    def decide(self, report: Dict) -> Dict[str, Any]:
        """Apply R1–R5 rules and return decision dict."""
        ptprint("\n[2/2] Applying Decision Rules", "TITLE", condition=not self.args.json)

        props        = report.get("result", {}).get("properties", report)
        valid        = props.get("validFiles", 0) or props.get("valid_files", 0)
        corrupted    = props.get("corruptedFiles", 0) or props.get("corrupted_files", 0)
        repairable   = report.get("filesNeedingRepair") or report.get("files_needing_repair") or []
        n_repairable = len(repairable)

        # --- R1: no corrupted files ---
        if corrupted == 0:
            return self._build("skip_repair", "high", "R1",
                               "No corrupted files detected – skipping repair phase.",
                               n_repairable, 0.0, valid)

        # --- R2: no repairable files ---
        if n_repairable == 0:
            return self._build("skip_repair", "high", "R2",
                               "No repairable files identified (all corrupted are unrecoverable).",
                               n_repairable, 0.0, valid)

        # Estimate weighted success rate
        total_weight = estimate_sum = 0.0
        for fi in repairable:
            ct   = fi.get("corruptionType") or fi.get("corruption_type") or "unknown"
            rate = REPAIR_SUCCESS_RATES.get(ct, REPAIR_SUCCESS_RATES["unknown"])
            estimate_sum  += rate
            total_weight  += 1
        estimate = round(estimate_sum / total_weight, 1) if total_weight else 0.0

        # --- R3: few valid files – always repair ---
        if valid < FEW_FILES_THRESHOLD:
            return self._build("perform_repair", "medium", "R3",
                               f"Only {valid} valid files recovered (<{FEW_FILES_THRESHOLD} threshold) – "
                               f"repair attempted regardless of estimated success ({estimate}%).",
                               n_repairable, estimate, valid)

        # --- R4: estimated success ≥ threshold ---
        if estimate >= REPAIR_THRESHOLD:
            return self._build("perform_repair", "high", "R4",
                               f"Estimated success rate {estimate}% ≥ {REPAIR_THRESHOLD}% threshold.",
                               n_repairable, estimate, valid)

        # --- R5: below threshold – skip ---
        return self._build("skip_repair", "high", "R5",
                           f"Estimated success rate {estimate}% < {REPAIR_THRESHOLD}% threshold – "
                           f"repair unlikely to be cost-effective.",
                           n_repairable, estimate, valid)

    def _build(self, strategy: str, confidence: str, rule: str,
               reasoning: str, n_repairable: int,
               estimate: float, valid: int) -> Dict[str, Any]:
        """Assemble the decision dict."""
        expected_additional = round(n_repairable * estimate / 100) if strategy == "perform_repair" else 0
        final_count         = valid + expected_additional
        improvement_pp      = round(expected_additional / max(valid, 1) * 100, 1)

        expected_outcome = {
            "expectedAdditionalFiles": expected_additional,
            "finalExpectedCount":      final_count,
            "improvementPp":           improvement_pp,
        }

        ptprint(f"Rule: {rule} | Strategy: {strategy} | Confidence: {confidence}",
                "OK", condition=not self.args.json)
        ptprint(f"Reasoning: {reasoning}", "INFO", condition=not self.args.json)
        if strategy == "perform_repair":
            ptprint(f"Expected: +{expected_additional} files → total {final_count}",
                    "INFO", condition=not self.args.json)

        return {
            "strategy": strategy, "confidence": confidence,
            "rule": rule, "reasoning": reasoning,
            "repairableFiles": n_repairable,
            "estimatedSuccessRate": estimate,
            "expectedOutcome": expected_outcome,
        }

    # --- run & save ---------------------------------------------------------

    def run(self) -> None:
        """Orchestrate the repair decision pipeline."""
        ptprint("=" * 70, "TITLE", condition=not self.args.json)
        ptprint(f"REPAIR DECISION v{__version__} | Case: {self.case_id}",
                "TITLE", condition=not self.args.json)
        if self.dry_run:
            ptprint("MODE: DRY-RUN", "WARNING", condition=not self.args.json)
        ptprint("=" * 70, "TITLE", condition=not self.args.json)

        report = self.load_report()
        if report is None:
            self.ptjsonlib.set_status("finished"); return

        d = self.decide(report)

        self.ptjsonlib.add_properties({
            "strategy":            d["strategy"],
            "confidence":          d["confidence"],
            "reasoning":           d["reasoning"],
            "estimatedSuccessRate": d["estimatedSuccessRate"],
            "repairableFiles":     d["repairableFiles"],
            "expectedOutcome":     d["expectedOutcome"],
        })
        self._add_node("repairDecision", True, **{k: v for k, v in d.items()
                                                  if k != "expectedOutcome"},
                       **d["expectedOutcome"])

        # Add Chain of Custody entry
        self.ptjsonlib.add_node(self.ptjsonlib.create_node_object(
            "chainOfCustodyEntry",
            properties={
                "action": f"Rozhodnutie o oprave: {d['strategy']} – pravidlo {d['rule']}, odhadovaná úspešnosť {d['estimatedSuccessRate']}%",
                "result": "SUCCESS",
                "analyst": self.args.analyst if hasattr(self.args, 'analyst') else "System",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ))

        ptprint("\n" + "=" * 70, "TITLE", condition=not self.args.json)
        ptprint("REPAIR DECISION COMPLETED", "OK", condition=not self.args.json)
        if d["strategy"] == "perform_repair":
            ptprint(f"→ PERFORM REPAIR  (confidence: {d['confidence']})",
                    "OK", condition=not self.args.json)
            ptprint("Next: Photo Repair", "INFO", condition=not self.args.json)
        else:
            ptprint(f"→ SKIP REPAIR  (confidence: {d['confidence']})",
                    "INFO", condition=not self.args.json)
            ptprint("Next: EXIF Analysis", "INFO", condition=not self.args.json)
        ptprint("=" * 70, "TITLE", condition=not self.args.json)
        self.ptjsonlib.set_status("finished")

    def save_report(self) -> Optional[str]:
        """Save {case_id}_repair_decision.json."""
        if self.args.json:
            ptprint(self.ptjsonlib.get_result_json(), "", self.args.json)
            return None

        props = json.loads(self.ptjsonlib.get_result_json())["result"]["properties"]
        decision = {
            "caseId":              self.case_id,
            "timestamp":           props.get("timestamp"),
            "strategy":            props.get("strategy"),
            "confidence":          props.get("confidence"),
            "reasoning":           props.get("reasoning"),
            "estimatedSuccessRate": props.get("estimatedSuccessRate"),
            "repairableFiles":     props.get("repairableFiles"),
            "expectedOutcome":     props.get("expectedOutcome"),
        }
        if not self.dry_run:
            self.decision_file.write_text(
                json.dumps(decision, indent=2, ensure_ascii=False),
                encoding="utf-8")
        ptprint(f"Decision saved: {self.decision_file.name}",
                "OK", condition=not self.args.json)
        return str(self.decision_file)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def get_help() -> List:
    return [
        {"description": [
            "Forensic repair decision – ptlibs compliant",
            "Applies 5 priority rules to decide whether photo repair is worthwhile",
            "READ-ONLY: no files are copied or modified",
            "Compliant with ISO/IEC 27037:2012 §7.6, NIST SP 800-86 §3.2",
        ]},
        {"usage": ["ptrepairdecision <case-id> [options]"]},
        {"usage_example": [
            "ptrepairdecision PHOTORECOVERY-2025-01-26-001",
            "ptrepairdecision PHOTORECOVERY-2025-01-26-001 --json",
            "ptrepairdecision PHOTORECOVERY-2025-01-26-001 --dry-run",
        ]},
        {"options": [
            ["case-id",            "",      "Forensic case identifier – REQUIRED"],
            ["-o", "--output-dir", "<dir>", f"Output directory (default: {DEFAULT_OUTPUT_DIR})"],
            ["-v", "--verbose",    "",      "Verbose logging"],
            ["--dry-run",          "",      "Simulate with synthetic validation data"],
            ["-j", "--json",       "",      "JSON output for Penterep platform"],
            ["-q", "--quiet",      "",      "Suppress progress output"],
            ["-h", "--help",       "",      "Show help"],
            ["--version",          "",      "Show version"],
        ]},
        {"notes": [
            "R1: no corrupted → skip | R2: none repairable → skip | R3: <50 valid → repair",
            "R4: estimate ≥50% → repair | R5: estimate <50% → skip",
            "Success rates: missing_footer 90% | invalid_header 85% | truncated 85%",
            "               corrupt_segments 60% | corrupt_data 40% | fragmented 15%",
            "Requires Photo Integrity Validation results ({case_id}_validation_report.json)",
            "Compliant with ISO/IEC 27037:2012 §7.6, NIST SP 800-86 §3.2",
        ]},
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("case_id")
    parser.add_argument("-o", "--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("-v", "--verbose",    action="store_true")
    parser.add_argument("-q", "--quiet",      action="store_true")
    parser.add_argument("--dry-run",          action="store_true")
    parser.add_argument("-j", "--json",       action="store_true")
    parser.add_argument("--version", action="version", version=f"{SCRIPTNAME} {__version__}")
    parser.add_argument("--socket-address",   default=None)
    parser.add_argument("--socket-port",      default=None)
    parser.add_argument("--process-ident",    default=None)

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