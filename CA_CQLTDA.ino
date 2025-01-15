#define SECRET_KEY "CQLTDA"

int in1 = 9;
int in2 = 10;

unsigned long previousSensorTime = 0;
const unsigned long sensorInterval = 500;

unsigned long previousMotorTime = 0;
unsigned long motorStepInterval = 2000;
int motorStep = 0;

bool motorActive = true;


float readTemperatureCelsius(int adcValue) {
  return (adcValue * 5.0 / 1024.0) / 0.01;
}

void sendEncryptedMessage(String message) {
  String encrypted = "";
  int keyLength = String(SECRET_KEY).length();
  for (int i = 0; i < message.length(); i++) {
    encrypted += char(message[i] ^ SECRET_KEY[i % keyLength]);
  }
  Serial.println(encrypted);
}

void setup() {
  Serial.begin(9600);
  pinMode(in1, OUTPUT);
  pinMode(in2, OUTPUT);

  digitalWrite(in1, LOW);
  digitalWrite(in2, LOW);
}

void readSensors() {
  int sensorVib = analogRead(A0);
  int sensorTemp = analogRead(A1);
  int Mic = analogRead(A2);

  float temperatureCelsius = readTemperatureCelsius(sensorTemp);

  String message = "Vib: " + String(sensorVib) +
                   ", Temp: " + String(temperatureCelsius, 1) +
                   ", Mic: " + String(Mic);

  sendEncryptedMessage(message);
}

void updateMotor() {
  if (!motorActive) {
    digitalWrite(in1, LOW);
    digitalWrite(in2, LOW);
    return;
  }

  unsigned long currentTime = millis();
  if (currentTime - previousMotorTime >= motorStepInterval) {
    previousMotorTime = currentTime;

    switch (motorStep) {
      case 0:
        digitalWrite(in1, HIGH);
        digitalWrite(in2, LOW);
        motorStep++;
        break;

      case 1:
        digitalWrite(in1, LOW);
        digitalWrite(in2, HIGH);
        motorStep++;
        break;

      case 2:
        digitalWrite(in1, LOW);
        digitalWrite(in2, LOW);
        motorStep = 0;
        break;
    }
  }
}

void processSerialCommand() {
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    command.trim();

    if (command == "STOP_MOTOR") {
      motorActive = false;
    } else if (command == "START_MOTOR") {
      motorActive = true;
    }
  }
}

void loop() {
  processSerialCommand();

  unsigned long currentTime = millis();
  if (currentTime - previousSensorTime >= sensorInterval) {
    previousSensorTime = currentTime;
    readSensors();
  }

  updateMotor();
}
