// Wheel Settings

int encoder_pin_1 = 8;
int encoder_pin_2 = 9;

long encoder_previous_position = 0;
volatile long encoder_current_position = 0;

unsigned long speed_last_read = millis();  
const unsigned long speed_bin_ms = 20;

const float wheel_diameter_cm = 20.0;
const float wheel_circumference_cm = 3.14159265 * wheel_diameter_cm;
const float counts_per_rev = 1024.0;   // because your encoder is 1024 PPR
const float dt_s = speed_bin_ms / 1000.0;
float max_signed_speed_cm_s = 200.0;

int speed = 0;


// Tone Settings
unsigned long tone_played_prev_millis = millis();  
unsigned long tone_played_current_millis = millis();  

int tone_state = 0;
unsigned long tone_started_current_millis = millis();  
int tone_duration = 100;

unsigned long tone_refractory_period = 2000;

int tone_input_pin = 10;
int piezo_pin = 11;



void setup() {
  Serial.begin (9600);
  pinMode(encoder_pin_1, INPUT);
  pinMode(encoder_pin_2, INPUT);
  pinMode(tone_input_pin, INPUT);
  pinMode(piezo_pin, OUTPUT);

  attachInterrupt(digitalPinToInterrupt(encoder_pin_1), update_encoder, RISING);
  analogWriteResolution(12); 
}

 
void loop() {
  update_speed();
  update_tone();

  }


void update_encoder() {
  if  (digitalRead(encoder_pin_2)==LOW) {encoder_current_position++;}
  else {encoder_current_position--;}
}


void update_speed(){

  unsigned long now = millis();

  if (now - speed_last_read >= speed_bin_ms) {
      speed_last_read = now;

      // Get Current Encoder Position
      long pos;
      noInterrupts();
      pos = encoder_current_position;
      interrupts();

      // Get Change in Encoder Counts
      long delta_counts = pos - encoder_previous_position;
      encoder_previous_position = pos;

      // Convert This into cm / s
      float speed_cm_s = (delta_counts * wheel_circumference_cm) / (counts_per_rev * dt_s);
    
      // Convert This Into A Voltage
      int dac_value = 2048 + (int)(speed_cm_s * 2047.0 / max_signed_speed_cm_s);

      // Clamp To Range
      if (dac_value < 0) dac_value = 0;
      if (dac_value > 4095) dac_value = 4095;
  
      // Write To Analog Voltage 
      analogWrite(A0, dac_value);
      //Serial.println(dac_value);
      }
  }


void update_tone(){

  // Check To See If We Are Playing A New Tone
  if (tone_state==0){

       // Leave it a period of 2s before we even start monitoring for tones again, incase the pulse is still high
      tone_played_current_millis = millis(); 
      if (tone_played_current_millis - tone_played_prev_millis >= tone_refractory_period) {


          if (digitalRead(tone_input_pin)==HIGH){
              tone_played_prev_millis = tone_played_current_millis;
              tone(piezo_pin, 3200);
              tone_state = 1;
              }

    }
  }

    // If We Are Already Playing A Tone - See If The Tone Duration has Elapse, if So Stop the Tone
    if (tone_state==1){
        tone_started_current_millis = millis(); 
        if (tone_started_current_millis - tone_played_prev_millis >= tone_duration){
            noTone(piezo_pin);
            tone_state = 0;
            }
        }
}