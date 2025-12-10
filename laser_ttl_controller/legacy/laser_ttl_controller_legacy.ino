/*
 * Configurable Arduino Laser TTL Control Script
 * Controls up to 3 lasers with configurable TTL logic and pin assignments
 * 
 * Hardware Requirements:
 * - Arduino (Uno, Nano, Pro Mini, etc.)
 * - Digital output pins connected to laser TTL inputs
 * - External power supply for lasers
 * 
 * Configuration Section Below - Modify as needed
 */

// ===== CONFIGURATION SECTION =====
// Modify these values to match your hardware setup

// Pin assignments for each laser (change to any available digital pins)
const int LASER1_PIN = 8;   // Change this to your desired pin for Laser 1
const int LASER2_PIN = 9;   // Change this to your desired pin for Laser 2
const int LASER3_PIN = 10;  // Change this to your desired pin for Laser 3

// TTL Logic Configuration
// Set what voltage levels turn lasers ON and OFF
// UPDATED: Based on your new laser requirements
const int LASER_ON_SIGNAL = LOW;  // HIGH (5V) turns laser ON
const int LASER_OFF_SIGNAL = HIGH;  // LOW (0V) turns laser OFF

// Alternative configurations (uncomment the one you need):
// For active-low lasers: LASER_ON_SIGNAL = LOW, LASER_OFF_SIGNAL = HIGH
// For active-high lasers: LASER_ON_SIGNAL = HIGH, LASER_OFF_SIGNAL = LOW

// Number of active lasers (1, 2, or 3)
const int NUM_LASERS = 3;


// ===== END CONFIGURATION SECTION =====

// Status LED pin (built-in LED on most Arduino boards)
const int STATUS_LED = 13;

// Timing variables for non-blocking patterns
unsigned long previousMillis = 0;
int patternStep = 0;

// Array to store laser pin numbers for easier iteration
int laserPins[] = {LASER1_PIN, LASER2_PIN, LASER3_PIN};

void setup() {
  // Initialize serial communication
  Serial.begin(9600);
  Serial.println("=== Configurable Arduino Laser TTL Controller ===");
  
  // Display current configuration
  printConfiguration();
  
  // Configure laser control pins as outputs
  for (int i = 0; i < NUM_LASERS; i++) {
    pinMode(laserPins[i], OUTPUT);
    digitalWrite(laserPins[i], LASER_OFF_SIGNAL); // Start with all lasers OFF
  }
  
  // Configure status LED
  pinMode(STATUS_LED, OUTPUT);
  digitalWrite(STATUS_LED, LOW);
  
  Serial.println("TTL Logic Configuration:");
  Serial.print("  Laser ON signal: ");
  Serial.println(LASER_ON_SIGNAL == HIGH ? "HIGH (5V)" : "LOW (0V)");
  Serial.print("  Laser OFF signal: ");
  Serial.println(LASER_OFF_SIGNAL == HIGH ? "HIGH (5V)" : "LOW (0V)");
  Serial.println();
  Serial.println();
  Serial.println("Available Commands:");
  Serial.println("  '1', '2', '3'     - Toggle individual lasers (only one at a time)");
  Serial.println("  'all_off'         - Turn all lasers OFF");
  Serial.println("  'status'          - Show current laser states");
  Serial.println("  'config'          - Display configuration");
  Serial.println("  'set_pin X Y'     - Set laser X to use pin Y");
  Serial.println("  'set_logic X Y'   - Set laser ON signal (0=LOW, 1=HIGH)");
  Serial.println("Setup complete.");
  Serial.println();
}

void loop() {
  // Check for serial commands
  if (Serial.available() > 0) {
    String command = Serial.readString();
    command.trim(); // Remove whitespace
    command.toLowerCase(); // Convert to lowercase for consistency
    
    processCommand(command);
  }
  
  // Brief delay to prevent overwhelming the system
  delay(10);
}

