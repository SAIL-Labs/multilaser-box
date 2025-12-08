"""
Multi-Laser Controller Python Class
Interfaces with Arduino-based laser TTL control system via serial communication

Requirements:
- pyserial: pip install pyserial
- Arduino running the provided laser control firmware

Author: Kok-Wei Bong
Date: 2025-09-19
"""

import serial
import time
from typing import Dict, Optional, Union
from enum import Enum
import logging


class LaserState(Enum):
    """Enumeration for laser states"""

    OFF = False
    ON = True


class LaserControllerError(Exception):
    """Custom exception for laser controller errors"""

    pass


class MultiLaserController:
    """
    Python class for controlling multiple lasers through Arduino MCU

    Simple state tracking - lasers only change state when explicitly toggled.
    No polling or background updates needed.
    """

    def __init__(
        self,
        port: str,
        baud_rate: int = 9600,
        timeout: float = 2.0,
        num_lasers: int = 3,
        auto_connect: bool = True,
    ):
        """
        Initialise the MultiLaserController

        Args:
            port: Serial port name (e.g., 'COM3' on Windows, '/dev/ttyUSB0' on Linux)
            baud_rate: Serial communication baud rate (default: 9600)
            timeout: Serial read timeout in seconds (default: 2.0)
            num_lasers: Number of lasers connected to the Arduino (default: 3)
            auto_connect: Whether to automatically connect on initialisation
        """
        self.port = port
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.num_lasers = num_lasers

        # Serial connection
        self.serial_conn: Optional[serial.Serial] = None
        self.connected = False

        # State tracking - assume all lasers start OFF
        self.laser_states: Dict[int, LaserState] = {}
        for i in range(1, num_lasers + 1):
            self.laser_states[i] = LaserState.OFF

        # Logging setup
        self.logger = logging.getLogger(__name__)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

        if auto_connect:
            self.connect()

    def connect(self) -> bool:
        """
        Establish serial connection to the Arduino

        Returns:
            bool: True if connection successful, False otherwise

        Raises:
            LaserControllerError: If connection fails
        """
        try:
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baud_rate,
                timeout=self.timeout,
                write_timeout=self.timeout,
            )

            # Wait for Arduino to initialise
            time.sleep(2)

            # Flush any initial data
            self.serial_conn.reset_input_buffer()
            self.serial_conn.reset_output_buffer()

            # Test connection
            if self.serial_conn.is_open:
                self.connected = True
                self.logger.info(f"Connected to laser controller on {self.port}")

                # Ensure all lasers are OFF on startup
                self.turn_off_all()
                return True
            else:
                raise LaserControllerError("Failed to open serial connection")

        except serial.SerialException as e:
            self.logger.error(f"Serial connection failed: {e}")
            raise LaserControllerError(f"Could not connect to {self.port}: {e}")

    def disconnect(self) -> None:
        """Close the serial connection"""
        if self.serial_conn and self.serial_conn.is_open:
            # Turn off all lasers before disconnecting
            try:
                self.turn_off_all()
            except:
                pass  # Ignore errors during cleanup

            self.serial_conn.close()
            self.connected = False
            self.logger.info("Disconnected from laser controller")

    def _send_command(self, command: str) -> bool:
        """
        Send a command to the Arduino

        Args:
            command: Command string to send

        Returns:
            bool: True if command sent successfully, False otherwise
        """
        if not self.connected or not self.serial_conn:
            raise LaserControllerError("Not connected to laser controller")

        try:
            # Send command
            command_bytes = (command + "\n").encode("utf-8")
            self.serial_conn.write(command_bytes)
            self.serial_conn.flush()

            self.logger.debug(f"Sent command: {command}")
            return True

        except serial.SerialException as e:
            self.logger.error(f"Communication error: {e}")
            return False

    def toggle_laser(self, laser_number: int) -> bool:
        """
        Toggle a specific laser on/off

        Args:
            laser_number: Laser number (1-based index)

        Returns:
            bool: True if command successful, False otherwise
        """
        if not (1 <= laser_number <= self.num_lasers):
            raise ValueError(f"Laser number must be between 1 and {self.num_lasers}")

        if self._send_command(str(laser_number)):
            # Update local state - toggle current state
            current_state = self.laser_states[laser_number]
            new_state = (
                LaserState.OFF if current_state == LaserState.ON else LaserState.ON
            )
            self.laser_states[laser_number] = new_state

            self.logger.info(f"Laser {laser_number} toggled to {new_state.name}")
            return True
        return False

    def set_laser(self, laser_number: int, state: Union[bool, LaserState]) -> bool:
        """
        Set a specific laser to a desired state

        Args:
            laser_number: Laser number (1-based index)
            state: Desired state (True/False or LaserState.ON/OFF)

        Returns:
            bool: True if command successful, False otherwise
        """
        if isinstance(state, LaserState):
            target_state = state
        else:
            target_state = LaserState.ON if state else LaserState.OFF

        current_state = self.laser_states[laser_number]

        # Only toggle if current state differs from target
        if current_state != target_state:
            return self.toggle_laser(laser_number)

        return True  # Already in desired state

    def turn_on_laser(self, laser_number: int) -> bool:
        """Turn on a specific laser"""
        return self.set_laser(laser_number, LaserState.ON)

    def turn_off_laser(self, laser_number: int) -> bool:
        """Turn off a specific laser"""
        return self.set_laser(laser_number, LaserState.OFF)

    def turn_on_all(self) -> bool:
        """Turn on all lasers"""
        if self._send_command("all_on"):
            # Update all local states to ON
            for i in range(1, self.num_lasers + 1):
                self.laser_states[i] = LaserState.ON
            self.logger.info("All lasers turned ON")
            return True
        return False

    def turn_off_all(self) -> bool:
        """Turn off all lasers"""
        if self._send_command("all_off"):
            # Update all local states to OFF
            for i in range(1, self.num_lasers + 1):
                self.laser_states[i] = LaserState.OFF
            self.logger.info("All lasers turned OFF")
            return True
        return False

    def get_laser_state(self, laser_number: int) -> LaserState:
        """
        Get current state of a specific laser

        Args:
            laser_number: Laser number (1-based index)

        Returns:
            LaserState: Current laser state
        """
        if not (1 <= laser_number <= self.num_lasers):
            raise ValueError(f"Laser number must be between 1 and {self.num_lasers}")

        return self.laser_states[laser_number]

    def get_all_laser_states(self) -> Dict[int, LaserState]:
        """
        Get current states of all lasers

        Returns:
            Dict[int, LaserState]: Dictionary mapping laser numbers to states
        """
        return self.laser_states.copy()

    def flash_laser(
        self, laser_number: int, flash_count: int = 3, flash_duration: float = 0.5
    ) -> bool:
        """
        Flash a laser a specified number of times

        Args:
            laser_number: Laser to flash
            flash_count: Number of flashes
            flash_duration: Duration of each flash in seconds

        Returns:
            bool: True if successful
        """
        if not (1 <= laser_number <= self.num_lasers):
            raise ValueError(f"Laser number must be between 1 and {self.num_lasers}")

        try:
            original_state = self.get_laser_state(laser_number)

            for _ in range(flash_count):
                self.turn_on_laser(laser_number)
                time.sleep(flash_duration)
                self.turn_off_laser(laser_number)
                time.sleep(flash_duration)

            # Restore original state
            if original_state == LaserState.ON:
                self.turn_on_laser(laser_number)

            self.logger.info(f"Flashed laser {laser_number} {flash_count} times")
            return True
        except Exception as e:
            self.logger.error(f"Flash sequence failed: {e}")
            return False

    def sequential_pattern(self, delay_seconds: float = 1.0, cycles: int = 1) -> bool:
        """
        Run a sequential pattern through all lasers

        Args:
            delay_seconds: Delay between laser switches
            cycles: Number of complete cycles to run

        Returns:
            bool: True if successful
        """
        try:
            for cycle in range(cycles):
                self.logger.info(f"Sequential pattern cycle {cycle + 1}/{cycles}")

                for laser_num in range(1, self.num_lasers + 1):
                    self.turn_off_all()
                    time.sleep(0.1)  # Brief pause
                    self.turn_on_laser(laser_num)
                    time.sleep(delay_seconds)

                self.turn_off_all()
                if cycle < cycles - 1:  # Don't delay after last cycle
                    time.sleep(delay_seconds)

            return True
        except Exception as e:
            self.logger.error(f"Sequential pattern failed: {e}")
            return False

    def emergency_stop(self) -> bool:
        """Emergency stop - turn off all lasers immediately"""
        try:
            self.turn_off_all()
            self.logger.warning("Emergency stop activated - all lasers off")
            return True
        except Exception as e:
            self.logger.error(f"Emergency stop failed: {e}")
            return False

    def __enter__(self):
        """Context manager entry"""
        if not self.connected:
            self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensure all lasers are off"""
        try:
            self.emergency_stop()
        finally:
            self.disconnect()

    def __repr__(self) -> str:
        """String representation of the controller"""
        status = "Connected" if self.connected else "Disconnected"
        return f"MultiLaserController(port='{self.port}', lasers={self.num_lasers}, status='{status}')"


# Example usage
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)

    try:
        # Create controller instance (adjust port as needed)
        # Windows: 'COM3', 'COM4', etc.
        # Linux/Mac: '/dev/ttyUSB0', '/dev/ttyACM0', etc.
        controller = MultiLaserController(
            port="/dev/ttyUSB0",  # Adjust this to your Arduino's port
            num_lasers=3,
            auto_connect=False,
        )

        # Using context manager for automatic cleanup
        with controller:
            print("Laser Controller Connected!")
            print(f"Controller: {controller}")

            # Check initial states (should all be OFF)
            print(f"\nInitial laser states:")
            for laser_num in range(1, controller.num_lasers + 1):
                state = controller.get_laser_state(laser_num)
                print(f"  Laser {laser_num}: {state.name}")

            # Turn on each laser individually
            for laser_num in range(1, controller.num_lasers + 1):
                print(f"Turning on laser {laser_num}")
                controller.turn_on_laser(laser_num)
                print(f"  State: {controller.get_laser_state(laser_num).name}")
                time.sleep(1)

            time.sleep(2)

            # Turn off all lasers
            print("Turning off all lasers")
            controller.turn_off_all()

            # Verify all are off
            all_states = controller.get_all_laser_states()
            print(f"Final states: {[(k, v.name) for k, v in all_states.items()]}")

            print("Demo completed successfully!")

    except LaserControllerError as e:
        print(f"Laser controller error: {e}")
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    except Exception as e:
        print(f"Unexpected error: {e}")
