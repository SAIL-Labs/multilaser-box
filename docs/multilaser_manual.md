# Multilaser Box User Manual

---

# 1. Introduction

## 1.1 About the Multilaser Box

The Multilaser Box is a Python-based control system designed for laboratory environments requiring precise control of multiple laser diode sources. This system provides a graphical user interface (GUI) for controlling up to three independent laser channels through an Arduino microcontroller via serial communication.

The system integrates three near-infrared laser diodes operating at distinct wavelengths (1064nm, 1310nm, and 1550nm), each rated at 10mW optical power output. Control is achieved through a relay-switched power distribution system housed in a 19-inch rack-mountable enclosure, making it suitable for integration into standard optical laboratory equipment racks.

# 2. System Overview

## 2.1 System Architecture

The Multilaser Box operates as a three-tier control system:

**Tier 1: User Interface Layer**
- PyQt6-based graphical interface running on host computer
- Serial communication over USB to microcontroller
- Real-time status monitoring and control feedback

**Tier 2: Microcontroller Layer**
- Arduino UNO R4 Minima microcontroller
- Processes serial commands from GUI
- Generates control signals for relay module
- Baud rate: 9600 bps (default)

**Tier 3: Power Distribution Layer**
- 4-channel relay module (5V trigger)
- 5V DC 4A plugpack power supply
- Switched positive rail to three laser diodes
- Common ground connection

The control architecture employs positive rail switching, where the 5V supply positive terminal is routed through individual relay channels to each laser's positive terminal, whilst all negative terminals share a common ground connection directly to the power supply.

## 2.2 Component List

### Core Electronics Components

| Component | Specification | Quantity | Source |
|-----------|--------------|----------|---------|
| Arduino UNO R4 Minima | Microcontroller | 1 | Arduino Store |
| 4-Channel Relay Module | 5V trigger, 10A contacts | 1 | Core Electronics |
| 5V DC Plugpack | 4A, 2.1mm DC jack | 1 | Core Electronics |
| DC Barrel Jack Adapter - Female | 5.5×2.1mm, screw terminals | 1 | Core Electronics |
| DC Barrel Jack Adapter - Male | 5.5×2.1mm, screw terminals | 3 | Core Electronics |
| DIN Rail Terminal Block | 2 input, 8 output | 1 | - |

### Laser Components

| Component | Specification | Quantity | Source |
|-----------|--------------|----------|---------|
| 1064nm Pigtailed Laser Diode | 10mW optical output | 1 | Edmund Optics Australia |
| 1310nm Pigtailed Laser Diode | 10mW optical output | 1 | Edmund Optics Australia |
| 1550nm Pigtailed Laser Diode | 10mW optical output | 1 | Edmund Optics Australia |

### Optical Components

| Component | Specification | Quantity | Source |
|-----------|--------------|----------|---------|
| Optical Isolator | 1064nm, SM fibre | 1 | AFW Optics Australia |
| Optical Isolator | 1310nm/1480nm/1550nm, SM fibre | 2 | AFW Optics Australia |
| Fibre Coupler | 1×2, 90:10, SM | 3 | AFW Optics Australia |

### Additional Materials (not included in parts list)

- USB-A to USB-C cable (for Arduino connection)
- Dupont connector cables (female-to-female) - red, blue, green
- Cable ties and cable management accessories

## 2.3 Technical Specifications

### Electrical Specifications

| Parameter | Value |
|-----------|-------|
| Input Voltage | 240V AC (mains) |
| System Voltage | 5V DC |
| Maximum Current | 4A |
| Power Consumption | ~20W maximum |
| Relay Contact Rating | 10A @ 250V AC / 30V DC |

### Communication Specifications

| Parameter | Value |
|-----------|-------|
| Communication Protocol | Serial (UART) |
| Default Baud Rate | 9600 bps |
| Data Bits | 8 |
| Parity | None |
| Stop Bits | 1 |
| Interface | USB (virtual COM port) |

### Physical Specifications

| Parameter | Value |
|-----------|-------|
| Enclosure Format | 19-inch rack mount, 1U |
| Dimensions | 44mm (H) × 483mm (W) × 250-466mm (D) |
| Weight | Approximately 2-3 kg (depends on configuration) |
| Mounting | Standard 19-inch rack rails |

## 2.4 Laser Specifications

### Laser 1: 1064nm

| Parameter | Value |
|-----------|-------|
| Wavelength | 1064nm ± 5nm |
| Output Power | 10mW (typical) |
| Beam Type | Single-mode fibre coupled |
| Fibre Type | SM fibre, 9/125µm |
| Connector | FC/APC or FC/PC |
| Operating Voltage | 5V DC |
| Operating Current | <500mA (typical) |
| Classification | Class 3B laser product |

### Laser 2: 1310nm

| Parameter | Value |
|-----------|-------|
| Wavelength | 1310nm ± 20nm |
| Output Power | 10mW (typical) |
| Beam Type | Single-mode fibre coupled |
| Fibre Type | SM fibre, 9/125µm |
| Connector | FC/APC or FC/PC |
| Operating Voltage | 5V DC |
| Operating Current | <500mA (typical) |
| Classification | Class 3B laser product |

### Laser 3: 1550nm

| Parameter | Value |
|-----------|-------|
| Wavelength | 1550nm ± 20nm |
| Output Power | 10mW (typical) |
| Beam Type | Single-mode fibre coupled |
| Fibre Type | SM fibre, 9/125µm |
| Connector | FC/APC or FC/PC |
| Operating Voltage | 5V DC |
| Operating Current | <500mA (typical) |
| Classification | Class 3B laser product |

---

# 3. Hardware Assembly

## 3.1 Required Components

