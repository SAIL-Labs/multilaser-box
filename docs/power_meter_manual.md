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
2. The application will search for connected Thorlabs devices
3. Status message will indicate:
   - "Found 2 power meters - ready to connect" (ready to proceed)
   - "No power meters found" (check connections)
   - "Found 1 power meter (need 2)" (connect second device)
   - "Found X power meters (need exactly 2)" (disconnect extra devices)

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

### 9. Disconnect
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
