#include <SoftwareSerial.h>

// -----------------------------
// RS485 DIR pin (RE+DE merged)
// -----------------------------
#define MAX485_DIR_PIN 8    // RE + DE merged to this pin

#define MAX485_RO_PIN 10    // RO -> Arduino RX
#define MAX485_DI_PIN 11    // DI -> Arduino TX

SoftwareSerial rs485(MAX485_RO_PIN, MAX485_DI_PIN);

// Modbus request for ZTS-3002: 01 03 00 00 00 07 CRC
uint8_t requestFrame[] = {0x01, 0x03, 0x00, 0x00, 0x00, 0x07, 0x04, 0x08};

uint16_t read16(const uint8_t *buf, int i) {
  return (uint16_t(buf[i]) << 8) | uint16_t(buf[i + 1]);
}

void setTransmitMode() {
  digitalWrite(MAX485_DIR_PIN, HIGH);   // Transmit mode
}

void setReceiveMode() {
  digitalWrite(MAX485_DIR_PIN, LOW);    // Receive mode
}

void sendCommand() {
  setTransmitMode();
  delay(2);

  while (rs485.available()) rs485.read();     // clear any junk
  rs485.write(requestFrame, sizeof(requestFrame));
  rs485.flush();

  setReceiveMode();
}

void setup() {
  Serial.begin(9600);       // must match Python BAUD_RATE
  rs485.begin(4800);

  pinMode(MAX485_DIR_PIN, OUTPUT);
  setReceiveMode();

  Serial.println("NPK Node Started");
}

void loop() {
  uint8_t buf[32];
  int bytesRead = 0;

  sendCommand();

  unsigned long start = millis();
  while (millis() - start < 800) {
    if (rs485.available() && bytesRead < (int)sizeof(buf)) {
      buf[bytesRead++] = rs485.read();
    }
  }

  if (bytesRead < 19) {
    Serial.print("WARN,RESP_BYTES,");
    Serial.println(bytesRead);
  } else {
    // Decode Modbus reply
    float moisture = read16(buf, 3) * 0.1;
    float temp     = read16(buf, 5) * 0.1;
    uint16_t EC    = read16(buf, 7);
    float pH       = read16(buf, 9) * 0.1;
    uint16_t N     = read16(buf, 11);
    uint16_t P     = read16(buf, 13);
    uint16_t K     = read16(buf, 15);

    // Human-readable debug (optional)
    Serial.println("SOIL_DATA_START");
    Serial.print("Moisture: "); Serial.println(moisture);
    Serial.print("Temp: ");     Serial.println(temp);
    Serial.print("EC: ");       Serial.println(EC);
    Serial.print("pH: ");       Serial.println(pH);
    Serial.print("N: ");        Serial.println(N);
    Serial.print("P: ");        Serial.println(P);
    Serial.print("K: ");        Serial.println(K);
    Serial.println("SOIL_DATA_END");

    // MACHINE READABLE LINE FOR PYTHON:
    // Format: NPK,temp,moisture,ph,N,P,K
    Serial.print("NPK,");
    Serial.print(temp);     Serial.print(",");
    Serial.print(moisture); Serial.print(",");
    Serial.print(pH);       Serial.print(",");
    Serial.print(N);        Serial.print(",");
    Serial.print(P);        Serial.print(",");
    Serial.println(K);
  }

  delay(2000);
}