Before beginning assembly, ensure you have all components listed in Section 2.2. Additionally, prepare the following tools:

- Wire strippers
- Small Phillips-head screwdriver
- Small flathead screwdriver
- Multi-meter (for continuity and voltage testing)
- Cable ties
- Heat gun or lighter (for heat-shrink tubing, if used)


## 3.2 Wiring the 5V 4A Plugpack Power Supply

The 5V DC 4A plugpack provides regulated power to the entire system. This switched-mode power supply features a fixed 2.1mm DC jack (2.1mm ID × 5.5mm OD × 10mm length) with positive centre tip.

### Components Used

1. **5V DC 4A Plugpack** - Main power supply
2. **DC Barrel Jack Adapter - Female** (5.5×2.1mm) - Connects plugpack to distribution system
3. **DIN Rail Terminal Block** (2 input, 8 output) - Distributes power to relays and lasers

### Connection Procedure

**Step 1: Connect plugpack to barrel jack adapter**

1. Plug the 5V DC plugpack into the female DC barrel jack adapter
2. The barrel jack adapter has screw terminals on the opposite end
3. **Verify polarity with multimeter**: Centre pin should be positive (+5V), outer sleeve should be ground (0V)

**Step 2: Wire barrel jack adapter to DIN rail terminal block**

1. Connect the positive screw terminal from the barrel jack adapter to one of the two input terminals on the DIN rail block (this will be your +5V rail)
2. Connect the negative screw terminal from the barrel jack adapter to the other input terminal on the DIN rail block (this will be your ground rail)
3. Tighten all screw terminals securely

**Step 3: Verify power distribution**

1. Before connecting any loads, measure voltage across the DIN rail terminals with a multimetre
2. Should read 5V DC between positive and negative rails
3. Check all output terminals on the DIN rail block for proper voltage distribution

### Current Capacity

With a 4A maximum current rating and three lasers drawing approximately 500mA each (total ~1.5A typical), plus Arduino consumption (~200mA), the power supply operates well within safe limits with approximately 50% headroom.


## 3.3 Connecting the 4-Channel Relay Module

The 4-channel relay module (specifications: 5V trigger voltage, 10A contact rating) acts as the switching interface between the Arduino control signals and the laser power distribution.

### Relay Module Pin Configuration

The module typically features the following connections per channel:

- **Control side**: VCC, GND, IN1, IN2, IN3, IN4
- **Contact side (per relay)**: COM (common), NO (normally open), NC (normally closed)

### Wiring Procedure

**Step 1: Power the relay module**

1. Connect relay module VCC to Arduino 5V pin
2. Connect relay module GND to Arduino GND pin

**Step 2: Connect control signals**

1. Connect relay IN1 to Arduino digital **pin 8** using a **red** Dupont wire
2. Connect relay IN2 to Arduino digital **pin 9** using a **blue** Dupont wire
3. Connect relay IN3 to Arduino digital **pin 10** using a **green** Dupont wire
4. Leave IN4 unconnected (reserved for future expansion)

**Step 3: Connect power switching contacts**

For each relay channel (1-3):

1. Connect power from the DIN rail terminal block positive output to the COM terminal of Relay 1, Relay 2, and Relay 3
   - You can wire these in parallel from the DIN rail outputs
   - Alternatively, daisy-chain from one COM terminal to the next

2. Connect the NO (normally open) terminal of each relay to the positive terminal of its corresponding laser:
   - Relay 1 NO → Laser 1 positive (1064nm)
   - Relay 2 NO → Laser 2 positive (1310nm)
   - Relay 3 NO → Laser 3 positive (1550nm)

**Step 4: Common ground connection**

Connect ground from the DIN rail terminal block to the negative terminal of all three lasers:

- Ground rail → Laser 1 negative
- Ground rail → Laser 2 negative
- Ground rail → Laser 3 negative

This can be accomplished using the DIN rail terminal block outputs or by daisy-chaining connections.

### Relay Logic

The relay module used in this system operates with **active-high** logic:
- Control signal **LOW (0V)** → Relay de-energised → Laser **OFF**
- Control signal **HIGH (5V)** → Relay energised → Laser **ON**

## 3.4 Arduino UNO R4 Minima Connection

The Arduino UNO R4 Minima serves as the microcontroller interface between the GUI software and the relay module.

### Arduino Setup

1. **Verify firmware compatibility**: The Arduino UNO R4 Minima uses the Renesas RA4M1 microcontroller and is fully compatible with Arduino IDE and standard Arduino libraries.

2. **USB connection**: Connect the Arduino to your computer using a USB-A to USB-C cable. The Arduino will be powered via USB during programming and can remain USB-powered during operation.

3. **Digital I/O connections**: Connect digital output pins to the relay module IN1, IN2, IN3 terminals using colour-coded Dupont wires.

4. **Power connections**: Connect Arduino 5V and GND to the relay module VCC and GND respectively.

### Pin Assignment (firmware configuration)

| Arduino Pin | Wire Colour | Function | Connection |
|-------------|-------------|----------|------------|
| Digital 8 | Red | Laser 1 control (1064nm) | Relay IN1 |
| Digital 9 | Blue | Laser 2 control (1310nm) | Relay IN2 |
| Digital 10 | Green | Laser 3 control (1550nm) | Relay IN3 |
| 5V | - | Relay power | Relay VCC |
| GND | - | Common ground | Relay GND |
| USB | - | Communication | Host computer |


## 3.5 Laser Diode Module Connections

The three pigtailed laser diodes require both electrical power connections and optical fibre management.

### Electrical Connections Using DC Barrel Jack Adapters

Each laser module typically features a DC barrel jack power input. To connect to the power distribution system:

