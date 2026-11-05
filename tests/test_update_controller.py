import pytest

pytest.importorskip("PyQt6.QtWidgets")
from PyQt6.QtWidgets import QApplication, QWidget

from multilaser.update_controller import UpdateController
from multilaser.updates import Updater
from fakes import FakeManager


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def make(qapp, mgr, before_restart=lambda: True, answer=False):
    window = QWidget()
    ctl = UpdateController(Updater(factory=lambda: mgr), window,
                           before_restart=lambda: before_restart(), threaded=False)
    ctl.messages = []
    ctl.questions = []
    ctl._message = lambda kind, title, text: ctl.messages.append((kind, title, text))

    def ask(title, text):
        ctl.questions.append(title)
        return answer
    ctl._ask = ask
    ctl._window = window  # keep alive
    return ctl


def test_startup_check_is_silent_when_up_to_date(qapp):
    ctl = make(qapp, FakeManager())
    ctl.check()
    assert ctl.messages == [] and ctl.questions == []
    assert ctl.bar.isHidden()


def test_startup_check_is_silent_on_failure(qapp):
    ctl = make(qapp, FakeManager(fail_on={"check_for_updates"}))
    ctl.check()
    assert ctl.messages == []


def test_startup_check_downloads_and_shows_bar(qapp):
    mgr = FakeManager(latest="1.5.0")
    ctl = make(qapp, mgr)
    ctl.check()
    assert "download_updates" in mgr.calls
    assert not ctl.bar.isHidden()
    assert "1.5.0" in ctl.bar.label.text()
    assert ctl.questions == []  # silent apart from the bar


def test_restart_button_applies_update(qapp):
    mgr = FakeManager(latest="1.5.0")
    ctl = make(qapp, mgr)
    ctl.check()
    ctl.bar.restart_button.click()
    assert mgr.applied.TargetFullRelease.Version == "1.5.0"


def test_restart_cancelled_by_unsaved_changes_prompt(qapp):
    mgr = FakeManager(latest="1.5.0")
    ctl = make(qapp, mgr, before_restart=lambda: False)
    ctl.check()
    ctl.bar.restart_button.click()
    assert "apply_updates_and_restart" not in mgr.calls
    assert not ctl.bar.isHidden()


def test_later_hides_bar_without_applying(qapp):
    mgr = FakeManager(latest="1.5.0")
    ctl = make(qapp, mgr)
    ctl.check()
    ctl.bar.later_button.click()
    assert ctl.bar.isHidden()
    assert "apply_updates_and_restart" not in mgr.calls


def test_restart_failure_is_reported(qapp):
    mgr = FakeManager(latest="1.5.0", fail_on={"apply_updates_and_restart"})
    ctl = make(qapp, mgr)
    ctl.check()
    ctl.restart_now()
    assert ctl.messages[-1][0] == "critical"


def test_manual_check_reports_up_to_date(qapp):
    ctl = make(qapp, FakeManager())
    ctl.check_manually()
    assert ctl.messages[0][1] == "No Updates"


def test_manual_check_reports_failure(qapp):
    ctl = make(qapp, FakeManager(fail_on={"check_for_updates"}))
    ctl.check_manually()
    kind, title, text = ctl.messages[0]
    assert kind == "warning" and "check_for_updates failed" in text


def test_manual_check_from_source_explains_why(qapp):
    window = QWidget()
    ctl = UpdateController(Updater(), window, before_restart=lambda: True, threaded=False)
    msgs = []
    ctl._message = lambda kind, title, text: msgs.append(text)
    ctl.check_manually()
    assert "running from source" in msgs[0]


def test_manual_check_offers_restart(qapp):
    mgr = FakeManager(latest="1.5.0")
    ctl = make(qapp, mgr, answer=True)
    ctl.check_manually()
    assert ctl.questions == ["Update Ready"]
    assert "apply_updates_and_restart" in mgr.calls


def test_manual_check_after_download_does_not_download_again(qapp):
    mgr = FakeManager(latest="1.5.0")
    ctl = make(qapp, mgr)
    ctl.check()
    ctl.check_manually()
    assert mgr.calls.count("download_updates") == 1
    assert ctl.questions == ["Update Ready"]


def test_manual_check_during_running_check_reports_its_result(qapp):
    mgr = FakeManager()
    ctl = make(qapp, mgr)
    # Simulate a silent start-up check still in flight
    ctl._running = True
    ctl._report = False
    ctl.check_manually()
    assert mgr.calls == []        # no second check started
    ctl._up_to_date.emit()        # the running check finishes
    assert ctl.messages[0][1] == "No Updates"
    assert not ctl._running


def test_threaded_check_delivers_result_on_gui_thread(qapp):
    import time
    mgr = FakeManager(latest="1.5.0")
    window = QWidget()
    ctl = UpdateController(Updater(factory=lambda: mgr), window, before_restart=lambda: True)
    ctl.check()
    deadline = time.time() + 5
    while ctl.pending is None and time.time() < deadline:
        qapp.processEvents()
        time.sleep(0.01)
    assert ctl.pending is not None and ctl.pending.version == "1.5.0"
    assert not ctl.bar.isHidden()


def test_main_window_wires_bar_and_restart_hook(qapp):
    from multilaser.laser_controller_gui import LaserControlGUI
    mgr = FakeManager(latest="1.5.0")
    win = LaserControlGUI(check_for_updates=False, updater=Updater(factory=lambda: mgr))
    assert win.updates.bar.parent() is not None
    win.updates.threaded = False
    win.updates.check()
    win.updates.bar.restart_button.click()   # no lasers connected: no prompt
    assert "apply_updates_and_restart" in mgr.calls
    win.close()
