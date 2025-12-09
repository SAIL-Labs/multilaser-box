"""
SCPI-Compatible Multi-Laser Controller
Provides SCPI command interface for Arduino-based laser control

This module provides a wrapper that communicates with the Arduino using
SCPI (Standard Commands for Programmable Instruments) protocol.

Compatible with:
- Test and measurement software (LabVIEW, MATLAB, Python PyVISA)
- Standard SCPI command sets
- IEEE 488.2 common commands

Author: Chris Betters, Kok-Wei Bong
Date: 2025-12-09
"""

import serial
import time
import logging
from typing import Optional, List, Tuple
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LaserState(Enum):
    """Enum for laser states"""
    OFF = 0
    ON = 1


class SCPIError(Exception):
    """Custom exception for SCPI communication errors"""
    def __init__(self, error_code: int, error_message: str):
        self.error_code = error_code
        self.error_message = error_message
        super().__init__(f"SCPI Error {error_code}: {error_message}")


class MultiLaserControllerSCPI:
    """
    SCPI-compatible controller for Arduino-based multi-laser system.

    Implements SCPI command protocol for standard instrument control.
    """

    def __init__(
        self,
        port: str,
        baud_rate: int = 9600,
        num_lasers: int = 3,
        timeout: float = 2.0,
        auto_connect: bool = True
    ):
        """
        Initialize the SCPI laser controller.

        Args:
            port: Serial port name (e.g., 'COM3', '/dev/ttyUSB0')
            baud_rate: Communication baud rate (default: 9600)
            num_lasers: Number of lasers (1-3, default: 3)
            timeout: Serial communication timeout in seconds
            auto_connect: Automatically connect on initialization
        """
        self.port = port
        self.baud_rate = baud_rate
        self.num_lasers = num_lasers
        self.timeout = timeout
        self.ser: Optional[serial.Serial] = None
        self.connected = False

        # Client-side state tracking
        self._laser_states = [LaserState.OFF] * num_lasers

        if auto_connect:
            self.connect()

    def connect(self):
        """Establish serial connection to the Arduino."""
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baud_rate,
                timeout=self.timeout,
                write_timeout=self.timeout
            )

            # Wait for Arduino to initialize
            time.sleep(2.0)

            # Flush buffers
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()

            # Verify connection with *IDN? query
            idn = self.query("*IDN?")
            logger.info(f"Connected to: {idn}")

            # Reset device to known state
            self.write("*RST")

            # Update client-side state
            self._sync_state()

            self.connected = True
            logger.info(f"Successfully connected to {self.port} at {self.baud_rate} baud")

        except serial.SerialException as e:
            logger.error(f"Failed to connect to {self.port}: {e}")
            raise SCPIError(-1, f"Connection failed: {str(e)}")

    def disconnect(self):
        """Disconnect from the Arduino."""
        if self.ser and self.ser.is_open:
            try:
                # Safety: Turn off all lasers before disconnect
                self.write("*RST")
                time.sleep(0.1)
                self.ser.close()
                logger.info("Disconnected from laser controller")
            except Exception as e:
                logger.error(f"Error during disconnect: {e}")
            finally:
                self.connected = False
                self._laser_states = [LaserState.OFF] * self.num_lasers

    def write(self, command: str):
        """
        Send SCPI command to the device.

        Args:
            command: SCPI command string
        """
        if not self.ser or not self.ser.is_open:
            raise SCPIError(-1, "Not connected")

        try:
            cmd_bytes = (command + '\n').encode('utf-8')
            self.ser.write(cmd_bytes)
            logger.debug(f"Sent: {command}")
        except serial.SerialException as e:
            logger.error(f"Write error: {e}")
            raise SCPIError(-200, f"Communication error: {str(e)}")

    def read(self) -> str:
        """
        Read response from the device.

        Returns:
            Response string (without newline)
        """
        if not self.ser or not self.ser.is_open:
            raise SCPIError(-1, "Not connected")

        try:
            response = self.ser.readline().decode('utf-8').strip()
            logger.debug(f"Received: {response}")
            return response
        except serial.SerialException as e:
            logger.error(f"Read error: {e}")
            raise SCPIError(-200, f"Communication error: {str(e)}")

    def query(self, command: str) -> str:
        """
        Send query and read response.

        Args:
            command: SCPI query string (should end with '?')

        Returns:
            Response string
        """
        self.write(command)
        return self.read()

    def check_errors(self) -> List[Tuple[int, str]]:
        """
        Check and retrieve all errors from error queue.

        Returns:
            List of (error_code, error_message) tuples
        """
        errors = []
        while True:
            try:
                response = self.query("SYST:ERR?")
                # Parse "code,\"message\"" format
                parts = response.split(',', 1)
                error_code = int(parts[0])
                error_msg = parts[1].strip('"') if len(parts) > 1 else "Unknown"

                if error_code == 0:
                    break  # No more errors

                errors.append((error_code, error_msg))
                logger.warning(f"Device error {error_code}: {error_msg}")
            except Exception as e:
                logger.error(f"Error checking error queue: {e}")
                break

        return errors

    # ===== High-Level Laser Control Methods =====

    def set_laser(self, laser_number: int, state: bool):
        """
        Set specific laser to ON or OFF using SCPI command.

        Args:
            laser_number: Laser number (1-3)
            state: True for ON, False for OFF
        """
        if laser_number < 1 or laser_number > self.num_lasers:
            raise ValueError(f"Invalid laser number: {laser_number}")

        state_str = "ON" if state else "OFF"
        self.write(f"SOUR{laser_number}:STAT {state_str}")

        # Update client-side state
        self._laser_states[laser_number - 1] = LaserState.ON if state else LaserState.OFF
        logger.info(f"Laser {laser_number} set to {state_str}")

    def get_laser_state(self, laser_number: int) -> LaserState:
        """
        Query laser state from device.

        Args:
            laser_number: Laser number (1-3)

        Returns:
            LaserState.ON or LaserState.OFF
        """
        if laser_number < 1 or laser_number > self.num_lasers:
            raise ValueError(f"Invalid laser number: {laser_number}")

        response = self.query(f"SOUR{laser_number}:STAT?")
        state = LaserState.ON if response == "1" else LaserState.OFF

        # Update client-side state
        self._laser_states[laser_number - 1] = state
        return state

    def turn_on_laser(self, laser_number: int):
        """Turn on specific laser."""
        self.set_laser(laser_number, True)

    def turn_off_laser(self, laser_number: int):
        """Turn off specific laser."""
        self.set_laser(laser_number, False)

    def toggle_laser(self, laser_number: int):
        """Toggle specific laser state."""
        current_state = self._laser_states[laser_number - 1]
        new_state = LaserState.OFF if current_state == LaserState.ON else LaserState.ON
        self.set_laser(laser_number, new_state == LaserState.ON)

    def turn_on_all(self):
        """Turn on all lasers."""
        self.write("ALL_ON")
        self._laser_states = [LaserState.ON] * self.num_lasers
        logger.info("All lasers turned ON")

    def turn_off_all(self):
        """Turn off all lasers."""
        self.write("ALL_OFF")
        self._laser_states = [LaserState.OFF] * self.num_lasers
        logger.info("All lasers turned OFF")

    def emergency_stop(self):
        """Emergency stop - reset device (turns off all lasers)."""
        self.write("*RST")
        self._laser_states = [LaserState.OFF] * self.num_lasers
        logger.warning("EMERGENCY STOP executed")

    def get_all_states(self) -> List[LaserState]:
        """
        Query all laser states at once.

        Returns:
            List of LaserState values
        """
        response = self.query("STAT?")
        states = response.split(',')

        result = []
        for i, state_str in enumerate(states[:self.num_lasers]):
            state = LaserState.ON if state_str == "1" else LaserState.OFF
            result.append(state)
            if i < len(self._laser_states):
                self._laser_states[i] = state

        return result

    def _sync_state(self):
        """Synchronize client-side state with device."""
        try:
            self.get_all_states()
        except Exception as e:
            logger.warning(f"Failed to sync state: {e}")

    # ===== IEEE 488.2 Common Commands =====

    def identify(self) -> str:
        """Get device identification string."""
        return self.query("*IDN?")

    def reset(self):
        """Reset device to default state."""
        self.write("*RST")
        self._laser_states = [LaserState.OFF] * self.num_lasers

    def clear_status(self):
        """Clear status registers and error queue."""
        self.write("*CLS")

    def operation_complete(self) -> bool:
        """Check if operation is complete."""
        response = self.query("*OPC?")
        return response == "1"

    def get_scpi_version(self) -> str:
        """Get SCPI version."""
        return self.query("SYST:VERS?")

    # ===== Context Manager Support =====

    def __enter__(self):
        """Context manager entry."""
        if not self.connected:
            self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
        return False


# Example usage
if __name__ == "__main__":
    # Example with context manager
    with MultiLaserControllerSCPI(port='/dev/ttyUSB0', num_lasers=3) as controller:
        # Get device info
        print(f"Device: {controller.identify()}")
        print(f"SCPI Version: {controller.get_scpi_version()}")

        # Control lasers using SCPI commands
        controller.turn_on_laser(1)
        time.sleep(1)

        state = controller.get_laser_state(1)
        print(f"Laser 1 state: {state}")

        controller.turn_off_all()

        # Check for errors
        errors = controller.check_errors()
        if errors:
            print(f"Errors detected: {errors}")