void processCommand(String cmd) {
  // Handle simple single-character commands
  if (cmd == "1" && NUM_LASERS >= 1) {
    toggleLaserExclusive(1);
  }
  else if (cmd == "2" && NUM_LASERS >= 2) {
    toggleLaserExclusive(2);
  }
  else if (cmd == "3" && NUM_LASERS >= 3) {
    toggleLaserExclusive(3);
  }
  else if (cmd == "all_off") {
    setAllLasers(false);
    Serial.println("All lasers turned OFF");
  }
  else if (cmd == "status") {
    printStatus();
  }
  else if (cmd == "config") {
    printConfiguration();
  }
  // Handle multi-parameter commands
  else if (cmd.startsWith("set_pin ")) {
    handleSetPinCommand(cmd);
  }
  else if (cmd.startsWith("set_logic ")) {
    handleSetLogicCommand(cmd);
  }
  else {
    Serial.println("Unknown command. Type 'config' to see available commands.");
  }
}

void toggleLaserExclusive(int laserNumber) {
  if (laserNumber < 1 || laserNumber > NUM_LASERS) {
    Serial.print("Invalid laser number. Use 1-");
    Serial.println(NUM_LASERS);
    return;
  }

  int pin = laserPins[laserNumber - 1];
  bool currentState = digitalRead(pin);
  bool newState = !currentState;

  // If turning this laser ON, turn all others OFF first (exclusive operation)
  if (newState == LASER_ON_SIGNAL) {
    setAllLasers(false);  // Turn all off
  }

  // Now set the requested laser to the new state
  digitalWrite(pin, newState);

  // Determine if laser is now ON or OFF based on configured logic
  bool laserIsOn = (newState == LASER_ON_SIGNAL);

  Serial.print("Laser ");
  Serial.print(laserNumber);
  Serial.print(" (Pin ");
  Serial.print(pin);
  Serial.print(") is now ");
  Serial.print(laserIsOn ? "ON" : "OFF");
  Serial.print(" (Signal: ");
  Serial.print(newState == HIGH ? "HIGH" : "LOW");
  Serial.println(")");
}

void toggleLaser(int laserNumber) {
  // Kept for compatibility - calls exclusive version
  toggleLaserExclusive(laserNumber);
}

void setAllLasers(bool turnOn) {
  int signalLevel = turnOn ? LASER_ON_SIGNAL : LASER_OFF_SIGNAL;
  
  for (int i = 0; i < NUM_LASERS; i++) {
    digitalWrite(laserPins[i], signalLevel);
  }
  
  // Update status LED
  digitalWrite(STATUS_LED, turnOn ? HIGH : LOW);
}

void setLaser(int laserNumber, bool state) {
  if (laserNumber < 1 || laserNumber > NUM_LASERS) {
    return; // Invalid laser number
  }
  
  int pin = laserPins[laserNumber - 1];
  int signalLevel = state ? LASER_ON_SIGNAL : LASER_OFF_SIGNAL;
  
  digitalWrite(pin, signalLevel);
}

void printStatus() {
  Serial.println("=== Current Laser Status ===");
  
  for (int i = 0; i < NUM_LASERS; i++) {
    int pin = laserPins[i];
    bool pinState = digitalRead(pin);
    bool laserIsOn = (pinState == LASER_ON_SIGNAL);
    
    Serial.print("Laser ");
    Serial.print(i + 1);
    Serial.print(" (Pin ");
    Serial.print(pin);
    Serial.print("): ");
    Serial.print(laserIsOn ? "ON " : "OFF");
    Serial.print(" [Signal: ");
    Serial.print(pinState == HIGH ? "HIGH" : "LOW");
    Serial.println("]");
  }

}

void printConfiguration() {
  Serial.println("=== Current Configuration ===");
  Serial.print("Number of active lasers: ");
  Serial.println(NUM_LASERS);
  Serial.print("Laser ON signal: ");
  Serial.println(LASER_ON_SIGNAL == HIGH ? "HIGH (5V)" : "LOW (0V)");
  Serial.print("Laser OFF signal: ");
  Serial.println(LASER_OFF_SIGNAL == HIGH ? "HIGH (5V)" : "LOW (0V)");
  Serial.println();
  Serial.println("Pin Assignments:");
  for (int i = 0; i < NUM_LASERS; i++) {
    Serial.print("  Laser ");
    Serial.print(i + 1);
    Serial.print(": Pin ");
    Serial.println(laserPins[i]);
  }
  Serial.println("==============================");
  Serial.println();
}