**Components needed per laser:**
- 1× DC Barrel Jack Adapter - Male (5.5×2.1mm with screw terminals)

**Connection procedure:**

1. **Prepare male barrel jack adapters**: You'll need three male DC barrel jack adapters, one for each laser

2. **Wire positive connections**:
   - Connect the positive screw terminal of Adapter 1 to Relay 1 NO terminal
   - Connect the positive screw terminal of Adapter 2 to Relay 2 NO terminal
   - Connect the positive screw terminal of Adapter 3 to Relay 3 NO terminal

3. **Wire negative connections**:
   - Connect all three negative screw terminals to the common ground rail (from DIN rail terminal block)
   - These can be daisy-chained or connected individually

4. **Connect to lasers**:
   - Plug Male Adapter 1 into Laser 1 (1064nm) power jack
   - Plug Male Adapter 2 into Laser 2 (1310nm) power jack
   - Plug Male Adapter 3 into Laser 3 (1550nm) power jack

5. **Verify polarity**: Ensure centre pin is positive on all connections

6. **Label**: Clearly label each adapter with its wavelength (1064nm, 1310nm, 1550nm)

> **💡 No Soldering Required**
> The DC barrel jack adapters with screw terminals eliminate the need for soldering, making assembly and maintenance simpler and allowing for easy component replacement.

### Optical Fibre Management

1. **Protect fibre connectors**: Keep protective caps on all FC/APC or FC/PC connectors until ready for use
2. **Minimum bend radius**: Maintain a minimum bend radius of 30mm for the fibre pigtails to prevent optical power loss or fibre damage
3. **Secure routing**: Use cable ties and adhesive-backed cable mounts to secure fibre pigtails within the enclosure, avoiding stress on the laser module itself

## 3.6 Optical Components Integration (Isolators and Couplers)

The system includes optical isolators and 90:10 fibre couplers for advanced optical configurations. These components are passive optical devices and require no electrical connections.

### Optical Isolators

**Purpose**: Optical isolators prevent back-reflections from re-entering the laser cavity, which can cause instability, noise, or damage to the laser diode.

**Installation guidance:**

1. **Orientation**: Isolators are directional devices. Ensure light propagates in the correct direction (typically indicated by an arrow on the housing or marked "input" and "output" ports)

2. **Wavelength-specific isolators**:
   - 1064nm isolator → Use with Laser 1 (1064nm)
   - 1310nm/1550nm isolators → Use with Laser 2 (1310nm) and Laser 3 (1550nm)

3. **Connection**:
   - Connect laser output pigtail to isolator input port
   - Connect isolator output to downstream optical system or coupler

4. **Insertion loss**: Typical isolators introduce 0.5-1.0 dB insertion loss. Verify optical power output after installation.

### Fibre Couplers (90:10 Split Ratio)

**Purpose**: The 90:10 fibre couplers split optical signals, directing 90% of the input light to the main output port and 10% to a tap port. This is useful for monitoring laser power whilst delivering most of the optical power to your experiment.

**Installation guidance:**

1. **Port identification**: Clearly identify and label:
   - **Input port**: Connects to isolator output or laser output
   - **90% output port**: Main output to experimental setup
   - **10% tap port**: Monitoring/reference output

2. **Typical configuration**:
   ```
   Laser → Isolator → Coupler (input)
                         ├→ 90% output (to experiment)
                         └→ 10% tap (to power metre/monitoring)
   ```

3. **Insertion loss**: Account for:
   - Theoretical splitting loss: ~0.5 dB at 90% port, ~10 dB at 10% port
   - Excess loss: typically 0.1-0.3 dB
   - Example: 10mW input → ~9mW at 90% port, ~1mW at 10% tap port

4. **Wavelength range**: Verify coupler specifications match your laser wavelengths (1064nm, 1310nm, 1550nm)

**Example system configuration:**

```
Laser 1 (1064nm, 10mW) → Isolator → 90:10 Coupler → 90% Output (~9mW)
                                                   → 10% Tap (~1mW, monitoring)

Laser 2 (1310nm, 10mW) → Isolator → 90:10 Coupler → 90% Output (~9mW)
                                                   → 10% Tap (~1mW, monitoring)

Laser 3 (1550nm, 10mW) → Isolator → 90:10 Coupler → 90% Output (~9mW)
                                                   → 10% Tap (~1mW, monitoring)
```

This configuration allows continuous power monitoring via the 10% taps whilst delivering maximum power to your experimental setup through the 90% outputs.

---

# 4. Arduino Firmware

## 4.1 Firmware Overview

The Arduino firmware provides the communication interface between the host computer's GUI and the relay control hardware. It receives serial commands and translates them into digital output signals that control the relay module.

**Firmware location**: The firmware is available in the project repository at:  
https://github.com/bongkokwei/multilaser-box/blob/main/laser_ttl_controller.ino

**Firmware responsibilities:**

- Initialise serial communication at 9600 baud
- Parse incoming serial commands (case-insensitive)
- Control digital outputs (pins 8, 9, 10) connected to relay channels
- Send detailed status responses for each command
- Maintain failsafe default state (all lasers OFF on power-up/reset)
- Provide configuration information and runtime diagnostics

**Pin configuration:**
- Pin 8 (red wire): Laser 1 control (1064nm)
- Pin 9 (blue wire): Laser 2 control (1310nm)
- Pin 10 (green wire): Laser 3 control (1550nm)

**TTL Logic:**
- HIGH (5V) signal = Laser ON
- LOW (0V) signal = Laser OFF

**Communication protocol:**

