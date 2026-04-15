#!/usr/bin/env python3
"""
    Copyright (c) 2025 Bc. Dominik Sabota, VUT FIT Brno

    ptimageverification - Forensic image hash verification tool

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License.
    See <https://www.gnu.org/licenses/> for details.
"""

import argparse
import hashlib
import json
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from ._version import __version__
from .ptforensictoolbase import ForensicToolBase
from ptlibs import ptjsonlib, ptprinthelper
from ptlibs.ptprinthelper import ptprint


def _custom_sigint_handler(sig, frame):
    raise KeyboardInterrupt


signal.signal(signal.SIGINT, _custom_sigint_handler)

SCRIPTNAME         = "ptimageverification"
DEFAULT_OUTPUT_DIR = "/var/forensics/images"
HASH_BLOCK_SIZE    = 4 * 1024 * 1024   # 4 MB


class PtImageVerification(ForensicToolBase):
    """
    Computes the SHA-256 of a forensic image and compares it against a
    known source hash to verify bit-for-bit integrity after acquisition.
    Read-only on the image file.
    """

    def __init__(self, args: argparse.Namespace) -> None:
        self.ptjsonlib   = ptjsonlib.PtJsonLib()
        self.args        = args
        self.case_id     = args.case_id.strip()
        self.analyst     = args.analyst
        self.dry_run     = args.dry_run
        self.image_path  = Path(args.image)
        self.source_hash = args.source_hash.lower().strip()
        self.output_dir  = Path(args.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.image_format: Optional[str]   = None
        self.image_size:   Optional[int]   = None
        self.image_hash:   Optional[str]   = None
        self.calc_time:    Optional[float] = None
        self.hash_match:   Optional[bool]  = None

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

    def validate_source_hash(self) -> bool:
        ptprint("\n[1/3] Validating source hash", "TITLE", condition=self._out())

        if not self.source_hash:
            return self._fail("hashValidation", "Source hash is required.")
        if len(self.source_hash) != 64:
            return self._fail("hashValidation",
                              f"Invalid hash length: {len(self.source_hash)} (expected 64)")
        if not all(c in "0123456789abcdef" for c in self.source_hash):
            return self._fail("hashValidation",
                              "Invalid hash: must be 64 lowercase hexadecimal characters")

        ptprint(f"  ✓ Hash valid: {self.source_hash[:16]}…",
                "OK", condition=self._out())
        self._add_node("hashValidation", True, hashPrefix=self.source_hash[:16])
        return True

    def find_image(self) -> bool:
        ptprint("\n[2/3] Locating forensic image", "TITLE", condition=self._out())

        if not self.image_path.exists() and not self.dry_run:
            return self._fail("imageLookup",
                              f"Image file not found: {self.image_path}")

        if self.dry_run:
            self.image_format = ".dd"
            self.image_size   = 0
        else:
            self.image_format = self.image_path.suffix.lower()
            self.image_size   = self.image_path.stat().st_size

        ptprint(f"  ✓ {self.image_path.name}  |  "
                f"Format: {self.image_format}  |  "
                f"Size: {(self.image_size or 0) / (1024**3):.2f} GB",
                "OK", condition=self._out())
        self._add_node("imageLookup", True,
                       imageFormat=self.image_format,
                       imageSizeBytes=self.image_size)
        return True

    def calculate_hash(self) -> bool:
        ptprint("\n[3/3] Calculating image hash", "TITLE", condition=self._out())

        if self.dry_run:
            ptprint("  [DRY-RUN] Hash calculation skipped.",
                    "INFO", condition=self._out())
            self.image_hash = self.source_hash
            self.calc_time  = 0.0
            self._add_node("hashCalculation", True, dryRun=True)
            return True

        if self.image_format in (".dd", ".raw", ".img"):
            return self._hash_raw()
        if self.image_format == ".e01":
            return self._hash_e01()
        return self._fail("hashCalculation",
                          f"Unsupported image format: {self.image_format}")

    def _hash_raw(self) -> bool:
        size_gb = (self.image_size or 0) / (1024**3)
        est_min = size_gb * 1024 / (200 * 60)
        ptprint(f"  SHA-256  |  ~{est_min:.1f} min estimated at 200 MB/s",
                "INFO", condition=self._out())

        sha     = hashlib.sha256()
        read    = 0
        last_gb = 0.0
        t0      = time.time()

        try:
            with open(self.image_path, "rb") as fh:
                while chunk := fh.read(HASH_BLOCK_SIZE):
                    sha.update(chunk)
                    read    += len(chunk)
                    cur_gb   = read / (1024**3)
                    if cur_gb - last_gb >= 1.0:
                        ela = time.time() - t0
                        spd = (read / (1024**2)) / ela if ela else 0
                        ptprint(f"  {cur_gb:.1f} GB  |  {spd:.0f} MB/s",
                                "INFO", condition=self._out())
                        last_gb = cur_gb
        except Exception as exc:
            return self._fail("hashCalculation", f"Hash calculation failed: {exc}")

        self.calc_time  = time.time() - t0
        self.image_hash = sha.hexdigest()
        avg_spd = ((self.image_size or 0) / (1024**2)) / max(self.calc_time, 0.001)

        ptprint(f"  ✓ Done in {self.calc_time:.0f}s  |  {avg_spd:.0f} MB/s",
                "OK", condition=self._out())
        ptprint(f"  Image hash: {self.image_hash}", "INFO", condition=self._out())
        self._add_node("hashCalculation", True,
                       algorithm="SHA-256",
                       imageHash=self.image_hash,
                       calculationTimeSec=round(self.calc_time, 2))
        return True

    def _hash_e01(self) -> bool:
        if not self._check_command("ewfverify"):
            return self._fail("hashCalculation",
                              "ewfverify not found – sudo apt install libewf-tools")
        t0 = time.time()
        r  = self._run_command(["ewfverify", "-d", "sha256", str(self.image_path)],
                               timeout=7200)
        self.calc_time = time.time() - t0

        if not r["success"]:
            return self._fail("hashCalculation", f"ewfverify failed: {r['stderr']}")

        for line in r["stdout"].splitlines():
            if "sha256" in line.lower() and ":" in line:
                self.image_hash = line.split(":")[-1].strip()
                break
        if not self.image_hash:
            return self._fail("hashCalculation",
                              "Could not parse hash from ewfverify output")

        ptprint(f"  ✓ ewfverify done in {self.calc_time:.0f}s",
                "OK", condition=self._out())
        ptprint(f"  Image hash: {self.image_hash}", "INFO", condition=self._out())
        self._add_node("hashCalculation", True,
                       algorithm="SHA-256", imageHash=self.image_hash,
                       calculationTimeSec=round(self.calc_time, 2))
        return True

    def verify_match(self) -> bool:
        ptprint("\n" + "=" * 70, "TITLE", condition=self._out())
        ptprint("HASH VERIFICATION", "TITLE", condition=self._out())
        ptprint("=" * 70, "TITLE", condition=self._out())

        if not self.source_hash or not self.image_hash:
            return self._fail("hashVerification",
                              "Missing hash values for comparison")

        ptprint(f"  Source hash (acquisition): {self.source_hash}",
                "INFO", condition=self._out())
        ptprint(f"  Image hash  (file):        {self.image_hash}",
                "INFO", condition=self._out())

        self.hash_match = (self.source_hash == self.image_hash)
        status = "VERIFIED" if self.hash_match else "MISMATCH"

        self.ptjsonlib.add_properties({
            "sourceHash":         self.source_hash,
            "imageHash":          self.image_hash,
            "hashMatch":          self.hash_match,
            "verificationStatus": status,
            "calculationTimeSec": round(self.calc_time or 0, 2),
        })

        if self.hash_match:
            ptprint("\n  ✓ HASH MATCH – image integrity VERIFIED",
                    "OK", condition=self._out())
            ptprint("    Image is bit-for-bit identical to the source medium.",
                    "INFO", condition=self._out())
        else:
            ptprint("\n  ✗ HASH MISMATCH – CRITICAL",
                    "ERROR", condition=self._out())
            ptprint("    Possible causes: I/O error during acquisition, "
                    "file corruption, or post-acquisition modification.",
                    "ERROR", condition=self._out())
            ptprint("    Action: repeat the acquisition.",
                    "ERROR", condition=self._out())

        self._add_node("hashVerification", self.hash_match,
                       sourceHash=self.source_hash, imageHash=self.image_hash,
                       hashMatch=self.hash_match, verificationStatus=status)
        return self.hash_match

    # ------------------------------------------------------------------
    # Run and save
    # ------------------------------------------------------------------

    def run(self) -> None:
        ptprint("=" * 70, "TITLE", condition=self._out())
        ptprint(f"IMAGE HASH VERIFICATION v{__version__}  |  Case: {self.case_id}",
                "TITLE", condition=self._out())
        if self.dry_run:
            ptprint("MODE: DRY-RUN", "WARNING", condition=self._out())
        ptprint("=" * 70, "TITLE", condition=self._out())

        if not self.validate_source_hash():
            self.ptjsonlib.set_status("finished"); return
        if not self.find_image():
            self.ptjsonlib.set_status("finished"); return
        if not self.calculate_hash():
            self.ptjsonlib.set_status("finished"); return
        self.verify_match()

        self.ptjsonlib.add_node(self.ptjsonlib.create_node_object(
            "chainOfCustodyEntry",
            properties={
                "action":    f"Image hash verification – result: "
                             f"{'VERIFIED' if self.hash_match else 'MISMATCH'}",
                "result":    "SUCCESS" if self.hash_match else "MISMATCH",
                "analyst":   self.analyst,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ))

        ptprint("\n" + "=" * 70, "TITLE", condition=self._out())
        ptprint(f"VERIFICATION COMPLETE – "
                f"{'VERIFIED ✓' if self.hash_match else 'MISMATCH ✗'}",
                "OK" if self.hash_match else "ERROR", condition=self._out())
        ptprint(f"Next: {'Filesystem Analysis' if self.hash_match else 'Repeat Acquisition'}",
                "INFO", condition=self._out())
        ptprint("=" * 70, "TITLE", condition=self._out())
        self.ptjsonlib.set_status("finished")

    def save_report(self) -> Optional[str]:
        if self.args.json:
            ptprint(self.ptjsonlib.get_result_json(), "", self.args.json)
            return None

        json_file = (Path(self.args.json_out) if self.args.json_out
                     else self.output_dir / f"{self.case_id}_verification_report.json")
        json_file.write_text(
            json.dumps({"result": json.loads(self.ptjsonlib.get_result_json())},
                       indent=2, ensure_ascii=False, default=str),
            encoding="utf-8")
        ptprint(f"JSON report: {json_file.name}", "OK", condition=self._out())

        if self.image_hash and not self.dry_run:
            sidecar = Path(str(self.image_path) + ".sha256")
            sidecar.write_text(f"{self.image_hash}  {self.image_path.name}\n")
            ptprint(f"Hash sidecar: {sidecar.name}", "OK", condition=self._out())

        return str(json_file)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def get_help() -> List[Dict]:
    return [
        {"description": [
            "Forensic image hash verification – ptlibs compliant",
            "Computes SHA-256 of an image file and compares it to the acquisition hash",
            "Read-only on the image file",
            "Compliant with NIST SP 800-86 §3.1.2 and ISO/IEC 27037:2012 §7.2",
        ]},
        {"usage": [
            "ptimageverification <case-id> <image> <source-hash> [options]"
        ]},
        {"usage_example": [
            "ptimageverification CASE-001 /var/forensics/images/CASE-001.dd <64-hex>",
            "ptimageverification CASE-001 /path/to/image.e01 <hash> --analyst 'Jane'",
            "ptimageverification CASE-001 /path/to/image.dd <hash> --dry-run",
        ]},
        {"options": [
            ["case-id",            "",      "Forensic case identifier – REQUIRED"],
            ["image",              "",      "Path to forensic image (.dd/.raw/.e01) – REQUIRED"],
            ["source-hash",        "",      "SHA-256 from acquisition step (64 hex chars) – REQUIRED"],
            ["-a", "--analyst",    "<n>",   "Analyst name (default: Analyst)"],
            ["-o", "--output-dir", "<dir>", f"Output directory (default: {DEFAULT_OUTPUT_DIR})"],
            ["-j", "--json-out",   "<f>",   "Save JSON report to file"],
            ["-q", "--quiet",      "",      "Suppress terminal output"],
            ["--dry-run",          "",      "Simulate without reading the image"],
            ["-h", "--help",       "",      "Show help"],
            ["--version",          "",      "Show version"],
        ]},
        {"notes": [
            "Supported formats: .dd / .raw / .img (native SHA-256) | .e01 (ewfverify)",
            "Creates a canonical <image>.sha256 sidecar on success",
            "Exit 0 = VERIFIED | Exit 1 = MISMATCH | Exit 99 = error | Exit 130 = Ctrl+C",
            "Compliant with NIST SP 800-86 §3.1.2 and ISO/IEC 27037:2012 §7.2",
        ]},
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("case_id")
    parser.add_argument("image")
    parser.add_argument("source_hash")
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
        tool = PtImageVerification(args)
        tool.run()
        tool.save_report()
        props  = json.loads(tool.ptjsonlib.get_result_json())["result"]["properties"]
        status = props.get("verificationStatus")
        if status == "VERIFIED": return 0
        if status == "MISMATCH": return 1
        return 99
    except KeyboardInterrupt:
        ptprint("Interrupted by user.", "WARNING", condition=True)
        return 130
    except Exception as exc:
        ptprint(f"ERROR: {exc}", "ERROR", condition=True)
        return 99


if __name__ == "__main__":
    sys.exit(main())