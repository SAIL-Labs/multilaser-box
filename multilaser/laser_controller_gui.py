"""
PyQt6 GUI for Multi-Laser Controller
Provides graphical interface for controlling Arduino-based laser system

Requirements:
- PyQt6: pip install PyQt6
- pyserial: pip install pyserial
- The MultiLaserController class from the provided code

Author: Based on MultiLaserController by Kok-Wei Bong
Date: 2025-09-29
"""

import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QComboBox,
    QLabel,
    QMessageBox,
    QTabWidget,
    QProgressDialog,
)
from PyQt6.QtCore import Qt, QTimer, QSettings
from PyQt6.QtGui import QFont, QAction
import serial.tools.list_ports
from typing import List

# Import the MultiLaserController class
from multilaser.laser_controller import MultiLaserController, LaserControllerError, LaserState
from multilaser._version import __version__

# Import the PowerMeterTab
try:
    from multilaser.power_meter_tab import PowerMeterTab
    from multilaser.power_meter_controller import PYVISA_AVAILABLE
    POWER_METER_AVAILABLE = PYVISA_AVAILABLE
    if not PYVISA_AVAILABLE:
        print("Warning: PyVISA not available. Power meter tab will not be shown. Install with: pip install pyvisa pyvisa-py")
except ImportError as e:
    POWER_METER_AVAILABLE = False
    print(f"Warning: Power meter tab not available. Install pyvisa and pyvisa-py to enable. ({e})")

from multilaser.updater import (
    UpdateCheckWorker,
    DownloadWorker,
)


class LEDIndicator(QLabel):
    """Custom LED indicator widget"""

    def __init__(self, laser_number: int, parent=None):
        super().__init__(parent)
        self.laser_number = laser_number
        self.is_on = False

        # Set fixed size for circular appearance
        self.setFixedSize(50, 50)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Set initial state
        self.set_state(False)

    def set_state(self, is_on: bool):
        """Update LED state and appearance"""
        self.is_on = is_on

        if is_on:
            # Green LED when on
            self.setStyleSheet(
                """
                QLabel {
                    background-color: #00ff00;
                    border: 2px solid #00cc00;
                    border-radius: 25px;
                    font-weight: bold;
                    color: #003300;
                }
            """
            )
            self.setText("ON")
        else:
            # Grey LED when off
            self.setStyleSheet(
                """
                QLabel {
                    background-color: #666666;
                    border: 2px solid #444444;
                    border-radius: 25px;
                    font-weight: bold;
                    color: #cccccc;
                }
            """
            )
            self.setText("OFF")


