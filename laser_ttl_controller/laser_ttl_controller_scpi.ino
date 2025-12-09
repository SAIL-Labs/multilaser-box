/*
 * SCPI-Compatible Arduino Laser TTL Control Script
 * Controls up to 3 lasers using SCPI (Standard Commands for Programmable Instruments)
 *
 * Hardware Requirements:
 * - Arduino (Uno, Nano, Pro Mini, etc.)
 * - Digital output pins connected to laser TTL inputs
 * - External power supply for lasers
 *
 * SCPI Compliance:
 * - IEEE 488.2 Common Commands (*IDN?, *RST, *CLS, *ESR?, *OPC)
 * - Hierarchical command tree (SOURce:LASerX:STATe)
 * - Query support with '?' terminator
 * - Error queue with numeric error codes
 *
 * Configuration Section Below - Modify as needed
 */

// ===== CONFIGURATION SECTION =====
// Modify these values to match your hardware setup

// Device identification (returned by *IDN? query)
const char *MANUFACTURER = "SAIL-Nexus";
const char *MODEL = "SAIL MultiLaser-TTL";
const char *SERIAL = "00001";
const char *FIRMWARE = "1.0.0-SCPI";

// Pin assignments for each laser (change to any available digital pins)
const int LASER1_PIN = 8;  // Change this to your desired pin for Laser 1
const int LASER2_PIN = 9;  // Change this to your desired pin for Laser 2
const int LASER3_PIN = 10; // Change this to your desired pin for Laser 3

// TTL Logic Configuration
const int LASER_ON_SIGNAL = LOW;   // LOW (0V) turns laser ON
const int LASER_OFF_SIGNAL = HIGH; // HIGH (5V) turns laser OFF

// Number of active lasers (1, 2, or 3)
const int NUM_LASERS = 3;

// ===== END CONFIGURATION SECTION =====

// Status LED pin (built-in LED on most Arduino boards)
const int STATUS_LED = 13;

// Array to store laser pin numbers for easier iteration
int laserPins[] = {LASER1_PIN, LASER2_PIN, LASER3_PIN};

// SCPI error queue
#define ERROR_QUEUE_SIZE 10
int errorQueue[ERROR_QUEUE_SIZE];
int errorQueueHead = 0;
int errorQueueTail = 0;
int errorQueueCount = 0;

// SCPI error codes
#define ERR_NO_ERROR 0
#define ERR_INVALID_COMMAND -100
#define ERR_INVALID_PARAMETER -102
#define ERR_MISSING_PARAMETER -103
#define ERR_PARAMETER_OUT_OF_RANGE -104
#define ERR_QUERY_ONLY -105
#define ERR_COMMAND_ONLY -106
#define ERR_EXECUTION_ERROR -200
#define ERR_QUEUE_OVERFLOW -350

// Operation complete flag for *OPC
bool operationComplete = true;

// Command buffer
#define CMD_BUFFER_SIZE 128
char cmdBuffer[CMD_BUFFER_SIZE];
int cmdBufferIndex = 0;

void setup()
{
  // Initialize serial communication
  Serial.begin(9600);

  // Configure laser control pins as outputs
  for (int i = 0; i < NUM_LASERS; i++)
  {
    pinMode(laserPins[i], OUTPUT);
    digitalWrite(laserPins[i], LASER_OFF_SIGNAL); // Start with all lasers OFF
  }

  // Configure status LED
  pinMode(STATUS_LED, OUTPUT);
  digitalWrite(STATUS_LED, LOW);

  // Clear error queue
  clearErrors();

  // Brief startup delay
  delay(100);
}

void loop()
{
  // Check for serial data
  while (Serial.available() > 0)
  {
    char c = Serial.read();

    // Handle newline or semicolon as command terminator
    if (c == '\n' || c == '\r' || c == ';')
    {
      if (cmdBufferIndex > 0)
      {
        cmdBuffer[cmdBufferIndex] = '\0';
        processCommand(cmdBuffer);
        cmdBufferIndex = 0;
      }
    }
    // Ignore leading whitespace
    else if (cmdBufferIndex == 0 && (c == ' ' || c == '\t'))
    {
      continue;
    }
    // Add to buffer
    else if (cmdBufferIndex < CMD_BUFFER_SIZE - 1)
    {
      cmdBuffer[cmdBufferIndex++] = c;
    }
    else
    {
      // Buffer overflow
      cmdBufferIndex = 0;
      pushError(ERR_EXECUTION_ERROR);
    }
  }

  delay(1);
}

