"""
Qt side of self-updating: background check/download and the restart bar.

:class:`UpdateController` runs :class:`multilaser.updates.Updater` checks on a
plain ``threading.Thread`` and hands results back to the GUI thread through
Qt signals. When an update has been downloaded, :class:`UpdateBar` appears at
the bottom of the window offering **Restart now** or **Later** ("Later" lets
Velopack install it the next time the app starts).

* The start-up check is silent unless an update is ready.
* A manual check (Help -> Check for Updates) reports every outcome. If one
  arrives while a check is already running, that check's result is reported
  when it finishes.
* ``before_restart()`` is called before restarting; if it returns False the
  restart is cancelled. The window uses it to switch lasers off safely.
"""

import logging
import threading
from typing import Callable, Optional

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QMessageBox, QPushButton, QWidget

from multilaser._version import __version__
from multilaser.updates import Update, UpdateError, Updater

logger = logging.getLogger(__name__)


class UpdateBar(QFrame):
    """Strip shown at the bottom of the window when an update is ready."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("updateBar")
        self.setStyleSheet(
            """
            QFrame#updateBar {
                background-color: #e3f2fd;
                border-top: 1px solid #90caf9;
            }
            QFrame#updateBar QLabel { color: #0d47a1; }
            """
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        self.label = QLabel()
        layout.addWidget(self.label, 1)
        self.restart_button = QPushButton("Restart now")
        self.later_button = QPushButton("Later")
        layout.addWidget(self.restart_button)
        layout.addWidget(self.later_button)
        self.hide()

    def show_update(self, version: str) -> None:
        self.label.setText(
            f"Version {version} has been downloaded. Restart to install it, "
            f"or choose Later to install it the next time the app starts."
        )
        self.show()


class UpdateController(QObject):
    """Coordinates update checks, the update bar and restarting.

    Args:
        updater: The (Qt-free) Updater.
        window: Parent widget for message boxes.
        before_restart: Called before restarting; return False to cancel.
        threaded: Run checks on a background thread (False for tests).
    """

    _ready = pyqtSignal(object)       # Update, downloaded and ready to apply
    _up_to_date = pyqtSignal()
    _failed = pyqtSignal(str)

    def __init__(
        self,
        updater: Updater,
        window: QWidget,
        before_restart: Callable[[], bool],
        threaded: bool = True,
    ):
        super().__init__(window)
        self.updater = updater
        self.window = window
        self.before_restart = before_restart
        self.threaded = threaded
        self.bar = UpdateBar(window)
        self.bar.restart_button.clicked.connect(self.restart_now)
        self.bar.later_button.clicked.connect(self.later)

        self.pending: Optional[Update] = None   # downloaded, awaiting restart
        self._running = False
        self._report = False    # report the running check's outcome to the user

        self._ready.connect(self._on_ready)
        self._up_to_date.connect(self._on_up_to_date)
        self._failed.connect(self._on_failed)

    # ------------------------------------------------------------------
    # Checking
    # ------------------------------------------------------------------

    def check(self, manual: bool = False) -> None:
        """Start a check (and download). Manual checks report every outcome."""
        if self.pending is not None:
            # Already downloaded: don't download again
            self.bar.show_update(self.pending.version)
            if manual:
                self._offer_restart(self.pending)
            return
        if self._running:
            if manual:
                self._report = True
            return
        self._running = True
        self._report = manual
        if self.threaded:
            threading.Thread(
                target=self._work, name="update-check", daemon=True
            ).start()
        else:
            self._work()

    def check_manually(self) -> None:
        self.check(manual=True)

    def _work(self) -> None:
        """Runs off the GUI thread: check, then download any newer release."""
        try:
            update = self.updater.check()
            if update is None:
                self._up_to_date.emit()
                return
            logger.info("Downloading update %s", update.version)
            self.updater.download(update)
            self._ready.emit(update)
        except UpdateError as e:
            self._failed.emit(str(e))
        except Exception as e:  # never let a bug here take the app down
            logger.exception("Unexpected error while checking for updates")
            self._failed.emit(f"Unexpected error: {e}")

    def _finish(self) -> bool:
        """Mark the check finished; return whether to report the outcome."""
        self._running = False
        report, self._report = self._report, False
        return report

    def _on_ready(self, update: Update) -> None:
        report = self._finish()
        self.pending = update
        logger.info("Update %s downloaded and ready", update.version)
        self.bar.show_update(update.version)
        if report:
            self._offer_restart(update)

    def _on_up_to_date(self) -> None:
        if self._finish():
            self._message(
                "info", "No Updates",
                f"You are running the latest version ({__version__}).",
            )

    def _on_failed(self, message: str) -> None:
        logger.info("Update check failed: %s", message)
        if self._finish():
            self._message("warning", "Update Check Failed", message)

    # ------------------------------------------------------------------
    # Restarting
    # ------------------------------------------------------------------

    def restart_now(self) -> None:
        """Install the downloaded update and restart (after before_restart)."""
        if self.pending is None:
            return
        if not self.before_restart():
            return
        try:
            self.updater.restart_into(self.pending)
        except UpdateError as e:
            self._message("critical", "Update Failed", str(e))

    def later(self) -> None:
        """Hide the bar; Velopack applies the update on the next start-up."""
        self.bar.hide()

    def _offer_restart(self, update: Update) -> None:
        if self._ask(
            "Update Ready",
            f"Version {update.version} has been downloaded "
            f"(you have {__version__}).\n\nRestart now to install it?\n\n"
            f"If you choose No, it will be installed the next time the app starts.",
        ):
            self.restart_now()

    # ------------------------------------------------------------------
    # Dialogs (separate methods so tests can replace them)
    # ------------------------------------------------------------------

    def _message(self, kind: str, title: str, text: str) -> None:
        box = {
            "info": QMessageBox.information,
            "warning": QMessageBox.warning,
            "critical": QMessageBox.critical,
        }[kind]
        box(self.window, title, text)

    def _ask(self, title: str, text: str) -> bool:
        reply = QMessageBox.question(
            self.window, title, text,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        return reply == QMessageBox.StandardButton.Yes
