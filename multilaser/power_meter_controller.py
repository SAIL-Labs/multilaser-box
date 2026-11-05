"""
Thorlabs PM100USB Power Meter Controller
Provides interface for controlling Thorlabs PM100USB power meters using PyVISA

Requirements:
- pyvisa: pip install pyvisa
- pyvisa-py: pip install pyvisa-py (for pure Python backend)

Author: Based on Thorlabs PMxxx_SCPI examples
Date: 2025-12-08
"""

from __future__ import annotations

import logging
import math
import os
import random
import threading
import time
from dataclasses import dataclass
from typing import Optional, List, Tuple
from enum import Enum


def format_power_auto_scale(power_watts: float) -> str:
    """
    Format power value with automatic unit scaling.

    Selects the most appropriate unit (W, mW, µW, nW) to display
    values in the 1-999 range before the decimal point.

    Args:
        power_watts: Power value in Watts

    Returns:
        Formatted string with value and unit (e.g., "125.3 mW")
    """
    if power_watts is None:
        return "--- W"

    abs_power = abs(power_watts)

    # Select appropriate unit based on magnitude
    if abs_power >= 1.0:
        # Display in Watts
        return f"{power_watts:.3f} W"
    elif abs_power >= 1e-3:
        # Display in milliwatts
        return f"{power_watts * 1e3:.3f} mW"
    elif abs_power >= 1e-6:
        # Display in microwatts
        return f"{power_watts * 1e6:.3f} µW"
    else:
        # Display in nanowatts
        return f"{power_watts * 1e9:.3f} nW"

try:
    import pyvisa
    PYVISA_AVAILABLE = True
except ImportError:
    pyvisa = None
    PYVISA_AVAILABLE = False


class PowerMeterRole(Enum):
    """Role assignment for power meters"""
    REFERENCE = "Reference"
    TARGET = "Target"
    UNASSIGNED = "Unassigned"


class PowerMeterError(Exception):
    """Custom exception for power meter errors"""
    pass


THORLABS_VID = 0x1313

# What VI_ERROR_RSRC_NFOUND on a listed Thorlabs entry nearly always means:
# NI-VISA remembers meters it has seen before (and lists them even when
# unplugged), and it cannot open a meter whose TMC interface is bound to
# Thorlabs' own WinUSB driver instead of the USBTMC (VISA) driver.
RSRC_NFOUND_HINT = (
    "not found by VISA - either not plugged in (VISA lists meters it has "
    "seen before), or the meter is using the Thorlabs driver; switch it to "
    "the VISA/USBTMC driver with Thorlabs' Power Meter Driver Switcher"
)


def _parse_int(text: str) -> Optional[int]:
    """Parse "0x1313" (NI-VISA) or "4883" (pyvisa-py) style numbers."""
    try:
        return int(text, 0)
    except (TypeError, ValueError):
        return None


@dataclass
class MeterCandidate:
    """One VISA resource found by a scan, with what probing it showed.

    A USB resource string looks like
    ``USB<board>::<vid>::<pid>::<serial>[::<interface>]::INSTR``; the VID/PID
    are hex under NI-VISA and decimal under pyvisa-py.
    """
    resource: str
    vid: Optional[int] = None
    pid: Optional[int] = None
    serial: str = ""
    interface: Optional[str] = None
    responding: Optional[bool] = None  # None = not probed
    idn: str = ""                      # *IDN? reply (the meter itself)
    error: str = ""                    # why probing failed
    elapsed_s: float = 0.0

    @classmethod
    def from_resource(cls, resource: str) -> "MeterCandidate":
        parts = resource.split("::")
        c = cls(resource=resource)
        if resource.startswith(SIM_RESOURCE_PREFIX):
            # SIM::0x1313::0x8078::SIM0001::INSTR
            parts = parts[1:]
            c.vid, c.pid = _parse_int(parts[0]), _parse_int(parts[1])
            c.serial = parts[2]
            return c
        if parts and parts[0].upper().startswith("USB") and len(parts) >= 4:
            c.vid = _parse_int(parts[1])
            c.pid = _parse_int(parts[2])
            c.serial = parts[3]
            if len(parts) >= 6:
                c.interface = parts[4]
        return c

    @property
    def model(self) -> str:
        """Model from *IDN? ("Thorlabs,PM100USB,P0012345,1.6.0"), if probed"""
        fields = [f.strip() for f in self.idn.split(",")]
        return fields[1] if len(fields) > 1 else ""

    @property
    def pid_text(self) -> str:
        return f"0x{self.pid:04X}" if self.pid is not None else "?"


