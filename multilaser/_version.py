"""
Version information for Multi-Laser Controller

This is the single source of truth for version numbers.

To update the version:
1. Edit the VERSION file in the repository root, OR
2. Edit __version__ below directly

Both methods work - VERSION file takes precedence if it exists.
"""

from pathlib import Path

# Try to read from VERSION file first
try:
    version_file = Path(__file__).parent.parent / "VERSION"
    if version_file.exists():
        __version__ = version_file.read_text().strip()
    else:
        __version__ = "0.4.2"
except Exception:
    # Fallback if VERSION file cannot be read
    __version__ = "0.4.2"
