# Multi-Laser Controller - Project Context

## Project Overview

This is a Python-based control system for managing multiple lasers through an Arduino microcontroller via serial communication. The system provides both a programmatic API and a PyQt6 graphical user interface for controlling up to 3 lasers, with optional Thorlabs PM100USB power meter integration and Excel/CSV measurement logging.

**Authors:** Kok-Wei Bong, Chris Betters
**Repository:** https://github.com/SAIL-Labs/multilaser-box

## Non-Obvious Gotchas

- **Excel log templates:** `MeasurementLogger` generates Excel logs programmatically in two layouts, both matching SAIL templates that are **intentionally NOT bundled** (they live on the team OneDrive): the throughput layout (`throughput_new.xlsx`: Trial / Port / injection / output in columns A-D, appended per trial) and the Lantern Test Report layout (`Lantern_Test_Report.xlsx`: one sheet per wavelength, port-keyed rows 22-40 for ports 1-19, PMREF/Launch calibration cells B17/B18). Report logs record the **raw** reference (µW) in column D — calibration is applied in-sheet via `Launch*(Ref/PMREF)` — unlike throughput logs which record the corrected reference.
- **openpyxl is an optional dependency** — CSV logging must keep working without it.
- **2-second Arduino initialization delay** is required after opening the serial connection before sending commands.
- **VISA resource strings format the USB vendor ID differently per backend**: NI-VISA uses hex (`USB0::0x1313::...`), pyvisa-py uses decimal (`USB0::4883::...`). The Thorlabs filter in `find_power_meters()` must accept both forms — this mismatch is why the filter was once commented out, which made any USB instrument count as a power meter.
- **Meters are identified by the serial field of their USB VISA resource** (`PowerMeter.serial`, `MeterCandidate.from_resource`), not by `device_info`: that comes from `SYST:SENS:IDN?` and describes the swappable *sensor head* (field 3 is its calibration date, which `get_short_name()` once showed by mistake). Friendly names (`MeterRegistry`, QSettings `power_meter/known_meters` JSON) are keyed by that serial.
- **One meter can enumerate twice** (e.g. with and without a `::0::` interface number, or via two drivers). `scan_power_meters()` probes each entry with `*IDN?`, and the tab shows a selection dialog whenever any entry fails to answer instead of connecting to both. `find_power_meters()` (no probing) is kept for API compatibility. Settings → Diagnose... (`multilaser/pm_diagnostics.py`) gives the full picture across VISA backends, pyusb and Windows PnP, including non-present devices.
- **Meter reads run on a worker thread** (`MeterPoller`, `multilaser/meter_poller.py`, kept as `PowerMeterTab.update_timer` with a QTimer-like start/stop/isActive/setInterval). VISA queries block; polling them from a GUI-thread QTimer made the app laggy. `PowerMeter` methods hold a per-meter `RLock` so GUI-thread writes (wavelength, averaging) never interleave with a poll. `poller.invalidate()` (called from `_clear_reading_history`) drops a read already in flight; `stop()` waits for it, so stop before reconfiguring or disconnecting.
- **A PM100USB with its sensor head unplugged never answers `MEAS:POW?`** — each read waits out the VISA timeout. `PowerMeterController._read_meter()` therefore marks the meter faulted (`PowerMeter.fault`, `NO_SENSOR_FAULT`/`READ_FAULT`) after one failure and, until `retry_at`, returns None without querying; retries use the quick `check_sensor()` (`SYST:SENS:IDN?`, 300 ms timeout) and only read power once a head is reported. Recovery re-runs `configure_default_settings()`. Read timeout is `1000 + 3*averaging` ms. `sensor_idn_present()` assumes the no-head IDN names "no sensor" — unverified on hardware; the first fault logs the raw IDN.
- **NI-VISA can only open a PM100USB whose TMC interface (`MI_00`) uses the USBTMC/IVI driver** (service `Usbtmc`), not Thorlabs' WinUSB driver (`ThorlabsUSBDevice`); otherwise it lists the meter but fails with `VI_ERROR_RSRC_NFOUND`. NI-VISA also lists meters seen before that aren't plugged in (same error). The `MI_01` DFU interface is firmware-update only and never a VISA resource. Found from a lab diagnostics report, Nov 2026.
- **CI builds install unpinned latest pyvisa/pyvisa-py/pyusb**, so two builds of identical source can enumerate USB devices differently (this surfaced the scan bug as a "v0.7.0 regression").
- **Simulated power meters** (`SimulatedPowerMeter`, resource names starting with `SIM::`) let the Power Meters tab run without hardware or pyvisa: the scan offers them when no real meters are found, or set `MULTILASER_SIM_METERS=1|2`. `PowerMeterController.__init__` deliberately does NOT require pyvisa — only the real scan/connect paths do.
- **Self-update uses Velopack.** `multilaser/updates.py` (no Qt) wraps `velopack.UpdateManager(GithubSource(...))` and turns every failure into `UpdateError`; `multilaser/update_controller.py` runs checks on a `threading.Thread`, returns results via Qt signals and shows the Restart now / Later bar. `run_install_hooks()` **must stay the first line of `main()`** (Velopack launches the exe with hook arguments during install/update/uninstall). `apply_updates_and_restart` exits the process without a normal close, so `LaserControlGUI.prepare_for_exit()` (lasers off, meters released, settings synced) is passed as `before_restart`.
- **`velopack==1.2.161` (pyproject) and `VPK_VERSION` (workflow) must match.** Only the PyInstaller **one-folder** build (`multilaser.spec`) can be packed; a bare `dist/` folder or source checkout reports updates as unavailable.
- **v1.0.0 and older use the old one-file updater**, which looks for `MultiLaserController-Windows.zip` and copies the first `MultiLaserController-v*.exe` inside it. The workflow keeps shipping that zip with the installer renamed `MultiLaserController-vX.Y.Z-Setup.exe` as a migration bridge.

