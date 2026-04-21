#!/usr/bin/env python3
"""
    Copyright (c) 2025 Bc. Dominik Sabota, VUT FIT Brno

    ptforensictoolbase - Shared helpers for ptlibs-compliant forensic tools

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License.
    See <https://www.gnu.org/licenses/> for details.
"""

import subprocess
from typing import Any, Dict, List

from ptlibs.ptprinthelper import ptprint


class ForensicToolBase:
    """
    Mixin providing the four helpers that every Group 2 tool needs.

    Subclasses must expose:
        self.args        – parsed argparse.Namespace
        self.dry_run     – bool
        self.ptjsonlib   – PtJsonLib instance
    """

    # ------------------------------------------------------------------
    # Output gate
    # ------------------------------------------------------------------

    def _out(self) -> bool:
        """Return True when terminal output should be shown."""
        return not (self.args.json or getattr(self.args, "quiet", False))

    # ------------------------------------------------------------------
    # JSON node helpers
    # ------------------------------------------------------------------

    def _add_node(self, node_type: str, success: bool, **kwargs) -> None:
        self.ptjsonlib.add_node(self.ptjsonlib.create_node_object(
            node_type, properties={"success": success, **kwargs}
        ))

    def _fail(self, node_type: str, msg: str) -> bool:
        """Log an error, record a failure node, and return False."""
        ptprint(msg, "ERROR", condition=self._out())
        self._add_node(node_type, False, error=msg)
        return False

    # ------------------------------------------------------------------
    # Command execution
    # ------------------------------------------------------------------

    def _check_command(self, cmd: str) -> bool:
        """Return True if cmd is available on PATH."""
        try:
            subprocess.run(["which", cmd], capture_output=True, check=True, timeout=5)
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
            return False

    def _run_command(self, cmd: List[str], timeout: int = 300,
                     binary: bool = False) -> Dict[str, Any]:
        """
        Run a subprocess and return a uniform result dict.

        Keys: success (bool), stdout (str or bytes), stderr (str), returncode (int).
        In dry-run mode returns success=True with empty output immediately.
        """
        if self.dry_run:
            return {"success": True, "stdout": b"" if binary else "",
                    "stderr": "", "returncode": 0}
        try:
            if binary:
                proc = subprocess.run(cmd, capture_output=True,
                                      timeout=timeout, check=False)
                return {
                    "success": proc.returncode == 0,
                    "stdout":  proc.stdout,
                    "stderr":  proc.stderr.decode(errors="replace").strip(),
                    "returncode": proc.returncode,
                }
            else:
                proc = subprocess.run(cmd, capture_output=True, text=True,
                                      timeout=timeout, check=False)
                return {
                    "success": proc.returncode == 0,
                    "stdout":  proc.stdout.strip(),
                    "stderr":  proc.stderr.strip(),
                    "returncode": proc.returncode,
                }
        except subprocess.TimeoutExpired:
            return {"success": False, "stdout": b"" if binary else "",
                    "stderr": f"Timeout after {timeout}s", "returncode": -1}
        except Exception as exc:
            return {"success": False, "stdout": b"" if binary else "",
                    "stderr": str(exc), "returncode": -1}