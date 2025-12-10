# SCPI Laser Controller Firmware

## Quick Start

This firmware (`laser_ttl_controller_scpi.ino`) implements SCPI (Standard Commands for Programmable Instruments) protocol for professional laser control.

### Device Information

- **Manufacturer**: SAIL-Nexus
- **Model**: SAIL MultiLaser-TTL
- **Firmware Version**: 1.0.0-SCPI
- **SCPI Version**: 1999.0
- **Serial Settings**: 9600 baud, 8N1, newline terminated (`\n`)

### Hardware Configuration

```cpp
// Default configuration (modify in firmware as needed)
const int NUM_LASERS = 3;
const int laserPins[] = {2, 3, 4};  // Arduino pins for Lasers 1-3

// TTL Signal Logic
const int LASER_ON_SIGNAL = LOW;   // Active-LOW (change to HIGH if needed)
const int LASER_OFF_SIGNAL = HIGH;
```

## Quick Command Reference

### Essential Commands

```
*IDN?                    Get device identification
*RST                     Reset all lasers to OFF
SOUR1:STAT ON           Turn Laser 1 ON
SOUR2:STAT OFF          Turn Laser 2 OFF
SOUR3:STAT?             Query Laser 3 state (returns 1 or 0)
STAT?                   Query all laser states (returns: 0,1,0)
SYST:ERR?               Check error queue
ALL_OFF                 Turn all lasers OFF (legacy command)
```

### SCPI Command Format

#### IEEE 488.2 Common Commands
| Command | Description | Response |
|---------|-------------|----------|
| `*IDN?` | Identification | `SAIL-Nexus,SAIL MultiLaser-TTL,00001,1.0.0-SCPI` |
| `*RST` | Reset to default | (none) |
| `*CLS` | Clear errors | (none) |
| `*OPC?` | Operation complete | `1` |
| `*ESR?` | Event status register | `0` |

#### Laser Control (SOURce Subsystem)
```
SOURce<n>:STATe <bool>     Set laser state
SOURce<n>:STATe?           Query laser state

Where:
  <n> = 1, 2, or 3 (laser number)
  <bool> = ON, OFF, 1, or 0 (case insensitive)

Examples:
  SOUR1:STAT ON
  SOUR2:STAT OFF
  source3:state 1
  SOUR1:STAT?
```

#### Laser Control (OUTPut Subsystem - Alternative)
```
OUTPut<n>:STATe <bool>     Set output state
OUTPut<n>:STATe?           Query output state
OUTPut<n> <bool>           Set output (shorthand)

Examples:
  OUTP1:STAT ON
  OUTP2 OFF
  OUTP3:STAT?
```

#### System Commands
| Command | Description | Response Example |
|---------|-------------|------------------|
| `SYSTem:ERRor?` | Read error from queue | `0,"No error"` |
| `SYSTem:VERSion?` | SCPI version | `1999.0` |
| `STATus?` | All laser states | `0,1,0` |

### Legacy Compatibility

Single-character commands from original firmware still work:
```
1           Toggle Laser 1
2           Toggle Laser 2
3           Toggle Laser 3
ALL_OFF     Turn all lasers OFF
```

**Note**: `ALL_ON` command has been removed. Only one laser can be active at a time (safety feature).

## Error Codes

| Code | Message | Cause |
|------|---------|-------|
| `0` | No error | Success |
| `-100` | Invalid command | Unrecognized command |
| `-102` | Invalid parameter | Bad parameter value |
| `-103` | Missing parameter | Required parameter not provided |
| `-104` | Parameter out of range | Laser number not 1-3 |
| `-105` | Query only command | Tried to set a query-only command |
| `-106` | Command only | Tried to query a command-only |
| `-200` | Execution error | Command failed to execute |
| `-350` | Error queue overflow | More than 10 errors |

### Error Handling Example
```
SOUR1:STAT ON        # Send command
SYST:ERR?            # Check for errors
0,"No error"         # Response if OK

SOUR5:STAT ON        # Invalid laser number
SYST:ERR?            # Check error
-104,"Parameter out of range"
```

## Safety Features

### Exclusive Laser Operation
**Only one laser can be ON at a time.** When turning on any laser, all others automatically turn OFF.

```
SOUR1:STAT ON        # Laser 1 ON, others OFF
SOUR2:STAT ON        # Laser 2 ON, Laser 1 now OFF
```

This is enforced in firmware for safety.

### Emergency Stop
```
*RST                 # Immediately turn all lasers OFF
ALL_OFF              # Turn all lasers OFF (legacy)
```

## Testing the Firmware

### Using Serial Monitor (Arduino IDE)

1. Upload firmware to Arduino
2. Open Serial Monitor (Tools → Serial Monitor)
3. Set to 9600 baud, "Newline" line ending
4. Type commands:

```
*IDN?
SOUR1:STAT ON
SOUR1:STAT?
STAT?
SYST:ERR?
*RST
```

### Using Python

