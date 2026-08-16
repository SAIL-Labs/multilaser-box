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
import os
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

    Pre-release/build suffixes ("0.8.0-rc1", "0.8.0+abc123") are ignored.

    Returns:
        Tuple of ints, e.g. (0, 5, 1).
    """
    s = version_string.strip().lstrip("v")
    s = s.split("-")[0].split("+")[0]
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


def _place_exe(src_exe: Path, dest_dir: Path) -> Path:
    """Copy src_exe into dest_dir, replacing an existing file safely.

    Copies to a temporary name first and then renames into place, so a
    partially written file is never left under the final name and an
    existing (non-running) copy is replaced atomically.
    """
    dest_exe = dest_dir / src_exe.name
    tmp_dest = dest_dir / (src_exe.name + ".part")
    try:
        shutil.copy2(str(src_exe), str(tmp_dest))
        os.replace(str(tmp_dest), str(dest_exe))
    except OSError:
        try:
            tmp_dest.unlink()
        except OSError:
            pass
        raise
    return dest_exe


def _deliver_exe(src_exe: Path, dest_dir: Path) -> Path:
    """Place the new exe in dest_dir, falling back to Downloads if not writable.

    On Windows the exe may live in a folder the user cannot write to
    (Program Files, a read-only network share, a Defender-protected
    folder). In that case the update is saved to the user's Downloads
    folder instead.

    Returns:
        Path to the delivered exe (parent differs from dest_dir when the
        fallback was used).

    Raises:
        PermissionError: If neither destination is writable, with a
            message naming the folders that were tried.
    """
    try:
        return _place_exe(src_exe, dest_dir)
    except OSError as primary_error:
        fallback_dir = Path.home() / "Downloads"
        tried = str(dest_dir)
        if fallback_dir != dest_dir and fallback_dir.is_dir():
            logging.warning(
                f"Could not save update to {dest_dir} ({primary_error}); "
                f"falling back to {fallback_dir}"
            )
            try:
                return _place_exe(src_exe, fallback_dir)
            except OSError:
                tried += f" or {fallback_dir}"
        raise PermissionError(
            f"Could not save the update to {tried}:\n{primary_error}\n\n"
            "Check that the folder is writable and that the new version "
            "is not already running."
        ) from primary_error


def download_update(
    download_url: str,
    dest_dir: Path,
    progress_callback=None,
    cancel_check=None,
) -> Path:
    """Download the update zip and place the new exe in dest_dir.

    Args:
        download_url: URL to the release zip asset.
        dest_dir: Preferred directory for the downloaded exe (alongside the
            current exe). Falls back to the user's Downloads folder when
            dest_dir is not writable.
        progress_callback: Optional callable(bytes_downloaded, total_bytes).
        cancel_check: Optional callable() -> bool that returns True if cancelled.

    Returns:
        Path to the new exe (may be in the Downloads fallback folder).

    Raises:
        Exception: If download is cancelled.
        PermissionError: If the exe could not be saved to any destination.
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
                    if cancel_check and cancel_check():
                        raise Exception("Download cancelled by user")
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
        dest_exe = _deliver_exe(src_exe, dest_dir)
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
        self._cancelled = False

    def cancel(self):
        """Request cancellation of the download"""
        self._cancelled = True

    def run(self):
        try:
            exe_path = download_update(
                self.download_url,
                self.dest_dir,
                progress_callback=lambda dl, total: self.progress.emit(dl, total) if not self._cancelled else None,
                cancel_check=lambda: self._cancelled,
            )
            if not self._cancelled:
                self.download_complete.emit(str(exe_path))
        except Exception as e:
            if not self._cancelled:
                logging.error(f"Update download failed: {e}")
                self.error_occurred.emit(str(e))
