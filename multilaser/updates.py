"""
Self-update support via Velopack (no Qt in this module).

The packaged Windows app is installed per-user by a Velopack installer
(``MultiLaserController-win-Setup.exe``) into ``%LOCALAPPDATA%\\MultiLaserController``
and updates itself from the GitHub releases of this repository. The
Portable zip build updates itself the same way.

Two pieces:

* :func:`run_install_hooks` must be the very first call in ``main()``.
  Velopack starts the exe with special arguments during install, update
  and uninstall; this call handles them (and exits) before any GUI starts.
  It also applies an update downloaded by a previous session ("Later").
* :class:`Updater` wraps ``velopack.UpdateManager``. Every failure (running
  from source, not installed, offline, rate-limited, ...) becomes a single
  :class:`UpdateError`, so callers can report it and carry on.

``velopack`` is imported lazily so source checkouts and Python 3.7 work
without it.
"""

import logging
import sys
from typing import Any, Callable, NamedTuple, Optional

logger = logging.getLogger(__name__)

REPO_URL = "https://github.com/SAIL-Labs/multilaser-box"


class UpdateError(Exception):
    """Any reason an update check, download or restart could not happen."""


class Update(NamedTuple):
    """A newer release found by :meth:`Updater.check`."""
    version: str
    info: Any        # velopack.UpdateInfo, passed back to download()/restart_into()
    notes: str       # release notes (Markdown), may be empty


def is_frozen() -> bool:
    """True when running from a PyInstaller build rather than source."""
    return bool(getattr(sys, "frozen", False))


def run_install_hooks() -> None:
    """Handle Velopack install/update/uninstall hooks. Call first in main().

    When frozen, Velopack may launch the exe with hook arguments; ``run()``
    handles those and exits the process. With auto-apply on, an update
    downloaded earlier and not yet applied is installed now and the app
    restarts into it.

    Never raises: a failure here must not stop the app from starting.
    """
    if not is_frozen():
        return
    try:
        import velopack
        velopack.App().set_auto_apply_on_startup(True).run()
    except Exception as e:  # pragma: no cover - depends on install state
        logger.warning("Velopack start-up hooks failed: %s", _first_line(e))


def _first_line(error: BaseException) -> str:
    """First line of an exception message (velopack appends a backtrace)."""
    text = str(error).strip()
    return text.splitlines()[0] if text else type(error).__name__


def _default_factory():
    """Build the real velopack UpdateManager for this repository."""
    import velopack
    token = None
    try:
        # Only present if CI writes one (needed if the repo is ever made private)
        from multilaser._update_token import TOKEN as token  # type: ignore
    except ImportError:
        pass
    return velopack.UpdateManager(velopack.GithubSource(REPO_URL, token, False))


class Updater:
    """Thin wrapper over ``velopack.UpdateManager`` that only raises UpdateError.

    Args:
        factory: Callable returning an UpdateManager-like object. Tests pass a
            fake; the default builds the real manager. When no factory is
            given and the app is not frozen, updates are unavailable.
    """

    def __init__(self, factory: Optional[Callable[[], Any]] = None):
        self._factory = factory
        self._manager = None

    def _get_manager(self):
        if self._manager is not None:
            return self._manager
        if self._factory is None:
            if not is_frozen():
                raise UpdateError(
                    "Updates are only available in the installed app "
                    "(this copy is running from source)."
                )
            factory = _default_factory
        else:
            factory = self._factory
        try:
            self._manager = factory()
        except ImportError as e:
            raise UpdateError(f"The update library is missing: {e}") from e
        except Exception as e:
            msg = _first_line(e)
            if "not properly installed" in msg.lower():
                msg = (
                    "This copy was not installed with the Multi-Laser Controller "
                    "installer, so it cannot update itself. Install it with "
                    "MultiLaserController-win-Setup.exe from the GitHub releases page."
                )
            raise UpdateError(msg) from e
        return self._manager

    def available(self) -> bool:
        """True if this copy can update itself (installed or portable build)."""
        try:
            self._get_manager()
            return True
        except UpdateError:
            return False

    def current_version(self) -> Optional[str]:
        """Installed version as Velopack sees it, or None if unavailable."""
        try:
            return str(self._get_manager().get_current_version())
        except Exception:
            return None

    def check(self) -> Optional[Update]:
        """Look for a newer release. Returns None when up to date."""
        manager = self._get_manager()
        try:
            info = manager.check_for_updates()
        except Exception as e:
            raise UpdateError(f"Could not check for updates: {_first_line(e)}") from e
        if info is None:
            return None
        target = info.TargetFullRelease
        return Update(
            version=str(target.Version),
            info=info,
            notes=str(getattr(target, "NotesMarkdown", "") or ""),
        )

    def download(self, update: Update,
                 progress: Optional[Callable[[int], None]] = None) -> None:
        """Download an update so it can be applied on restart (or next start)."""
        manager = self._get_manager()
        try:
            if progress is None:
                manager.download_updates(update.info)
            else:
                manager.download_updates(update.info, progress)
        except Exception as e:
            raise UpdateError(f"Could not download the update: {_first_line(e)}") from e

    def restart_into(self, update: Update) -> None:
        """Apply the downloaded update and restart. The process exits."""
        manager = self._get_manager()
        try:
            manager.apply_updates_and_restart(update.info)
        except Exception as e:
            raise UpdateError(f"Could not install the update: {_first_line(e)}") from e
