"""Duplicate / stale meter entries, friendly names and diagnostics."""

from types import SimpleNamespace

import pytest

from multilaser import power_meter_controller as pmc
from multilaser.meter_registry import MeterRegistry
from multilaser.power_meter_controller import MeterCandidate, PowerMeterController

GOOD = "USB0::0x1313::0x8078::P0012345::INSTR"
STALE = "USB0::0x1313::0x8078::P0012345::0::INSTR"   # same meter, second entry
OTHER = "USB0::4883::32888::P0099999::INSTR"          # pyvisa-py decimal form


class FakeInstrument:
    def __init__(self, resource):
        self.resource = resource
        self.timeout = None
        self.closed = False

    def query(self, cmd):
        serial = MeterCandidate.from_resource(self.resource).serial
        if cmd == "*IDN?":
            return f"Thorlabs,PM100USB,{serial},1.7.0\n"
        if cmd == "SYST:SENS:IDN?":
            return "S120C,240101,01-Jan-2024,1,18,289\n"
        if cmd == "MEAS:POW?":
            return "1.0e-3"
        raise AssertionError(cmd)

    def write(self, cmd):
        pass

    def close(self):
        self.closed = True


class FakeRM:
    def __init__(self, resources, dead=()):
        self.resources = list(resources)
        self.dead = set(dead)
        self.opened = []

    def list_resources(self, query="?*::INSTR"):
        return tuple(self.resources)

    def open_resource(self, resource, open_timeout=None):
        if resource in self.dead:
            raise OSError("VI_ERROR_RSRC_NFOUND (-1073807343): Insufficient location information")
        inst = FakeInstrument(resource)
        self.opened.append(inst)
        return inst

    def close(self):
        pass


@pytest.fixture
def fake_visa(monkeypatch):
    def install(resources, dead=()):
        rm = FakeRM(resources, dead)
        monkeypatch.setattr(pmc, "pyvisa", SimpleNamespace(ResourceManager=lambda *a: rm))
        monkeypatch.delenv("MULTILASER_SIM_METERS", raising=False)
        return rm
    return install


class DictSettings:
    def __init__(self):
        self.data = {}

    def value(self, key, defaultValue=None, type=None):
        return self.data.get(key, defaultValue)

    def setValue(self, key, value):
        self.data[key] = value


# --- parsing -------------------------------------------------------------

@pytest.mark.parametrize("resource,pid,serial,interface", [
    (GOOD, 0x8078, "P0012345", None),
    (STALE, 0x8078, "P0012345", "0"),
    (OTHER, 0x8078, "P0099999", None),
    ("SIM::0x1313::0x8078::SIM0001::INSTR", 0x8078, "SIM0001", None),
])
def test_resource_parsing_hex_and_decimal(resource, pid, serial, interface):
    c = MeterCandidate.from_resource(resource)
    assert c.vid == pmc.THORLABS_VID
    assert (c.pid, c.serial, c.interface) == (pid, serial, interface)


# --- probing -------------------------------------------------------------

def test_scan_flags_the_entry_that_does_not_respond(fake_visa):
    rm = fake_visa([GOOD, STALE], dead=[STALE])
    found = PowerMeterController().scan_power_meters()
    assert [c.responding for c in found] == [True, False]
    assert found[0].model == "PM100USB"
    assert "RSRC_NFOUND" in found[1].error
    assert all(inst.closed for inst in rm.opened)   # probes don't hold sessions


def test_find_power_meters_api_unchanged(fake_visa):
    fake_visa([GOOD, "USB0::0x0957::0x1796::MY1::INSTR"])
    assert PowerMeterController().find_power_meters() == [GOOD]


def test_failed_connect_closes_the_session(fake_visa, monkeypatch):
    rm = fake_visa([GOOD])

    def broken_query(self, cmd):
        raise OSError("timeout")
    monkeypatch.setattr(FakeInstrument, "query", broken_query)
    pm = pmc.PowerMeter(GOOD, rm)
    with pytest.raises(pmc.PowerMeterError):
        pm.connect()
    assert rm.opened[-1].closed and pm.instrument is None


def test_power_meter_serial_is_the_meter_not_the_sensor(fake_visa):
    rm = fake_visa([GOOD])
    pm = pmc.PowerMeter(GOOD, rm)
    pm.connect()
    assert pm.serial == "P0012345"
    assert pm.device_info.startswith("S120C")


# --- registry ------------------------------------------------------------

def test_registry_names_survive_record_seen():
    reg = MeterRegistry(DictSettings())
    assert reg.label("P0012345") == "P0012345"
    reg.set_name("P0012345", "  Ref tap ")
    reg.record_seen("P0012345", model="PM100USB", resource=GOOD)
    assert reg.label("P0012345") == "Ref tap (P0012345)"
    assert reg.devices()["P0012345"]["model"] == "PM100USB"
    reg.remove("P0012345")
    assert reg.devices() == {}