| Command | Function | Example Response |
|---------|----------|------------------|
| `1` | Toggle Laser 1 | `Laser 1 (Pin 8) is now ON (Signal: HIGH)` |
| `2` | Toggle Laser 2 | `Laser 2 (Pin 9) is now OFF (Signal: LOW)` |
| `3` | Toggle Laser 3 | `Laser 3 (Pin 10) is now ON (Signal: HIGH)` |
| `all_on` | Turn all lasers ON | `All active lasers turned ON` |
| `all_off` | Turn all lasers OFF | `All lasers turned OFF` |
| `status` | Query current states | Multi-line status report |
| `config` | Show configuration | Configuration details |

**Advanced commands** (for diagnostics and reconfiguration):
- `set_pin X Y` - Reassign laser X to pin Y
- `set_logic X Y` - Change TTL logic level (requires recompile)

The firmware is highly configurable and includes built-in diagnostics, making it suitable for various relay module types and TTL logic requirements.

## 4.2 Uploading the Firmware to Arduino UNO R4 Minima

### Prerequisites

1. **Arduino IDE**: Download and install the Arduino IDE (version 2.0 or later recommended) from https://www.arduino.cc/en/software

2. **Board support**: The Arduino UNO R4 Minima is supported in Arduino IDE 2.0+. If using an older IDE version, you may need to add board support through the Boards Manager.

3. **Drivers**: Modern operating systems typically recognise the Arduino UNO R4 Minima automatically. If not detected, install the appropriate USB drivers for your operating system.

### Upload Procedure

**Step 1: Download the firmware**

1. Navigate to the repository: https://github.com/bongkokwei/multilaser-box
2. Download the `laser_ttl_controller.ino` file

**Step 2: Open the firmware**

1. Launch Arduino IDE
2. Navigate to `File > Open`
3. Browse to the downloaded `laser_ttl_controller.ino` file
4. Open the file

**Step 3: Configure the IDE**

1. Select board: `Tools > Board > Arduino UNO R4 Minima`
2. Select port: `Tools > Port > [Your Arduino's COM port]`
   - Windows: COM3, COM4, etc.
   - macOS: /dev/cu.usbmodem[xxxxx]
   - Linux: /dev/ttyACM0 or /dev/ttyUSB0

**Step 4: Verify the code**

1. Click the "Verify" button (checkmark icon) to compile the firmware
2. Check for any compilation errors in the console
3. Verify that compilation completes with "Done compiling" message

**Step 5: Upload the firmware**

1. Click the "Upload" button (right arrow icon)
2. Wait for the upload process to complete
3. The Arduino's built-in LED should flash during upload
4. Upon successful upload, you should see "Done uploading" message

**Step 6: Test serial communication**

1. Open the Serial Monitor: `Tools > Serial Monitor`
2. Set baud rate to `9600`
3. Set line ending to `Newline` or `No line ending` (depending on firmware implementation)
4. Send a test command to verify the Arduino responds correctly

## 4.3 Serial Communication Protocol

The firmware implements a text-based serial protocol with detailed status feedback for reliable communication between the GUI and Arduino.

### Command Format

Commands are text strings that can be sent with or without line endings. The firmware automatically converts commands to lowercase and removes whitespace for consistent processing.

### Basic Control Commands

**Individual Laser Toggle:**

```
Command: '1'
Response: "Laser 1 (Pin 8) is now ON (Signal: HIGH)"
Function: Toggles Laser 1 (1064nm) between ON and OFF states

Command: '2'
Response: "Laser 2 (Pin 9) is now OFF (Signal: LOW)"
Function: Toggles Laser 2 (1310nm) between ON and OFF states

Command: '3'
Response: "Laser 3 (Pin 10) is now ON (Signal: HIGH)"
Function: Toggles Laser 3 (1550nm) between ON and OFF states
```

**Bulk Control Commands:**

```
Command: 'all_on'
Response: "All active lasers turned ON"
Function: Turns all three lasers ON simultaneously

Command: 'all_off'
Response: "All lasers turned OFF"
Function: Turns all three lasers OFF simultaneously
```

### Status and Diagnostics Commands

**Status Query:**

```
Command: 'status'
Response: 
"=== Current Laser Status ===
Laser 1 (Pin 8): ON  [Signal: HIGH]
Laser 2 (Pin 9): OFF [Signal: LOW]
Laser 3 (Pin 10): ON  [Signal: HIGH]"
Function: Reports current state of all lasers
```

**Configuration Query:**

```
Command: 'config'
Response:
"=== Current Configuration ===
Number of active lasers: 3
Laser ON signal: HIGH (5V)
Laser OFF signal: LOW (0V)

Pin Assignments:
  Laser 1: Pin 8
  Laser 2: Pin 9
  Laser 3: Pin 10
=============================="
Function: Displays current firmware configuration
```

### Advanced Commands

**Reconfigure Pin Assignment:**

```
Command: 'set_pin 1 12'
Response: "Laser 1 moved from pin 8 to pin 12"
Function: Reassigns Laser 1 control to pin 12 (useful for troubleshooting)
```

**Query Logic Configuration:**

```
Command: 'set_logic 0 1'
Response: Information about current TTL logic configuration
Function: Displays logic level settings (requires recompile to change)
```

### Communication Parameters

| Parameter | Value |
|-----------|-------|
| Baud rate | 9600 bps |
| Data bits | 8 |
| Parity | None |
| Stop bits | 1 |
| Flow control | None |
| Case sensitivity | No (commands converted to lowercase) |
| Line ending | Optional (CR, LF, or CRLF) |

### Control Logic

The firmware controls relay pins with active-high logic:
- **Pin HIGH** (5V) → Relay energised → Laser ON
- **Pin LOW** (0V) → Relay de-energised → Laser OFF