void processCommand(char *cmd)
{
  // Trim trailing whitespace
  int len = strlen(cmd);
  while (len > 0 && (cmd[len - 1] == ' ' || cmd[len - 1] == '\t'))
  {
    cmd[--len] = '\0';
  }

  if (len == 0)
    return;

  // Check if it's a query (ends with '?')
  bool isQuery = (cmd[len - 1] == '?');

  // Convert to uppercase for case-insensitive matching
  // But preserve original for parameter parsing
  char cmdUpper[CMD_BUFFER_SIZE];
  strncpy(cmdUpper, cmd, CMD_BUFFER_SIZE);
  toUpperCase(cmdUpper);

  // IEEE 488.2 Common Commands (start with *)
  if (cmdUpper[0] == '*')
  {
    processCommonCommand(cmdUpper, isQuery);
  }
  // SCPI Subsystem Commands
  else
  {
    processSCPICommand(cmdUpper, cmd, isQuery);
  }
}

void processCommonCommand(char *cmd, bool isQuery)
{
  // *IDN? - Identification query
  if (strcmp(cmd, "*IDN?") == 0)
  {
    Serial.print(MANUFACTURER);
    Serial.print(',');
    Serial.print(MODEL);
    Serial.print(',');
    Serial.print(SERIAL);
    Serial.print(',');
    Serial.println(FIRMWARE);
  }
  // *RST - Reset to default state
  else if (strcmp(cmd, "*RST") == 0)
  {
    if (isQuery)
    {
      pushError(ERR_COMMAND_ONLY);
    }
    else
    {
      resetDevice();
    }
  }
  // *CLS - Clear status
  else if (strcmp(cmd, "*CLS") == 0)
  {
    if (isQuery)
    {
      pushError(ERR_COMMAND_ONLY);
    }
    else
    {
      clearErrors();
    }
  }
  // *ESR? - Event Status Register query
  else if (strcmp(cmd, "*ESR?") == 0)
  {
    Serial.println("0"); // Simple implementation: no events
  }
  // *OPC - Operation complete
  else if (strcmp(cmd, "*OPC") == 0)
  {
    if (isQuery)
    {
      Serial.println(operationComplete ? "1" : "0");
    }
    else
    {
      operationComplete = true;
    }
  }
  // *OPC? - Operation complete query
  else if (strcmp(cmd, "*OPC?") == 0)
  {
    Serial.println("1"); // Always complete for this simple device
  }
  // Unknown common command
  else
  {
    pushError(ERR_INVALID_COMMAND);
  }
}

void processSCPICommand(char *cmdUpper, char *cmdOriginal, bool isQuery)
{
  // Parse SCPI hierarchical commands

  // SYSTem:ERRor? - Query error queue
  if (strcmp(cmdUpper, "SYST:ERR?") == 0 || strcmp(cmdUpper, "SYSTEM:ERROR?") == 0)
  {
    printError();
  }
  // SYSTem:VERSion? - SCPI version
  else if (strcmp(cmdUpper, "SYST:VERS?") == 0 || strcmp(cmdUpper, "SYSTEM:VERSION?") == 0)
  {
    Serial.println("1999.0"); // SCPI-1999 version
  }

  // SOURce[1-3]:STATe - Set/query laser state
  else if (strncmp(cmdUpper, "SOUR", 4) == 0)
  {
    processSourceCommand(cmdUpper, cmdOriginal, isQuery);
  }
  // OUTPut[1-3][:STATe] - Alternative syntax for laser state
  else if (strncmp(cmdUpper, "OUTP", 4) == 0)
  {
    processOutputCommand(cmdUpper, cmdOriginal, isQuery);
  }

  // STATus? - Query all laser states
  else if (strcmp(cmdUpper, "STAT?") == 0 || strcmp(cmdUpper, "STATUS?") == 0)
  {
    printAllStates();
  }

  // Legacy compatibility commands (from original firmware)
  else if (strcmp(cmdUpper, "ALL_OFF") == 0 || strcmp(cmdUpper, "ALLOFF") == 0)
  {
    setAllLasers(false);
  }
  else if (strcmp(cmdUpper, "1") == 0 && NUM_LASERS >= 1)
  {
    toggleLaserExclusive(1);
  }
  else if (strcmp(cmdUpper, "2") == 0 && NUM_LASERS >= 2)
  {
    toggleLaserExclusive(2);
  }
  else if (strcmp(cmdUpper, "3") == 0 && NUM_LASERS >= 3)
  {
    toggleLaserExclusive(3);
  }

  // Unknown command
  else
  {
    pushError(ERR_INVALID_COMMAND);
  }
}

