// Relay + Ultrasonic + Serial Pump Control (web-controlled)

#define RELAY_PIN 7   // Relay for water pump (ACTIVE LOW)
#define TRIG_PIN  9
#define ECHO_PIN  8

bool pumpOn = false;   // start OFF by default

void setup() {
  Serial.begin(9600);

  pinMode(RELAY_PIN, OUTPUT);
  // ACTIVE LOW relay: HIGH = OFF, LOW = ON
  digitalWrite(RELAY_PIN, HIGH);   // Pump OFF at startup

  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  Serial.println("Water Node Started (pump OFF, web-controlled)");
}

long readDistanceCm() {
  long duration;

  // Clear TRIG
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);

  // 10µs pulse
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  // Read echo time (timeout 30ms)
  duration = pulseIn(ECHO_PIN, HIGH, 30000);

  if (duration == 0) return -1;   // no echo
  long distance = (long)(duration * 0.034 / 2.0);
  return distance;
}

void handleSerialCommand() {
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd.equalsIgnoreCase("PUMP,ON")) {
      pumpOn = true;
      digitalWrite(RELAY_PIN, LOW);   // ACTIVE LOW -> ON
      Serial.println("PUMP,STATE,1");
    } else if (cmd.equalsIgnoreCase("PUMP,OFF")) {
      pumpOn = false;
      digitalWrite(RELAY_PIN, HIGH);  // ACTIVE LOW -> OFF
      Serial.println("PUMP,STATE,0");
    }
  }
}

void loop() {
  handleSerialCommand();

  long distance = readDistanceCm();
  int pumpState = pumpOn ? 1 : 0;

  // Send status to Python: WATER,distance_cm,pumpState
  Serial.print("WATER,");
  Serial.print(distance);
  Serial.print(",");
  Serial.println(pumpState);

  delay(500);
}