NO_SENSOR_FAULT = "No sensor head connected - plug the photodiode into the meter"
READ_FAULT = "No reading from meter - check the sensor head"
FAULT_RETRY_S = 2.0          # while faulted, re-check this often
SENSOR_CHECK_TIMEOUT_MS = 300


def sensor_idn_present(idn: str) -> Optional[bool]:
    """Interpret a SYST:SENS:IDN? reply ("S120C,<serial>,<cal date>,...").

    Returns False when the meter reports no sensor head, True when it names
    one, None when the reply can't be interpreted.
    """
    name = idn.split(",")[0].strip().lower() if idn else ""
    if not name:
        return None
    if "no sensor" in name or name in ("none", "nosensor", "no_sensor"):
        return False
    return True


class PowerMeter:
    """Individual power meter instance"""

    def __init__(self, resource_name: str, rm: pyvisa.ResourceManager):
        """
        Initialize a power meter instance

        Args:
            resource_name: VISA resource name (e.g., 'USB0::0x1313::0x8078::P0007837::INSTR')
            rm: PyVISA resource manager
        """
        self.resource_name = resource_name
        self.rm = rm
        self.instrument = None
        self.connected = False
        self.role = PowerMeterRole.UNASSIGNED
        self.device_info = ""
        self._wavelength = 1310  # Default wavelength in nm
        self._power_unit = "W"   # Default unit: Watts
        self._averaging = 1   # Default averaging samples
        # Readings come from a background poller while settings changes come
        # from the GUI thread; one VISA session must not interleave them.
        self._lock = threading.RLock()
        # Set when readings fail (typically the sensor head is unplugged);
        # read_meters() then backs off instead of blocking on every poll
        self.fault = ""
        self.retry_at = 0.0

    def connect(self):
        """Connect to the power meter"""
        with self._lock:
            try:
                self.instrument = self.rm.open_resource(self.resource_name)
                self.instrument.timeout = self._read_timeout_ms()
                # Sensor head identity ("S120C,<serial>,...") - not the meter's
                self.device_info = self.instrument.query("SYST:SENS:IDN?").strip()
                self.connected = True
                if sensor_idn_present(self.device_info) is False:
                    # Connect anyway, but don't let the first poll time out
                    self.fault = NO_SENSOR_FAULT
                    self.retry_at = time.monotonic() + FAULT_RETRY_S
                    logging.warning(
                        f"{self.resource_name}: no sensor head ({self.device_info})"
                    )

                # Apply default settings
                self.configure_default_settings()

                logging.info(f"Connected to power meter: {self.device_info}")
            except Exception as e:
                # Don't leave the session open: a later retry would find it busy
                if self.instrument is not None:
                    try:
                        self.instrument.close()
                    except Exception:
                        pass
                    self.instrument = None
                self.connected = False
                raise PowerMeterError(f"Failed to connect to {self.resource_name}: {str(e)}")

    def disconnect(self):
        """Disconnect from the power meter"""
        with self._lock:
            if self.instrument:
                try:
                    self.instrument.close()
                    self.connected = False
                    logging.info(f"Disconnected from power meter: {self.device_info}")
                except Exception as e:
                    logging.error(f"Error disconnecting: {str(e)}")

    def configure_default_settings(self):
        """Configure default measurement settings"""
        with self._lock:
            if not self.connected:
                raise PowerMeterError("Not connected to power meter")

            try:
                # Enable auto-ranging
                self.instrument.write("SENS:RANGE:AUTO ON")
                # Set wavelength
                self.instrument.write(f"SENS:CORR:WAV {self._wavelength}")
                # Set power unit
                self.instrument.write(f"SENS:POW:UNIT {self._power_unit}")
                # Set averaging
                self.instrument.write(f"SENS:AVER:COUN {self._averaging}")
            except Exception as e:
                raise PowerMeterError(f"Failed to configure settings: {str(e)}")

    def set_wavelength(self, wavelength_nm: int):
        """
        Set the wavelength calibration

        Args:
            wavelength_nm: Wavelength in nanometers
        """
        with self._lock:
            if not self.connected:
                raise PowerMeterError("Not connected to power meter")

            try:
                self._wavelength = wavelength_nm
                self.instrument.write(f"SENS:CORR:WAV {wavelength_nm}")
            except Exception as e:
                raise PowerMeterError(f"Failed to set wavelength: {str(e)}")

    def set_averaging(self, samples: int):
        """
        Set the number of averaging samples

        Args:
            samples: Number of samples to average
        """
        with self._lock:
            if not self.connected:
                raise PowerMeterError("Not connected to power meter")

            try:
                self._averaging = samples
                self.instrument.write(f"SENS:AVER:COUN {samples}")
                self.instrument.timeout = self._read_timeout_ms()
            except Exception as e:
                raise PowerMeterError(f"Failed to set averaging: {str(e)}")

    def read_power(self) -> float:
        """
        Read current power measurement

        Returns:
            Power reading in Watts
        """
        with self._lock:
            if not self.connected:
                raise PowerMeterError("Not connected to power meter")

            try:
                power_str = self.instrument.query("MEAS:POW?").strip()
                return float(power_str)
            except Exception as e:
                # Flush whatever the meter may still send for this query
                try:
                    self.instrument.clear()
                except Exception:
                    pass
                raise PowerMeterError(f"Failed to read power: {str(e)}")

    def _read_timeout_ms(self) -> int:
        """VISA timeout for a reading: generous for the averaging, but short
        enough that a meter with no sensor head can't stall polling for long."""
        return 1000 + 3 * max(1, int(self._averaging))

    def check_sensor(self, timeout_ms: int = SENSOR_CHECK_TIMEOUT_MS) -> Optional[bool]:
        """Ask the meter which sensor head is attached (quick, short timeout).

        Updates device_info. Returns True/False for sensor present/absent,
        None if the meter didn't answer or the reply was unclear.
        """
        with self._lock:
            if not self.connected or self.instrument is None:
                return None
            old_timeout = self.instrument.timeout
            try:
                self.instrument.timeout = timeout_ms
                idn = self.instrument.query("SYST:SENS:IDN?").strip()
            except Exception as e:
                logging.debug(f"{self.resource_name}: sensor check failed: {e}")
                try:
                    self.instrument.clear()
                except Exception:
                    pass
                return None
            finally:
                try:
                    self.instrument.timeout = old_timeout
                except Exception:
                    pass
        self.device_info = idn
        return sensor_idn_present(idn)

    @property
    def serial(self) -> str:
        """The meter's own serial number (from the USB resource string).

        Friendly names are keyed on this; it identifies the meter body,
        whereas device_info describes the (swappable) sensor head.
        """
        return MeterCandidate.from_resource(self.resource_name).serial

    def set_role(self, role: PowerMeterRole):
        """Set the role of this power meter"""
        self.role = role

    def get_short_name(self) -> str:
        """Get a short name for display purposes: "PM (<meter serial>)".

        (This used to take field 3 of the sensor IDN, which is the sensor's
        calibration date, not a serial - so two meters were hard to tell
        apart.)
        """
        serial = self.serial
        return f"PM ({serial})" if serial else self.resource_name