## Key Design Patterns

### State Management
- Client-side state tracking (no Arduino polling)
- States only change on explicit commands
- LaserState enum for type safety (ON/OFF)

### Safety Features
- All lasers initialize to OFF on connection
- Emergency stop functionality
- Automatic shutdown on disconnect
- Confirmation dialogs for critical operations

### Error Handling
- Custom LaserControllerError exception
- Comprehensive logging throughout
- Serial communication error recovery

## Development Guidelines

### Code Style
- Python 3.7+ compatibility required
- Type hints used throughout (`typing` module)
- Docstrings in Google/NumPy style
- Logging via Python `logging` module

### Testing Approach
- Test with hardware when available
- Serial port mocking for development without Arduino
- GUI testing requires Arduino connection

### Common Tasks

#### Adding New Laser Control Features
1. Add method to `MultiLaserController` class
2. Update state tracking if needed
3. Add corresponding GUI button/control if user-facing
4. Update documentation in README.md

#### Modifying Serial Protocol
1. Update command format in `_send_command()`
2. Coordinate with Arduino firmware changes
3. Test with actual hardware
4. Document protocol changes

#### GUI Enhancements
1. Follow existing PyQt6 patterns
2. Maintain consistent styling (see existing stylesheets)
3. Keep controls disabled when disconnected
4. Update LED indicators after state changes

## Build & Distribution

### Version Management

- `multilaser/_version.py` (`__version__ = "X.Y.Z"`) is the **single version source**; `pyproject.toml` reads it via `[tool.setuptools.dynamic]`. The release workflow fails if the tag ≠ `v{__version__}`, so bump it before tagging.
- Release: bump `__version__`, commit, then `git tag -a vX.Y.Z -m "Release version X.Y.Z" && git push origin vX.Y.Z` — GitHub Actions (windows-latest) runs the tests, builds with PyInstaller, packs with `vpk` and publishes Setup.exe, Portable zip and the update feed files to the release. Keep all of those assets; installed copies update from them.
- Tests: `QT_QPA_PLATFORM=offscreen python -m pytest` (`tests/`, uses a `FakeManager` instead of velopack).
- See `docs/updating_version.md` for detailed release instructions.

## Hardware Context

### Command Protocol
- Commands sent as UTF-8 strings with newline terminator
- Individual laser toggle: `"1\n"`, `"2\n"`, `"3\n"`
- All on: `"all_on\n"`
- All off: `"all_off\n"`
- Default 9600 baud

## Known Issues & TODOs

### Current Issues
- `turn_on_laser()` debug mode commented out in GUI (line 446-451 in `multilaser/laser_controller_gui.py`)

### Future Enhancements
- Add laser intensity control (PWM)
- Pattern sequencing from GUI
- Configuration save/load
- Multiple controller profiles
- Real-time status feedback from Arduino
- Data logging and export for power measurements
- Calibration routines for power meters

## Git Workflow

- Main branch: `main`
- Conventional commits preferred; clear, descriptive messages; reference issue numbers when applicable

## Important Constraints

- `multilaser/` is the main package directory — DO NOT break import paths (all imports use the `multilaser.` prefix)
- `laser_controller.py` is the core API — DO NOT break compatibility; other code depends on it
- Package uses lazy imports via `__getattr__` in `__init__.py`
- Changes to public classes affect multiple modules

## Communication Protocol Notes

### State Synchronization
- Client maintains authoritative state
- No status queries sent to Arduino
- State updates only after successful command transmission
- Assumes Arduino firmware implements commands correctly

## Safety Considerations

### Laser Safety
- Always default to OFF state
- Emergency stop requires confirmation
- Disconnect triggers automatic shutdown
- Context manager ensures cleanup (`__enter__`/`__exit__`)

### Error Recovery
- Serial errors logged but don't crash application
- Failed commands don't update state
- Connection failures show user-friendly messages

## Notes for Claude Code

- **GUI changes:** Maintain existing stylesheet patterns, keep disabled states consistent
- **Controller changes:** Update state tracking, preserve command protocol
- **New features:** Add to both API and GUI unless explicitly backend-only
- **Bug fixes:** Check if issue exists in both controller and GUI layers
