# Multi-Laser Controller

A Python-based control system for managing multiple lasers through an Arduino microcontroller via serial communication. Features both a PyQt6 graphical interface and a programmatic API with SCPI protocol support.

**Authors:** Kok-Wei Bong, Chris Betters
**Repository:** https://github.com/SAIL-Labs/multilaser-box

---

## Features

- **Intuitive GUI** - PyQt6-based interface with LED indicators and safety controls
- **SCPI Protocol** - Industry-standard SCPI commands for professional integration
- **Dual Power Meter Support** - Optional Thorlabs PM100USB integration (see [Power Meter Guide](docs/power_meter_manual.md))
- **Measurement Logging** - Log power readings (averaged over the recent display readings) to Excel or CSV with throughput/loss calculations, shown live in a measurements table beside the controls; Excel logs support the throughput layout or the per-port Lantern Test Report layout
- **Safety First** - Emergency stop, single-laser enforcement, automatic shutdown
- **Cross-Platform** - Works on Windows, macOS, and Linux
- **Windows Installer** - Per-user installer (no admin rights) with Start menu shortcut and Add/Remove Programs entry, or a portable zip; no Python required
- **Auto-Update** - The installed and portable apps download new releases in the background and offer *Restart now* / *Later* (Later installs it on the next start)
- **Programmable API** - Use as a library in your own Python code

---

## Quick Start

### For End Users (No Python Required)