SIM_RESOURCE_PREFIX = "SIM::"


class SimulatedPowerMeter(PowerMeter):
    """Simulated power meter for testing the GUI without hardware.

    Models the real bench: a ~2 mW laser into a 10/90 fibre splitter, with
    the 10% tap on meter 1 (the reference, ~200 uW) and the 90% arm on
    meter 2 (the target, ~1.8 mW), so Calibrate Now yields a factor of ~9.
    Both meters share the same slow source drift (same laser) with
    independent measurement noise; averaging reduces the noise as it would
    on a real meter.
    """

    SOURCE_POWER_W = 2.0e-3  # simulated laser power
    SPLIT_FRACTIONS = [0.10, 0.90]  # 10/90 splitter: meter 1 is the reference tap

    def __init__(self, resource_name: str, index: int = 0):
        super().__init__(resource_name, rm=None)
        self._base_power = (
            self.SOURCE_POWER_W
            * self.SPLIT_FRACTIONS[index % len(self.SPLIT_FRACTIONS)]
        )
        self._serial = f"SIM{index + 1:04d}"
        self.sensor_connected = True   # set False to simulate an unplugged head

    def _sensor_idn(self) -> str:
        if self.sensor_connected:
            return f"S120C (simulated),{self._serial},01-Jan-2026,1,18,289"
        return "no sensor,0,0,0,0,0"

    def check_sensor(self, timeout_ms: int = SENSOR_CHECK_TIMEOUT_MS) -> Optional[bool]:
        if not self.connected:
            return None
        self.device_info = self._sensor_idn()
        return self.sensor_connected

    def connect(self):
        self.device_info = f"Thorlabs,PM100USB,{self._serial},1.0 (simulated)"
        self.connected = True
        logging.info(f"Connected to simulated power meter: {self.device_info}")

    def disconnect(self):
        self.connected = False
        logging.info(f"Disconnected from simulated power meter: {self.device_info}")

    def configure_default_settings(self):
        pass  # nothing to configure

    def set_wavelength(self, wavelength_nm: int):
        self._wavelength = wavelength_nm

    def set_averaging(self, samples: int):
        self._averaging = samples

    def read_power(self) -> float:
        if not self.connected:
            raise PowerMeterError("Not connected to power meter")
        if not self.sensor_connected:
            raise PowerMeterError("Failed to read power: timeout (simulated, no sensor)")
        # ±2% sinusoidal drift (30 s period) so the display visibly changes
        drift = 1.0 + 0.02 * math.sin(2.0 * math.pi * time.time() / 30.0)
        # 1% Gaussian noise, reduced by averaging like a real meter
        noise = random.gauss(0.0, 0.01) / math.sqrt(max(1, self._averaging))
        return self._base_power * drift * (1.0 + noise)