void processSourceCommand(char *cmdUpper, char *cmdOriginal, bool isQuery)
{
  // Parse SOURce[1-3]:LASeR:STATe or SOURce[1-3]:STATe
  int laserNum = 0;

  // Extract laser number if present
  if (strlen(cmdUpper) > 4 && cmdUpper[4] >= '1' && cmdUpper[4] <= '3')
  {
    laserNum = cmdUpper[4] - '0';
  }

  // Check for :STATE or :LASER:STATE suffix
  char *statePos = strstr(cmdUpper, ":STAT");
  if (!statePos)
  {
    pushError(ERR_INVALID_COMMAND);
    return;
  }

  if (laserNum < 1 || laserNum > NUM_LASERS)
  {
    pushError(ERR_PARAMETER_OUT_OF_RANGE);
    return;
  }

  if (isQuery)
  {
    // Query laser state
    bool state = getLaserState(laserNum);
    Serial.println(state ? "1" : "0");
  }
  else
  {
    // Set laser state - find parameter after space
    char *param = strchr(cmdOriginal, ' ');
    if (!param)
    {
      pushError(ERR_MISSING_PARAMETER);
      return;
    }
    param++; // Skip space

    // Parse ON/OFF/1/0
    if (strcasecmp(param, "ON") == 0 || strcmp(param, "1") == 0)
    {
      setLaser(laserNum, true);
    }
    else if (strcasecmp(param, "OFF") == 0 || strcmp(param, "0") == 0)
    {
      setLaser(laserNum, false);
    }
    else
    {
      pushError(ERR_INVALID_PARAMETER);
    }
  }
}

void processOutputCommand(char *cmdUpper, char *cmdOriginal, bool isQuery)
{
  // Parse OUTPut[1-3][:STATe]
  int laserNum = 0;

  // Extract laser number if present
  if (strlen(cmdUpper) > 4 && cmdUpper[4] >= '1' && cmdUpper[4] <= '3')
  {
    laserNum = cmdUpper[4] - '0';
  }
  else
  {
    // OUTP without number defaults to laser 1
    laserNum = 1;
  }

  if (laserNum < 1 || laserNum > NUM_LASERS)
  {
    pushError(ERR_PARAMETER_OUT_OF_RANGE);
    return;
  }

  if (isQuery)
  {
    // Query laser state
    bool state = getLaserState(laserNum);
    Serial.println(state ? "1" : "0");
  }
  else
  {
    // Set laser state
    char *param = strchr(cmdOriginal, ' ');
    if (!param)
    {
      pushError(ERR_MISSING_PARAMETER);
      return;
    }
    param++;

    if (strcasecmp(param, "ON") == 0 || strcmp(param, "1") == 0)
    {
      setLaser(laserNum, true);
    }
    else if (strcasecmp(param, "OFF") == 0 || strcmp(param, "0") == 0)
    {
      setLaser(laserNum, false);
    }
    else
    {
      pushError(ERR_INVALID_PARAMETER);
    }
  }
}

// ===== Laser Control Functions =====

void setLaser(int laserNumber, bool state)
{
  if (laserNumber < 1 || laserNumber > NUM_LASERS)
  {
    pushError(ERR_PARAMETER_OUT_OF_RANGE);
    return;
  }

  // If turning this laser ON, turn all others OFF first (exclusive operation)
  if (state)
  {
    setAllLasers(false);  // Turn all off
  }

  int pin = laserPins[laserNumber - 1];
  int signalLevel = state ? LASER_ON_SIGNAL : LASER_OFF_SIGNAL;
  digitalWrite(pin, signalLevel);
}

