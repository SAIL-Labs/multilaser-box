"""
Power Meter Tab Widget
PyQt6 widget for viewing and controlling Thorlabs PM100USB power meters

Requirements:
- PyQt6: pip install PyQt6
- pyvisa: pip install pyvisa pyvisa-py

Author: Multi-Laser Box Project
Date: 2025-12-08
"""

import logging

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QComboBox,
    QGroupBox,
    QMessageBox,
    QSpinBox,
    QDoubleSpinBox,
)
from PyQt6.QtCore import Qt, QTimer, QSettings
from PyQt6.QtGui import QFont
from typing import Optional

from multilaser.power_meter_controller import (
    PowerMeterController,
    PowerMeterError,
    PowerMeterRole,
    format_power_auto_scale,
)


class PowerDisplay(QWidget):
    """Widget to display power reading for a single meter"""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.title = title
        self.init_ui()

    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout()
        layout.setSpacing(5)

        # Title
        title_label = QLabel(self.title)
        title_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Power reading display (auto-scaled)
        self.power_label = QLabel("--- W")
        self.power_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        self.power_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.power_label.setStyleSheet(
            """
            QLabel {
                background-color: #2c3e50;
                color: #00ff00;
                border: 2px solid #34495e;
                border-radius: 8px;
                padding: 20px;
                min-height: 60px;
            }
        """
        )
        layout.addWidget(self.power_label)

        # Power in Watts (raw value, smaller font)
        self.power_watts_label = QLabel("(--- W)")
        self.power_watts_label.setFont(QFont("Arial", 10))
        self.power_watts_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.power_watts_label.setStyleSheet("color: #7f8c8d;")
        layout.addWidget(self.power_watts_label)

        # Raw (uncalibrated) info label — only shown for reference meter when calibrated
        self.raw_label = QLabel("")
        self.raw_label.setFont(QFont("Arial", 9))
        self.raw_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.raw_label.setStyleSheet("color: #e67e22;")
        self.raw_label.setVisible(False)
        layout.addWidget(self.raw_label)

        # Device info
        self.device_label = QLabel("Not connected")
        self.device_label.setFont(QFont("Arial", 8))
        self.device_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.device_label.setStyleSheet("color: #95a5a6;")
        layout.addWidget(self.device_label)

        self.setLayout(layout)

    def update_power(self, power_w: Optional[float]):
        """Update the power reading with auto-scaled units"""
        if power_w is not None:
            # Display auto-scaled value in large font
            self.power_label.setText(format_power_auto_scale(power_w))
            # Display raw Watts value in smaller font
            self.power_watts_label.setText(f"({power_w:.6e} W)")
        else:
            self.power_label.setText("--- W")
            self.power_watts_label.setText("(--- W)")

    def set_raw_info(self, raw_power_w: Optional[float]):
        """Show the raw (uncalibrated) power reading below the main display"""
        if raw_power_w is not None:
            self.raw_label.setText(f"Raw: {format_power_auto_scale(raw_power_w)}")
            self.raw_label.setVisible(True)
        else:
            self.raw_label.setText("")
            self.raw_label.setVisible(False)

    def set_device_info(self, info: str):
        """Set the device information text"""
        self.device_label.setText(info)


