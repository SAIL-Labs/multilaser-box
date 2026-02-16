"""
Auto-update module for Multi-Laser Controller.

Checks GitHub releases for new versions and downloads the updated exe
to the same folder as the current one. The user then runs the new
versioned exe manually.

Uses only stdlib (urllib, json, zipfile, tempfile, shutil) plus
PyQt6 QThread for background operations.
"""

import json
import logging
import shutil
import ssl
import tempfile
import zipfile
from pathlib import Path
from typing import NamedTuple, Optional

import urllib.request
import urllib.error

from PyQt6.QtCore import QThread, pyqtSignal

GITHUB_API_URL = "https://api.github.com/repos/SAIL-Labs/multilaser-box/releases/latest"


def _create_ssl_context() -> ssl.SSLContext:
    """Create an SSL context, falling back to certifi if system certs fail."""
    ctx = ssl.create_default_context()
    try:
        if ctx.get_ca_certs():
            return ctx
    except Exception:
        pass
    # Fallback: use certifi's bundled CA certificates
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        pass
    return ssl.create_default_context()


_ssl_context = _create_ssl_context()
ASSET_NAME = "MultiLaserController-Windows.zip"
EXE_GLOB = "MultiLaserController-v*.exe"


# ---------------------------------------------------------------------------
# Version comparison
# ---------------------------------------------------------------------------

def parse_version(version_string: str) -> tuple:
    """Parse a version string like '0.5.1' or 'v0.5.1' into a comparable tuple.

    Returns:
        Tuple of ints, e.g. (0, 5, 1).
    """
    s = version_string.strip().lstrip("v")
    return tuple(int(x) for x in s.split("."))


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

class UpdateInfo(NamedTuple):
    """Information about an available update."""
    latest_version: str   # e.g. "0.6.0"
    download_url: str     # URL to the .zip asset
    release_notes: str    # Body text from the GitHub release
    html_url: str         # URL to the release page


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def check_for_update(current_version: str) -> Optional[UpdateInfo]:
    """Check GitHub for a newer release.

    Args:
        current_version: The current app version string (e.g. "0.5.1").

    Returns:
        UpdateInfo if a newer version is available, None if up to date.

    Raises:
        Exception on network or API errors.
    """
    req = urllib.request.Request(
        GITHUB_API_URL,
        headers={
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "MultiLaserController-Updater",
        },
    )

    with urllib.request.urlopen(req, timeout=10, context=_ssl_context) as response:
        data = json.loads(response.read().decode("utf-8"))

    tag_name = data.get("tag_name", "")
    latest = parse_version(tag_name)
    current = parse_version(current_version)

    if latest <= current:
        return None  # Up to date

    # Find the zip asset
    download_url = None
    for asset in data.get("assets", []):
        if asset["name"] == ASSET_NAME:
            download_url = asset["browser_download_url"]
            break

    if download_url is None:
        logging.warning(f"Release {tag_name} has no asset named {ASSET_NAME}")
        return None

    return UpdateInfo(
        latest_version=tag_name.lstrip("v"),
        download_url=download_url,
        release_notes=data.get("body", ""),
        html_url=data.get("html_url", ""),
    )


def download_update(
    download_url: str,
    dest_dir: Path,
    progress_callback=None,
) -> Path:
    """Download the update zip and place the new exe in dest_dir.

    Args:
        download_url: URL to the release zip asset.
        dest_dir: Directory to place the downloaded exe (alongside current exe).
        progress_callback: Optional callable(bytes_downloaded, total_bytes).

    Returns:
        Path to the new exe in dest_dir.
    """
    req = urllib.request.Request(
        download_url,
        headers={"User-Agent": "MultiLaserController-Updater"},
    )

    temp_dir = Path(tempfile.mkdtemp(prefix="multilaser_update_"))

    try:
        zip_path = temp_dir / "update.zip"

        with urllib.request.urlopen(req, timeout=120, context=_ssl_context) as response:
            total_size = int(response.headers.get("Content-Length", 0))
            downloaded = 0
            chunk_size = 65536  # 64 KB

            with open(zip_path, "wb") as f:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback:
                        progress_callback(downloaded, total_size)

        # Extract zip
        extract_dir = temp_dir / "extracted"
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_dir)

        # Find the versioned exe in extracted contents
        exe_candidates = list(extract_dir.rglob(EXE_GLOB))
        if not exe_candidates:
            raise FileNotFoundError(
                f"No file matching {EXE_GLOB} found in downloaded archive"
            )

        src_exe = exe_candidates[0]
        dest_exe = dest_dir / src_exe.name

        # Copy to destination folder
        shutil.copy2(str(src_exe), str(dest_exe))
        logging.info(f"Update downloaded to {dest_exe}")

        return dest_exe

    finally:
        # Clean up temp directory
        shutil.rmtree(temp_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# QThread workers for non-blocking GUI integration
# ---------------------------------------------------------------------------

class UpdateCheckWorker(QThread):
    """Background thread to check for updates without blocking the GUI."""

    update_available = pyqtSignal(object)   # emits UpdateInfo
    check_finished = pyqtSignal()           # emits when done (even if no update)
    error_occurred = pyqtSignal(str)        # emits error message string

    def __init__(self, current_version: str, parent=None):
        super().__init__(parent)
        self.current_version = current_version

    def run(self):
        try:
            info = check_for_update(self.current_version)
            if info is not None:
                self.update_available.emit(info)
        except Exception as e:
            logging.debug(f"Update check failed: {e}")
            self.error_occurred.emit(str(e))
        finally:
            self.check_finished.emit()


class DownloadWorker(QThread):
    """Background thread to download an update."""

    progress = pyqtSignal(int, int)        # (bytes_downloaded, total_bytes)
    download_complete = pyqtSignal(str)    # emits path to new exe
    error_occurred = pyqtSignal(str)       # emits error message

    def __init__(self, download_url: str, dest_dir: Path, parent=None):
        super().__init__(parent)
        self.download_url = download_url
        self.dest_dir = dest_dir

    def run(self):
        try:
            exe_path = download_update(
                self.download_url,
                self.dest_dir,
                progress_callback=lambda dl, total: self.progress.emit(dl, total),
            )
            self.download_complete.emit(str(exe_path))
        except Exception as e:
            logging.error(f"Update download failed: {e}")
            self.error_occurred.emit(str(e))
