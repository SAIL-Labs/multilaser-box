"""Logs use the meters' wavelength (own sheet each) and record instrument serials."""

import csv

import pytest

openpyxl = pytest.importorskip("openpyxl")

from multilaser.measurement_logger import (
    CSV_HEADER,
    MeasurementLogger,
    MeterIdentity,
    XLSX_EXTRA_FIRST_COL,
    XLSX_EXTRA_HEADERS,
)
from multilaser.power_meter_controller import PowerMeter

METERS = {
    "reference": MeterIdentity("P2008306", "S120C", "15011607"),
    "target": MeterIdentity("P2010335", "S122C", "16020202"),
}


def sheet_titles(path):
    return openpyxl.load_workbook(path).sheetnames


# --- report layout -------------------------------------------------------

def test_new_report_includes_external_wavelength_sheet(tmp_path):
    path = tmp_path / "r.xlsx"
    MeasurementLogger(str(path)).create_new(wavelength_nm=980, layout="report", serial="L42")
    assert sheet_titles(path) == ["980 nm", "1550 nm", "1310 nm", "1064 nm"]
    ws = openpyxl.load_workbook(path)["980 nm"]
    assert ws["B16"].value == 980 and ws["B1"].value == "L42"


def test_standard_wavelength_report_unchanged(tmp_path):
    path = tmp_path / "r.xlsx"
    MeasurementLogger(str(path)).create_new(wavelength_nm=1310, layout="report")
    assert sheet_titles(path) == ["1550 nm", "1310 nm", "1064 nm"]


def test_report_logs_to_exact_wavelength_not_nearest(tmp_path):
    path = tmp_path / "r.xlsx"
    log = MeasurementLogger(str(path))
    log.create_new(wavelength_nm=1310, layout="report", serial="L42")
    log.append_measurement(3, None, 1.0e-3, wavelength_nm=1300,
                           raw_reference_w=2.0e-4, meters=METERS)
    wb = openpyxl.load_workbook(path)
    assert "1300 nm" in wb.sheetnames
    ws = wb["1300 nm"]
    assert ws["B16"].value == 1300 and ws["B1"].value == "L42"   # S/N copied
    assert ws["C24"].value == pytest.approx(1.0) and ws["D24"].value == pytest.approx(200.0)
    assert wb["1310 nm"]["C24"].value is None                     # not the nearest sheet
    # instruments in the header block
    assert [ws[f"{c}12"].value for c in "ABCD"] == [
        "Reference (PMREF)", "P2008306", "sensor S120C", "15011607"]
    assert [ws[f"{c}13"].value for c in "ABCD"] == [
        "Target (PM1)", "P2010335", "sensor S122C", "16020202"]


def test_report_reads_nothing_for_wavelength_without_sheet(tmp_path):
    path = tmp_path / "r.xlsx"
    log = MeasurementLogger(str(path))
    log.create_new(layout="report")
    log.append_measurement(1, None, 1e-3, wavelength_nm=1310, raw_reference_w=1e-4)
    assert log.read_measurements(wavelength_nm=1310)
    assert log.read_measurements(wavelength_nm=1300) == []
    assert not log.has_port_measurement(1, wavelength_nm=1300)
    assert log.get_report_calibration(1300) is None


def test_report_calibration_creates_sheet_and_records_meters(tmp_path):
    path = tmp_path / "r.xlsx"
    log = MeasurementLogger(str(path))
    log.create_new(layout="report")
    log.set_report_calibration(905, pmref_w=2e-4, launch_w=1.8e-3, meters=METERS)
    ws = openpyxl.load_workbook(path)["905 nm"]
    assert ws["B17"].value == pytest.approx(200.0) and ws["B18"].value == pytest.approx(1.8)
    assert ws["B12"].value == "P2008306"
    assert log.get_report_calibration(905) == pytest.approx((2e-4, 1.8e-3))


# --- throughput layout ---------------------------------------------------