### Timing Characteristics

- Command processing time: <1ms
- Response transmission time: ~10ms (depends on message length)
- Relay switching time: 5-10ms (relay-dependent)
- Total response time: <20ms from command to laser state change

### Error Handling

The firmware provides user-friendly error responses:

```
Invalid command → "Unknown command. Type 'config' to see available commands."
Invalid laser number → "Invalid laser number. Use 1-3"
Invalid pin number → "Invalid pin number. Use pins 2-13"
```

### Example Communication Session

```
Host → Arduino: 'config'
Arduino → Host: [Configuration details displayed]

Host → Arduino: '1'
Arduino → Host: 'Laser 1 (Pin 8) is now ON (Signal: HIGH)'

Host → Arduino: 'status'
Arduino → Host: 
"=== Current Laser Status ===
Laser 1 (Pin 8): ON  [Signal: HIGH]
Laser 2 (Pin 9): OFF [Signal: LOW]
Laser 3 (Pin 10): OFF [Signal: LOW]"

Host → Arduino: 'all_on'
Arduino → Host: 'All active lasers turned ON'

Host → Arduino: 'all_off'
Arduino → Host: 'All lasers turned OFF'
```

## 4.4 Verifying Firmware Operation

After uploading the firmware, perform these verification tests before connecting the GUI software.

### Test 1: Firmware Initialisation

1. Open Serial Monitor in Arduino IDE (9600 baud)
2. Press the Arduino reset button
3. You should see the initialisation message:
   ```
   === Configurable Arduino Laser TTL Controller ===
   === Current Configuration ===
   Number of active lasers: 3
   Laser ON signal: HIGH (5V)
   Laser OFF signal: LOW (0V)
   
   Pin Assignments:
     Laser 1: Pin 8
     Laser 2: Pin 9
     Laser 3: Pin 10
   ==============================
   
   TTL Logic Configuration:
     Laser ON signal: HIGH (5V)
     Laser OFF signal: LOW (0V)
   
   Available Commands:
     '1', '2', '3'     - Toggle individual lasers
     'all_on'          - Turn all lasers ON
     'all_off'         - Turn all lasers OFF
     'status'          - Show current laser states
     'config'          - Display configuration
     'set_pin X Y'     - Set laser X to use pin Y
     'set_logic X Y'   - Set laser ON signal (0=LOW, 1=HIGH)
   Setup complete.
   ```

4. This confirms the firmware is running correctly

### Test 2: Configuration Verification

1. Send command: `config`
2. Verify response shows correct pin assignments (8, 9, 10)
3. Verify TTL logic is set to HIGH=ON, LOW=OFF
4. Confirm 3 active lasers are configured

**Expected output:**
```
=== Current Configuration ===
Number of active lasers: 3
Laser ON signal: HIGH (5V)
Laser OFF signal: LOW (0V)

Pin Assignments:
  Laser 1: Pin 8
  Laser 2: Pin 9
  Laser 3: Pin 10
==============================
```

### Test 3: Status Query

1. Send command: `status`
2. Verify all lasers report OFF state initially

**Expected output:**
```
=== Current Laser Status ===
Laser 1 (Pin 8): OFF [Signal: LOW]
Laser 2 (Pin 9): OFF [Signal: LOW]
Laser 3 (Pin 10): OFF [Signal: LOW]
```

### Test 4: Individual Relay Control

1. Send command: `1`
2. Observe: Relay 1 should click and LED should illuminate
3. Verify response: `Laser 1 (Pin 8) is now ON (Signal: HIGH)`
4. Send command: `1` again to toggle OFF
5. Verify response: `Laser 1 (Pin 8) is now OFF (Signal: LOW)`
6. Observe: Relay 1 should click again, LED should extinguish
7. Repeat for commands `2` and `3` to test all channels

**Verification checklist:**
- [ ] Relay 1 clicks when toggling Laser 1
- [ ] Relay 2 clicks when toggling Laser 2
- [ ] Relay 3 clicks when toggling Laser 3
- [ ] LED indicators on relay module correspond to states
- [ ] Serial responses match expected format

### Test 5: Bulk Commands

1. Send command: `all_on`
2. Observe: All three relays should activate simultaneously
3. Verify response: `All active lasers turned ON`
4. Send command: `status` to verify all show ON
5. Send command: `all_off`
6. Observe: All three relays should deactivate
7. Verify response: `All lasers turned OFF`

**Expected status after all_on:**
```
=== Current Laser Status ===
Laser 1 (Pin 8): ON  [Signal: HIGH]
Laser 2 (Pin 9): ON  [Signal: HIGH]
Laser 3 (Pin 10): ON  [Signal: HIGH]
```

### Test 6: Error Handling

1. Send an invalid command: `xyz`
2. Verify response: `Unknown command. Type 'config' to see available commands.`
3. This confirms error handling is working correctly

### Test 7: Laser Power Verification

> **⚠️ Safety First**
> Wear appropriate laser safety eyewear before performing this test. Never look into the fibre output or point the laser at reflective surfaces.

**For each laser:**

1. Connect optical power metre to laser output
2. Send command to turn laser ON (e.g., `1` for Laser 1)
3. Verify:
   - Serial response indicates ON state
   - Relay clicks audibly
   - Optical power metre reads ~10mW ±20%
4. Send same command again to toggle OFF
5. Verify:
   - Serial response indicates OFF state
   - Relay clicks again
   - Power reading drops to <0.1mW

**Power verification table:**

| Laser | Wavelength | Expected Power (ON) | Acceptable Range |
|-------|------------|---------------------|------------------|
| 1 | 1064nm | 10mW | 8-12mW |
| 2 | 1310nm | 10mW | 8-12mW |
| 3 | 1550nm | 10mW | 8-12mW |

