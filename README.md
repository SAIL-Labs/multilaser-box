# Multi-Laser Controller

A Python-based graphical interface for controlling multiple lasers through an Arduino microcontroller via serial communication.

## Overview

This system consists of two main components:
1. **MultiLaserController** - Python class for serial communication with Arduino
2. **LaserControlGUI** - PyQt6 graphical interface for user interaction

## Requirements

### Software Dependencies

```bash
pip install pyserial PyQt6
```

- Python 3.7 or higher
- pyserial 3.5+
- PyQt6 6.0+

### Hardware Requirements

- Arduino board (Uno, Mega, Nano, etc.)
- Arduino firmware for laser TTL control (not included in this repository)
- Up to 3 lasers connected to Arduino digital outputs
- USB cable for Arduino connection

## Installation

### Option 1: Standalone Executables (No Python Required)

**For end users who just want to run the application:**

Download pre-built executables from the [Releases page](https://github.com/yourusername/multilaser-box/releases):

- **Windows**: Download `MultiLaserController-Windows.zip`, extract, and run `MultiLaserController.exe`
- **macOS**: Download `MultiLaserController-macOS.tar.gz`, extract, and run `MultiLaserController.app`

These executables include everything needed - no Python installation required!

### Option 2: Install as Package (For Developers)

Using conda (recommended):

```bash
# Create and activate the conda environment
conda env create -f environment.yml
conda activate multilaser
```

The package will be installed in editable mode with the `multilaser` and `multilaser-gui` commands available.

Using pip:

```bash
# Install the package
pip install -e .
```

After installation, you can run the GUI from anywhere using:

```bash
multilaser
# or
multilaser-gui
```

### Option 3: Manual Installation

1. Clone or download this repository
2. Install required Python packages:
   ```bash
   pip install -r requirements.txt
   ```
3. Upload the appropriate firmware to your Arduino
4. Run the GUI directly:
   ```bash
   python laser_controller_gui.py
   ```

## Usage

### Starting the GUI

If installed as a package:

```bash
multilaser
```

Or run directly:

```bash
python laser_controller_gui.py
```

### Connecting to Hardware

1. **Select COM Port** - Choose your Arduino's port from the dropdown menu
   - Windows: typically `COM3`, `COM4`, etc.
   - Linux: typically `/dev/ttyUSB0`, `/dev/ttyACM0`
   - macOS: typically `/dev/cu.usbserial-*` or `/dev/cu.usbmodem-*`

2. **Select Baud Rate** - Choose the baud rate matching your Arduino firmware (default: 9600)

3. **Click Connect** - Establishes serial connection and initialises all lasers to OFF state

### Controlling Lasers

Once connected, you can:

- **Toggle Individual Lasers** - Click "Toggle Laser 1/2/3" buttons
- **Turn All On** - Activate all lasers simultaneously
- **Turn All Off** - Deactivate all lasers simultaneously
- **Emergency Stop** - Immediately turn off all lasers (with confirmation)

### LED Indicators

- **Green** - Laser is ON
- **Grey** - Laser is OFF

### Disconnecting

Click the "Disconnect" button to safely close the serial connection. All lasers will be turned off before disconnecting.

## Compilation to Standalone Executable

For easier deployment, you can compile the GUI into a standalone executable that doesn't require Python to be installed.

### Recommended Method: PyInstaller

PyInstaller creates a single executable file that bundles Python and all dependencies.

**1. Install PyInstaller:**

```bash
pip install pyinstaller
```

**2. Compile the application:**

```bash
pyinstaller --onefile --windowed --name="LaserController" laser_controller_gui.py
```

**Command options explained:**
- `--onefile` - Creates a single executable file (easier to distribute)
- `--windowed` - Hides the console window (GUI applications only)
- `--name="LaserController"` - Sets the name of the executable

**3. Locate your executable:**

The compiled executable will be in the `dist/` folder:
- **Windows:** `dist/LaserController.exe`
- **macOS:** `dist/LaserController.app` or `dist/LaserController`
- **Linux:** `dist/LaserController`

**4. Run the executable:**

Simply double-click the file to launch the application. No Python installation required!