# SCPI Implementation Guide

## Overview

This project now includes an **SCPI-compatible** version of the laser controller firmware and Python client. SCPI (Standard Commands for Programmable Instruments) is an industry-standard protocol used in test and measurement equipment.

## Benefits of SCPI Implementation

- **Industry Standard**: Compatible with LabVIEW, MATLAB, Python PyVISA, and other T&M software
- **Interoperability**: Can be controlled by any SCPI-compatible software
- **Error Handling**: Built-in error queue with standardized error codes
- **Self-Documenting**: Hierarchical command structure is intuitive
- **Remote Control**: Easily integrate into automated test systems

## Files

- **Firmware**: `laser_ttl_controller/laser_ttl_controller_scpi.ino`
- **Python Client**: `multilaser/laser_controller_scpi.py`
- **Documentation**: This file

## SCPI Command Reference

### IEEE 488.2 Common Commands

| Command | Type | Description | Response Example |
|---------|------|-------------|------------------|
| `*IDN?` | Query | Identification | `OpenSource,MultiLaser-TTL,00001,1.0.0-SCPI` |
| `*RST` | Command | Reset to default state | (none) |
| `*CLS` | Command | Clear status/errors | (none) |
| `*ESR?` | Query | Event Status Register | `0` |
| `*OPC` | Command | Operation complete | (none) |
| `*OPC?` | Query | Operation complete query | `1` |

### System Commands

| Command | Type | Description | Response Example |
|---------|------|-------------|------------------|
| `SYSTem:ERRor?` | Query | Read error from queue | `0,"No error"` |
| `SYST:ERR?` | Query | Short form | `-100,"Invalid command"` |
| `SYSTem:VERSion?` | Query | SCPI version | `1999.0` |

### Laser Control Commands

#### Source Subsystem (Recommended)

| Command | Type | Description | Example |
|---------|------|-------------|---------|
| `SOURce1:STATe <bool>` | Command | Set Laser 1 state | `SOUR1:STAT ON` |
| `SOURce2:STATe <bool>` | Command | Set Laser 2 state | `SOUR2:STAT OFF` |
| `SOURce3:STATe <bool>` | Command | Set Laser 3 state | `SOUR3:STAT 1` |
| `SOURce1:STATe?` | Query | Query Laser 1 state | Returns: `1` or `0` |
| `SOURce2:STATe?` | Query | Query Laser 2 state | Returns: `1` or `0` |
| `SOURce3:STATe?` | Query | Query Laser 3 state | Returns: `1` or `0` |

**Accepted Parameters**: `ON`, `OFF`, `1`, `0` (case insensitive)

#### Output Subsystem (Alternative)

| Command | Type | Description | Example |
|---------|------|-------------|---------|
| `OUTPut1:STATe <bool>` | Command | Set Laser 1 output | `OUTP1:STAT ON` |
| `OUTPut2 <bool>` | Command | Set Laser 2 output | `OUTP2 OFF` |
| `OUTPut1?` | Query | Query Laser 1 output | Returns: `1` or `0` |

#### Status Commands

| Command | Type | Description | Response Example |
|---------|------|-------------|------------------|
| `STATus?` | Query | Query all laser states | `0,1,0` (L1=OFF, L2=ON, L3=OFF) |

### Legacy Compatibility Commands

For backward compatibility with the original firmware:

| Command | Description |
|---------|-------------|
| `1` | Toggle Laser 1 |
| `2` | Toggle Laser 2 |
| `3` | Toggle Laser 3 |
| `ALL_ON` | Turn all lasers ON |
| `ALL_OFF` | Turn all lasers OFF |

## Error Codes

| Code | Description |
|------|-------------|
| `0` | No error |
| `-100` | Invalid command |
| `-102` | Invalid parameter |
| `-103` | Missing parameter |
| `-104` | Parameter out of range |
| `-105` | Query only command |
| `-106` | Command only (not a query) |
| `-200` | Execution error |
| `-350` | Error queue overflow |

## Python Usage Examples

### Basic Usage

```python
from multilaser.laser_controller_scpi import MultiLaserControllerSCPI

# Connect to controller
controller = MultiLaserControllerSCPI(port='/dev/ttyUSB0', num_lasers=3)

# Get device information
print(controller.identify())  # Device ID
print(controller.get_scpi_version())  # SCPI version

# Control lasers
controller.turn_on_laser(1)
controller.turn_off_laser(2)
controller.set_laser(3, True)  # Turn on laser 3

# Query states
state = controller.get_laser_state(1)
all_states = controller.get_all_states()

# Error handling
errors = controller.check_errors()
for code, message in errors:
    print(f"Error {code}: {message}")

# Cleanup
controller.disconnect()
```

### Context Manager

```python
from multilaser.laser_controller_scpi import MultiLaserControllerSCPI

with MultiLaserControllerSCPI(port='COM3') as controller:
    controller.turn_on_laser(1)
    # Automatically disconnects and turns off lasers on exit
```