class LaserControlGUI(QMainWindow):
    """Main GUI window for laser controller"""

    def __init__(self):
        super().__init__()
        self.settings = QSettings("MultiLaserBox", "LaserController")
        self.controller = None
        self.num_lasers = 3

        # Store LED indicators, labels, and toggle buttons
        self.led_indicators = []
        self.laser_labels = []
        self.toggle_buttons = []

        # Power meter tab reference
        self.power_meter_tab = None

        # Emergency stop state
        self.emergency_stop_active = False

        # Track last toggled laser for wavelength sync
        self.last_toggled_laser = None

        # Update check state
        self._pending_update = None
        self._update_manual = False

        self.init_ui()
        self.populate_com_ports()
        self.load_settings()
        self.connect_settings_signals()

        # Deferred update check on startup (3-second delay)
        QTimer.singleShot(3000, self._startup_update_check)

    def init_ui(self):
        """Initialise the user interface"""
        self.setWindowTitle(f"Multi-Laser Controller v{__version__}")
        self.setGeometry(100, 100, 800, 600)

        # Menu bar
        menu_bar = self.menuBar()
        help_menu = menu_bar.addMenu("Help")

        check_updates_action = QAction("Check for Updates...", self)
        check_updates_action.triggered.connect(
            lambda: self._check_for_update(manual=True)
        )
        help_menu.addAction(check_updates_action)

        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Create tab widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # Create laser control tab
        laser_tab = self.create_laser_control_tab()
        self.tab_widget.addTab(laser_tab, "Laser Control")

        # Create power meter tab if available
        if POWER_METER_AVAILABLE:
            self.power_meter_tab = PowerMeterTab(settings=self.settings)
            self.tab_widget.addTab(self.power_meter_tab, "Power Meters")

        # Status bar
        self.statusBar().showMessage("Disconnected")

    def create_laser_control_tab(self):
        """Create the laser control tab widget"""
        tab_widget = QWidget()
        tab_layout = QVBoxLayout(tab_widget)
        tab_layout.setSpacing(20)
        tab_layout.setContentsMargins(20, 20, 20, 20)

        # === ROW 1: Connection Controls ===
        connection_layout = QHBoxLayout()

        # COM port selection
        port_label = QLabel("COM Port:")
        port_label.setFont(QFont("Arial", 10))
        connection_layout.addWidget(port_label)

        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(150)
        connection_layout.addWidget(self.port_combo)

        # Refresh button for COM ports
        self.refresh_btn = QPushButton("🔄")
        self.refresh_btn.setFixedWidth(40)
        self.refresh_btn.setToolTip("Refresh COM ports")
        self.refresh_btn.clicked.connect(self.populate_com_ports)
        connection_layout.addWidget(self.refresh_btn)

        connection_layout.addSpacing(20)

        # Baud rate selection
        baud_label = QLabel("Baud Rate:")
        baud_label.setFont(QFont("Arial", 10))
        connection_layout.addWidget(baud_label)

        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["9600", "19200", "38400", "57600", "115200"])
        self.baud_combo.setCurrentText("9600")
        connection_layout.addWidget(self.baud_combo)

        connection_layout.addSpacing(20)

        # Connect button
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setMinimumWidth(120)
        self.connect_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """
        )
        self.connect_btn.clicked.connect(self.toggle_connection)
        connection_layout.addWidget(self.connect_btn)

        connection_layout.addStretch()
        tab_layout.addLayout(connection_layout)

        # === ROW 2: LED Indicators ===
        led_layout = QHBoxLayout()
        led_layout.setSpacing(30)

        for i in range(1, self.num_lasers + 1):
            # Container for each LED and label
            led_container = QVBoxLayout()
            led_container.setAlignment(Qt.AlignmentFlag.AlignCenter)

            # LED indicator
            led = LEDIndicator(i)
            self.led_indicators.append(led)
            led_container.addWidget(led, alignment=Qt.AlignmentFlag.AlignCenter)

            # Label below LED (will be updated with wavelength after connection)
            label = QLabel(f"Laser {i}")
            label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.laser_labels.append(label)
            led_container.addWidget(label)

            led_layout.addLayout(led_container)

        tab_layout.addLayout(led_layout)

        # === ROW 3: Control Buttons ===
        button_layout = QHBoxLayout()
        button_layout.setSpacing(30)

        for i in range(1, self.num_lasers + 1):
            btn = QPushButton(f"Toggle Laser {i}")
            btn.setMinimumSize(150, 50)
            btn.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            btn.setStyleSheet(
                """
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #0b7dda;
                }
                QPushButton:pressed {
                    background-color: #0966b8;
                }
                QPushButton:disabled {
                    background-color: #cccccc;
                    color: #666666;
                }
            """
            )
            btn.setEnabled(False)
            btn.clicked.connect(
                lambda checked, laser_num=i: self.toggle_laser(laser_num)
            )
            self.toggle_buttons.append(btn)
            button_layout.addWidget(btn)

        tab_layout.addLayout(button_layout)

        # === Additional Controls Row ===
        extra_controls_layout = QHBoxLayout()

        # All Off button
        self.all_off_btn = QPushButton("All OFF")
        self.all_off_btn.setMinimumSize(120, 40)
        self.all_off_btn.setEnabled(False)
        self.all_off_btn.clicked.connect(self.turn_all_off)
        self.all_off_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #f44336;
                color: white;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """
        )
        extra_controls_layout.addWidget(self.all_off_btn)

        extra_controls_layout.addStretch()

        # Emergency stop button (toggle)
        self.emergency_btn = QPushButton("⚠ EMERGENCY STOP")
        self.emergency_btn.setMinimumSize(160, 40)
        self.emergency_btn.setEnabled(False)
        self.emergency_btn.clicked.connect(self.toggle_emergency_stop)
        self.emergency_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #ff0000;
                color: white;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #cc0000;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """
        )
        extra_controls_layout.addWidget(self.emergency_btn)

        tab_layout.addLayout(extra_controls_layout)

        tab_layout.addStretch()

        return tab_widget

    def populate_com_ports(self):
        """Scan and populate available COM ports"""
        self.port_combo.clear()
        ports = serial.tools.list_ports.comports()

        if ports:
            for port in ports:
                self.port_combo.addItem(
                    f"{port.device} - {port.description}", port.device
                )
        else:
            self.port_combo.addItem("No COM ports found", None)
            self.connect_btn.setEnabled(False)
            return

        self.connect_btn.setEnabled(True)

    def toggle_connection(self):
        """Connect or disconnect from the laser controller"""
        if self.controller is None or not self.controller.connected:
            self.connect_to_controller()
        else:
            self.disconnect_from_controller()

    def connect_to_controller(self):
        """Establish connection to the laser controller"""
        port = self.port_combo.currentData()
        if port is None:
            QMessageBox.warning(
                self, "Connection Error", "Please select a valid COM port"
            )
            return

        baud_rate = int(self.baud_combo.currentText())

        try:
            self.controller = MultiLaserController(
                port=port,
                baud_rate=baud_rate,
                num_lasers=self.num_lasers,
                auto_connect=False,
                use_scpi=True,  # Enable SCPI mode by default
            )

            self.controller.connect()

            # Update UI
            self.connect_btn.setText("Disconnect")
            self.connect_btn.setStyleSheet(
                """
                QPushButton {
                    background-color: #f44336;
                    color: white;
                    font-weight: bold;
                    padding: 8px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #da190b;
                }
            """
            )

            # Enable controls
            for btn in self.toggle_buttons:
                btn.setEnabled(True)
            self.all_off_btn.setEnabled(True)
            self.emergency_btn.setEnabled(True)

            # Disable connection settings
            self.port_combo.setEnabled(False)
            self.baud_combo.setEnabled(False)
            self.refresh_btn.setEnabled(False)

            self.statusBar().showMessage(f"Connected to {port} at {baud_rate} baud")

            # Update LED indicators
            self.update_led_states()

            # Query and display wavelengths (SCPI mode only)
            self.update_wavelength_labels()

        except LaserControllerError as e:
            QMessageBox.critical(
                self, "Connection Error", f"Failed to connect:\n{str(e)}"
            )
            self.controller = None

    def disconnect_from_controller(self):
        """Disconnect from the laser controller"""
        if self.controller:
            try:
                self.controller.disconnect()
            except Exception as e:
                QMessageBox.warning(
                    self, "Disconnection Warning", f"Error during disconnect:\n{str(e)}"
                )
            finally:
                self.controller = None

        # Update UI
        self.connect_btn.setText("Connect")
        self.connect_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """
        )

        # Disable controls
        for btn in self.toggle_buttons:
            btn.setEnabled(False)
        self.all_off_btn.setEnabled(False)
        self.emergency_btn.setEnabled(False)

        # Reset emergency stop state
        self.emergency_stop_active = False

        # Reset last toggled laser tracking
        self.last_toggled_laser = None

        # Reset power meter calibration/wavelength (no active laser)
        if self.power_meter_tab:
            self.power_meter_tab.set_calibration_factor(1.0, laser_number=None)

        # Enable connection settings
        self.port_combo.setEnabled(True)
        self.baud_combo.setEnabled(True)
        self.refresh_btn.setEnabled(True)

        # Reset LED indicators
        for led in self.led_indicators:
            led.set_state(False)

        self.statusBar().showMessage("Disconnected")

    def toggle_laser(self, laser_number: int):
        """Turn on a specific laser and turn off all others"""
        if not self.controller or not self.controller.connected:
            return

        # Don't allow laser control if emergency stop is active
        if self.emergency_stop_active:
            return

        try:
            # # Turn off all lasers first TODO: debug turn_on_laser
            # self.controller.turn_off_all()
            # # Turn on the requested laser
            # self.controller.turn_on_laser(laser_number)
            # self.update_led_states()
            # self.statusBar().showMessage(f"Laser {laser_number} ON (all others OFF)")

            self.controller.toggle_laser(laser_number)
            # Track which laser was just toggled for wavelength sync
            self.last_toggled_laser = laser_number
            self.update_led_states()
            self.sync_power_meter_wavelength()
            self.sync_power_meter_calibration()
            self.statusBar().showMessage(f"Toggled Laser {laser_number}")

        except Exception as e:
            QMessageBox.critical(
                self, "Control Error", f"Failed to control laser:\n{str(e)}"
            )

    def turn_all_off(self):
        """Turn all lasers off"""
        if not self.controller or not self.controller.connected:
            return

        # Don't allow if emergency stop is active
        if self.emergency_stop_active:
            return

        try:
            self.controller.turn_off_all()
            self.last_toggled_laser = None  # Reset since no laser is on
            self.update_led_states()
            self.sync_power_meter_calibration()
            self.statusBar().showMessage("All lasers turned OFF")
        except Exception as e:
            QMessageBox.critical(
                self, "Control Error", f"Failed to turn off all lasers:\n{str(e)}"
            )

    def toggle_emergency_stop(self):
        """Toggle emergency stop - turn off all lasers and disable/enable controls"""
        if not self.controller or not self.controller.connected:
            return

        if not self.emergency_stop_active:
            # Activate emergency stop
            try:
                self.controller.emergency_stop()
                self.update_led_states()
                self.emergency_stop_active = True

                # Disable all laser controls
                for btn in self.toggle_buttons:
                    btn.setEnabled(False)
                self.all_off_btn.setEnabled(False)

                # Update emergency button appearance
                self.emergency_btn.setText("⚠ EMERGENCY STOP ACTIVE")
                self.emergency_btn.setStyleSheet(
                    """
                    QPushButton {
                        background-color: #8B0000;
                        color: white;
                        font-weight: bold;
                        border-radius: 4px;
                        border: 3px solid #ff0000;
                    }
                    QPushButton:hover {
                        background-color: #660000;
                    }
                    """
                )

                self.statusBar().showMessage("EMERGENCY STOP ACTIVATED - All lasers OFF and locked")
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Emergency Stop Error",
                    f"Failed to execute emergency stop:\n{str(e)}",
                )
        else:
            # Deactivate emergency stop
            self.emergency_stop_active = False

            # Re-enable all laser controls
            for btn in self.toggle_buttons:
                btn.setEnabled(True)
            self.all_off_btn.setEnabled(True)

            # Restore normal emergency button appearance
            self.emergency_btn.setText("⚠ EMERGENCY STOP")
            self.emergency_btn.setStyleSheet(
                """
                QPushButton {
                    background-color: #ff0000;
                    color: white;
                    font-weight: bold;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #cc0000;
                }
                QPushButton:disabled {
                    background-color: #cccccc;
                }
                """
            )

            self.statusBar().showMessage("Emergency stop deactivated - Controls enabled")

    def update_led_states(self):
        """Update all LED indicators based on controller state"""
        if not self.controller or not self.controller.connected:
            return

        for i, led in enumerate(self.led_indicators, start=1):
            state = self.controller.get_laser_state(i)
            led.set_state(state == LaserState.ON)

    def sync_power_meter_wavelength(self):
        """Set power meter wavelength to match the currently active laser"""
        if not self.power_meter_tab or not self.controller or not self.controller.connected:
            return
        if not self.controller.use_scpi:
            return
        if not self.power_meter_tab.controller.get_power_meters():
            return

        try:
            # Use the last toggled laser if available and ON
            if self.last_toggled_laser is not None:
                if self.controller.get_laser_state(self.last_toggled_laser) == LaserState.ON:
                    wavelength = self.controller.get_laser_wavelength(self.last_toggled_laser)
                    if wavelength:
                        self.power_meter_tab.set_wavelength(wavelength)
                    return

            # Fallback: find any laser that is ON
            for i in range(1, self.controller.num_lasers + 1):
                if self.controller.get_laser_state(i) == LaserState.ON:
                    wavelength = self.controller.get_laser_wavelength(i)
                    if wavelength:
                        self.power_meter_tab.set_wavelength(wavelength)
                    return
        except Exception:
            pass

    def sync_power_meter_calibration(self):
        """Set power meter calibration factor to match the currently active laser"""
        if not self.power_meter_tab or not self.controller or not self.controller.connected:
            return

        try:
            # Use the last toggled laser if available and ON
            if self.last_toggled_laser is not None:
                if self.controller.get_laser_state(self.last_toggled_laser) == LaserState.ON:
                    saved_cal = self.settings.value(
                        f"laser/calibration_factor_{self.last_toggled_laser}", defaultValue=1.0, type=float
                    )
                    self.power_meter_tab.set_calibration_factor(saved_cal, laser_number=self.last_toggled_laser)
                    return

            # Fallback: find any laser that is ON and load its saved calibration factor
            for i in range(1, self.controller.num_lasers + 1):
                if self.controller.get_laser_state(i) == LaserState.ON:
                    saved_cal = self.settings.value(
                        f"laser/calibration_factor_{i}", defaultValue=1.0, type=float
                    )
                    self.power_meter_tab.set_calibration_factor(saved_cal, laser_number=i)
                    return
            # No laser ON — reset calibration display
            self.power_meter_tab.set_calibration_factor(1.0, laser_number=None)
        except Exception:
            pass

    def update_wavelength_labels(self):
        """Update laser labels with wavelength information (SCPI mode only)"""
        if not self.controller or not self.controller.connected:
            return

        # Only works with SCPI firmware
        if not self.controller.use_scpi:
            return

        try:
            wavelengths = self.controller.get_all_wavelengths()
            for i, label in enumerate(self.laser_labels, start=1):
                wavelength = wavelengths.get(i)
                if wavelength:
                    label.setText(f"Laser {i}\n({wavelength} nm)")
                else:
                    label.setText(f"Laser {i}")
        except Exception as e:
            # If wavelength query fails, just keep default labels
            print(f"Could not query wavelengths: {e}")

    def load_settings(self):
        """Restore saved settings from QSettings"""
        saved_port = self.settings.value("laser/com_port", defaultValue="", type=str)
        if saved_port:
            for i in range(self.port_combo.count()):
                if self.port_combo.itemData(i) == saved_port:
                    self.port_combo.setCurrentIndex(i)
                    break

        saved_baud = self.settings.value("laser/baud_rate", defaultValue="9600", type=str)
        index = self.baud_combo.findText(saved_baud)
        if index >= 0:
            self.baud_combo.setCurrentIndex(index)

    def save_settings(self):
        """Persist current settings to QSettings"""
        port = self.port_combo.currentData()
        if port:
            self.settings.setValue("laser/com_port", port)

        self.settings.setValue("laser/baud_rate", self.baud_combo.currentText())

    def connect_settings_signals(self):
        """Connect widget change signals to save_settings (after initial load)"""
        self.port_combo.currentIndexChanged.connect(self.save_settings)
        self.baud_combo.currentIndexChanged.connect(self.save_settings)

    # ------------------------------------------------------------------
    # Auto-update
    # ------------------------------------------------------------------

    def _startup_update_check(self):
        """Check for updates on startup, at most once per day."""
        last_check = self.settings.value("update/last_check", defaultValue=0, type=int)
        now = int(time.time())
        one_day = 86400

        if now - last_check < one_day:
            return  # Already checked today

        self._check_for_update(manual=False)

    def _check_for_update(self, manual: bool = False):
        """Launch background update check.

        Args:
            manual: If True, show errors and 'up to date' messages.
                    If False (startup), be completely silent unless an update is found.
        """
        self._update_manual = manual
        self._pending_update = None
        self._update_worker = UpdateCheckWorker(__version__, parent=self)
        self._update_worker.update_available.connect(self._on_update_available)
        if manual:
            self._update_worker.error_occurred.connect(self._on_update_error)
            self._update_worker.check_finished.connect(self._on_update_check_finished)
        self._update_worker.finished.connect(self._update_worker.deleteLater)
        self._update_worker.start()

        # Record check time
        self.settings.setValue("update/last_check", int(time.time()))

    def _on_update_available(self, info):
        """Handle update found — show dialog to user."""
        # Check if user chose to skip this version (only for automatic checks)
        skipped = self.settings.value("update/skip_version", defaultValue="", type=str)
        if not self._update_manual and skipped == info.latest_version:
            return

        self._pending_update = info
        is_frozen = getattr(sys, "frozen", False)

        msg = QMessageBox(self)
        msg.setWindowTitle("Update Available")
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setText(
            f"A new version of Multi-Laser Controller is available.\n\n"
            f"Current version: {__version__}\n"
            f"New version: {info.latest_version}"
        )

        if info.release_notes:
            msg.setDetailedText(info.release_notes)

        if is_frozen:
            update_btn = msg.addButton("Update Now", QMessageBox.ButtonRole.AcceptRole)
        else:
            update_btn = msg.addButton("View Release", QMessageBox.ButtonRole.AcceptRole)

        msg.addButton("Later", QMessageBox.ButtonRole.RejectRole)
        skip_btn = msg.addButton("Skip This Version", QMessageBox.ButtonRole.DestructiveRole)

        msg.exec()

        clicked = msg.clickedButton()
        if clicked == update_btn:
            if is_frozen:
                self._start_download(info)
            else:
                webbrowser.open(info.html_url)
        elif clicked == skip_btn:
            self.settings.setValue("update/skip_version", info.latest_version)

    def _start_download(self, info):
        """Download the update with a progress dialog."""
        # Determine destination folder: next to current exe, or cwd for source
        if getattr(sys, "frozen", False):
            dest_dir = Path(sys.executable).parent
        else:
            dest_dir = Path.cwd()

        self._progress = QProgressDialog(
            f"Downloading v{info.latest_version}...",
            "Cancel",
            0, 100,
            self,
        )
        self._progress.setWindowTitle("Updating")
        self._progress.setMinimumDuration(0)
        self._progress.setAutoClose(False)
        self._progress.setAutoReset(False)

        self._download_worker = DownloadWorker(
            info.download_url, dest_dir, parent=self
        )
        self._download_worker.progress.connect(self._on_download_progress)
        self._download_worker.download_complete.connect(self._on_download_complete)
        self._download_worker.error_occurred.connect(self._on_download_error)
        self._download_worker.finished.connect(self._download_worker.deleteLater)

        self._progress.canceled.connect(self._download_worker.cancel)

        self._download_worker.start()

    def _on_download_progress(self, downloaded: int, total: int):
        """Update progress dialog."""
        if total > 0:
            percent = int(downloaded * 100 / total)
            self._progress.setValue(percent)
            self._progress.setLabelText(
                f"Downloading... {downloaded // 1024} / {total // 1024} KB"
            )
        else:
            self._progress.setLabelText(f"Downloading... {downloaded // 1024} KB")

    def _on_download_complete(self, exe_path_str: str):
        """Download finished — show the new exe to the user."""
        self._progress.close()

        new_exe = Path(exe_path_str)

        QMessageBox.information(
            self,
            "Update Downloaded",
            f"New version downloaded:\n\n"
            f"{new_exe.name}\n\n"
            f"Close this application and run the new version.",
        )

        # Open Explorer with the new exe selected
        if sys.platform == "win32":
            subprocess.Popen(["explorer", "/select,", str(new_exe)])
        else:
            webbrowser.open(str(new_exe.parent))

    def _on_download_error(self, error_msg: str):
        """Handle download failure."""
        self._progress.close()
        QMessageBox.critical(
            self,
            "Download Failed",
            f"Failed to download the update:\n\n{error_msg}\n\n"
            "You can download it manually from GitHub.",
        )

    def _on_update_error(self, error_msg: str):
        """Show error on manual check failure."""
        QMessageBox.warning(
            self,
            "Update Check Failed",
            f"Could not check for updates:\n\n{error_msg}\n\n"
            "Check your internet connection or try again later.",
        )

    def _on_update_check_finished(self):
        """Called when manual check finishes — show 'up to date' if no update was found."""
        if self._pending_update is None:
            QMessageBox.information(
                self,
                "No Updates",
                f"You are running the latest version ({__version__}).",
            )

    def _show_about(self):
        """Show about dialog."""
        is_frozen = getattr(sys, "frozen", False)
        mode = "Standalone executable" if is_frozen else "Running from source"
        QMessageBox.about(
            self,
            "About Multi-Laser Controller",
            f"Multi-Laser Controller v{__version__}\n\n"
            f"{mode}\n\n"
            f"Authors: Kok-Wei Bong, Chris Betters\n"
            f"https://github.com/SAIL-Labs/multilaser-box",
        )

    def closeEvent(self, event):
        """Handle window close event"""
        should_close = True

        if self.controller and self.controller.connected:
            reply = QMessageBox.question(
                self,
                "Confirm Exit",
                "Disconnect and turn off all lasers before exiting?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.disconnect_from_controller()
            else:
                should_close = False

        # Clean up power meter tab if it exists
        if should_close and self.power_meter_tab:
            self.power_meter_tab.cleanup()

        if should_close:
            event.accept()
        else:
            event.ignore()


def main():
    """Main entry point for the application"""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Modern look across platforms

    window = LaserControlGUI()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
