#define SECRET_KEY "CQLTDA"

// Motor A connections
int in1 = 9;
int in2 = 10;

unsigned long previousSensorTime = 0; // Armazena o tempo da última leitura dos sensores
const unsigned long sensorInterval = 500; // Intervalo para leitura dos sensores em milissegundos

unsigned long previousMotorTime = 0; // Armazena o tempo da última atualização dos motores
unsigned long motorStepInterval = 2000; // Intervalo entre cada etapa do motor em milissegundos
int motorStep = 0; // Controla a etapa atual do motor

// Função para calcular a temperatura em Celsius a partir do valor analógico do sensor
float readTemperatureCelsius(int adcValue) {
  // Convert ADC value to temperature in Celsius for LM35 sensor
  return (adcValue * 5.0 / 1024.0) / 0.01; // 10mV por °C
}

// Função para enviar mensagens criptografadas
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
  // Set all the motor control pins to outputs
  pinMode(in1, OUTPUT);
  pinMode(in2, OUTPUT);

  // Turn off motors - Initial state
  digitalWrite(in1, LOW);
  digitalWrite(in2, LOW);
}

// Função para ler os sensores e exibir os valores
void readSensors() {
  int sensorVib = analogRead(A0); // Sensor de vibração
  int sensorTemp = analogRead(A1); // Sensor de temperatura
  int Mic = analogRead(A2); // Microfone

  // Converte o valor analógico do sensor de temperatura para graus Celsius
  float temperatureCelsius = readTemperatureCelsius(sensorTemp);

  // Formata a mensagem
  String message = "Vib: " + String(sensorVib) +
                   ", Temp: " + String(temperatureCelsius, 1) +
                   ", Mic: " + String(Mic);

  // Envia a mensagem criptografada
  sendEncryptedMessage(message);
}

// Função para atualizar o estado do motor
void updateMotor() {
  unsigned long currentTime = millis();

  // Avança para a próxima etapa do controle do motor a cada 2 segundos
  if (currentTime - previousMotorTime >= motorStepInterval) {
    previousMotorTime = currentTime;

    switch (motorStep) {
      case 0:
        // Turn on motor A & B in one direction
        digitalWrite(in1, HIGH);
        digitalWrite(in2, LOW);
        motorStep++;
        break;

      case 1:
        // Change motor direction
        digitalWrite(in1, LOW);
        digitalWrite(in2, HIGH);
        motorStep++;
        break;

      case 2:
        // Turn off motors
        digitalWrite(in1, LOW);
        digitalWrite(in2, LOW);
        motorStep = 0; // Reinicia o ciclo
        break;
    }
  }
}

void loop() {
  unsigned long currentTime = millis();

  // Verifica se é hora de ler os sensores
  if (currentTime - previousSensorTime >= sensorInterval) {
    previousSensorTime = currentTime;
    readSensors();
  }

  // Atualiza o estado dos motores
  updateMotor();
}