def test_registry_ignores_corrupt_setting():
    s = DictSettings()
    s.setValue("power_meter/known_meters", "{not json")
    assert MeterRegistry(s).devices() == {}


# --- diagnostics ---------------------------------------------------------

def test_diagnostics_report_shows_duplicate_and_probe_results(monkeypatch, fake_visa):
    from multilaser import pm_diagnostics
    rm = fake_visa([GOOD, STALE], dead=[STALE])
    monkeypatch.setattr(pm_diagnostics, "_resource_managers", lambda: [("default", rm)])
    monkeypatch.setattr(pm_diagnostics.sys, "platform", "linux")
    report = pm_diagnostics.collect_report(names={"P0012345": "Ref tap"}.get)
    assert report.count("SAME SERIAL AS ANOTHER ENTRY") == 2
    assert 'named "Ref tap"' in report
    assert "Thorlabs,PM100USB,P0012345" in report
    assert "open:      FAILED" in report and "RSRC_NFOUND" in report


def test_diagnostics_does_not_probe_meters_in_use(monkeypatch, fake_visa):
    from multilaser import pm_diagnostics
    rm = fake_visa([GOOD])
    monkeypatch.setattr(pm_diagnostics, "_resource_managers", lambda: [("default", rm)])
    report = pm_diagnostics.collect_report(in_use={GOOD: "Ref tap"})
    assert "connected in the app - not probed" in report
    assert rm.opened == []


# --- GUI -----------------------------------------------------------------

@pytest.fixture
def pm_tab(qapp, tmp_path):
    from PyQt6.QtCore import QSettings
    from multilaser.power_meter_tab import PowerMeterTab
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    tab = PowerMeterTab(settings=settings)
    yield tab
    tab.cleanup()


@pytest.fixture(scope="module")
def qapp():
    pytest.importorskip("PyQt6.QtWidgets")
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_dialog_preselects_only_responding_meter(qapp):
    from multilaser.power_meter_tab import MeterSelectionDialog
    good = MeterCandidate.from_resource(GOOD)
    good.responding, good.idn = True, "Thorlabs,PM100USB,P0012345,1.7.0"
    stale = MeterCandidate.from_resource(STALE)
    stale.responding, stale.error = False, "VI_ERROR_RSRC_NFOUND"
    dlg = MeterSelectionDialog([good, stale], lambda s: f"Ref tap ({s})")
    assert dlg.selected_resources() == [GOOD]
    texts = [cb.text() for cb, _ in dlg._items]
    assert "NOT RESPONDING" in texts[1] and "same serial" in texts[1]
    assert texts[0].startswith("Ref tap (P0012345) - PM100USB")


def test_scan_with_duplicate_asks_instead_of_connecting_both(qapp, pm_tab, fake_visa, monkeypatch):
    from multilaser import power_meter_tab as tabmod
    fake_visa([GOOD, STALE], dead=[STALE])
    shown = {}

    def fake_exec(dialog):
        shown["resources"] = dialog.selected_resources()
        return True
    monkeypatch.setattr(tabmod.MeterSelectionDialog, "exec", fake_exec)
    pm_tab.scan_power_meters()
    assert shown["resources"] == [GOOD]
    assert pm_tab.available_meters == [GOOD]
    assert pm_tab.registry.devices()["P0012345"]["model"] == "PM100USB"


def test_friendly_name_shows_on_connected_meter(qapp, pm_tab, fake_visa):
    fake_visa([GOOD])
    pm_tab.registry.set_name("P0012345", "Ref tap")
    pm_tab.scan_power_meters()          # clean scan: no dialog
    assert "Ref tap (P0012345)" in pm_tab.status_label.text()
    pm_tab.connect_meters()
    assert "Ref tap (P0012345)" in pm_tab.target_combo.currentText()
    pm_tab.registry.set_name("P0012345", "Bench B")
    pm_tab.refresh_meter_names()
    assert "Bench B" in pm_tab.target_combo.currentText()
    assert pm_tab.meter_roles() == {"P0012345": "Target"}
    pm_tab.disconnect_meters()


def test_settings_tab_edits_names(qapp, pm_tab, fake_visa):
    from multilaser.settings_tab import SettingsTab
    fake_visa([GOOD])
    pm_tab.scan_power_meters()
    st = SettingsTab(pm_tab.settings, pm_tab)
    assert st.meters_table.rowCount() == 1
    st.meters_table.item(0, 0).setText("Launch meter")
    assert pm_tab.registry.name("P0012345") == "Launch meter"


def test_short_name_uses_meter_serial_not_sensor_cal_date(fake_visa):
    rm = fake_visa([GOOD])
    pm = pmc.PowerMeter(GOOD, rm)
    pm.connect()
    assert pm.get_short_name() == "PM (P0012345)"
