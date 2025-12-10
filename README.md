# Multi-Laser Controller

A Python-based control system for managing multiple lasers through an Arduino microcontroller via serial communication. Features both a PyQt6 graphical interface and a programmatic API with SCPI protocol support.

**Authors:** Kok-Wei Bong, Chris Betters
**Repository:** https://github.com/SAIL-Labs/multilaser-box

---

## Features

- **Intuitive GUI** - PyQt6-based interface with LED indicators and safety controls
- **SCPI Protocol** - Industry-standard SCPI commands for professional integration
- **Dual Power Meter Support** - Optional Thorlabs PM100USB integration (see [Power Meter Guide](POWER_METER_GUIDE.md))
- **Safety First** - Emergency stop, single-laser enforcement, automatic shutdown
- **Cross-Platform** - Works on Windows, macOS, and Linux
- **Standalone Executables** - Pre-built binaries available (no Python required)
- **Programmable API** - Use as a library in your own Python code

---

## Quick Start

### For End Users (No Python Required)

Download pre-built executables from the [Releases page](https://github.com/SAIL-Labs/multilaser-box/releases):

- **Windows**: Download and extract `MultiLaserController-Windows.zip`, run `MultiLaserController.exe`
- **macOS**: Download and extract `MultiLaserController-macOS.tar.gz`, run `MultiLaserController.app`

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

No installation required! Download from [Releases](https://github.com/SAIL-Labs/multilaser-box/releases) and run.

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

Push a version tag to automatically build executables:

```bash
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0
```

GitHub Actions will build Windows and macOS executables and create a release.

### Manual Build with PyInstaller

**Install PyInstaller:**

```bash
pip install pyinstaller
```

**Build executable:**

```bash
# Windows and Linux
pyinstaller --onefile --windowed --name="MultiLaserController" \
    multilaser/laser_controller_gui.py

# macOS (creates .app bundle)
pyinstaller --windowed --name="MultiLaserController" \
    --icon=figures/icon.icns \
    multilaser/laser_controller_gui.py
```

**Output location:**

- Windows: `dist/MultiLaserController.exe`
- macOS: `dist/MultiLaserController.app`
- Linux: `dist/MultiLaserController`

**Advanced options:**

```bash
# With custom icon
pyinstaller --onefile --windowed --icon=figures/icon.ico \
    --name="MultiLaserController" multilaser/laser_controller_gui.py

# Console version (for debugging)
pyinstaller --onefile --name="MultiLaserController" \
    multilaser/laser_controller_gui.py
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