class PowerMeterController:
    """Controller for managing one or two Thorlabs PM100USB power meters"""

    def __init__(self):
        """Initialize the power meter controller"""
        # PyVISA is only required for real hardware; simulated meters
        # (see simulated_resources) work without it.
        self.rm = None
        self.power_meters: List[PowerMeter] = []
        self.reference_meter: Optional[PowerMeter] = None
        self.target_meter: Optional[PowerMeter] = None
        self.calibration_factor: float = 1.0
        # (raw_reference_w, target_w) from the last calibrate_from_measurements
        self.last_calibration: Optional[Tuple[float, float]] = None

        logging.basicConfig(level=logging.INFO)

    @staticmethod
    def simulated_resources(count: int = 2) -> List[str]:
        """Return resource names for simulated power meters (for testing)"""
        return [
            f"{SIM_RESOURCE_PREFIX}0x1313::0x8078::SIM{i + 1:04d}::INSTR"
            for i in range(count)
        ]

    @staticmethod
    def is_simulated_resource(resource_name: str) -> bool:
        """Check whether a resource name refers to a simulated meter"""
        return resource_name.startswith(SIM_RESOURCE_PREFIX)

    def find_power_meters(self) -> List[str]:
        """
        Find all available Thorlabs power meters

        Set the MULTILASER_SIM_METERS environment variable to 1 or 2 to skip
        the hardware scan and return that many simulated meters instead.

        Returns:
            List of VISA resource names for found power meters
        """
        sim_env = os.environ.get("MULTILASER_SIM_METERS", "").strip()
        if sim_env and sim_env != "0":
            count = int(sim_env) if sim_env in ("1", "2") else 2
            logging.info(f"MULTILASER_SIM_METERS set: using {count} simulated meter(s)")
            return self.simulated_resources(count)

        if pyvisa is None:
            raise PowerMeterError(
                "PyVISA is not installed. Install with: pip install pyvisa pyvisa-py"
            )

        try:
            if self.rm is None:
                self.rm = pyvisa.ResourceManager()

            # Find all USB VISA instruments
            resources = self.rm.list_resources("USB?*::INSTR")

            # Filter for Thorlabs devices (VID 0x1313). The VID field is
            # formatted as hex by NI-VISA ("0x1313") but as decimal by
            # pyvisa-py ("4883"), so accept both forms.
            thorlabs_resources = []
            for resource in resources:
                parts = resource.split("::")
                vid = parts[1].lower() if len(parts) > 1 else ""
                if vid in ("0x1313", "4883"):
                    thorlabs_resources.append(resource)
                else:
                    logging.info(f"Ignoring non-Thorlabs USB instrument: {resource}")
            logging.info(f"Found {len(thorlabs_resources)} Thorlabs power meter(s)")
            return thorlabs_resources

        except Exception as e:
            raise PowerMeterError(f"Failed to find power meters: {str(e)}")

    def probe_resource(self, resource: str, timeout_ms: int = 2000) -> MeterCandidate:
        """Open a resource, ask *IDN? and close it again.

        Used to tell a working meter from a stale or duplicate VISA entry.
        Never raises; the outcome is in the returned candidate.
        """
        c = MeterCandidate.from_resource(resource)
        if self.is_simulated_resource(resource):
            c.responding = True
            c.idn = f"Thorlabs,PM100USB,{c.serial},1.0 (simulated)"
            return c
        start = time.monotonic()
        inst = None
        try:
            if self.rm is None:
                self.rm = pyvisa.ResourceManager()
            inst = self.rm.open_resource(resource, open_timeout=timeout_ms)
            inst.timeout = timeout_ms
            c.idn = inst.query("*IDN?").strip()
            c.responding = True
        except Exception as e:
            c.responding = False
            c.error = f"{type(e).__name__}: {e}".strip()
            if "RSRC_NFOUND" in c.error:
                c.error = f"{RSRC_NFOUND_HINT} [VI_ERROR_RSRC_NFOUND]"
        finally:
            if inst is not None:
                try:
                    inst.close()
                except Exception:
                    pass
            c.elapsed_s = time.monotonic() - start
        level = logging.INFO if c.responding else logging.WARNING
        logging.log(level, f"Probe {resource}: "
                    + (c.idn if c.responding else f"no response ({c.error})"))
        return c

    def scan_power_meters(self, probe: bool = True) -> List[MeterCandidate]:
        """Find Thorlabs meters and (optionally) check each one answers.

        Like find_power_meters(), but returns MeterCandidate objects so the
        GUI can flag entries that don't respond (e.g. a duplicate or stale
        VISA entry for the same meter) instead of failing to connect.
        """
        resources = self.find_power_meters()
        if not probe:
            return [MeterCandidate.from_resource(r) for r in resources]
        return [self.probe_resource(r) for r in resources]

    def connect_power_meters(self, resource_names: List[str]):
        """
        Connect to specified power meters

        Args:
            resource_names: List of VISA resource names to connect to (1 or 2)
        """
        if len(resource_names) not in [1, 2]:
            raise PowerMeterError("1 or 2 power meters are required")

        self.power_meters.clear()

        for i, resource_name in enumerate(resource_names):
            if self.is_simulated_resource(resource_name):
                pm = SimulatedPowerMeter(resource_name, index=i)
            else:
                if pyvisa is None:
                    raise PowerMeterError(
                        "PyVISA is not installed. Install with: pip install pyvisa pyvisa-py"
                    )
                if self.rm is None:
                    self.rm = pyvisa.ResourceManager()
                pm = PowerMeter(resource_name, self.rm)
            pm.connect()
            self.power_meters.append(pm)

    def disconnect_all(self):
        """Disconnect from all power meters"""
        for pm in self.power_meters:
            pm.disconnect()
        self.power_meters.clear()
        self.reference_meter = None
        self.target_meter = None

        if self.rm:
            self.rm.close()
            self.rm = None

    def assign_roles(self, reference_index: Optional[int], target_index: Optional[int]):
        """
        Assign reference and target roles to power meters

        Args:
            reference_index: Index of power meter to use as reference, or None
            target_index: Index of power meter to use as target, or None
        """
        if not self.power_meters:
            raise PowerMeterError("No connected power meters")

        if reference_index is not None and target_index is not None:
            if reference_index == target_index:
                raise PowerMeterError("Reference and target must be different power meters")

        # Reset all roles
        for pm in self.power_meters:
            pm.set_role(PowerMeterRole.UNASSIGNED)

        self.reference_meter = None
        self.target_meter = None

        if reference_index is not None:
            self.power_meters[reference_index].set_role(PowerMeterRole.REFERENCE)
            self.reference_meter = self.power_meters[reference_index]
            logging.info(f"Assigned Reference: {self.reference_meter.get_short_name()}")

        if target_index is not None:
            self.power_meters[target_index].set_role(PowerMeterRole.TARGET)
            self.target_meter = self.power_meters[target_index]
            logging.info(f"Assigned Target: {self.target_meter.get_short_name()}")

    def set_calibration_factor(self, factor: float):
        """
        Set the calibration factor for the reference meter.

        The corrected reference reading = raw_reading * calibration_factor.
        For a 90:10 fibre splitter where 10% goes to the reference meter,
        the calibration factor would be ~10 so that the corrected reference
        matches the target power.

        Args:
            factor: Calibration factor (default 1.0 = no correction)
        """
        if factor <= 0:
            raise PowerMeterError("Calibration factor must be positive")
        self.calibration_factor = factor
        logging.info(f"Calibration factor set to {factor:.6f}")

    def calibrate_from_measurements(self) -> float:
        """
        Auto-calibrate by reading both meters and computing the factor.

        Sets calibration_factor = target_power / reference_power so that
        corrected_reference ≈ target_power after calibration.

        Returns:
            The computed calibration factor

        Raises:
            PowerMeterError: If both meters are not available or reference reads zero
        """
        raw_ref, _, target = self.read_meters()

        if raw_ref is None or target is None:
            faults = self.meter_faults()
            if faults:
                raise PowerMeterError(f"Cannot calibrate: {faults[0]}")
            raise PowerMeterError("Both meters must be connected to calibrate")
        if raw_ref <= 0:
            raise PowerMeterError("Reference power must be positive to calibrate")

        factor = target / raw_ref
        self.calibration_factor = factor
        self.last_calibration = (raw_ref, target)
        logging.info(f"Calibrated: factor = {factor:.6f} (target={target:.6e}, ref={raw_ref:.6e})")
        return factor

    def _read_meter(self, pm: PowerMeter) -> Optional[float]:
        """Read one meter, backing off while it is faulted.

        A meter without its sensor head never answers MEAS:POW?, so every
        read would wait out the VISA timeout while holding the meter. After
        a failure the meter is marked faulted (pm.fault) and only a quick
        sensor check runs every FAULT_RETRY_S until readings work again.
        """
        now = time.monotonic()
        if pm.fault:
            if now < pm.retry_at:
                return None
            if pm.check_sensor() is False:
                pm.fault = NO_SENSOR_FAULT
                pm.retry_at = time.monotonic() + FAULT_RETRY_S
                return None
        try:
            value = pm.read_power()
        except PowerMeterError as e:
            first = not pm.fault
            present = pm.check_sensor()
            pm.fault = NO_SENSOR_FAULT if present is False else READ_FAULT
            pm.retry_at = time.monotonic() + FAULT_RETRY_S
            if first:
                logging.warning(
                    f"{pm.get_short_name()}: {pm.fault} ({e}; sensor: {pm.device_info!r})"
                )
            return None
        if pm.fault:
            logging.info(f"{pm.get_short_name()}: readings restored ({pm.device_info})")
            pm.fault = ""
            try:
                # A (possibly different) head was plugged in: re-apply settings
                pm.configure_default_settings()
            except PowerMeterError as e:
                logging.warning(f"{pm.get_short_name()}: could not re-apply settings: {e}")
        return value

    def meter_faults(self) -> List[str]:
        """Fault messages for connected meters that currently can't read."""
        return [pm.fault for pm in self.power_meters if pm.fault]

    def read_meters(self) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """
        Read power from both meters with calibration applied to reference.

        A meter that can't read (e.g. sensor head unplugged) gives None and
        is retried every FAULT_RETRY_S; see _read_meter() and PowerMeter.fault.

        Returns:
            Tuple of (raw_reference_power, corrected_reference_power, target_power) in Watts.
            corrected_reference = raw_reference * calibration_factor.
        """
        raw_ref = None
        corrected_ref = None
        target_power = None

        if self.reference_meter and self.reference_meter.connected:
            raw_ref = self._read_meter(self.reference_meter)
            if raw_ref is not None:
                corrected_ref = raw_ref * self.calibration_factor

        if self.target_meter and self.target_meter.connected:
            target_power = self._read_meter(self.target_meter)

        return raw_ref, corrected_ref, target_power

    def read_both_meters(self) -> Tuple[Optional[float], Optional[float]]:
        """
        Read power from both meters (corrected reference, target).

        Returns:
            Tuple of (corrected_reference_power, target_power) in Watts
        """
        _, corrected_ref, target_power = self.read_meters()
        return corrected_ref, target_power

    def calculate_ratio(self) -> Optional[float]:
        """
        Calculate the ratio of target/corrected_reference power

        Returns:
            Ratio of target to corrected reference power, or None if not available
        """
        corrected_ref, target_power = self.read_both_meters()

        if corrected_ref is not None and target_power is not None:
            if corrected_ref > 0:
                return target_power / corrected_ref

        return None

    def get_power_meters(self) -> List[PowerMeter]:
        """Get list of all connected power meters"""
        return self.power_meters

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup"""
        self.disconnect_all()