void toggleLaserExclusive(int laserNumber)
{
  if (laserNumber < 1 || laserNumber > NUM_LASERS)
  {
    pushError(ERR_PARAMETER_OUT_OF_RANGE);
    return;
  }

  int pin = laserPins[laserNumber - 1];
  bool currentState = digitalRead(pin);
  bool newState = !currentState;

  // If turning this laser ON, turn all others OFF first (exclusive operation)
  if (newState == LASER_ON_SIGNAL)
  {
    setAllLasers(false);  // Turn all off
  }

  digitalWrite(pin, newState);
}

void toggleLaser(int laserNumber)
{
  // Kept for compatibility - calls exclusive version
  toggleLaserExclusive(laserNumber);
}

void setAllLasers(bool state)
{
  int signalLevel = state ? LASER_ON_SIGNAL : LASER_OFF_SIGNAL;
  for (int i = 0; i < NUM_LASERS; i++)
  {
    digitalWrite(laserPins[i], signalLevel);
  }
  digitalWrite(STATUS_LED, state ? HIGH : LOW);
}

bool getLaserState(int laserNumber)
{
  if (laserNumber < 1 || laserNumber > NUM_LASERS)
  {
    return false;
  }
  int pin = laserPins[laserNumber - 1];
  bool pinState = digitalRead(pin);
  return (pinState == LASER_ON_SIGNAL);
}

void printAllStates()
{
  for (int i = 0; i < NUM_LASERS; i++)
  {
    if (i > 0)
      Serial.print(',');
    Serial.print(getLaserState(i + 1) ? "1" : "0");
  }
  Serial.println();
}

void resetDevice()
{
  // Turn off all lasers
  setAllLasers(false);
  // Clear error queue
  clearErrors();
  operationComplete = true;
}

// ===== Error Queue Functions =====

void pushError(int errorCode)
{
  if (errorQueueCount >= ERROR_QUEUE_SIZE)
  {
    // Queue overflow - replace oldest with overflow error
    errorQueue[errorQueueTail] = ERR_QUEUE_OVERFLOW;
    return;
  }

  errorQueue[errorQueueHead] = errorCode;
  errorQueueHead = (errorQueueHead + 1) % ERROR_QUEUE_SIZE;
  errorQueueCount++;
}

void printError()
{
  if (errorQueueCount == 0)
  {
    Serial.println("0,\"No error\"");
    return;
  }

  int errorCode = errorQueue[errorQueueTail];
  errorQueueTail = (errorQueueTail + 1) % ERROR_QUEUE_SIZE;
  errorQueueCount--;

  Serial.print(errorCode);
  Serial.print(",\"");
  Serial.print(getErrorMessage(errorCode));
  Serial.println("\"");
}

const char *getErrorMessage(int errorCode)
{
  switch (errorCode)
  {
  case ERR_NO_ERROR:
    return "No error";
  case ERR_INVALID_COMMAND:
    return "Invalid command";
  case ERR_INVALID_PARAMETER:
    return "Invalid parameter";
  case ERR_MISSING_PARAMETER:
    return "Missing parameter";
  case ERR_PARAMETER_OUT_OF_RANGE:
    return "Parameter out of range";
  case ERR_QUERY_ONLY:
    return "Query only command";
  case ERR_COMMAND_ONLY:
    return "Command only (not a query)";
  case ERR_EXECUTION_ERROR:
    return "Execution error";
  case ERR_QUEUE_OVERFLOW:
    return "Error queue overflow";
  default:
    return "Unknown error";
  }
}

void clearErrors()
{
  errorQueueHead = 0;
  errorQueueTail = 0;
  errorQueueCount = 0;
}

// ===== Utility Functions =====

void toUpperCase(char *str)
{
  for (int i = 0; str[i]; i++)
  {
    if (str[i] >= 'a' && str[i] <= 'z')
    {
      str[i] = str[i] - 32;
    }
  }
}

int strcasecmp(const char *s1, const char *s2)
{
  while (*s1 && *s2)
  {
    char c1 = (*s1 >= 'a' && *s1 <= 'z') ? *s1 - 32 : *s1;
    char c2 = (*s2 >= 'a' && *s2 <= 'z') ? *s2 - 32 : *s2;
    if (c1 != c2)
      return c1 - c2;
    s1++;
    s2++;
  }
  return *s1 - *s2;
}
