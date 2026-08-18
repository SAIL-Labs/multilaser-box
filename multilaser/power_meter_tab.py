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
import math
from collections import deque
from datetime import datetime
from pathlib import Path

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
    QFileDialog,
    QDialog,
    QDialogButtonBox,
    QCheckBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
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
from multilaser.measurement_logger import (
    MeasurementLogger,
    MeasurementLogError,
    OPENPYXL_AVAILABLE,
)


class MeterSelectionDialog(QDialog):
    """Dialog to choose which power meters to use when more than two are found"""

    MAX_SELECTED = 2

    def __init__(self, resources, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Power Meters")
        layout = QVBoxLayout(self)

        layout.addWidget(
            QLabel(
                f"{len(resources)} power meters were detected.\n"
                f"Select up to {self.MAX_SELECTED} to use:"
            )
        )

        self._checkboxes = []
        for resource in resources:
            checkbox = QCheckBox(resource)
            checkbox.toggled.connect(self._update_ok_button)
            layout.addWidget(checkbox)
            self._checkboxes.append(checkbox)

        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)
        layout.addWidget(self._buttons)

        self._update_ok_button()

    def selected_resources(self):
        """Return the resource names of the checked meters"""
        return [cb.text() for cb in self._checkboxes if cb.isChecked()]

    def _update_ok_button(self):
        count = len(self.selected_resources())
        ok_button = self._buttons.button(QDialogButtonBox.StandardButton.Ok)
        ok_button.setEnabled(1 <= count <= self.MAX_SELECTED)


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
        self._updating_roles = False  # Flag to prevent signal loops
        self.measurement_log: Optional[MeasurementLogger] = None
        self._last_corrected_ref: Optional[float] = None
        self._last_target_power: Optional[float] = None
        # Rolling buffers of recent displayed readings; logged measurements
        # are the average of these (see log_measurement)
        self._ref_history: deque = deque(maxlen=10)
        self._target_history: deque = deque(maxlen=10)
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
        # Connect signal later to avoid loops during initialization
        role_layout.addWidget(self.ref_combo)

        role_layout.addSpacing(20)

        role_layout.addWidget(QLabel("Target Meter:"))
        self.target_combo = QComboBox()
        self.target_combo.setEnabled(False)
        # Connect signal later to avoid loops during initialization
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

        # === Measurement Logging Section ===
        logging_group = QGroupBox("Measurement Logging")
        logging_layout = QVBoxLayout()

        # Log file selection row
        file_row = QHBoxLayout()

        self.new_log_btn = QPushButton("New Log File…")
        self.new_log_btn.setToolTip(
            "Create a new log file.\n"
            "Excel logs are created from the throughput template\n"
            "(Trial / Port / injection power / lantern output power)."
        )
        self.new_log_btn.clicked.connect(self.new_log_file)
        file_row.addWidget(self.new_log_btn)

        self.open_log_btn = QPushButton("Append to Existing…")
        self.open_log_btn.setToolTip("Continue logging into an existing .xlsx or .csv file")
        self.open_log_btn.clicked.connect(self.open_log_file)
        file_row.addWidget(self.open_log_btn)

        self.log_file_label = QLabel("No log file selected")
        self.log_file_label.setStyleSheet("color: #7f8c8d; font-style: italic;")
        file_row.addWidget(self.log_file_label)

        file_row.addStretch()
        logging_layout.addLayout(file_row)

        # Log measurement row
        log_row = QHBoxLayout()

        port_label = QLabel("Port:")
        port_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        log_row.addWidget(port_label)
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 99)
        self.port_spin.setValue(1)
        self.port_spin.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.port_spin.setMinimumWidth(70)
        self.port_spin.setMinimumHeight(36)
        self.port_spin.setToolTip("Lantern port number recorded with each measurement")
        log_row.addWidget(self.port_spin)

        log_row.addSpacing(20)

        log_row.addWidget(QLabel("Average over:"))
        self.log_avg_spin = QSpinBox()
        self.log_avg_spin.setRange(1, 100)
        self.log_avg_spin.setValue(10)
        self.log_avg_spin.setSuffix(" readings")
        self.log_avg_spin.setToolTip(
            "Each logged measurement is the average of this many recent\n"
            "display readings (at the current update rate)"
        )
        self.log_avg_spin.valueChanged.connect(self._on_log_avg_changed)
        log_row.addWidget(self.log_avg_spin)

        log_row.addSpacing(20)

        self.log_btn = QPushButton("Log Measurement")
        self.log_btn.setMinimumWidth(180)
        self.log_btn.setMinimumHeight(40)
        self.log_btn.setEnabled(False)
        self.log_btn.setToolTip(
            "Record the average of the recent readings to the log file:\n"
            "injection power = corrected reference, output power = target"
        )
        self.log_btn.clicked.connect(self.log_measurement)
        self.log_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #27ae60;
                color: white;
                font-weight: bold;
                font-size: 14px;
                padding: 8px 16px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """
        )
        log_row.addWidget(self.log_btn)

        self.log_status_label = QLabel("")
        self.log_status_label.setStyleSheet("color: #27ae60;")
        log_row.addWidget(self.log_status_label)

        log_row.addStretch()
        logging_layout.addLayout(log_row)

        logging_group.setLayout(logging_layout)
        main_layout.addWidget(logging_group)

        main_layout.addStretch()

        # === Side-by-side layout: controls on the left, measurement table on the right ===
        controls_widget = QWidget()
        controls_widget.setLayout(main_layout)

        outer_layout = QHBoxLayout()
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)
        outer_layout.addWidget(controls_widget, stretch=3)
        outer_layout.addWidget(self._create_measurement_table_panel(), stretch=2)

        self.setLayout(outer_layout)

        # Connect role combo signals after UI initialization to avoid loops
        self.ref_combo.currentIndexChanged.connect(self.update_role_assignment)
        self.target_combo.currentIndexChanged.connect(self.update_role_assignment)

    def _create_measurement_table_panel(self) -> QGroupBox:
        """Create the logged-measurements table shown beside the controls"""
        panel = QGroupBox("Logged Measurements")
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        self.measurement_table = QTableWidget(0, 6)
        self.measurement_table.setHorizontalHeaderLabels(
            ["Trial", "Port", "Injection", "Output", "Throughput", "Loss (dB)"]
        )
        self.measurement_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.measurement_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.measurement_table.setAlternatingRowColors(True)
        self.measurement_table.verticalHeader().setVisible(False)
        header = self.measurement_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.measurement_table)

        self.table_summary_label = QLabel("No measurements")
        self.table_summary_label.setStyleSheet("color: #7f8c8d; font-style: italic;")
        layout.addWidget(self.table_summary_label)

        panel.setLayout(layout)
        return panel

    def _append_table_row(self, trial, port, injection_w, output_w):
        """Add one measurement row to the table"""
        throughput = loss_db = None
        if (
            isinstance(injection_w, (int, float))
            and isinstance(output_w, (int, float))
            and injection_w > 0
        ):
            throughput = output_w / injection_w
            if throughput > 0:
                loss_db = 10.0 * math.log10(throughput)

        def power_text(value):
            if isinstance(value, (int, float)):
                return format_power_auto_scale(value)
            return "---"

        values = [
            str(trial) if trial is not None else "",
            str(port) if port is not None else "",
            power_text(injection_w),
            power_text(output_w),
            f"{throughput * 100:.1f} %" if throughput is not None else "---",
            f"{loss_db:.2f}" if loss_db is not None else "---",
        ]

        row = self.measurement_table.rowCount()
        self.measurement_table.insertRow(row)
        for col, text in enumerate(values):
            item = QTableWidgetItem(text)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.measurement_table.setItem(row, col, item)

        self.measurement_table.scrollToBottom()
        self._update_table_summary()

    def _update_table_summary(self):
        count = self.measurement_table.rowCount()
        if count == 0:
            self.table_summary_label.setText("No measurements")
        else:
            self.table_summary_label.setText(f"{count} measurement(s)")

    def _reload_measurement_table(self):
        """Rebuild the table from the current log file (empty if none)"""
        self.measurement_table.setRowCount(0)
        if self.measurement_log is not None:
            try:
                for trial, port, injection, output in (
                    self.measurement_log.read_measurements()
                ):
                    self._append_table_row(trial, port, injection, output)
            except MeasurementLogError as e:
                logging.getLogger(__name__).warning(
                    f"Could not read existing measurements: {e}"
                )
        self._update_table_summary()

    def scan_power_meters(self):
        """Scan for available power meters"""
        try:
            self.available_meters = self.controller.find_power_meters()
            count = len(self.available_meters)

            if count == 0:
                reply = QMessageBox.question(
                    self,
                    "No Devices Found",
                    "No Thorlabs power meters found.\n\n"
                    "Make sure the devices are connected and drivers are installed.\n\n"
                    "Use simulated power meters instead (for testing without hardware)?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self.available_meters = self.controller.simulated_resources()
                    self.status_label.setText(
                        "Simulation mode - 2 simulated meters ready to connect"
                    )
                    self.status_label.setStyleSheet("color: #f39c12; font-weight: bold;")
                    self.connect_btn.setEnabled(True)
                else:
                    self.status_label.setText("No power meters found")
                    self.status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
                    self.connect_btn.setEnabled(False)

            elif count in [1, 2]:
                self.status_label.setText(f"Found {count} power meter(s) - ready to connect")
                self.status_label.setStyleSheet("color: #27ae60; font-weight: bold;")
                self.connect_btn.setEnabled(True)

            else:
                dialog = MeterSelectionDialog(self.available_meters, self)
                if dialog.exec():
                    self.available_meters = dialog.selected_resources()
                    selected = len(self.available_meters)
                    self.status_label.setText(
                        f"Selected {selected} of {count} power meters - ready to connect"
                    )
                    self.status_label.setStyleSheet("color: #27ae60; font-weight: bold;")
                    self.connect_btn.setEnabled(True)
                else:
                    self.status_label.setText(
                        f"Found {count} power meters - none selected (scan again to choose)"
                    )
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

            simulated = any(
                self.controller.is_simulated_resource(pm.resource_name)
                for pm in meters
            )
            if simulated:
                self.status_label.setText(
                    f"Connected to {num_meters} SIMULATED power meter(s)"
                )
                self.status_label.setStyleSheet("color: #f39c12; font-weight: bold;")
            else:
                self.status_label.setText(f"Connected to {num_meters} power meter(s)")
                self.status_label.setStyleSheet("color: #27ae60; font-weight: bold;")

            self._update_log_controls()

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

        self._last_corrected_ref = None
        self._last_target_power = None
        self._clear_reading_history()
        self._update_log_controls()

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

        # Prevent signal loops
        if self._updating_roles:
            return
        self._updating_roles = True

        try:
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
                other = 1 if ref_index == 0 else 0
                # Find combo index for that meter index
                for i in range(self.target_combo.count()):
                    if self.target_combo.itemData(i) == other:
                        self.target_combo.setCurrentIndex(i)
                        break
                target_index = other

            try:
                self.controller.assign_roles(ref_index, target_index)
                # Buffered readings came from the previous role assignment
                self._clear_reading_history()

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
        finally:
            self._updating_roles = False

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

        # Pause readings while we write settings to avoid VISA I/O conflicts
        was_running = self.update_timer.isActive()
        self.update_timer.stop()

        error = None
        try:
            for pm in self.controller.get_power_meters():
                pm.set_wavelength(wavelength)
                pm.set_averaging(averaging)
        except PowerMeterError as e:
            error = e
        finally:
            # Always restart timer before showing error dialog
            if was_running:
                self.update_timer.start()

        # Show error dialog after timer is restarted
        if error:
            QMessageBox.critical(
                self, "Settings Error", f"Failed to apply settings:\n{str(error)}"
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

    def _clear_reading_history(self, ref: bool = True, target: bool = True):
        """Drop buffered readings that no longer reflect the current setup"""
        if ref:
            self._ref_history.clear()
        if target:
            self._target_history.clear()

    def _on_log_avg_changed(self, value: int):
        """Resize the averaging buffers, keeping the most recent readings"""
        self._ref_history = deque(self._ref_history, maxlen=value)
        self._target_history = deque(self._target_history, maxlen=value)
        self.settings.setValue("power_meter/log_averaging", value)

    def _on_calibration_changed(self, value: float):
        """Handle manual calibration factor change"""
        if value > 0:
            self.controller.set_calibration_factor(value)
            # Buffered corrected-reference readings used the old factor
            self._clear_reading_history(ref=True, target=False)
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
            # Buffered corrected-reference readings used the old factor
            self._clear_reading_history(ref=True, target=False)
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

            # Remember latest readings for measurement logging
            # (frozen display holds these values since the timer is stopped)
            self._last_corrected_ref = corrected_ref
            self._last_target_power = target_power
            if corrected_ref is not None:
                self._ref_history.append(corrected_ref)
            if target_power is not None:
                self._target_history.append(target_power)

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

    def _log_file_filters(self) -> str:
        """File dialog filters for log files (Excel only when openpyxl available)"""
        if OPENPYXL_AVAILABLE:
            return "Excel Workbook (*.xlsx);;CSV File (*.csv)"
        return "CSV File (*.csv)"

    def _log_start_dir(self) -> str:
        """Initial directory for log file dialogs"""
        if self.measurement_log is not None:
            return str(self.measurement_log.file_path.parent)
        return self.settings.value(
            "power_meter/log_dir", defaultValue=str(Path.home()), type=str
        )

    def new_log_file(self):
        """Create a new measurement log file (Excel from template, or CSV)"""
        path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "New Measurement Log",
            self._log_start_dir(),
            self._log_file_filters(),
        )
        if not path:
            return

        # Add extension if the user didn't type one
        if not Path(path).suffix:
            path += ".csv" if "CSV" in selected_filter else ".xlsx"

        try:
            log = MeasurementLogger(path)
            log.create_new(wavelength_nm=self.wavelength_spin.value())
        except MeasurementLogError as e:
            QMessageBox.critical(
                self, "Logging Error", f"Failed to create log file:\n{str(e)}"
            )
            return

        self._set_log_file(log)

    def open_log_file(self):
        """Select an existing log file to append measurements to"""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Append to Measurement Log",
            self._log_start_dir(),
            self._log_file_filters(),
        )
        if not path:
            return

        try:
            log = MeasurementLogger(path)
        except MeasurementLogError as e:
            QMessageBox.critical(self, "Logging Error", str(e))
            return

        self._set_log_file(log)

    def _set_log_file(self, log: Optional[MeasurementLogger]):
        """Set the active log file and update UI/settings"""
        self.measurement_log = log
        if log is not None:
            self.log_file_label.setText(log.file_path.name)
            self.log_file_label.setToolTip(str(log.file_path))
            self.log_file_label.setStyleSheet("color: #2c3e50; font-weight: bold;")
            self.settings.setValue("power_meter/log_file", str(log.file_path))
            self.settings.setValue("power_meter/log_dir", str(log.file_path.parent))
        else:
            self.log_file_label.setText("No log file selected")
            self.log_file_label.setToolTip("")
            self.log_file_label.setStyleSheet("color: #7f8c8d; font-style: italic;")
            self.settings.setValue("power_meter/log_file", "")
        self.log_status_label.setText("")
        self._reload_measurement_table()
        self._update_log_controls()

    def _update_log_controls(self):
        """Enable the log button only when connected with a log file selected"""
        connected = bool(self.controller.get_power_meters())
        self.log_btn.setEnabled(connected and self.measurement_log is not None)

    def log_measurement(self):
        """Record the averaged recent readings to the measurement log.

        Injection power = corrected reference power, lantern output power =
        target power. Each value is the average of the buffered recent
        display readings (up to the "Average over" count). When frozen, the
        readings buffered before the freeze are logged.
        """
        if self.measurement_log is None:
            return

        injection = (
            sum(self._ref_history) / len(self._ref_history)
            if self._ref_history
            else None
        )
        output = (
            sum(self._target_history) / len(self._target_history)
            if self._target_history
            else None
        )

        if injection is None and output is None:
            QMessageBox.warning(
                self,
                "No Readings",
                "No power readings available to log yet.",
            )
            return

        port = self.port_spin.value()
        try:
            trial = self.measurement_log.append_measurement(
                port=port,
                injection_power_w=injection,
                output_power_w=output,
                wavelength_nm=self.wavelength_spin.value(),
            )
        except MeasurementLogError as e:
            QMessageBox.critical(self, "Logging Error", str(e))
            return

        self._append_table_row(trial, port, injection, output)

        navg = max(len(self._ref_history), len(self._target_history))
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_status_label.setText(
            f"Logged trial {trial} (port {port}, avg of {navg} readings) at {timestamp}"
        )
        self.settings.setValue("power_meter/log_port", port)

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

        # Restore measurement log file if it still exists
        self.port_spin.setValue(
            self.settings.value("power_meter/log_port", defaultValue=1, type=int)
        )
        self.log_avg_spin.setValue(
            self.settings.value("power_meter/log_averaging", defaultValue=10, type=int)
        )
        saved_log = self.settings.value(
            "power_meter/log_file", defaultValue="", type=str
        )
        if saved_log and Path(saved_log).exists():
            try:
                self._set_log_file(MeasurementLogger(saved_log))
            except MeasurementLogError:
                pass  # e.g. openpyxl no longer installed

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
