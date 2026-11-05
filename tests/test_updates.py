import pytest

from multilaser import updates
from multilaser.updates import Update, UpdateError, Updater
from fakes import FakeManager, fake_info


def test_dev_checkout_has_no_updates():
    up = Updater()  # not frozen, no factory
    assert not up.available()
    assert up.current_version() is None
    with pytest.raises(UpdateError, match="running from source"):
        up.check()


def test_install_hooks_are_a_no_op_from_source():
    updates.run_install_hooks()  # must not raise or exit


def test_check_download_restart():
    mgr = FakeManager(latest="1.2.0")
    up = Updater(factory=lambda: mgr)
    assert up.available()
    assert up.current_version() == "1.0.0"
    update = up.check()
    assert update.version == "1.2.0"
    assert update.notes == "Bug fixes"
    up.download(update)
    assert mgr.downloaded is update.info
    up.restart_into(update)
    assert mgr.applied is update.info


def test_up_to_date_returns_none():
    up = Updater(factory=lambda: FakeManager(latest=None))
    assert up.check() is None


@pytest.mark.parametrize("method,call", [
    ("check_for_updates", lambda up: up.check()),
    ("download_updates", lambda up: up.download(Update("2.0.0", fake_info("2.0.0"), ""))),
    ("apply_updates_and_restart", lambda up: up.restart_into(Update("2.0.0", fake_info("2.0.0"), ""))),
])
def test_errors_become_update_error(method, call):
    up = Updater(factory=lambda: FakeManager(latest="2.0.0", fail_on={method}))
    with pytest.raises(UpdateError) as exc:
        call(up)
    assert "backtrace" not in str(exc.value).lower()


def test_not_installed_gives_friendly_message():
    def factory():
        raise RuntimeError("This application is not properly installed: ...")
    up = Updater(factory=factory)
    assert not up.available()
    with pytest.raises(UpdateError, match="Setup.exe"):
        up.check()


def test_missing_library_becomes_update_error():
    def factory():
        raise ImportError("No module named 'velopack'")
    with pytest.raises(UpdateError, match="missing"):
        Updater(factory=factory).check()
