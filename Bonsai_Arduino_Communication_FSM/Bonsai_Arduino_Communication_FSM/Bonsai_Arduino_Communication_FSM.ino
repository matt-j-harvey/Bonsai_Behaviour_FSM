#include <Arduino.h>

// ----------- Configuration -----------
const uint8_t reward_valve_pin = 4;

const uint8_t start_pin = 5;
const uint8_t n_output_pins = 5;   // ordinary output pins: 5..9

const uint8_t speed_ch = 4;        // analog channel
const uint8_t lick_ch = 1;

const uint32_t baud = 9600;
const uint16_t sample_period_ms = 20;

const uint16_t reward_cooldown_ms = 1000;

const uint8_t rx_buf_size = 32;
// Combined hardware command:
// H,10011,0050,1
//
// Meaning:
// H,<ordinary pin states>,<reward duration ms>,<reward trigger>
//
// ordinary pin states are for pins 5..9
// reward valve is on pin 4
// -------------------------------------


// ----------- State -----------
uint32_t last_sample_time = 0;

char rx_buf[rx_buf_size];
uint8_t rx_len = 0;
bool rx_overflow = false;

bool reward_valve_is_open = false;
uint32_t reward_valve_close_time = 0;
uint32_t last_reward_valve_open_time = 0;
// -----------------------------


// ---- Setup Serial Communication and Initialise Output Pins
void setup() {
  
  Serial.begin(baud);

  // Initialise ordinary output pins: 5..9
  for (uint8_t i = 0; i < n_output_pins; i++) {
    pinMode(start_pin + i, OUTPUT);
    digitalWrite(start_pin + i, LOW);
  }

  // Initialise timed reward valve pin: 4
  pinMode(reward_valve_pin, OUTPUT);
  digitalWrite(reward_valve_pin, LOW);
}


// Reset the current receive buffer state
void reset_rx_buffer() {
  rx_len = 0;
  rx_overflow = false;
}


// Read incoming serial bytes and append them to the buffer.
// Returns true only when a full line ending in '\n' has been received.
bool read_serial_message_into_buffer() {

  while (Serial.available() > 0) {

    // Read Next Character in serial message
    char c = Serial.read();

    // Ignore carriage returns
    if (c == '\r') {
      continue;
    }

    // End of line -> terminate string and report complete message
    if (c == '\n') {
      if (!rx_overflow && rx_len > 0) {
        rx_buf[rx_len] = '\0';
        return true;
      } else {
        reset_rx_buffer();
        return false;
      }
    }

    // Append character if there is still room
   if (rx_len < rx_buf_size - 1) {
    rx_buf[rx_len] = c;
    rx_len = rx_len + 1;
      } else {
        rx_overflow = true;
      }
  }

  return false;
}


// ---------------- Combined hardware command ----------------
//
// Expected format:
// H,10011,0050,1
//
// Meaning:
// H,<5 ordinary pin bits>,<4 digit reward duration>,<reward trigger bool>
//
// Pin bits control pins 5..9.
// Reward valve is pin 4 and is controlled only by the timed valve function.
//
bool check_hardware_message_is_valid() {

  // Expected:
  // H,10011,0050,1
  //
  // Length = 14 characters:
  //
  // index:
  //  0  H
  //  1  ,
  //  2  pin 5 state
  //  3  pin 6 state
  //  4  pin 7 state
  //  5  pin 8 state
  //  6  pin 9 state
  //  7  ,
  //  8  reward duration thousands
  //  9  reward duration hundreds
  // 10  reward duration tens
  // 11  reward duration ones
  // 12  ,
  // 13  reward trigger bool

  if (rx_len != 14) {
    return false;
  }

  if (rx_buf[0] != 'H') {
    return false;
  }

  if (rx_buf[1] != ',' || rx_buf[7] != ',' || rx_buf[12] != ',') {
    return false;
  }

  // Check ordinary pin state bits: indices 2..6
  for (uint8_t i = 2; i <= 6; i++) {
    if (rx_buf[i] != '0' && rx_buf[i] != '1') {
      return false;
    }
  }

  // Check 4-digit reward duration: indices 8..11
  for (uint8_t i = 8; i <= 11; i++) {
    if (rx_buf[i] < '0' || rx_buf[i] > '9') {
      return false;
    }
  }

  // Check reward trigger bool
  if (rx_buf[13] != '0' && rx_buf[13] != '1') {
    return false;
  }

  // Check null terminator
  if (rx_buf[14] != '\0') {
    return false;
  }

  return true;
}


uint16_t get_reward_duration_ms() {

  uint16_t duration_ms = 0;

  duration_ms += (rx_buf[8]  - '0') * 1000;
  duration_ms += (rx_buf[9]  - '0') * 100;
  duration_ms += (rx_buf[10] - '0') * 10;
  duration_ms += (rx_buf[11] - '0');

  return duration_ms;
}


bool get_reward_trigger() {
  return rx_buf[13] == '1';
}


void open_reward_valve(uint16_t duration_ms) {

  uint32_t now = millis();

  // Ignore zero-duration rewards
  if (duration_ms == 0) {
    return;
  }

  // Do not re-open if the valve is already open
  if (reward_valve_is_open) {
    return;
  }

  // Enforce cooldown from the previous valve opening
  if (now - last_reward_valve_open_time < reward_cooldown_ms) {
    return;
  }

  digitalWrite(reward_valve_pin, HIGH);

  reward_valve_is_open = true;
  reward_valve_close_time = now + duration_ms;
  last_reward_valve_open_time = now;
}


void update_reward_valve() {

  if (!reward_valve_is_open) {
    return;
  }

  uint32_t now = millis();

  // Safe across millis() rollover
  if ((int32_t)(now - reward_valve_close_time) >= 0) {
    digitalWrite(reward_valve_pin, LOW);
    reward_valve_is_open = false;
  }
}


void execute_hardware_message() {

  // Apply ordinary output pin states to pins 5..9
  for (uint8_t i = 0; i < n_output_pins; i++) {
    char bit_char = rx_buf[2 + i];
    digitalWrite(start_pin + i, bit_char == '1' ? HIGH : LOW);
  }

  // Handle timed reward valve request on pin 4
  uint16_t duration_ms = get_reward_duration_ms();
  bool trigger_reward = get_reward_trigger();

  if (trigger_reward) {
    open_reward_valve(duration_ms);
  }
}


// Receive and process any complete serial messages
void receive_serial_data() {

  // Check If We Have Recivied A Full Message
  bool message_complete = read_serial_message_into_buffer();
  if (!message_complete) {
    return;
  }

  // If We Have - Check The Syntax Is Valid and Execute It
  if (check_hardware_message_is_valid()) {
    execute_hardware_message();
  }

  // Reset The Transmission Buffer
  reset_rx_buffer();
}


void transmit_serial_data() {

  uint32_t now = millis();

  if (now - last_sample_time >= sample_period_ms) {

    last_sample_time = now;

    int speed = analogRead(speed_ch);
    int lick = analogRead(lick_ch);

    char line[20];
    snprintf(line, sizeof(line), "I,%04d,%04d\n", speed, lick);
    Serial.print(line);
  }
}


void loop() {

  // Receive and execute incoming Bonsai command
  receive_serial_data();

  // Close reward valve when its requested open duration has elapsed
  update_reward_valve();

  // Transmit speed and lick analog values
  transmit_serial_data();
}