"""Stand-in for velopack.UpdateManager used by the update tests."""

from types import SimpleNamespace


def fake_info(version="9.9.9", notes="Bug fixes"):
    asset = SimpleNamespace(Version=version, NotesMarkdown=notes)
    return SimpleNamespace(TargetFullRelease=asset)


class FakeManager:
    def __init__(self, current="1.0.0", latest=None, fail_on=None):
        self.current = current
        self.latest = latest            # version string, or None for up to date
        self.fail_on = fail_on or set() # method names that raise
        self.calls = []

    def _maybe_fail(self, name):
        self.calls.append(name)
        if name in self.fail_on:
            raise RuntimeError(f"{name} failed\nStack backtrace:\n  0: ...")

    def get_current_version(self):
        self._maybe_fail("get_current_version")
        return self.current

    def check_for_updates(self):
        self._maybe_fail("check_for_updates")
        return fake_info(self.latest) if self.latest else None

    def download_updates(self, info, progress=None):
        self._maybe_fail("download_updates")
        self.downloaded = info

    def apply_updates_and_restart(self, info):
        self._maybe_fail("apply_updates_and_restart")
        self.applied = info