```python
import serial

ser = serial.Serial('/dev/ttyUSB0', 9600, timeout=2)
time.sleep(2)  # Wait for Arduino to initialize

# Send command
ser.write(b"*IDN?\n")
print(ser.readline().decode().strip())

# Turn on laser
ser.write(b"SOUR1:STAT ON\n")

# Query state
ser.write(b"SOUR1:STAT?\n")
print(f"Laser 1 state: {ser.readline().decode().strip()}")

ser.close()
```

### Using Screen (Linux/macOS)

```bash
screen /dev/ttyUSB0 9600

# Type commands (press Enter after each):
*IDN?
SOUR1:STAT ON
STAT?

# Exit: Ctrl-A, then K
```

## Command Syntax Rules

1. **Case Insensitive**: Commands are not case-sensitive
   - `SOUR1:STAT ON` = `sour1:stat on` = `Sour1:Stat On`

2. **Abbreviations Allowed**:
   - `SOURce` = `SOUR`
   - `STATe` = `STAT`
   - `SYSTem` = `SYST`
   - `OUTPut` = `OUTP`

3. **Terminators**: Commands must end with newline (`\n`)

4. **Queries**: Query commands end with `?`

5. **Separators**: Use space between command and parameter
   - Correct: `SOUR1:STAT ON`
   - Incorrect: `SOUR1:STATON`

6. **Multiple Commands**: Separate with semicolon
   - `SOUR1:STAT ON; SOUR2:STAT OFF`

## Firmware Customization

### Changing Number of Lasers

```cpp
const int NUM_LASERS = 4;                    // Change to 4 lasers
const int laserPins[] = {2, 3, 4, 5};       // Add pin 5
```

### Changing TTL Logic (Active-HIGH vs Active-LOW)

```cpp
// For Active-HIGH logic (uncommon):
const int LASER_ON_SIGNAL = HIGH;
const int LASER_OFF_SIGNAL = LOW;

// For Active-LOW logic (default, most common):
const int LASER_ON_SIGNAL = LOW;
const int LASER_OFF_SIGNAL = HIGH;
```

### Changing Serial Speed

```cpp
void setup() {
  Serial.begin(115200);  // Change from 9600 to 115200
  // ...
}
```

**Note**: Update Python client to match: `MultiLaserController(port='COM3', baud_rate=115200)`

### Changing Device Information

```cpp
const char *MANUFACTURER = "YourLab";
const char *MODEL = "CustomLaser-v2";
const char *SERIAL_NUMBER = "SN12345";
const char *FIRMWARE = "2.0.0-SCPI";
```

## Integration with Other Software

### LabVIEW
- Use VISA Serial resource
- Set terminator to `\n`
- Send SCPI commands via VISA Write
- Read responses via VISA Read

### MATLAB
```matlab
s = serialport('COM3', 9600);
writeline(s, "*IDN?");
idn = readline(s);
disp(idn);
```

### Python PyVISA
```python
import pyvisa
rm = pyvisa.ResourceManager()
laser = rm.open_resource('ASRL3::INSTR')
print(laser.query("*IDN?"))
```

### National Instruments TestStand
- Configure serial port (9600, 8N1, \n terminator)
- Use String Value Test to send commands
- Use String Value Test with query mode for responses

## Troubleshooting

### No Response to Commands

1. Check serial connection is established
2. Verify baud rate (9600)
3. Ensure commands end with newline (`\n`)
4. Wait 2 seconds after connecting (Arduino bootloader delay)
5. Try `*IDN?` to verify communication

### Commands Return Errors

1. Query error queue: `SYST:ERR?`
2. Check command syntax (case doesn't matter, but format does)
3. Verify laser number is in range (1-3 by default)
4. Use `*CLS` to clear errors and `*RST` to reset

### Laser Not Turning On

1. Check hardware connections
2. Verify correct pin numbers in firmware
3. Check TTL logic polarity (LASER_ON_SIGNAL)
4. Query state: `SOUR1:STAT?` to confirm firmware state
5. Check error queue for execution errors

### State Query Mismatch

- Firmware maintains authoritative state
- Use `STAT?` to get all states at once
- Use `*RST` to reset to known state (all OFF)

## Performance

- **Command Processing**: ~1-5ms per command
- **Serial Overhead**: ~10ms typical at 9600 baud
- **Maximum Command Rate**: ~100 commands/second
- **Error Queue Size**: 10 errors maximum

## Pin Reference

Default Arduino pin assignments:

| Laser | Pin | Function |
|-------|-----|----------|
| 1 | 2 | TTL output for Laser 1 |
| 2 | 3 | TTL output for Laser 2 |
| 3 | 4 | TTL output for Laser 3 |
| - | 13 | Built-in LED (mirrors Laser 1 state) |

## Additional Resources

- **Full Documentation**: See `../SCPI_GUIDE.md` in repository root
- **Python Client**: See `../multilaser/laser_controller_scpi.py`
- **SCPI Standard**: IVI Foundation SCPI-1999 specification
- **IEEE 488.2**: Common Commands and Status specification

## License

Same as main project - see LICENSE file in repository root.

## Version History

- **1.0.0-SCPI** (2024-12): Initial SCPI implementation
  - IEEE 488.2 common commands
  - SOURce and OUTPut subsystems
  - Error queue with standard codes
  - Exclusive laser operation (safety feature)
  - Legacy command compatibility
