# Power Meter Tab Guide

## Overview

The Multi-Laser Controller now includes support for viewing and monitoring Thorlabs PM100USB power meters. This feature allows you to simultaneously monitor two power meters and designate them as "Reference" and "Target" for power ratio measurements.

## Requirements

### Hardware
- 2x Thorlabs PM100USB power meters
- USB connections to your computer
- Compatible Thorlabs power meter sensors

### Software Dependencies

To enable the power meter functionality, install the additional dependencies:

```bash
pip install pyvisa pyvisa-py
```

Or install with the powermeter extras:

```bash
pip install -e ".[powermeter]"
```

If these dependencies are not installed, the application will still work but the Power Meters tab will not be available.

For logging measurements to Excel, openpyxl is also required (included in the powermeter extras):

```bash
pip install openpyxl
```

Without openpyxl, measurement logging still works but only in CSV format.

## Features

### Dual Power Meter Monitoring
- Connect to exactly 2 Thorlabs PM100USB power meters
- Real-time power readings displayed simultaneously
- Auto-detection of connected devices

### Reference/Target Assignment
- Designate one meter as "Reference" and the other as "Target"
- Easily swap assignments using dropdown menus
- Visual indication of which meter is assigned to which role

### Power Ratio Calculation
- Automatic calculation of Target/Reference ratio
- Display in both decimal and percentage formats
- Real-time updates as power readings change

### Configurable Settings
- **Wavelength**: Set the calibration wavelength (400-2000 nm)
- **Averaging**: Configure number of averaging samples (1-10000)
- **Update Rate**: Adjust reading update frequency (0.1-10 Hz)

### Display Features
- Power readings shown in both Watts and milliwatts
- Large, easy-to-read display with high-contrast colors
- Device information displayed for each meter
- Status indicators for connection state

### Measurement Logging
- Log measurements to Excel (.xlsx) or CSV (.csv) files
- Excel logs use the lantern throughput worksheet layout: each logged
  measurement adds a row with Trial, Port, injection power (corrected
  reference) and lantern output power (target); throughput, loss and
  per-port statistics are computed by built-in formulas
- Alternatively, Excel logs can use the **Lantern Test Report** layout:
  one sheet per wavelength (1550/1310/1064 nm) with a header block
  (Lantern S/N, PMREF, Launch power) and a port-keyed table (ports 1-19);
  "Calibrate Now" records the PMREF (uW) and Launch (mW) cells, and each
  logged measurement writes the target power (mW) and raw reference (uW)
  into the current port's row — re-logging a port overwrites it. The
  sheet is chosen by the current wavelength setting
- CSV logs include a timestamp, wavelength, and throughput/loss computed
  at log time
- Each logged value is the average of the recent display readings (the
  "Average over" count, default 10) for a more stable measurement
- Trial numbers auto-increment; the port number is set in the GUI
- Append to an existing log file to continue a measurement session
- Logged measurements are shown live in a table beside the controls;
  selecting an existing log file loads its measurements into the table.
  For report logs the table is port-keyed and shows both the recorded raw
  reference reading and the calculated injection power (Launch × Ref/PMREF)
- Works with Freeze: freeze the display, then log the held readings

### Simulated Meters (Testing)
- The Power Meters tab can run without hardware: when a scan finds no
  meters, the dialog offers two simulated meters modelling a ~2 mW laser
  into a 10/90 splitter (meter 1 = 10% reference tap ~200 uW, meter 2 =
  90% arm ~1.8 mW, with realistic noise and shared drift)
- "Calibrate Now" works without an active laser after a confirmation (the
  factor just isn't saved to a laser's settings) — needed when testing
  with simulated meters and no laser box attached
- Set the `MULTILASER_SIM_METERS` environment variable to `1` or `2` to
  skip the hardware scan entirely (works without pyvisa installed)
- The status label shows "SIMULATED" while simulated meters are connected

## Usage Instructions

### 1. Connect Hardware
1. Connect both Thorlabs PM100USB power meters to your computer via USB
2. Ensure the devices are recognized by your operating system
3. Make sure appropriate sensors are attached to each power meter

### 2. Launch Application
```bash
python laser_controller_gui.py
```

### 3. Navigate to Power Meters Tab
Click on the "Power Meters" tab in the main application window.

### 4. Scan for Devices
1. Click the "Scan for Power Meters" button
2. The application searches for connected Thorlabs devices (other USB
   instruments are ignored and listed in the log)
3. Status message will indicate:
   - "Found 1/2 power meter(s) - ready to connect" (ready to proceed)
   - "No power meters found" (check connections)
4. If more than two Thorlabs meters are detected, a dialog lists them so
   you can select which one or two to use

### 5. Connect to Power Meters
1. Click the "Connect" button
2. The application will establish connection to both meters
3. Device information will be displayed for each meter
4. Default assignment: Meter 1 = Reference, Meter 2 = Target

### 6. Assign Roles (Optional)
1. Use the "Reference Meter" dropdown to select which meter is the reference
2. Use the "Target Meter" dropdown to select which meter is the target
3. The two selections must be different meters

### 7. Configure Settings (Optional)
1. **Wavelength**: Set to match your laser wavelength for accurate calibration
2. **Averaging**: Increase for more stable readings, decrease for faster response
3. **Update Rate**: Adjust how often the display updates (higher = more frequent)

### 8. Monitor Readings
- Reference power displayed on the left
- Target power displayed on the right
- Ratio displayed at the bottom (Target / Reference)
- All readings update automatically at the configured rate

