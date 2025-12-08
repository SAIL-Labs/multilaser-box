"""
Power Meter Tab Widget
PyQt6 widget for viewing and controlling Thorlabs PM100USB power meters

Requirements:
- PyQt6: pip install PyQt6
- pyvisa: pip install pyvisa pyvisa-py

Author: Multi-Laser Box Project
Date: 2025-12-08
"""

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
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from typing import Optional

from power_meter_controller import (
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

    def set_device_info(self, info: str):
        """Set the device information text"""
        self.device_label.setText(info)


class PowerMeterTab(QWidget):
    """Main power meter tab widget"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.controller = PowerMeterController()
        self.available_meters = []
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_readings)

        self.init_ui()

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
        self.wavelength_spin.valueChanged.connect(self.apply_settings)
        settings_layout.addWidget(self.wavelength_spin)

        settings_layout.addSpacing(20)

        # Averaging setting
        settings_layout.addWidget(QLabel("Averaging (samples):"))
        self.averaging_spin = QSpinBox()
        self.averaging_spin.setRange(1, 10000)
        self.averaging_spin.setValue(1)
        self.averaging_spin.setSingleStep(1)
        self.averaging_spin.setEnabled(False)
        self.averaging_spin.valueChanged.connect(self.apply_settings)
        settings_layout.addWidget(self.averaging_spin)

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

        # === Power Readings Section ===
        readings_layout = QHBoxLayout()
        readings_layout.setSpacing(20)

        # Reference power display
        self.ref_display = PowerDisplay("Reference Power")
        readings_layout.addWidget(self.ref_display)

        # Target power display
        self.target_display = PowerDisplay("Target Power")
        readings_layout.addWidget(self.target_display)

        main_layout.addLayout(readings_layout)

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

            if len(self.available_meters) == 0:
                QMessageBox.warning(
                    self,
                    "No Devices Found",
                    "No Thorlabs power meters found.\n\n"
                    "Make sure the devices are connected and drivers are installed.",
                )
                self.status_label.setText("No power meters found")
                self.status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
                self.connect_btn.setEnabled(False)

            elif len(self.available_meters) == 1:
                QMessageBox.warning(
                    self,
                    "Insufficient Devices",
                    f"Found only 1 power meter.\n\n"
                    "This application requires 2 power meters to be connected.",
                )
                self.status_label.setText("Found 1 power meter (need 2)")
                self.status_label.setStyleSheet("color: #e67e22; font-weight: bold;")
                self.connect_btn.setEnabled(False)

            elif len(self.available_meters) == 2:
                self.status_label.setText("Found 2 power meters - ready to connect")
                self.status_label.setStyleSheet("color: #27ae60; font-weight: bold;")
                self.connect_btn.setEnabled(True)

            else:
                QMessageBox.warning(
                    self,
                    "Too Many Devices",
                    f"Found {len(self.available_meters)} power meters.\n\n"
                    "This application requires exactly 2 power meters.\n"
                    "Please disconnect extra devices.",
                )
                self.status_label.setText(f"Found {len(self.available_meters)} power meters (need exactly 2)")
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

            # Populate role selection combo boxes
            meters = self.controller.get_power_meters()
            self.ref_combo.clear()
            self.target_combo.clear()

            for i, pm in enumerate(meters):
                label = f"Meter {i + 1}: {pm.get_short_name()}"
                self.ref_combo.addItem(label, i)
                self.target_combo.addItem(label, i)

            # Set default assignment: Meter 0 = Reference, Meter 1 = Target
            self.ref_combo.setCurrentIndex(0)
            self.target_combo.setCurrentIndex(1)

            # Update role assignment
            self.update_role_assignment()

            # Update device info in displays
            self.ref_display.set_device_info(meters[0].device_info)
            self.target_display.set_device_info(meters[1].device_info)

            # Enable controls
            self.ref_combo.setEnabled(True)
            self.target_combo.setEnabled(True)
            self.wavelength_spin.setEnabled(True)
            self.averaging_spin.setEnabled(True)
            self.update_rate_spin.setEnabled(True)

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

            self.status_label.setText("Connected to 2 power meters")
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
        # Stop timer
        self.update_timer.stop()

        # Disconnect
        self.controller.disconnect_all()

        # Reset UI
        self.ref_combo.clear()
        self.target_combo.clear()
        self.ref_combo.setEnabled(False)
        self.target_combo.setEnabled(False)
        self.wavelength_spin.setEnabled(False)
        self.averaging_spin.setEnabled(False)
        self.update_rate_spin.setEnabled(False)

        self.ref_display.update_power(None)
        self.target_display.update_power(None)
        self.ref_display.set_device_info("Not connected")
        self.target_display.set_device_info("Not connected")

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

        if ref_index is None or target_index is None:
            return

        if ref_index == target_index:
            QMessageBox.warning(
                self,
                "Invalid Assignment",
                "Reference and Target must be different power meters!",
            )
            # Reset to valid assignment
            if ref_index == 0:
                self.target_combo.setCurrentIndex(1)
            else:
                self.target_combo.setCurrentIndex(0)
            return

        try:
            self.controller.assign_roles(ref_index, target_index)

            # Update device info in displays
            meters = self.controller.get_power_meters()
            self.ref_display.set_device_info(meters[ref_index].device_info)
            self.target_display.set_device_info(meters[target_index].device_info)

        except PowerMeterError as e:
            QMessageBox.critical(
                self, "Assignment Error", f"Failed to assign roles:\n{str(e)}"
            )

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

    def update_readings(self):
        """Update power readings from both meters"""
        try:
            ref_power, target_power = self.controller.read_both_meters()

            self.ref_display.update_power(ref_power)
            self.target_display.update_power(target_power)

            # Calculate and display ratio
            if ref_power is not None and target_power is not None and ref_power > 0:
                ratio = target_power / ref_power
                self.ratio_label.setText(f"Target / Reference = {ratio:.6f}")
                self.ratio_percent_label.setText(f"({ratio * 100:.3f} %)")
            else:
                self.ratio_label.setText("Target / Reference = ---")
                self.ratio_percent_label.setText("--- %")

        except Exception as e:
            # Don't pop up error dialogs during continuous reading
            # Just log to console
            print(f"Error reading power meters: {str(e)}")

    def cleanup(self):
        """Clean up resources when closing"""
        self.update_timer.stop()
        self.controller.disconnect_all()