void handleSetPinCommand(String cmd) {
  // Parse "set_pin X Y" command
  int firstSpace = cmd.indexOf(' ');
  int secondSpace = cmd.indexOf(' ', firstSpace + 1);
  
  if (firstSpace == -1 || secondSpace == -1) {
    Serial.println("Usage: set_pin <laser_number> <pin_number>");
    Serial.println("Example: set_pin 1 12");
    return;
  }
  
  int laserNum = cmd.substring(firstSpace + 1, secondSpace).toInt();
  int newPin = cmd.substring(secondSpace + 1).toInt();
  
  if (laserNum < 1 || laserNum > NUM_LASERS) {
    Serial.print("Invalid laser number. Use 1-");
    Serial.println(NUM_LASERS);
    return;
  }
  
  if (newPin < 2 || newPin > 13) {
    Serial.println("Invalid pin number. Use pins 2-13");
    return;
  }
  
  // Update pin assignment
  int oldPin = laserPins[laserNum - 1];
  laserPins[laserNum - 1] = newPin;
  
  // Reconfigure pins
  pinMode(oldPin, INPUT); // Release old pin
  pinMode(newPin, OUTPUT); // Configure new pin
  digitalWrite(newPin, LASER_OFF_SIGNAL); // Start in OFF state
  
  Serial.print("Laser ");
  Serial.print(laserNum);
  Serial.print(" moved from pin ");
  Serial.print(oldPin);
  Serial.print(" to pin ");
  Serial.println(newPin);
}

void handleSetLogicCommand(String cmd) {
  // Parse "set_logic X Y" command (where X is ignored, Y sets the ON signal)
  int firstSpace = cmd.indexOf(' ');
  int secondSpace = cmd.indexOf(' ', firstSpace + 1);
  
  if (firstSpace == -1 || secondSpace == -1) {
    Serial.println("Usage: set_logic 0 <signal> (0=reserved, signal: 0=LOW, 1=HIGH)");
    Serial.println("Example: set_logic 0 1  (sets laser ON signal to HIGH)");
    return;
  }
  
  int newLogic = cmd.substring(secondSpace + 1).toInt();
  
  if (newLogic != 0 && newLogic != 1) {
    Serial.println("Invalid logic level. Use 0 for LOW or 1 for HIGH");
    return;
  }
  
  // This is a demonstration - in practice, these would need to be non-const
  // for runtime modification. For now, just show what would change.
  Serial.println("Note: Logic levels are set at compile time in configuration section.");
  Serial.print("To change logic: Set LASER_ON_SIGNAL = ");
  Serial.print(newLogic == 1 ? "HIGH" : "LOW");
  Serial.println(" and recompile.");
  Serial.print("Currently: ON=");
  Serial.print(LASER_ON_SIGNAL == HIGH ? "HIGH" : "LOW");
  Serial.print(", OFF=");
  Serial.println(LASER_OFF_SIGNAL == HIGH ? "HIGH" : "LOW");
}

/*
 * Advanced control functions
 */

void flashLaser(int laserNumber, int flashCount, int flashDuration) {
  if (laserNumber < 1 || laserNumber > NUM_LASERS) {
    return;
  }
  
  for (int i = 0; i < flashCount; i++) {
    setLaser(laserNumber, true);  // Turn on
    delay(flashDuration);
    setLaser(laserNumber, false); // Turn off
    delay(flashDuration);
  }
}

void sequentialPattern(int delayMs) {
  for (int i = 1; i <= NUM_LASERS; i++) {
    setAllLasers(false);
    setLaser(i, true);
    delay(delayMs);
  }
  setAllLasers(false);
}