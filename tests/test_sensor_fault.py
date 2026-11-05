"""A meter with its photodiode head unplugged must not stall polling."""

import pytest

from multilaser import power_meter_controller as pmc
from multilaser.power_meter_controller import (
    NO_SENSOR_FAULT,
    PowerMeter,
    PowerMeterController,
    SimulatedPowerMeter,
    sensor_idn_present,
)

RES = "USB0::0x1313::0x8072::P2008306::0::INSTR"


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


@pytest.fixture
def clock(monkeypatch):
    c = Clock()
    monkeypatch.setattr(pmc.time, "monotonic", c)
    return c


class Inst:
    """PM100USB: MEAS:POW? times out when no head is plugged in."""

    def __init__(self, meter):
        self.meter = meter
        self.timeout = 2000
        self.queries = []
        self.writes = []
        self.cleared = 0

    def query(self, cmd):
        self.queries.append(cmd)
        if cmd == "SYST:SENS:IDN?":
            return "S120C,15011607,25-Jan-2023,1,18,289" if self.meter.head else "no sensor,0,0,0,0,0"
        if cmd == "MEAS:POW?":
            if not self.meter.head:
                raise OSError("VI_ERROR_TMO (-1073807339): Timeout expired")
            return "1.5e-3"
        raise AssertionError(cmd)

    def write(self, cmd):
        self.writes.append(cmd)

    def clear(self):
        self.cleared += 1

    def close(self):
        pass


class Meter:
    head = True


class RM:
    def __init__(self):
        self.meter = Meter()
        self.inst = None

    def open_resource(self, resource, **kw):
        self.inst = Inst(self.meter)
        return self.inst


def connected(rm):
    ctl = PowerMeterController()
    pm = PowerMeter(RES, rm)
    pm.connect()
    ctl.power_meters = [pm]
    ctl.target_meter = pm
    return ctl, pm


@pytest.mark.parametrize("idn,expected", [
    ("S120C,15011607,25-Jan-2023,1,18,289", True),
    ("no sensor,0,0,0,0,0", False),
    ("No Sensor", False),
    ("", None),
])
def test_sensor_idn_interpretation(idn, expected):
    assert sensor_idn_present(idn) is expected


def test_unplugged_head_backs_off_instead_of_timing_out_every_poll(clock):
    rm = RM()
    ctl, pm = connected(rm)
    assert ctl.read_meters()[2] == 1.5e-3

    rm.meter.head = False
    assert ctl.read_meters()[2] is None          # one failed read...
    assert pm.fault == NO_SENSOR_FAULT
    assert rm.inst.cleared >= 1                   # stale reply flushed
    meas_before = rm.inst.queries.count("MEAS:POW?")

    for _ in range(20):                           # ...then no more blocking reads
        clock.t += 0.05
        assert ctl.read_meters()[2] is None
    assert rm.inst.queries.count("MEAS:POW?") == meas_before

    clock.t += 2.0                                # retry: quick sensor check only
    ctl.read_meters()
    assert rm.inst.queries.count("MEAS:POW?") == meas_before
    assert rm.inst.queries[-1] == "SYST:SENS:IDN?"
    assert ctl.meter_faults() == [NO_SENSOR_FAULT]


def test_plugging_head_back_in_recovers_and_reapplies_settings(clock):
    rm = RM()
    ctl, pm = connected(rm)
    pm.set_wavelength(1550)
    rm.meter.head = False
    ctl.read_meters()
    rm.meter.head = True
    rm.inst.writes.clear()
    clock.t += 2.5
    assert ctl.read_meters()[2] == 1.5e-3
    assert pm.fault == "" and ctl.meter_faults() == []
    assert "SENS:CORR:WAV 1550" in rm.inst.writes      # settings re-applied
    assert pm.device_info.startswith("S120C")


def test_connect_without_head_is_flagged_immediately(clock):
    rm = RM()
    rm.meter.head = False
    ctl, pm = connected(rm)
    assert pm.connected and pm.fault == NO_SENSOR_FAULT
    assert ctl.read_meters()[2] is None
    assert "MEAS:POW?" not in rm.inst.queries          # no timeout on first poll


def test_read_timeout_is_short_and_scales_with_averaging():
    rm = RM()
    _, pm = connected(rm)
    assert rm.inst.timeout == 1003
    pm.set_averaging(100)
    assert rm.inst.timeout == 1300


def test_calibrate_reports_the_fault(clock):
    ctl = PowerMeterController()
    ctl.connect_power_meters(ctl.simulated_resources(2))
    ctl.assign_roles(0, 1)
    ctl.power_meters[0].sensor_connected = False
    ctl.read_meters()
    with pytest.raises(pmc.PowerMeterError, match="No sensor head"):
        ctl.calibrate_from_measurements()


def test_display_shows_fault_and_clears_on_recovery(tmp_path, monkeypatch):
    pytest.importorskip("PyQt6.QtWidgets")
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import QSettings
    from multilaser.power_meter_tab import PowerMeterTab

    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("MULTILASER_SIM_METERS", "2")
    tab = PowerMeterTab(settings=QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat))
    tab.available_meters = tab.controller.find_power_meters()
    tab.connect_meters()
    tab.update_timer.stop()                      # drive readings by hand
    target = tab.controller.target_meter
    target.sensor_connected = False
    tab.update_readings()
    assert tab.target_display.fault_label.text() == NO_SENSOR_FAULT
    assert not tab.target_display.fault_label.isHidden()
    assert tab.target_display.power_label.text() == "--- W"
    assert tab.ref_display.fault_label.isHidden()
    target.sensor_connected = True
    target.retry_at = 0
    tab.update_readings()
    assert tab.target_display.fault_label.isHidden()
    tab.disconnect_meters()
    tab.cleanup()
