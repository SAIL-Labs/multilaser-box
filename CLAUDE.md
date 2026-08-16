# Multi-Laser Controller - Project Context

## Project Overview

This is a Python-based control system for managing multiple lasers through an Arduino microcontroller via serial communication. The system provides both a programmatic API and a PyQt6 graphical user interface for controlling up to 3 lasers, with optional Thorlabs PM100USB power meter integration and Excel/CSV measurement logging.

**Authors:** Kok-Wei Bong, Chris Betters
**Repository:** https://github.com/yourusername/multilaser-box

## Non-Obvious Gotchas

- **Excel log template:** `MeasurementLogger` generates Excel logs programmatically with the lantern throughput worksheet layout (Trial / Port / injection power / lantern output power in columns A-D, formulas for throughput, loss and per-port statistics). The layout matches the SAIL `throughput_new.xlsx` template, which is **intentionally NOT bundled** — it lives on the team OneDrive.
- **openpyxl is an optional dependency** — CSV logging must keep working without it.
- **2-second Arduino initialization delay** is required after opening the serial connection before sending commands.

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

- Git tags (format: `v{major}.{minor}.{patch}`) are the **single source of truth** for releases; GitHub Actions extracts the version from the tag that triggers the workflow — no manual VERSION file edits needed.
- For development, `_version.py` falls back: VERSION file → `git describe --tags --abbrev=0` → `"0.0.0-dev"`.
- Release: `git tag -a v0.7.0 -m "Release version 0.7.0" && git push origin v0.7.0` — GitHub Actions builds Windows/macOS executables and creates the release automatically.
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
- Repository URL placeholder in setup.py and README.md

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