### 9. Log Measurements (Optional)
1. Click "New Log File…" and choose the format and where to save the log
   - **Excel Throughput Log (.xlsx)**: generated with the lantern throughput
     worksheet layout, including formulas for throughput, loss and per-port
     statistics; the sheet is named after the current wavelength
     (e.g. `wave_1550`)
   - **Lantern Test Report (.xlsx)**: generated with the report layout
     (one sheet per wavelength, ports 1-19); you are prompted for the
     lantern serial number. Use "Calibrate Now" (with the reference patch
     cord in the target meter) to record the PMREF/Launch cells, then log
     each port — measurements go to the sheet matching the current
     wavelength, and the Port spinner advances automatically after each
     log so repeated logs walk down the ports; spin back to re-log a port
     (its row is overwritten). If you calibrated before selecting the
     report file, you are offered to record those readings when the
     report is attached
   - **CSV File (.csv)**: plain-text log with computed throughput and loss
2. Or click "Append to Existing…" to continue an earlier log file — the
   layout of an existing Excel log is detected automatically
3. Set the **Port** number for the lantern port being measured
4. Optionally adjust **Average over** — each logged measurement is the
   average of this many recent display readings (default 10, about 1 s at
   the default 10 Hz update rate; set to 1 to log single readings)
5. Click "Log Measurement" to record the averaged readings
   - Injection power = corrected reference power
   - Lantern output power = target power
   - The trial number auto-increments
   - The measurement appears in the table beside the controls
6. Optionally use "Freeze" first to hold a reading, then log it (the
   readings buffered before the freeze are averaged)
7. Keep the log file closed in Excel while logging — the file is written on
   every logged measurement

### 10. Disconnect
1. Click the "Disconnect" button when finished
2. Meters will be safely disconnected
3. Click "Scan for Power Meters" to start a new session

## Troubleshooting

### Power Meter Tab Not Visible
- **Cause**: PyVISA dependencies not installed
- **Solution**: Install with `pip install pyvisa pyvisa-py`

### No Devices Found During Scan
- **Cause**: Devices not connected or drivers not installed
- **Solution**:
  - Check USB connections
  - Install Thorlabs USB drivers (included with Optical Power Monitor software)
  - Try a different USB port
- **Note**: The scan only accepts Thorlabs devices (USB vendor ID 0x1313).
  If a meter is attached but not found, check the application log — ignored
  USB instruments are listed there by resource name
- **Testing without hardware**: the "no devices found" dialog offers
  simulated meters — answer Yes to test the tab (readings, logging, table)
  with no meters attached

### Wrong or Extra Devices Detected
- **Cause**: Before v0.7.1, any USB VISA instrument on the computer was
  counted as a power meter
- **Solution**: Update to v0.7.1 or later; non-Thorlabs instruments are now
  filtered out, and if you genuinely have more than two meters attached, a
  selection dialog lets you choose which ones to use

### Connection Error
- **Cause**: Device in use by another application or permission issue
- **Solution**:
  - Close other applications using the power meters
  - On Linux, ensure you have USB device permissions
  - Try reconnecting the USB cables

### Readings Show "---"
- **Cause**: Communication error or meter not properly connected
- **Solution**:
  - Disconnect and reconnect
  - Check sensor connections
  - Ensure sensors are properly attached to meters

### Can't Assign Same Role
- **Cause**: Attempting to assign both Reference and Target to same meter
- **Solution**: Select different meters for Reference and Target roles

## Technical Details

### Communication Protocol
- Uses SCPI (Standard Commands for Programmable Instruments) protocol
- Communication via PyVISA library
- Compatible with all PM100USB models

### Measurement Parameters
- Power range: Auto-ranging enabled by default
- Power units: Watts (W)
- Default wavelength: 1310 nm
- Default averaging: 1000 samples

### Update Performance
- Maximum update rate: 10 Hz (100ms interval)
- Minimum update rate: 0.1 Hz (10s interval)
- Actual measurement rate depends on meter averaging settings

## Code Architecture

### Main Components

1. **power_meter_controller.py**
   - `PowerMeterController`: Main controller class
   - `PowerMeter`: Individual meter instance
   - `PowerMeterRole`: Enum for role assignment
   - Device discovery and connection management
   - SCPI command interface

2. **power_meter_tab.py**
   - `PowerMeterTab`: Main tab widget
   - `PowerDisplay`: Individual power reading display widget
   - UI layout and user interaction
   - Real-time data updates via QTimer

3. **laser_controller_gui.py** (modified)
   - Added QTabWidget for tab-based interface
   - Integration of PowerMeterTab
   - Graceful handling when PyVISA not available

### Key Features of Implementation

- **Modular Design**: Power meter functionality isolated in separate modules
- **Optional Dependency**: Application works without PyVISA installed
- **Error Handling**: Comprehensive exception handling for device errors
- **Resource Management**: Proper cleanup of VISA resources
- **Context Manager Support**: PowerMeterController supports `with` statement

## Example Use Cases

### Optical Alignment
Use the power meter ratio to optimize optical coupling:
1. Set reference meter at a known stable point in optical path
2. Set target meter at the point being optimized
3. Adjust alignment while monitoring ratio
4. Achieve maximum ratio for best coupling

### Beam Splitting Ratio
Measure and verify beam splitter ratios:
1. Place reference meter in one output arm
2. Place target meter in other output arm
3. Read ratio directly from display
4. Verify against specified splitting ratio

### Power Stability Monitoring
Monitor power stability over time:
1. Use reference meter as baseline
2. Monitor target meter for variations
3. Track ratio to identify drift or instability
4. Adjust update rate for desired temporal resolution

## Future Enhancements (Potential)

- Data logging to file
- Graphical plotting of power vs time
- Statistical analysis (mean, std dev, etc.)
- Support for single-channel PM100D meters
- Alarm thresholds for out-of-range conditions
- Export data to CSV format