Download pre-built executables from the [Releases page](https://github.com/SAIL-Labs/multilaser-box/releases):

- **Windows (recommended)**: run `MultiLaserController-win-Setup.exe`. It installs for your user only (no admin rights) into `%LOCALAPPDATA%\MultiLaserController`, adds a Start menu shortcut, and keeps itself up to date.
- **Windows (portable)**: extract `MultiLaserController-win-Portable.zip` anywhere and run `MultiLaserController.exe`. It updates itself too.

A few seconds after start-up the app checks GitHub for a newer release and downloads it quietly; a bar at the bottom of the window then offers **Restart now** or **Later**. Help → Check for Updates checks on demand; Help → About shows the version. Start with `--no-update-check` to skip the start-up check.

> **Upgrading from v1.0.0 or earlier** (single `MultiLaserController-v*.exe`): those versions can't update into the installer by themselves. Their *Update Now* button downloads `MultiLaserController-v<version>-Setup.exe`; run it once, then delete the old exe. Settings (COM port, meter roles, Airtable, ...) are kept, as they live in the user's registry, not the app folder.

### For Developers

**Using conda (recommended):**

```bash
# Create and activate environment
conda env create -f environment.yml
conda activate multilaser

# Run the GUI
multilaser
```

**Using pip:**

```bash
# Install package
pip install -e .

# Run the GUI
multilaser
# or
multilaser-gui
```

**Running directly from source:**

```bash
# Install dependencies
pip install -r requirements.txt

# Run the GUI
python -m multilaser.laser_controller_gui
```

---

## Hardware Setup

**Detailed assembly instructions:** See [Hardware Manual](docs/multilaser_manual.md)

---

## Usage

### GUI Application

1. **Launch the application:**
   ```bash
   multilaser OR MultiLaserController.exe OR MultiLaserController.app
   ``` 

2. **Connect to Arduino:**
   - Select COM/Serial port from dropdown
   - Select baud rate (default: 9600)
   - Click "Connect"

3. **Control lasers:**
   - Click "Toggle Laser 1/2/3" to control individual lasers
   - Click "Turn Off All Lasers" to deactivate all
   - Click "Emergency Stop" toggle for safety shutdown

4. **Monitor status:**
   - LED indicators show ON (green) or OFF (grey)
   - Only one laser can be active at a time (safety feature)

#### Simulated Power Meters (Testing Without Hardware)

To test the Power Meters tab (readings, calibration, measurement logging and
the measurements table) without any hardware attached:

- Click "Scan for Power Meters" and answer **Yes** when offered simulated
  meters (the offer appears when no real meters are found), **or**
- Set the `MULTILASER_SIM_METERS` environment variable to `1` or `2` before
  launching to skip the hardware scan entirely (works without pyvisa
  installed).

Simulated meters model the real bench — a ~2 mW laser into a 10/90 splitter,
with the 10% tap on meter 1 (reference, ~200 µW) and the 90% arm on meter 2
(target, ~1.8 mW) — with realistic noise and shared slow drift; the status
bar shows "SIMULATED" while they are connected.

### Python API

#### SCPI Mode (Recommended)

```python
from multilaser.laser_controller import MultiLaserController

# Connect with SCPI protocol (auto-detected)
controller = MultiLaserController(
    port='/dev/ttyUSB0',
    baud_rate=9600,
    use_scpi=True
)

# Get device information
print(controller.identify())  # *IDN? query

# Control lasers
controller.turn_on_laser(1)
controller.turn_off_laser(2)
controller.set_laser(3, True)

# Query states
state = controller.get_laser_state(1)
print(f"Laser 1: {state}")

# Check for errors
errors = controller.check_errors()
for code, message in errors:
    print(f"Error {code}: {message}")

# Clean shutdown
controller.disconnect()
```

#### Context Manager

```python
with MultiLaserController(port='COM3', use_scpi=True) as controller:
    controller.turn_on_laser(1)
    # Automatically disconnects and turns off lasers on exit
```

### SCPI Commands (Direct Serial)

For integration with LabVIEW, MATLAB, or other software:

```
*IDN?                    # Get device identification
*RST                     # Reset all lasers to OFF
SOUR1:STAT ON           # Turn Laser 1 ON
SOUR2:STAT OFF          # Turn Laser 2 OFF
SOUR3:STAT?             # Query Laser 3 state
STAT?                   # Query all laser states
SYST:ERR?               # Check error queue
ALL_OFF                 # Turn all lasers OFF
```

**Complete SCPI documentation:** See [SCPI Guide](SCPI_GUIDE.md)
**Firmware SCPI reference:** See [Firmware SCPI Guide](laser_ttl_controller/README_SCPI.md)

---

## Documentation

| Document | Description |
|----------|-------------|
| **README.md** (this file) | Quick start, installation, basic usage |
| **[multilaser_manual.md](docs/multilaser_manual.md)** | Complete hardware assembly and operation manual |
| **[laser_ttl_controller/README_SCPI.md](laser_ttl_controller/README_SCPI.md)** | Firmware SCPI reference and customization |
| **[power_meter_manual.md](docs/power_meter_manual.md)** | Power meter integration (optional feature) |

---

## Installation Details

### System Requirements

- **Python:** 3.7 or higher
- **Operating System:** Windows, macOS, or Linux
- **Dependencies:** pyserial, PyQt6
- **Optional:** pyvisa, pyvisa-py (for power meter support)

### Installation Methods

#### Method 1: Conda Environment (Recommended for Development)

```bash
# Clone the repository
git clone https://github.com/SAIL-Labs/multilaser-box.git
cd multilaser-box

# Create conda environment
conda env create -f environment.yml

# Activate environment
conda activate multilaser

# Run the application
multilaser
```

The conda environment includes all dependencies and installs the package in editable mode.

#### Method 2: pip Installation

```bash
# Basic installation
pip install -e .

# With power meter support
pip install -e ".[powermeter]"

# From requirements file
pip install -r requirements.txt
```

#### Method 3: Standalone Executable (End Users)

Download `MultiLaserController-win-Setup.exe` (or the Portable zip) from [Releases](https://github.com/SAIL-Labs/multilaser-box/releases) and run it. See [Quick Start](#for-end-users-no-python-required).

### Serial Port Permissions (Linux)

On Linux, add your user to the `dialout` group:

```bash
sudo usermod -a -G dialout $USER
# Log out and log back in
```

### Verification

Test the installation:

```bash
# Check if command is available
which multilaser

# Run the GUI
multilaser
```

---

## Firmware

### Available Firmware Versions

The project includes two Arduino firmware versions:

1. **SCPI Firmware (Recommended)** - `laser_ttl_controller/laser_ttl_controller_scpi.ino`
   - Industry-standard SCPI protocol
   - IEEE 488.2 common commands
   - Error queue with standard error codes
   - Full compatibility with LabVIEW, MATLAB, PyVISA
   - See [Firmware SCPI Guide](laser_ttl_controller/README_SCPI.md)

2. **Legacy Firmware** - `laser_ttl_controller/laser_ttl_controller.ino`
   - Simple text-based protocol
   - Backward compatibility
   - Lighter code footprint

### Uploading Firmware

1. Open Arduino IDE
2. Open the desired `.ino` file
3. Select your Arduino board: `Tools > Board`
4. Select the COM port: `Tools > Port`
5. Click Upload (→)

### Firmware Configuration

Both firmwares support customization:

```cpp
// Number of lasers (1-4)
const int NUM_LASERS = 3;

// Pin assignments
const int laserPins[] = {8, 9, 10};

// TTL logic (change for active-LOW relays)
const int LASER_ON_SIGNAL = HIGH;   // HIGH for active-high
const int LASER_OFF_SIGNAL = LOW;

// Serial baud rate
Serial.begin(9600);  // Change to 115200 for faster communication
```

After changes, re-upload to Arduino.

---

## Building Executables

### GitHub Actions (Automated)

1. Bump `__version__` in `multilaser/_version.py` (the single version source) and commit.
2. Push a matching tag:

```bash
git tag -a v1.1.0 -m "Release version 1.1.0"
git push origin v1.1.0
```

The workflow fails if the tag isn't `v{__version__}`. Otherwise it runs the tests, builds with PyInstaller (one-folder), packs the installer with [Velopack](https://velopack.io) and publishes the GitHub release. Installed copies update from that release's files, so leave all of them on it. A manual run (*Run workflow*) builds the same files as a workflow artifact without releasing. See [docs/updating_version.md](docs/updating_version.md).

### Manual Build

```bash
pip install -e ".[powermeter,dev]"
pyinstaller multilaser.spec --noconfirm
```

This produces `dist/MultiLaserController/MultiLaserController.exe` (one-folder build). That folder runs as-is but can't update itself; to make the installer as well, install the [vpk](https://docs.velopack.io) .NET tool at the same version as the `velopack` pin in `pyproject.toml`:

```bash
dotnet tool install -g vpk --version 1.2.161
```

```bash
vpk pack --packId MultiLaserController --packVersion 1.1.0 --packDir dist/MultiLaserController --mainExe MultiLaserController.exe --outputDir Releases
```

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

Copyright (c) 2025 SAIL, The University of Sydney

---

## Version History

### v0.4.2 (2025)

- Initial SCPI implementation with IEEE 488.2 commands
- Single-laser enforcement (safety feature)
- Emergency stop toggle (no confirmation dialog)
- Removed "Turn On All Lasers" functionality
- GUI defaults to SCPI mode with fallback
- Power meter integration (optional)
- Comprehensive documentation
- GitHub Actions CI/CD for releases

---

## Acknowledgments

- **Arduino Community** - For excellent hardware and software ecosystem
- **PyQt6** - For powerful cross-platform GUI framework
- **PySerial** - For reliable serial communication
- **SCPI Consortium** - For standardized instrument control protocol

---

**For detailed hardware assembly, wiring diagrams, and operational procedures, see [docs/multilaser_manual.md](docs/multilaser_manual.md)**
