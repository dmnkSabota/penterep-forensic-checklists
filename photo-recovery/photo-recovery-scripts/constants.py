#!/usr/bin/env python3
"""
    Copyright (c) 2026 Bc. Dominik Sabota, VUT FEKT Brno

    _constants - Shared constants for photo-recovery forensic tools

    Single source of truth for image extensions and format maps.
    Import from here instead of duplicating across scripts.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License.
    See <https://www.gnu.org/licenses/> for details.
"""

from typing import Dict, FrozenSet

# ---------------------------------------------------------------------------
# Image file extensions recognised by all photo-recovery tools
# ---------------------------------------------------------------------------

IMAGE_EXTENSIONS: FrozenSet[str] = frozenset({
    ".jpg", ".jpeg", ".png", ".gif", ".bmp",
    ".tiff", ".tif", ".heic", ".heif", ".webp",
    ".cr2", ".cr3", ".nef", ".nrw", ".arw", ".srf", ".sr2",
    ".dng", ".orf", ".raf", ".rw2", ".pef", ".raw",
})

# Keywords used by file(1) to identify image content (subset of MIME descriptions)
IMAGE_FILE_KEYWORDS: FrozenSet[str] = frozenset({
    "image", "jpeg", "png", "tiff", "gif", "bitmap",
    "raw", "canon", "nikon", "exif", "riff webp", "heic",
})

# ---------------------------------------------------------------------------
# Format grouping maps
# ---------------------------------------------------------------------------

# Extension (without dot) → logical group name used in statistics
FORMAT_GROUP_MAP: Dict[str, str] = {
    "jpg":  "jpeg", "jpeg": "jpeg",
    "png":  "png",
    "tif":  "tiff", "tiff": "tiff",
    "gif":  "other", "bmp":  "other",
    "heic": "other", "heif": "other", "webp": "other",
    "cr2":  "raw",  "cr3":  "raw",  "nef":  "raw",  "nrw":  "raw",
    "arw":  "raw",  "srf":  "raw",  "sr2":  "raw",  "dng":  "raw",
    "orf":  "raw",  "raf":  "raw",  "rw2":  "raw",  "pef":  "raw",  "raw": "raw",
}

# Extension (without dot) → output subdirectory name
FORMAT_DIR_MAP: Dict[str, str] = {
    "jpg":  "jpg",  "jpeg": "jpg",
    "png":  "png",
    "tif":  "tiff", "tiff": "tiff",
    "gif":  "other", "bmp":  "other",
    "heic": "other", "heif": "other", "webp": "other",
    "cr2":  "raw",  "cr3":  "raw",  "nef":  "raw",  "nrw":  "raw",
    "arw":  "raw",  "srf":  "raw",  "sr2":  "raw",  "dng":  "raw",
    "orf":  "raw",  "raf":  "raw",  "rw2":  "raw",  "pef":  "raw",  "raw": "raw",
}