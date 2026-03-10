#include <Arduino.h>

// ----------- Configuration -----------
const uint8_t start_pin = 4;
const uint8_t n_output_pins = 6;   // pins: 4..9 if start_pin = 4
const uint8_t speed_ch = 4;        // analog channel
const uint8_t lick_ch = 1;

const uint32_t baud = 115200;
const uint16_t sample_period_ms = 20;

const uint8_t rx_buf_size = 32;    // plenty for "P,010011\n"
// -------------------------------------


// ----------- State -----------
uint32_t last_sample_time = 0;

char rx_buf[rx_buf_size];
uint8_t rx_len = 0;
bool rx_overflow = false;
// -----------------------------


// ---- Setup Serial Communication and Initialise Output Pins
void setup() {
  
  Serial.begin(baud);

  for (uint8_t i = 0; i < n_output_pins; i++) {
    pinMode(start_pin + i, OUTPUT);
    digitalWrite(start_pin + i, LOW);
  }
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
      rx_buf[rx_len++] = c;
    } else {
      rx_overflow = true;
    }
  }

  return false;
}


// Check whether the completed message has the expected format:
// P,010011
bool check_serial_message_is_valid() {
  
 // Must be the correct length exactly: "P," + n_output_pins bits
  if (rx_len != 2 + n_output_pins) {
    return false;
  }

  // Must begin with "P,"
  if (rx_buf[0] != 'P' || rx_buf[1] != ',') {
    return false;
  }

  // Must contain exactly n_output_pins bits after "P,"
  for (uint8_t i = 0; i < n_output_pins; i++) {
    char bit_char = rx_buf[2 + i];
    if (bit_char != '0' && bit_char != '1') {
      return false;
    }
  }

  // Must end exactly after those bits
  if (rx_buf[2 + n_output_pins] != '\0') {
    return false;
  }

  return true;
}


// Apply the pin changes encoded in a validated message
void execute_serial_message() {
  for (uint8_t i = 0; i < n_output_pins; i++) {
    char bit_char = rx_buf[2 + i];
    digitalWrite(start_pin + i, bit_char == '1' ? HIGH : LOW);
  }
}


// Receive and process any complete serial messages
void receive_serial_data() {

  // Read Message Into Serial Buffer and check if its complete
  bool message_complete = read_serial_message_into_buffer();

  // If Not Complete then return 
  if (!message_complete) {
    return;
  }

  // If it is complete - the check if the message is valuid
  bool message_valid = check_serial_message_is_valid();

 // If the message is valid - execute the command
  if (message_valid) {
    execute_serial_message();
  }

  // reset the transmission buffer
  reset_rx_buffer();

}


void transmit_serial_data() {

  //  Get Current Time
  uint32_t now = millis();

  // If The Sample period as elpased since our last message - Send a new one
  if (now - last_sample_time >= sample_period_ms) {

    // Reset Time Of Last Message Sent
    last_sample_time = now;

    // Read Speed and Lick
    int speed = analogRead(speed_ch);
    int lick = analogRead(lick_ch);

    // Transmit this message - with a constant legnth 
    char line[20];
    snprintf(line, sizeof(line), "I,%04d,%04d\n", speed, lick);
    Serial.print(line);

  }
}


void loop() {

  // Receive and execute any changes in pin voltage
  receive_serial_data();

  // Transmit the speed and licking analog voltages
  transmit_serial_data();

}