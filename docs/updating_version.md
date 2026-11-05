# Releasing a New Version

## Single version source

`multilaser/_version.py` holds the version:

```python
__version__ = "1.1.0"
```

Everything else reads it: the window title and Help → About, `pyproject.toml`
(`[tool.setuptools.dynamic]`), and the release workflow. The workflow **fails
if the pushed tag is not exactly `v{__version__}`**, so bump the file first.

## Creating a release

1. Bump `__version__` in `multilaser/_version.py`, commit and push to `main`:

   ```bash
   git commit -am "chore: release 1.1.0"
   git push origin main
   ```

2. Tag and push:

   ```bash
   git tag -a v1.1.0 -m "Release version 1.1.0"
   git push origin v1.1.0
   ```

3. GitHub Actions (`.github/workflows/build-executables.yml`, on `windows-latest`):
   - checks the tag against `__version__` and runs the tests;
   - builds `dist/MultiLaserController/` with `pyinstaller multilaser.spec` (one-folder);
   - packs it with Velopack (`vpk pack`);
   - publishes the GitHub release with everything in `Releases/`.

Tag format must be `v{major}.{minor}.{patch}` (SemVer): `v1.1.0`, not `1.1.0` or `v1.1`.

## What's on a release (keep all of it)

| File | Purpose |
| --- | --- |
| `MultiLaserController-win-Setup.exe` | Per-user installer (no admin) into `%LOCALAPPDATA%\MultiLaserController` |
| `MultiLaserController-win-Portable.zip` | Runs without installing; updates itself |
| `MultiLaserController-X.Y.Z-full.nupkg` | Update package installed copies download |
| `releases.win.json`, `assets.win.json`, `RELEASES` | Velopack update feed |
| `MultiLaserController-Windows.zip` | Bridge for v1.0.0 and older: contains `MultiLaserController-vX.Y.Z-Setup.exe`, which the old updater finds and saves next to the old exe |

Installed copies use `velopack.GithubSource` on this repository, which reads the
latest (non-pre-release) release. Deleting those files breaks updates.

Only full packages are built (no delta step). That's fine; deltas are optional.

## How updating works

- `run_install_hooks()` (`multilaser/updates.py`) is the first call in `main()`.
  Velopack starts the exe with special arguments during install, update and
  uninstall; this handles them and exits. It also applies an update that was
  downloaded earlier but not installed ("Later").
- Three seconds after start-up the app checks quietly and downloads any newer
  release in the background (`multilaser/update_controller.py`). A bar at the
  bottom of the window then offers **Restart now** or **Later**.
- **Restart now** first runs the window's exit routine: if lasers are connected
  it asks to switch them off and disconnect (cancelling aborts the restart),
  then releases the power meters and saves settings.
- Help → Check for Updates reports every outcome (up to date, error, ready).
- `--no-update-check` disables the start-up check; it is also skipped when
  `QT_QPA_PLATFORM=offscreen` (tests/CI).
- Settings live in `QSettings` (the user's registry on Windows), outside the
  install folder, so they survive updates, which replace the whole folder.

## Version pins

`velopack==1.2.161` in `pyproject.toml` and `VPK_VERSION: "1.2.161"` in the
workflow must stay equal. Bump them together.

## Repository access

The repository is public, so no token is needed. If it is ever made private,
installed copies need a read token: create a fine-grained PAT (resource owner
SAIL-Labs, this repository only, Contents: Read-only), store it as the
`UPDATE_TOKEN` secret, and add a workflow step before PyInstaller that writes
`multilaser/_update_token.py` containing `TOKEN = "..."` (it is gitignored and
already picked up by `multilaser/updates.py` and `multilaser.spec`), plus an
`if: always()` step afterwards that deletes it. Anyone with the exe could
extract that token. Unauthenticated checks are limited to 60 requests/hour per
IP address, which is plenty for one check per start-up.

## Manual / development builds

- *Actions → Build and Release (Windows) → Run workflow* builds the same files
  and uploads them as a workflow artifact, with no release.
- Locally: `pyinstaller multilaser.spec --noconfirm`. The resulting folder runs
  but reports that it can't update itself, because it wasn't installed.
- Running from source never updates; Help → Check for Updates says so.

## Deleting a release

```bash
git tag -d v1.1.0
git push origin :refs/tags/v1.1.0
```

Then delete the release on GitHub (Releases → Edit → Delete). Installed copies
then see the previous release as the latest.
