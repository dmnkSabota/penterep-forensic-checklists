#!/usr/bin/env python3
"""
    Copyright (c) 2026 Bc. Dominik Sabota, VUT FIT Brno

    ptforensictoolbase - Shared helpers for ptlibs-compliant forensic tools

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License.
    See <https://www.gnu.org/licenses/> for details.
"""
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
 
from ptlibs.ptprinthelper import ptprint
 
 
class ForensicToolBase:
    """
    Mixin providing shared helpers for all Group 2 forensic tools.
 
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
    # Write-blocker confirmation  (Steps 3 and 5)
    # ------------------------------------------------------------------
 
    @staticmethod
    def confirm_write_blocker() -> bool:
        """
        Interactive write-blocker confirmation required before any device
        access. Displays a checklist and waits for analyst confirmation.
        Returns True if confirmed, False if declined.
 
        Defined once here to avoid duplication between ptmediareadability
        and ptforensicimaging.
        """
        ptprint("\n" + "!" * 70, "WARNING", condition=True)
        ptprint("CRITICAL: WRITE-BLOCKER MUST BE CONNECTED",
                "WARNING", condition=True, colortext=True)
        ptprint("!" * 70, "WARNING", condition=True)
        for line in [
            "  1. Hardware write-blocker is physically connected",
            "  2. LED indicator shows PROTECTED",
            "  3. Source media connected THROUGH the write-blocker",
            "  4. Target storage has sufficient free space",
        ]:
            ptprint(line, "TEXT", condition=True)
 
        while True:
            resp = input("\nConfirm write-blocker is active [y/N]: ").strip().lower()
            if resp in ("y", "yes"):    ok = True;  break
            if resp in ("n", "no", ""): ok = False; break
            ptprint("Please enter 'y' or 'n'.", "WARNING", condition=True)
 
        sym = "✓" * 70 if ok else "✗" * 70
        lv  = "OK" if ok else "ERROR"
        ptprint("\n" + sym, lv, condition=True)
        ptprint("CONFIRMED – proceeding" if ok else "NOT CONFIRMED – aborted",
                lv, condition=True, colortext=True)
        ptprint(sym, lv, condition=True)
        return ok
 
    # ------------------------------------------------------------------
    # Shared image file validation  (Steps 8a, 8b, 10)
    # ------------------------------------------------------------------
 
    def _validate_image_file(self, filepath: Path) -> Tuple[str, Dict]:
        """
        Two-stage image validation shared by filesystem recovery, file
        carving, and integrity validation (basic path only).
 
        Stage 1 – minimum size and file(1) type recognition.
        Stage 2 – ImageMagick identify for structural integrity.
 
        Returns (status, info_dict) where status is one of:
            'valid'     – passes both stages
            'corrupted' – fails stage 2 but is large enough to be a real file
            'invalid'   – too small, empty, or not recognised as an image
        """
        info: Dict = {"size": 0, "imageFormat": None, "dimensions": None}
 
        try:
            info["size"] = filepath.stat().st_size
        except Exception as exc:
            return "invalid", {**info, "error": str(exc)}
 
        if info["size"] < 100:
            return "invalid", info
 
        # Stage 1 – file(1) type check
        r = self._run_command(["file", "-b", str(filepath)], timeout=10)
        if r["success"] and not any(
                kw in r["stdout"].lower()
                for kw in ("image", "jpeg", "png", "tiff", "gif", "bitmap",
                           "raw", "canon", "nikon", "exif", "riff webp", "heic")):
            return "invalid", info
 
        # Stage 2 – ImageMagick structural check
        r = self._run_command(["identify", str(filepath)], timeout=30)
        if r["success"]:
            m = re.search(r"(\w+)\s+(\d+)x(\d+)", r["stdout"])
            if m:
                info["imageFormat"] = m.group(1)
                info["dimensions"]  = f"{m.group(2)}x{m.group(3)}"
            return "valid", info
 
        return ("corrupted" if info["size"] > 1024 else "invalid"), info
 
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
                    "success":    proc.returncode == 0,
                    "stdout":     proc.stdout,
                    "stderr":     proc.stderr.decode(errors="replace").strip(),
                    "returncode": proc.returncode,
                }
            else:
                proc = subprocess.run(cmd, capture_output=True, text=True,
                                      timeout=timeout, check=False)
                return {
                    "success":    proc.returncode == 0,
                    "stdout":     proc.stdout.strip(),
                    "stderr":     proc.stderr.strip(),
                    "returncode": proc.returncode,
                }
        except subprocess.TimeoutExpired:
            return {"success": False, "stdout": b"" if binary else "",
                    "stderr": f"Timeout after {timeout}s", "returncode": -1}
        except Exception as exc:
            return {"success": False, "stdout": b"" if binary else "",
                    "stderr": str(exc), "returncode": -1}