### Test 8: Advanced Commands (Optional)

Test the pin reassignment function:

1. Send command: `set_pin 1 12`
2. Verify response: `Laser 1 moved from pin 8 to pin 12`
3. Test if Laser 1 control now works on pin 12
4. Restore original configuration: `set_pin 1 8`
5. Verify response: `Laser 1 moved from pin 12 to pin 8`

> **💡 Note**
> Pin reassignment is useful for troubleshooting but should be restored to the default configuration (8, 9, 10) for normal operation with the GUI.

### Troubleshooting Verification Failures

**No serial response:**
- Check baud rate is set to 9600
- Verify correct COM port is selected
- Try pressing Arduino reset button
- Check USB cable connection

**Relays not clicking:**
- Verify relay module is powered (VCC and GND connected)
- Check Dupont wire connections (pins 8, 9, 10)
- Measure voltage at Arduino pins: should read ~5V when HIGH, ~0V when LOW
- Test with multimetre: measure voltage at relay IN1, IN2, IN3 terminals

**Inconsistent relay behaviour:**
- Verify firmware TTL logic matches relay module requirements
- Some relay modules are active-low; if yours is, you'll need to modify the firmware constants
- Check for loose connections in Dupont wires

**No optical power output:**
- Verify laser power connections (DC barrel jack adapters)
- Check continuity from relay NO terminal to laser positive terminal
- Verify ground connections are secure
- Measure voltage at laser DC jack when relay is ON: should read ~5V

If all tests pass, the firmware is correctly configured and ready for GUI operation. Proceed to Section 5 for software installation.

---

# 5. Software Installation

## 5.1 Creating a Standalone Executable (Optional)

For deployment to computers without Python installed, you can compile the GUI into a standalone executable using PyInstaller.

### Why Create an Executable?

**Advantages:**
- No Python installation required on target computer
- Simplified deployment (single file to distribute)
- Reduced potential for dependency conflicts
- Professional appearance for end users

