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

import sys
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
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
import serial.tools.list_ports
from typing import List

# Import the MultiLaserController class
from multilaser.laser_controller import MultiLaserController, LaserControllerError, LaserState

# Import the PowerMeterTab
try:
    from multilaser.power_meter_tab import PowerMeterTab
    POWER_METER_AVAILABLE = True
except ImportError:
    POWER_METER_AVAILABLE = False
    print("Warning: Power meter tab not available. Install pyvisa and pyvisa-py to enable.")


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
        self.controller = None
        self.num_lasers = 3

        # Store LED indicators and toggle buttons
        self.led_indicators = []
        self.toggle_buttons = []

        # Power meter tab reference
        self.power_meter_tab = None

        self.init_ui()
        self.populate_com_ports()

    def init_ui(self):
        """Initialise the user interface"""
        self.setWindowTitle("Multi-Laser Controller")
        self.setGeometry(100, 100, 800, 600)

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
            self.power_meter_tab = PowerMeterTab()
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

            # Label below LED
            label = QLabel(f"Laser {i}")
            label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
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

        # All On button
        self.all_on_btn = QPushButton("All ON")
        self.all_on_btn.setMinimumSize(120, 40)
        self.all_on_btn.setEnabled(False)
        self.all_on_btn.clicked.connect(self.turn_all_on)
        self.all_on_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #4CAF50;
                color: white;
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
        extra_controls_layout.addWidget(self.all_on_btn)

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

        # Emergency stop button
        self.emergency_btn = QPushButton("⚠ EMERGENCY STOP")
        self.emergency_btn.setMinimumSize(160, 40)
        self.emergency_btn.setEnabled(False)
        self.emergency_btn.clicked.connect(self.emergency_stop)
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
            self.all_on_btn.setEnabled(True)
            self.all_off_btn.setEnabled(True)
            self.emergency_btn.setEnabled(True)

            # Disable connection settings
            self.port_combo.setEnabled(False)
            self.baud_combo.setEnabled(False)
            self.refresh_btn.setEnabled(False)

            self.statusBar().showMessage(f"Connected to {port} at {baud_rate} baud")

            # Update LED indicators
            self.update_led_states()

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
        self.all_on_btn.setEnabled(False)
        self.all_off_btn.setEnabled(False)
        self.emergency_btn.setEnabled(False)

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

        try:
            # # Turn off all lasers first TODO: debug turn_on_laser
            # self.controller.turn_off_all()
            # # Turn on the requested laser
            # self.controller.turn_on_laser(laser_number)
            # self.update_led_states()
            # self.statusBar().showMessage(f"Laser {laser_number} ON (all others OFF)")

            self.controller.toggle_laser(laser_number)
            self.update_led_states()
            self.statusBar().showMessage(f"Toggled Laser {laser_number}")

        except Exception as e:
            QMessageBox.critical(
                self, "Control Error", f"Failed to control laser:\n{str(e)}"
            )

    def turn_all_on(self):
        """Turn all lasers on"""
        if not self.controller or not self.controller.connected:
            return

        try:
            self.controller.turn_on_all()
            self.update_led_states()
            self.statusBar().showMessage("All lasers turned ON")
        except Exception as e:
            QMessageBox.critical(
                self, "Control Error", f"Failed to turn on all lasers:\n{str(e)}"
            )

    def turn_all_off(self):
        """Turn all lasers off"""
        if not self.controller or not self.controller.connected:
            return

        try:
            self.controller.turn_off_all()
            self.update_led_states()
            self.statusBar().showMessage("All lasers turned OFF")
        except Exception as e:
            QMessageBox.critical(
                self, "Control Error", f"Failed to turn off all lasers:\n{str(e)}"
            )

    def emergency_stop(self):
        """Emergency stop - turn off all lasers immediately"""
        if not self.controller or not self.controller.connected:
            return

        reply = QMessageBox.question(
            self,
            "Emergency Stop",
            "Turn off all lasers immediately?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.controller.emergency_stop()
                self.update_led_states()
                self.statusBar().showMessage(
                    "EMERGENCY STOP ACTIVATED - All lasers OFF"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Emergency Stop Error",
                    f"Failed to execute emergency stop:\n{str(e)}",
                )

    def update_led_states(self):
        """Update all LED indicators based on controller state"""
        if not self.controller or not self.controller.connected:
            return

        for i, led in enumerate(self.led_indicators, start=1):
            state = self.controller.get_laser_state(i)
            led.set_state(state == LaserState.ON)

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