def test_throughput_gets_a_sheet_per_wavelength_with_serial_columns(tmp_path):
    path = tmp_path / "t.xlsx"
    log = MeasurementLogger(str(path))
    log.create_new(wavelength_nm=1310)
    assert log.append_measurement(1, 2e-3, 1e-3, wavelength_nm=1310, meters=METERS) == 1
    assert log.append_measurement(1, 2e-3, 1e-3, wavelength_nm=1550, meters=METERS) == 1
    assert log.append_measurement(2, 2e-3, 1e-3, wavelength_nm=1310, meters=METERS) == 2
    wb = openpyxl.load_workbook(path)
    assert wb.sheetnames == ["wave_1310", "wave_1550"]
    ws = wb["wave_1550"]
    headers = [ws.cell(1, XLSX_EXTRA_FIRST_COL + i).value for i in range(len(XLSX_EXTRA_HEADERS))]
    assert headers == XLSX_EXTRA_HEADERS
    row = [ws.cell(2, XLSX_EXTRA_FIRST_COL + i).value for i in range(len(XLSX_EXTRA_HEADERS))]
    assert row[1:] == [1550, "P2008306", "S120C", "15011607", "P2010335", "S122C", "16020202"]
    assert ws["E2"].value.startswith("=")            # formulas on the new sheet too
    assert [r[0] for r in log.read_measurements(wavelength_nm=1310)] == [1, 2]
    assert len(log.read_measurements(wavelength_nm=1550)) == 1
    assert log.read_measurements(wavelength_nm=980) == []


def test_legacy_single_sheet_without_wavelength_is_kept(tmp_path):
    path = tmp_path / "t.xlsx"
    log = MeasurementLogger(str(path))
    log.create_new(wavelength_nm=None)                # sheet "throughput"
    log.append_measurement(1, 2e-3, 1e-3, wavelength_nm=1550)
    assert sheet_titles(path) == ["throughput"]


# --- CSV -----------------------------------------------------------------

def test_csv_records_wavelength_and_serials(tmp_path):
    path = tmp_path / "t.csv"
    log = MeasurementLogger(str(path))
    log.create_new()
    log.append_measurement(4, 2e-3, 1e-3, wavelength_nm=980, meters=METERS)
    with open(path, newline="") as f:
        header, row = list(csv.reader(f))
    assert header == CSV_HEADER
    d = dict(zip(header, row))
    assert d["wavelength_nm"] == "980"
    assert (d["ref_meter_sn"], d["ref_sensor"], d["ref_sensor_sn"]) == ("P2008306", "S120C", "15011607")
    assert d["target_meter_sn"] == "P2010335" and d["target_sensor_sn"] == "16020202"
    assert log.read_measurements()[0][:2] == (1, 4)


# --- instrument identity -------------------------------------------------

def test_power_meter_identity_from_resource_and_sensor_idn():
    pm = PowerMeter("USB0::0x1313::0x8072::P2008306::0::INSTR", rm=None)
    pm.device_info = "S120C,15011607,25-Jan-2023,1,18,289"
    assert pm.identity() == MeterIdentity("P2008306", "S120C", "15011607")
    pm.device_info = "no sensor,0,0,0,0,0"
    assert pm.identity() == MeterIdentity("P2008306", "", "")


# --- GUI: logs at the meters' wavelength ---------------------------------

@pytest.fixture
def tab(tmp_path, monkeypatch):
    pytest.importorskip("PyQt6.QtWidgets")
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import QSettings
    from multilaser.power_meter_tab import PowerMeterTab

    app = QApplication.instance() or QApplication([])  # noqa: F841 (keep alive)
    monkeypatch.setenv("MULTILASER_SIM_METERS", "2")
    t = PowerMeterTab(settings=QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat))
    t.available_meters = t.controller.find_power_meters()
    t.connect_meters()
    t.update_timer.stop()
    yield t
    t.disconnect_meters()
    t.cleanup()


def test_unapplied_wavelength_edit_is_not_what_gets_logged(tab):
    tab.wavelength_spin.setValue(1310)
    tab.apply_settings()
    tab.wavelength_spin.setValue(980)           # typed, not applied
    assert tab._log_wavelength() == 1310
    tab.apply_settings()
    assert tab._log_wavelength() == 980
    assert tab._confirm_log_wavelength()        # matches now: no prompt


def test_logged_row_carries_wavelength_and_simulated_serials(tab, tmp_path):
    tab.wavelength_spin.setValue(980)
    tab.apply_settings()
    path = tmp_path / "log.csv"
    log = MeasurementLogger(str(path))
    log.create_new()
    tab._set_log_file(log)
    for _ in range(3):
        tab.update_readings()
    tab._write_measurement()
    with open(path, newline="") as f:
        header, row = list(csv.reader(f))
    d = dict(zip(header, row))
    assert d["wavelength_nm"] == "980"
    assert d["ref_meter_sn"] == "SIM0001" and d["target_meter_sn"] == "SIM0002"
    assert d["ref_sensor"].startswith("S120C")
    assert "980 nm" in tab.log_status_label.text()
