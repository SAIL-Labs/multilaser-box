"""
Auto-update module for Multi-Laser Controller.

Checks GitHub releases for new versions and handles downloading,
extracting, and applying updates for the PyInstaller-packaged exe.

Uses only stdlib (urllib, json, zipfile, tempfile, subprocess) plus
PyQt6 QThread for background operations.
"""

import json
import logging
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import NamedTuple, Optional

import urllib.request
import urllib.error

from PyQt6.QtCore import QThread, pyqtSignal

GITHUB_API_URL = "https://api.github.com/repos/SAIL-Labs/multilaser-box/releases/latest"
ASSET_NAME = "MultiLaserController-Windows.zip"
EXE_NAME = "MultiLaserController.exe"


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

    with urllib.request.urlopen(req, timeout=10) as response:
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
    progress_callback=None,
) -> Path:
    """Download the update zip and extract the exe.

    Args:
        download_url: URL to the release zip asset.
        progress_callback: Optional callable(bytes_downloaded, total_bytes).

    Returns:
        Path to the extracted exe file.
    """
    req = urllib.request.Request(
        download_url,
        headers={"User-Agent": "MultiLaserController-Updater"},
    )

    # Persistent temp directory (not auto-cleaned — batch script cleans it)
    temp_dir = Path(tempfile.mkdtemp(prefix="multilaser_update_"))
    zip_path = temp_dir / "update.zip"

    with urllib.request.urlopen(req, timeout=120) as response:
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

    # Find the exe in extracted contents
    exe_candidates = list(extract_dir.rglob(EXE_NAME))
    if not exe_candidates:
        raise FileNotFoundError(
            f"{EXE_NAME} not found in downloaded archive"
        )

    return exe_candidates[0]


def get_current_exe_path() -> Optional[Path]:
    """Return the path to the currently running exe, or None if not frozen."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable)
    return None


def apply_update(new_exe_path: Path, current_exe_path: Path = None):
    """Apply the update by writing and launching a replacement batch script.

    The batch script waits for this process to exit, swaps the exe, relaunches
    the app, then cleans up temp files and itself.

    After calling this function, the caller should exit the application.

    Args:
        new_exe_path: Path to the newly downloaded exe.
        current_exe_path: Path to the running exe. Auto-detected if None.

    Raises:
        RuntimeError: If not running as a frozen executable or not on Windows.
    """
    if sys.platform != "win32":
        raise RuntimeError("Automatic update is only supported on Windows")

    if current_exe_path is None:
        current_exe_path = get_current_exe_path()

    if current_exe_path is None:
        raise RuntimeError("Cannot apply update: not running as a frozen executable")

    current_exe = str(current_exe_path)
    new_exe = str(new_exe_path)
    bak_exe = current_exe + ".bak"
    pid = os.getpid()

    # The temp dir that contains downloaded files — clean it up too
    temp_dir = str(new_exe_path.parent.parent)

    batch_content = f'''@echo off
REM Wait for the current process to exit
:wait_loop
tasklist /FI "PID eq {pid}" 2>NUL | find /I "{pid}" >NUL
if not errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto wait_loop
)

REM Small safety delay
timeout /t 1 /nobreak >nul

REM Remove old backup if exists
if exist "{bak_exe}" del /f "{bak_exe}"

REM Rename current exe to .bak
move /y "{current_exe}" "{bak_exe}"
if errorlevel 1 (
    echo ERROR: Failed to rename current executable
    pause
    exit /b 1
)

REM Move new exe into place
move /y "{new_exe}" "{current_exe}"
if errorlevel 1 (
    echo ERROR: Failed to move new executable. Restoring backup.
    move /y "{bak_exe}" "{current_exe}"
    pause
    exit /b 1
)

REM Relaunch the application
start "" "{current_exe}"

REM Clean up
timeout /t 3 /nobreak >nul
del /f "{bak_exe}" 2>nul
rmdir /s /q "{temp_dir}" 2>nul

REM Delete this batch script itself
del /f "%~f0"
'''

    batch_path = Path(temp_dir) / "update.bat"
    with open(batch_path, "w") as f:
        f.write(batch_content)

    logging.info(f"Launching update script: {batch_path}")

    # Launch the batch script as a detached process
    subprocess.Popen(
        [str(batch_path)],
        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
        close_fds=True,
        shell=True,
    )


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
    download_complete = pyqtSignal(str)    # emits path to extracted exe
    error_occurred = pyqtSignal(str)       # emits error message

    def __init__(self, download_url: str, parent=None):
        super().__init__(parent)
        self.download_url = download_url

    def run(self):
        try:
            exe_path = download_update(
                self.download_url,
                progress_callback=lambda dl, total: self.progress.emit(dl, total),
            )
            self.download_complete.emit(str(exe_path))
        except Exception as e:
            logging.error(f"Update download failed: {e}")
            self.error_occurred.emit(str(e))