### Direct SCPI Commands

```python
# Send raw SCPI commands
controller.write("SOUR1:STAT ON")
response = controller.query("SOUR1:STAT?")
print(f"Laser 1 state: {response}")
```

## Using with Other Software

### LabVIEW (VISA)

```
VISA Resource: COM3::INSTR
Baud Rate: 9600
Termination Character: \n

Commands:
- Write: "SOUR1:STAT ON"
- Query: "SOUR1:STAT?"
- Read response
```

### MATLAB (Instrument Control Toolbox)

```matlab
% Create serial connection
s = serialport('/dev/ttyUSB0', 9600);
configureTerminator(s, 'LF');

% Send commands
writeline(s, "*IDN?");
idn = readline(s);
disp(idn);

writeline(s, "SOUR1:STAT ON");

% Query state
writeline(s, "SOUR1:STAT?");
state = readline(s);
disp(state);

% Cleanup
clear s;
```

### Python PyVISA

```python
import pyvisa

rm = pyvisa.ResourceManager()
laser = rm.open_resource('ASRL/dev/ttyUSB0::INSTR')
laser.baud_rate = 9600
laser.read_termination = '\n'
laser.write_termination = '\n'

# Send commands
print(laser.query("*IDN?"))
laser.write("SOUR1:STAT ON")
state = laser.query("SOUR1:STAT?")
print(f"Laser state: {state}")

laser.close()
```

### Linux/macOS Terminal (screen/minicom)

```bash
# Connect with screen
screen /dev/ttyUSB0 9600

# Type commands:
*IDN?
SOUR1:STAT ON
SOUR1:STAT?
STAT?
SYST:ERR?

# Exit: Ctrl-A, then K
```

## Command Syntax Rules

1. **Case Insensitive**: `SOUR1:STAT`, `sour1:stat`, `Sour1:Stat` are all valid
2. **Terminators**: Commands must end with newline (`\n`) or semicolon (`;`)
3. **Queries**: Queries must end with `?`
4. **Separators**: Use space to separate command from parameter
5. **Multiple Commands**: Separate with semicolon: `SOUR1:STAT ON; SOUR2:STAT OFF`
6. **Abbreviations**: Short forms allowed: `SOUR` = `SOURCE`, `STAT` = `STATE`

## Valid Command Examples

```
*IDN?
*RST
SOUR1:STAT ON
SOUR2:STAT OFF
source1:state 1
OUTP1 ON
outp2:stat?
STAT?
SYST:ERR?
ALL_ON
ALL_OFF
```

## Installation

### Arduino Firmware

1. Open `laser_ttl_controller_scpi.ino` in Arduino IDE
2. Configure pins and TTL logic in the configuration section
3. Upload to Arduino board
4. Connect lasers to configured pins

### Python Client

```bash
# Install in development mode
pip install -e .

# Or use directly
python -c "from multilaser.laser_controller_scpi import MultiLaserControllerSCPI"
```

## Integration with Existing GUI

The SCPI controller can be used as a drop-in replacement for the original controller:

```python
# In laser_controller_gui.py, change import:
# from multilaser.laser_controller import MultiLaserController
from multilaser.laser_controller_scpi import MultiLaserControllerSCPI as MultiLaserController

# Everything else works the same!
```

The SCPI version maintains full API compatibility with the original while adding standard SCPI commands.

## Troubleshooting

### Connection Issues

- Verify correct COM port/device path
- Check baud rate matches (9600)
- Ensure Arduino has finished booting (2 second delay)
- Try sending `*IDN?` to verify communication

### Command Errors

- Check error queue: `SYST:ERR?`
- Verify command syntax
- Ensure parameters are valid (`ON`/`OFF`/`1`/`0`)
- Check laser number is within range (1-3)

### State Synchronization

- Query state before assuming: `SOUR1:STAT?`
- Use `STAT?` to get all states at once
- After errors, use `*RST` to reset to known state

## Performance Considerations

- **Command Rate**: ~10ms per command minimum (Arduino processing + serial)
- **Query Overhead**: Queries require round-trip time (~20ms typical)
- **Batch Commands**: Use semicolon-separated commands for faster execution
- **State Caching**: Python client caches state locally for faster reads

## Future Enhancements

Potential SCPI extensions:

- `SOURce:CURRent?` - Query laser current (if sensors added)
- `SOURce:POWer?` - Query laser power (if power meters added)
- `TRIGger:SOURce` - External trigger configuration
- `SYSTem:COMMunicate:SERial:BAUD` - Runtime baud rate change
- `CALibration:*` commands for calibration routines

## References

- **SCPI-1999 Specification**: IVI Foundation
- **IEEE 488.2**: Common Commands and Status
- **PyVISA Documentation**: https://pyvisa.readthedocs.io/

## Support

For issues or questions about the SCPI implementation, check:
- Error queue: `SYST:ERR?`
- Device identification: `*IDN?`
- SCPI version: `SYST:VERS?`
