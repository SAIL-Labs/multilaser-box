"""Background polling keeps the GUI thread free and drops stale readings."""

import threading
import time

import pytest

pytest.importorskip("PyQt6.QtWidgets")
from PyQt6.QtWidgets import QApplication

from multilaser.meter_poller import MeterPoller


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def pump(qapp, seconds):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        qapp.processEvents()
        time.sleep(0.005)


def test_slow_reads_run_off_the_gui_thread(qapp):
    threads = []

    def slow_read():
        threads.append(threading.current_thread())
        time.sleep(0.15)          # a slow meter
        return (1.0, 1.0, 2.0)

    poller = MeterPoller(slow_read)
    got, timings = [], []
    poller.readings.connect(got.append)
    poller.timing.connect(lambda e, i: timings.append(e))
    poller.setInterval(50)
    t0 = time.monotonic()
    poller.start()
    assert time.monotonic() - t0 < 0.05      # start() doesn't wait for a read
    pump(qapp, 0.6)
    poller.stop()
    assert got and got[0] == (1.0, 1.0, 2.0)
    assert threading.main_thread() not in threads
    assert min(timings) >= 0.14               # reports the real read time


def test_no_readings_delivered_after_stop(qapp):
    poller = MeterPoller(lambda: (1.0, 1.0, 1.0))
    got = []
    poller.readings.connect(got.append)
    poller.setInterval(10)
    poller.start()
    pump(qapp, 0.1)
    poller.stop()
    n = len(got)
    pump(qapp, 0.1)                           # queued results are dropped
    assert len(got) == n and not poller.isActive()


def test_invalidate_drops_read_in_flight(qapp):
    release = threading.Event()
    calls = []

    def read():
        calls.append(1)
        release.wait(1.0)
        return (len(calls),) * 3

    poller = MeterPoller(read)
    got = []
    poller.readings.connect(got.append)
    poller.setInterval(10)
    poller.start()
    time.sleep(0.05)              # first read is now blocked in flight
    poller.invalidate()           # e.g. roles changed
    release.set()
    pump(qapp, 0.2)
    poller.stop()
    assert got and all(r[0] >= 2 for r in got)   # first (stale) read dropped


def test_power_meter_tab_polls_in_background(qapp, tmp_path, monkeypatch):
    from PyQt6.QtCore import QSettings
    from multilaser.power_meter_tab import PowerMeterTab

    monkeypatch.setenv("MULTILASER_SIM_METERS", "2")
    tab = PowerMeterTab(settings=QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat))
    tab.available_meters = tab.controller.find_power_meters()
    tab.connect_meters()
    assert isinstance(tab.update_timer, MeterPoller) and tab.update_timer.isActive()
    pump(qapp, 0.4)
    assert tab.target_display is not None and tab._target_history
    tab.toggle_freeze()                       # freeze stops polling
    assert not tab.update_timer.isActive()
    tab.toggle_freeze()
    tab.disconnect_meters()
    assert not tab.update_timer.isActive()
    tab.cleanup()