class PowerMeterTab(QWidget):
    """Main power meter tab widget"""

    def __init__(self, settings: QSettings = None, parent=None):
        super().__init__(parent)
        self.settings = settings or QSettings("MultiLaserBox", "LaserController")
        self.controller = PowerMeterController()
        self.available_meters = []
        self.frozen = False
        self.active_laser_number = None
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_readings)

        self.init_ui()
        self.load_settings()
        self.connect_settings_signals()

    def init_ui(self):
        """Initialize the user interface"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # === Connection Section ===
        connection_group = QGroupBox("Power Meter Connection")
        connection_layout = QVBoxLayout()

        # Scan and connect row
        scan_row = QHBoxLayout()

        self.scan_btn = QPushButton("Scan for Power Meters")
        self.scan_btn.setMinimumWidth(150)
        self.scan_btn.clicked.connect(self.scan_power_meters)
        scan_row.addWidget(self.scan_btn)

        self.status_label = QLabel("No power meters connected")
        self.status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
        scan_row.addWidget(self.status_label)

        scan_row.addStretch()

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setMinimumWidth(120)
        self.connect_btn.setEnabled(False)
        self.connect_btn.clicked.connect(self.toggle_connection)
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
        scan_row.addWidget(self.connect_btn)

        connection_layout.addLayout(scan_row)
        connection_group.setLayout(connection_layout)
        main_layout.addWidget(connection_group)

        # === Role Assignment Section ===
        role_group = QGroupBox("Role Assignment")
        role_layout = QHBoxLayout()

        role_layout.addWidget(QLabel("Reference Meter:"))
        self.ref_combo = QComboBox()
        self.ref_combo.setEnabled(False)
        self.ref_combo.currentIndexChanged.connect(self.update_role_assignment)
        role_layout.addWidget(self.ref_combo)

        role_layout.addSpacing(20)

        role_layout.addWidget(QLabel("Target Meter:"))
        self.target_combo = QComboBox()
        self.target_combo.setEnabled(False)
        self.target_combo.currentIndexChanged.connect(self.update_role_assignment)
        role_layout.addWidget(self.target_combo)

        role_layout.addStretch()

        role_group.setLayout(role_layout)
        main_layout.addWidget(role_group)

        # === Settings Section ===
        settings_group = QGroupBox("Measurement Settings")
        settings_layout = QHBoxLayout()

        # Wavelength setting
        settings_layout.addWidget(QLabel("Wavelength (nm):"))
        self.wavelength_spin = QSpinBox()
        self.wavelength_spin.setRange(400, 2000)
        self.wavelength_spin.setValue(1310)
        self.wavelength_spin.setSingleStep(1)
        self.wavelength_spin.setEnabled(False)
        settings_layout.addWidget(self.wavelength_spin)

        settings_layout.addSpacing(20)

        # Averaging setting
        settings_layout.addWidget(QLabel("Averaging (samples):"))
        self.averaging_spin = QSpinBox()
        self.averaging_spin.setRange(1, 10000)
        self.averaging_spin.setValue(1)
        self.averaging_spin.setSingleStep(1)
        self.averaging_spin.setEnabled(False)
        settings_layout.addWidget(self.averaging_spin)

        settings_layout.addSpacing(20)

        # Apply settings button
        self.apply_settings_btn = QPushButton("Apply Settings")
        self.apply_settings_btn.setEnabled(False)
        self.apply_settings_btn.clicked.connect(self.apply_settings)
        settings_layout.addWidget(self.apply_settings_btn)

        settings_layout.addSpacing(20)

        # Update rate setting
        settings_layout.addWidget(QLabel("Update Rate (Hz):"))
        self.update_rate_spin = QDoubleSpinBox()
        self.update_rate_spin.setRange(0.1, 20.0)
        self.update_rate_spin.setValue(10)
        self.update_rate_spin.setSingleStep(0.1)
        self.update_rate_spin.setSuffix(" Hz")
        self.update_rate_spin.setEnabled(False)
        self.update_rate_spin.valueChanged.connect(self.update_timer_rate)
        settings_layout.addWidget(self.update_rate_spin)

        settings_layout.addStretch()

        settings_group.setLayout(settings_layout)
        main_layout.addWidget(settings_group)

        # === Calibration Section ===
        calibration_group = QGroupBox("Reference Calibration")
        calibration_layout = QHBoxLayout()

        calibration_layout.addWidget(QLabel("Calibration Factor:"))
        self.calibration_spin = QDoubleSpinBox()
        self.calibration_spin.setRange(0.001, 1000.0)
        self.calibration_spin.setValue(1.0)
        self.calibration_spin.setDecimals(6)
        self.calibration_spin.setSingleStep(0.1)
        self.calibration_spin.setEnabled(False)
        self.calibration_spin.valueChanged.connect(self._on_calibration_changed)
        calibration_layout.addWidget(self.calibration_spin)

        self.calibration_laser_label = QLabel("")
        self.calibration_laser_label.setStyleSheet("color: #7f8c8d; font-style: italic;")
        calibration_layout.addWidget(self.calibration_laser_label)

        calibration_layout.addSpacing(10)

        self.calibrate_btn = QPushButton("Calibrate Now")
        self.calibrate_btn.setEnabled(False)
        self.calibrate_btn.setToolTip(
            "Read both meters and compute calibration factor so that\n"
            "corrected reference = target power"
        )
        self.calibrate_btn.clicked.connect(self.auto_calibrate)
        calibration_layout.addWidget(self.calibrate_btn)

        calibration_layout.addStretch()

        calibration_group.setLayout(calibration_layout)
        main_layout.addWidget(calibration_group)

        # === Power Readings Section ===
        readings_row = QHBoxLayout()
        readings_row.setSpacing(20)

        # Reference power display
        self.ref_display = PowerDisplay("Reference Power")
        readings_row.addWidget(self.ref_display)

        # Target power display
        self.target_display = PowerDisplay("Target Power")
        readings_row.addWidget(self.target_display)

        main_layout.addLayout(readings_row)

        # === Freeze Button ===
        freeze_row = QHBoxLayout()
        freeze_row.addStretch()
        self.freeze_btn = QPushButton("Freeze")
        self.freeze_btn.setMinimumWidth(120)
        self.freeze_btn.setEnabled(False)
        self.freeze_btn.clicked.connect(self.toggle_freeze)
        freeze_row.addWidget(self.freeze_btn)
        freeze_row.addStretch()
        main_layout.addLayout(freeze_row)

        # === Ratio Display ===
        ratio_group = QGroupBox("Power Ratio")
        ratio_layout = QVBoxLayout()

        self.ratio_label = QLabel("Target / Reference = ---")
        self.ratio_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.ratio_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ratio_label.setStyleSheet(
            """
            QLabel {
                background-color: #34495e;
                color: #3498db;
                border: 2px solid #2c3e50;
                border-radius: 8px;
                padding: 15px;
            }
        """
        )
        ratio_layout.addWidget(self.ratio_label)

        self.ratio_percent_label = QLabel("--- %")
        self.ratio_percent_label.setFont(QFont("Arial", 12))
        self.ratio_percent_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ratio_percent_label.setStyleSheet("color: #7f8c8d;")
        ratio_layout.addWidget(self.ratio_percent_label)

        ratio_group.setLayout(ratio_layout)
        main_layout.addWidget(ratio_group)

        main_layout.addStretch()

        self.setLayout(main_layout)

    def scan_power_meters(self):
        """Scan for available power meters"""
        try:
            self.available_meters = self.controller.find_power_meters()
            count = len(self.available_meters)

            if count == 0:
                QMessageBox.warning(
                    self,
                    "No Devices Found",
                    "No Thorlabs power meters found.\n\n"
                    "Make sure the devices are connected and drivers are installed.",
                )
                self.status_label.setText("No power meters found")
                self.status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
                self.connect_btn.setEnabled(False)

            elif count in [1, 2]:
                self.status_label.setText(f"Found {count} power meter(s) - ready to connect")
                self.status_label.setStyleSheet("color: #27ae60; font-weight: bold;")
                self.connect_btn.setEnabled(True)

            else:
                QMessageBox.warning(
                    self,
                    "Too Many Devices",
                    f"Found {count} power meters.\n\n"
                    "This application supports up to 2 power meters.\n"
                    "Please disconnect extra devices.",
                )
                self.status_label.setText(f"Found {count} power meters (need 1 or 2)")
                self.status_label.setStyleSheet("color: #e67e22; font-weight: bold;")
                self.connect_btn.setEnabled(False)

        except PowerMeterError as e:
            QMessageBox.critical(
                self, "Scan Error", f"Failed to scan for power meters:\n{str(e)}"
            )

    def toggle_connection(self):
        """Toggle connection to power meters"""
        if not self.controller.get_power_meters():
            self.connect_meters()
        else:
            self.disconnect_meters()

    def connect_meters(self):
        """Connect to the power meters"""
        try:
            self.controller.connect_power_meters(self.available_meters)

            meters = self.controller.get_power_meters()
            num_meters = len(meters)

            # Populate role selection combo boxes
            self.ref_combo.blockSignals(True)
            self.target_combo.blockSignals(True)
            self.ref_combo.clear()
            self.target_combo.clear()

            # Add "None" option for single-meter mode
            none_label = "— None —"
            self.ref_combo.addItem(none_label, None)
            self.target_combo.addItem(none_label, None)

            for i, pm in enumerate(meters):
                label = f"Meter {i + 1}: {pm.get_short_name()}"
                self.ref_combo.addItem(label, i)
                self.target_combo.addItem(label, i)

            # Restore saved role assignment if the same meters are present
            role_restored = False
            if self._saved_ref_resource or self._saved_target_resource:
                ref_idx = None   # meter index (not combo index)
                target_idx = None
                for i, pm in enumerate(meters):
                    if pm.resource_name == self._saved_ref_resource:
                        ref_idx = i
                    if pm.resource_name == self._saved_target_resource:
                        target_idx = i

                if ref_idx is not None or target_idx is not None:
                    # Convert meter index → combo index (+1 for "None" item)
                    ref_combo_idx = (ref_idx + 1) if ref_idx is not None else 0
                    target_combo_idx = (target_idx + 1) if target_idx is not None else 0
                    # Don't allow both pointing at the same meter
                    if ref_combo_idx != target_combo_idx or ref_combo_idx == 0:
                        self.ref_combo.setCurrentIndex(ref_combo_idx)
                        self.target_combo.setCurrentIndex(target_combo_idx)
                        role_restored = True

            if not role_restored:
                if num_meters == 2:
                    self.ref_combo.setCurrentIndex(1)      # Meter 0
                    self.target_combo.setCurrentIndex(2)    # Meter 1
                else:
                    self.ref_combo.setCurrentIndex(0)       # None
                    self.target_combo.setCurrentIndex(1)    # Meter 0

            self.ref_combo.blockSignals(False)
            self.target_combo.blockSignals(False)

            # Update role assignment
            self.update_role_assignment()

            # Update device info in displays
            if num_meters == 2:
                self.ref_display.set_device_info(meters[0].device_info)
                self.target_display.set_device_info(meters[1].device_info)
            else:
                self.ref_display.set_device_info("Not assigned")
                self.target_display.set_device_info(meters[0].device_info)

            # Enable controls
            self.ref_combo.setEnabled(True)
            self.target_combo.setEnabled(True)
            self.wavelength_spin.setEnabled(True)
            self.averaging_spin.setEnabled(True)
            self.update_rate_spin.setEnabled(True)
            self.apply_settings_btn.setEnabled(True)
            self.freeze_btn.setEnabled(True)

            # Calibration controls remain disabled until a laser is toggled on
            # (set_calibration_factor() enables them when called from GUI)

            # Disable scan and update connect button
            self.scan_btn.setEnabled(False)
            self.connect_btn.setText("Disconnect")
            self.connect_btn.setStyleSheet(
                """
                QPushButton {
                    background-color: #e74c3c;
                    color: white;
                    font-weight: bold;
                    padding: 8px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #c0392b;
                }
            """
            )

            self.status_label.setText(f"Connected to {num_meters} power meter(s)")
            self.status_label.setStyleSheet("color: #27ae60; font-weight: bold;")

            # Start updating readings
            self.update_timer_rate()
            self.update_timer.start()

        except PowerMeterError as e:
            QMessageBox.critical(
                self, "Connection Error", f"Failed to connect to power meters:\n{str(e)}"
            )

    def disconnect_meters(self):
        """Disconnect from the power meters"""
        # Stop timer and unfreeze
        self.update_timer.stop()
        self.frozen = False
        self.freeze_btn.setText("Freeze")
        self.freeze_btn.setStyleSheet("")

        # Disconnect
        self.controller.disconnect_all()

        # Reset calibration state
        self.controller.calibration_factor = 1.0
        self.active_laser_number = None
        self.calibration_laser_label.setText("")

        # Reset UI
        self.ref_combo.clear()
        self.target_combo.clear()
        self.ref_combo.setEnabled(False)
        self.target_combo.setEnabled(False)
        self.wavelength_spin.setEnabled(False)
        self.averaging_spin.setEnabled(False)
        self.update_rate_spin.setEnabled(False)
        self.apply_settings_btn.setEnabled(False)
        self.freeze_btn.setEnabled(False)
        self.calibrate_btn.setEnabled(False)
        self.calibration_spin.setEnabled(False)

        self.ref_display.update_power(None)
        self.target_display.update_power(None)
        self.ref_display.set_device_info("Not connected")
        self.target_display.set_device_info("Not connected")
        self.ref_display.set_raw_info(None)

        self.ratio_label.setText("Target / Reference = ---")
        self.ratio_percent_label.setText("--- %")

        self.scan_btn.setEnabled(True)
        self.connect_btn.setText("Connect")
        self.connect_btn.setEnabled(False)
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

        self.status_label.setText("Disconnected")
        self.status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")

    def update_role_assignment(self):
        """Update the role assignment based on combo box selection"""
        if not self.controller.get_power_meters():
            return

        ref_index = self.ref_combo.currentData()
        target_index = self.target_combo.currentData()

        # Both None is invalid
        if ref_index is None and target_index is None:
            return

        # Same meter for both roles is invalid
        if ref_index is not None and target_index is not None and ref_index == target_index:
            QMessageBox.warning(
                self,
                "Invalid Assignment",
                "Reference and Target must be different power meters!",
            )
            # Reset: put the other meter in the target slot
            self.target_combo.blockSignals(True)
            other = 1 if ref_index == 0 else 0
            # Find combo index for that meter index
            for i in range(self.target_combo.count()):
                if self.target_combo.itemData(i) == other:
                    self.target_combo.setCurrentIndex(i)
                    break
            self.target_combo.blockSignals(False)
            target_index = other

        try:
            self.controller.assign_roles(ref_index, target_index)

            # Update device info in displays
            meters = self.controller.get_power_meters()
            if ref_index is not None:
                self.ref_display.set_device_info(meters[ref_index].device_info)
            else:
                self.ref_display.set_device_info("Not assigned")

            if target_index is not None:
                self.target_display.set_device_info(meters[target_index].device_info)
            else:
                self.target_display.set_device_info("Not assigned")

            # Enable calibrate button only when both roles are assigned
            has_both = ref_index is not None and target_index is not None
            self.calibrate_btn.setEnabled(has_both)

        except PowerMeterError as e:
            QMessageBox.critical(
                self, "Assignment Error", f"Failed to assign roles:\n{str(e)}"
            )

    def set_calibration_factor(self, factor: float, laser_number: int = None):
        """Set the calibration factor for the given laser.

        Called by LaserControlGUI.sync_power_meter_calibration() when a laser
        is toggled on/off.
        """
        self.active_laser_number = laser_number

        # Update label to show which laser's calibration is active
        if laser_number is not None:
            self.calibration_laser_label.setText(f"(Laser {laser_number})")
            self.calibration_spin.setEnabled(True)
            self.calibrate_btn.setEnabled(
                len(self.controller.get_power_meters()) == 2
            )
        else:
            self.calibration_laser_label.setText("(No laser active)")
            self.calibration_spin.setEnabled(False)
            self.calibrate_btn.setEnabled(False)

        # Set spin box — triggers _on_calibration_changed → controller sync
        self.calibration_spin.setValue(factor)

    def set_wavelength(self, wavelength_nm: int):
        """Set the wavelength on the GUI and apply to connected meters"""
        self.wavelength_spin.setValue(wavelength_nm)
        self.apply_settings()

    def apply_settings(self):
        """Apply wavelength and averaging settings to all meters"""
        if not self.controller.get_power_meters():
            return

        wavelength = self.wavelength_spin.value()
        averaging = self.averaging_spin.value()

        try:
            for pm in self.controller.get_power_meters():
                pm.set_wavelength(wavelength)
                pm.set_averaging(averaging)
        except PowerMeterError as e:
            QMessageBox.critical(
                self, "Settings Error", f"Failed to apply settings:\n{str(e)}"
            )

    def update_timer_rate(self):
        """Update the timer interval based on the update rate"""
        rate_hz = self.update_rate_spin.value()
        interval_ms = int(1000 / rate_hz)
        self.update_timer.setInterval(interval_ms)

    def toggle_freeze(self):
        """Toggle freeze/unfreeze of measurement display"""
        if self.frozen:
            # Unfreeze: restart timer
            self.frozen = False
            self.freeze_btn.setText("Freeze")
            self.freeze_btn.setStyleSheet("")
            self.update_timer_rate()
            self.update_timer.start()
        else:
            # Freeze: stop timer, hold current values
            self.frozen = True
            self.update_timer.stop()
            self.freeze_btn.setText("Unfreeze")
            self.freeze_btn.setStyleSheet(
                """
                QPushButton {
                    background-color: #3498db;
                    color: white;
                    font-weight: bold;
                    padding: 8px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #2980b9;
                }
            """
            )

    def _on_calibration_changed(self, value: float):
        """Handle manual calibration factor change"""
        if value > 0:
            self.controller.set_calibration_factor(value)
            # Persist to the active laser's QSettings key
            if self.active_laser_number is not None:
                self.settings.setValue(
                    f"laser/calibration_factor_{self.active_laser_number}", value
                )

    def auto_calibrate(self):
        """Auto-calibrate using current meter readings"""
        if self.active_laser_number is None:
            QMessageBox.warning(
                self, "No Laser Active",
                "Turn on a laser before calibrating."
            )
            return
        try:
            factor = self.controller.calibrate_from_measurements()
            self.calibration_spin.blockSignals(True)
            self.calibration_spin.setValue(factor)
            self.calibration_spin.blockSignals(False)
            # Persist to the active laser's QSettings key
            self.settings.setValue(
                f"laser/calibration_factor_{self.active_laser_number}", factor
            )
        except PowerMeterError as e:
            QMessageBox.critical(
                self, "Calibration Error", f"Failed to calibrate:\n{str(e)}"
            )

    def update_readings(self):
        """Update power readings from both meters"""
        try:
            raw_ref, corrected_ref, target_power = self.controller.read_meters()

            # Show corrected reference as main display
            self.ref_display.update_power(corrected_ref)
            self.target_display.update_power(target_power)

            # Show raw reference when calibration is active
            if self.controller.calibration_factor != 1.0 and raw_ref is not None:
                self.ref_display.set_raw_info(raw_ref)
            else:
                self.ref_display.set_raw_info(None)

            # Calculate and display ratio using corrected reference
            if corrected_ref is not None and target_power is not None and corrected_ref > 0:
                ratio = target_power / corrected_ref
                self.ratio_label.setText(f"Target / Reference = {ratio:.6f}")
                self.ratio_percent_label.setText(f"({ratio * 100:.3f} %)")
            else:
                self.ratio_label.setText("Target / Reference = ---")
                self.ratio_percent_label.setText("--- %")

        except Exception as e:
            # Don't pop up error dialogs during continuous reading
            logging.error(f"Error reading power meters: {str(e)}")

    def load_settings(self):
        """Restore power meter settings from QSettings"""
        self.wavelength_spin.setValue(
            self.settings.value("power_meter/wavelength", defaultValue=1310, type=int)
        )
        self.averaging_spin.setValue(
            self.settings.value("power_meter/averaging", defaultValue=1, type=int)
        )
        self.update_rate_spin.setValue(
            self.settings.value("power_meter/update_rate", defaultValue=10.0, type=float)
        )
        # Calibration factor is now per-laser and loaded via
        # set_calibration_factor() when a laser is toggled on
        self._saved_ref_resource = self.settings.value(
            "power_meter/reference_resource", defaultValue="", type=str
        )
        self._saved_target_resource = self.settings.value(
            "power_meter/target_resource", defaultValue="", type=str
        )

    def save_settings(self):
        """Persist current power meter settings to QSettings"""
        self.settings.setValue("power_meter/wavelength", self.wavelength_spin.value())
        self.settings.setValue("power_meter/averaging", self.averaging_spin.value())
        self.settings.setValue("power_meter/update_rate", self.update_rate_spin.value())
        # Calibration factor is saved per-laser in _on_calibration_changed()

        # Save role assignment by VISA resource string when meters are connected
        meters = self.controller.get_power_meters()
        if meters:
            ref_idx = self.ref_combo.currentData()
            target_idx = self.target_combo.currentData()
            if ref_idx is not None and ref_idx < len(meters):
                self.settings.setValue(
                    "power_meter/reference_resource", meters[ref_idx].resource_name
                )
            if target_idx is not None and target_idx < len(meters):
                self.settings.setValue(
                    "power_meter/target_resource", meters[target_idx].resource_name
                )

    def connect_settings_signals(self):
        """Connect widget change signals to save_settings (after initial load)"""
        self.wavelength_spin.valueChanged.connect(self.save_settings)
        self.averaging_spin.valueChanged.connect(self.save_settings)
        self.update_rate_spin.valueChanged.connect(self.save_settings)
        # calibration_spin saves per-laser in _on_calibration_changed()
        self.ref_combo.currentIndexChanged.connect(self.save_settings)
        self.target_combo.currentIndexChanged.connect(self.save_settings)

    def cleanup(self):
        """Clean up resources when closing"""
        self.update_timer.stop()
        self.controller.disconnect_all()