**Disadvantages:**
- Larger file size (50-100 MB vs. ~10 KB source code)
- Platform-specific (Windows .exe won't run on macOS)
- Longer compile time (~1-2 minutes)
- More difficult to modify/update

### Installation and Compilation

**Step 1: Install PyInstaller**

```bash
pip install pyinstaller
```

**Step 2: Compile the application**

From the repository directory:

```bash
pyinstaller --onefile --windowed --name="LaserController" laser_controller_gui.py
```

**Command options explained:**

- `--onefile`: Bundles everything into a single executable file
- `--windowed`: Hides the console window (GUI applications only)
- `--name="LaserController"`: Sets the executable name

**Step 3: Wait for compilation**

PyInstaller will:
1. Analyse dependencies
2. Bundle Python interpreter
3. Package all required libraries
4. Create executable

This process takes 1-2 minutes and produces substantial console output.

**Step 4: Locate the executable**

The compiled executable is in the `dist/` folder:

- **Windows**: `dist/LaserController.exe`
- **macOS**: `dist/LaserController.app` or `dist/LaserController`
- **Linux**: `dist/LaserController`

**Step 5: Test the executable**

1. Navigate to the `dist/` folder
2. Double-click the executable to launch
3. Verify all functionality works as expected
4. Test COM port detection and connection

### Distribution

To distribute the application:

1. Copy the executable from `dist/` to target computer
2. No additional files or installation required
3. User simply double-clicks to run

> **💡 Tip**
> The `build/` and `dist/` folders, as well as the `.spec` file, can be deleted after compilation if you only need the executable. Keep the `.spec` file if you plan to recompile with modified settings.

### Advanced Compilation Options

**Add an icon (Windows):**

```bash
pyinstaller --onefile --windowed --icon=icon.ico --name="LaserController" laser_controller_gui.py
```

**Include additional files:**

If you need to bundle additional resources (images, configuration files):

```bash
pyinstaller --onefile --windowed --add-data "config.txt;." --name="LaserController" laser_controller_gui.py
```

(On macOS/Linux, use `:` instead of `;`)

**Console version (for debugging):**

Remove the `--windowed` flag to create a version that shows a console window, useful for debugging:

```bash
pyinstaller --onefile --name="LaserController" laser_controller_gui.py
```

---

# 6. Operation

## 6.1 Initial Setup and Connection

Before first use, ensure the hardware is properly assembled (Section 3) and the firmware is uploaded to the Arduino (Section 4).

### Pre-Operation Checklist

- [ ] All wiring connections are secure and properly insulated
- [ ] Arduino firmware is uploaded and verified
- [ ] Power supply is connected but not yet switched on
- [ ] Appropriate laser safety eyewear is available
- [ ] Optical output fibres are secured and not pointed at personnel
- [ ] Laboratory door signage indicates laser operation
- [ ] Emergency stop procedures are understood by all users

### Initial Power-Up Sequence

1. **Connect Arduino to computer**: Connect the USB cable between the Arduino and your host computer

2. **Verify Arduino power**: The Arduino's built-in LED should illuminate, indicating USB power

3. **Launch the GUI application**: 
   - From source: `python laser_controller_gui.py`
   - From executable: Double-click `LaserController.exe` (or equivalent)

4. **Apply main power**: Switch on the 5V plugpack power supply

5. **Verify relay power**: Some relay modules have LED indicators that should illuminate when powered

## 6.2 GUI Overview and Interface Elements

![Multi-laser GUI](./figures/multilaser_gui.svg)

The Multi-Laser Controller GUI provides an intuitive interface organised into several functional areas.

### Interface Layout

**Top Section: Connection Controls**
- **COM Port dropdown**: Selects the Arduino's serial port
- **Refresh button** (circular arrow icon): Rescans for available COM ports
- **Baud Rate dropdown**: Selects communication speed (default: 9600)
- **Connect button** (green): Establishes serial connection

**Middle Section: Individual Laser Controls**
- **Three status indicators**: Circular LED-style indicators showing OFF (grey) or ON (green)
- **Laser labels**: "Laser 1", "Laser 2", "Laser 3"
- **Toggle buttons**: "Toggle Laser 1", "Toggle Laser 2", "Toggle Laser 3"

**Bottom Section: Bulk Control and Emergency**
- **All ON button**: Activates all three lasers simultaneously
- **All OFF button**: Deactivates all three lasers simultaneously
- **EMERGENCY STOP button** (red, with warning icon): Immediately turns off all lasers with confirmation

**Status Bar**
- Displays current connection status: "Connected" or "Disconnected"

### Visual Status Indicators

**Status Indicator Colours:**
- **Grey**: Laser is OFF (relay de-energised)
- **Green**: Laser is ON (relay energised, optical output active)

**Button States:**
- **Enabled** (normal colour): Button is clickable
- **Disabled** (greyed out): Button is not clickable (typically when disconnected)

## 6.3 COM Port and Baud Rate Selection

Before connecting, you must select the correct COM port corresponding to your Arduino.

### Identifying the COM Port

**Windows:**

1. Open Device Manager (`Win + X`, then select "Device Manager")
2. Expand "Ports (COM & LPT)"
3. Look for "USB Serial Device" or "Arduino UNO R4 Minima"
4. Note the COM port number (e.g., "COM3")

**macOS:**

1. Open Terminal
2. List devices: `ls /dev/cu.*`
3. Look for `/dev/cu.usbmodem[xxxxx]` or `/dev/cu.usbserial-[xxxxx]`

**Linux:**

1. Open Terminal
2. List devices: `ls /dev/tty*`
3. Look for `/dev/ttyACM0` or `/dev/ttyUSB0`
4. If permissions are denied, add yourself to the `dialout` group:
   ```bash
   sudo usermod -a -G dialout $USER
   ```
   (Requires logout/login to take effect)

### Selecting in GUI

1. Click the **COM Port dropdown** in the GUI
2. Available ports are automatically detected and listed
3. Select your Arduino's port from the list
4. If your port doesn't appear, click the **Refresh button** (circular arrow)

### Baud Rate Selection

The baud rate must match the firmware configuration (default: 9600 bps).

1. Click the **Baud Rate dropdown**
2. Select `9600` (unless you've modified the firmware)

Common baud rates available:
- 9600 (default)
- 19200
- 38400
- 57600
- 115200

> **💡 Tip**
> If you experience communication errors or garbled responses, verify that the baud rate in the GUI matches the baud rate set in the Arduino firmware (`Serial.begin(9600)` in the code).

## 6.4 Connecting to the Device

Once the COM port and baud rate are selected, establish the connection.

### Connection Procedure

**Step 1: Click Connect**

1. Click the large green **Connect** button
2. The application attempts to open the serial port
3. Wait for connection confirmation (typically <1 second)

**Step 2: Verify Connection**

Upon successful connection:
- The status bar changes from "Disconnected" to "Connected"
- The Connect button becomes a **Disconnect** button
- All laser control buttons become enabled (no longer greyed out)
- The Arduino automatically initialises all lasers to OFF state
- All three status indicators should show grey (OFF)

**Connection Error Handling:**

If connection fails, a dialogue box appears with an error message. Common errors:

**"Could not open port"**
- Another application is using the serial port (close other terminal software)
- Incorrect COM port selected (verify in Device Manager)
- Insufficient permissions (Linux: check `dialout` group membership)

**"Arduino not responding"**
- USB cable is disconnected or faulty
- Arduino is not powered
- Firmware is not uploaded or has crashed (reset Arduino and retry)

**"Timeout"**
- Baud rate mismatch (verify 9600 baud in both GUI and firmware)
- Faulty USB cable
- Serial buffer corruption (disconnect, wait 5 seconds, reconnect)

### Reconnection

If the connection is lost (cable unplugged, Arduino reset, etc.):

1. Click **Disconnect** if still showing connected
2. Wait 2-3 seconds
3. Click **Connect** again
4. Verify all lasers initialise to OFF state

## 6.5 Emergency Stop Function

The Emergency Stop provides a failsafe mechanism to immediately shut down all lasers.

### Purpose

The Emergency Stop is designed for:
- Unexpected hazards in the optical path
- Personnel entering the laser safety zone unexpectedly
- Equipment malfunction or unusual behaviour
- Accidental exposure risks
- Immediate cessation required for any reason

### Operation

**Procedure:**

1. Click the **⚠ EMERGENCY STOP** button (large red button)
2. A confirmation dialogue appears: "Emergency Stop: Turn off all lasers?"
3. Click **Yes** to confirm
4. All lasers immediately turn OFF
5. All status indicators turn grey

**Timing:**
- From button click to laser shutdown: ~20-30ms (includes dialogue confirmation)
- If confirmation is bypassed (future firmware modification), shutdown could be instantaneous

### Confirmation Dialogue

The confirmation dialogue prevents accidental activation whilst still providing rapid response when needed.

**To bypass confirmation** (for extremely time-critical applications):

Modify the `emergency_stop()` method in `laser_controller_gui.py` to remove the confirmation dialogue and call `turn_all_off()` directly. However, this increases the risk of accidental activation.

### After Emergency Stop

After an emergency stop:
- All lasers remain OFF until manually reactivated
- The connection remains active
- You can use individual toggle buttons or All ON to resume operation
- No automatic reactivation occurs
- The system does not "remember" the previous state

### Hardware Emergency Stop (Recommended Addition)

For maximum safety, consider adding a physical emergency stop button wired to:
- Cut mains power to the 5V supply, **OR**
- Interrupt Arduino 5V supply (relay module loses power, all relays de-energise)

Physical emergency stops provide hardware-level redundancy independent of software control.

## 6.6 Status Indicators

The GUI provides real-time visual feedback on system state.

### LED-Style Indicators

Three circular status indicators at the top of each laser control section provide at-a-glance status:

**Grey indicator**: Laser is OFF
- Relay is de-energised
- No optical output
- Safe state

**Green indicator**: Laser is ON
- Relay is energised
- Optical output active
- Observe laser safety protocols

### Connection Status

Bottom left status bar displays current connection state:

- **"Disconnected"**: No serial connection to Arduino
- **"Connected"**: Active serial connection established

### Button State Feedback

Buttons change appearance based on availability:

- **Enabled buttons**: Normal colour, clickable
- **Disabled buttons**: Greyed out, not clickable (when disconnected)

### No Optical Power Display

The GUI does not display actual optical power levels. It shows commanded state only (relay ON/OFF), not measured optical output. Use separate optical power metres for power verification.

## 6.7 Disconnecting Safely

Always disconnect properly before closing the application or disconnecting hardware.

### Disconnect Procedure

**Step 1: Turn off all lasers**

1. Click **All OFF** button
2. Verify all status indicators are grey
3. Wait for all relays to de-energise (listen for clicks)

**Step 2: Disconnect serial connection**

1. Click the **Disconnect** button (replaces Connect button when connected)
2. The serial port is closed
3. Status bar changes to "Disconnected"
4. All control buttons become disabled (greyed out)

**Step 3: Safe to disconnect hardware**

Now it's safe to:
- Unplug the USB cable
- Power off the 5V supply
- Access the optical setup

### Automatic Shutdown on Disconnect

When you click Disconnect, the GUI automatically sends an "All OFF" command before closing the serial port, ensuring lasers are not left in an ON state.

### Closing the Application

**Proper shutdown sequence:**

1. Turn all lasers OFF
2. Click Disconnect
3. Close the GUI window (click X or File > Exit)

**If you close without disconnecting:**

The GUI attempts to send an "All OFF" command and close the serial port gracefully. However, it's better practice to disconnect explicitly before closing.

### Emergency Hardware Disconnect

If you must disconnect the USB cable whilst lasers are ON (e.g., computer crash):

1. **Turn off mains power first** (switch off the 5V plugpack)
2. Then disconnect USB cable
3. This ensures lasers are off before communication is lost

> **⚠️ Important**
> Disconnecting the USB whilst lasers are ON may leave them in their current state (ON) if the relay module has latching behaviour or remains powered. Always turn lasers OFF via software before disconnecting hardware.

---

# 7. Appendices

## Appendix A: Complete Wiring Diagrams

### System Architecture Diagram

![System Architecture Diagram](./figures/system_architecture_diagram.svg)


### Arduino to Relay Control Connections

![Arduino to Relay Control Connections](./figures/arduino_relay_control.svg)


### Signal Flow Diagram

![Signal Flow Diagram](./figures/signal_flow_diagram.svg)



<!-- ### Complete Optical System Block Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                          240V AC Mains                            │
└────────────────────────────────┬─────────────────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   5V DC 4A Plugpack     │
                    │   (Switchmode PSU)      │
                    └────────────┬────────────┘
                                 │ 2.1mm DC jack
                    ┌────────────▼────────────┐
                    │  DC Barrel Jack Adapter │
                    │  (Female, screw term)   │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │  DIN Rail Terminal      │
                    │  Block (2in/8out)       │
                    └────────┬────────────────┘
                             │ 5V distribution
                    ┌────────┴────────┐
                    │                 │
           ┌────────▼────────┐       ┌───────▼────────┐
           │  Arduino UNO    │       │  Relay Module  │
           │  R4 Minima      │       │  (4 channels)  │
           │                 │       │                │
           │  USB ←→ PC      │       │  VCC ← 5V      │
           │  Pin8→ IN1      │───────┤  IN1 (red)     │
           │  Pin9→ IN2      │───────┤  IN2 (blue)    │
           │  Pin10→ IN3     │───────┤  IN3 (green)   │
           │  GND ← → GND    │       │  GND           │
           └─────────────────┘       └───────┬────────┘
                                             │ Switched 5V
                                             │ (via barrel jacks)
                              ┌──────────────┼──────────────┐
                              │              │              │
                    ┌─────────▼───┐   ┌──────▼────┐  ┌─────▼──────┐
                    │  Laser 1    │   │  Laser 2  │  │  Laser 3   │
                    │  1064nm     │   │  1310nm   │  │  1550nm    │
                    │  10mW       │   │  10mW     │  │  10mW      │
                    │             │   │           │  │            │
                    │  → Isolator │   │ →Isolator │  │ →Isolator  │
                    │  → 90:10    │   │ → 90:10   │  │ → 90:10    │
                    │    Coupler  │   │   Coupler │  │   Coupler  │
                    │      ├90%→  │   │     ├90%→ │  │     ├90%→  │
                    │      └10%→  │   │     └10%→ │  │     └10%→  │
                    └─────────────┘   └───────────┘  └────────────┘
                         (tap)             (tap)          (tap)
``` -->

---

**End of Manual**

*Document Version: 1.0*  
*Last Updated: 2025*  
*Repository: https://github.com/bongkokwei/multilaser-box*