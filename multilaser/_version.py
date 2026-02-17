"""
Version information for Multi-Laser Controller

Version is determined from multiple sources (in priority order):
1. VERSION file (if present) - for development convenience
2. Git tags (git describe --tags) - for git-based workflows
3. Fallback to "0.0.0-dev" for unknown builds

For releases, git tags are the authoritative source. GitHub Actions
extracts the version from the tag that triggered the workflow.
"""

import subprocess
from pathlib import Path


def _get_version():
    """Get version from VERSION file, git tag, or default to dev version."""
    # 1. Try VERSION file first (for backwards compatibility and convenience)
    try:
        version_file = Path(__file__).parent.parent / "VERSION"
        if version_file.exists():
            version = version_file.read_text().strip()
            if version and not version.startswith('#'):
                return version
    except Exception:
        pass

    # 2. Try to get version from git tags (for development builds from repo)
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            tag = result.stdout.strip()
            # Remove 'v' prefix if present
            if tag:
                return tag.lstrip('v')
    except Exception:
        pass

    # 3. Fallback for development/unknown builds
    return "0.0.0-dev"


__version__ = _get_version()
