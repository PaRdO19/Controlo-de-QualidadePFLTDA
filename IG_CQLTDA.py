import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QStackedWidget
from PyQt5.QtCore import QThread, pyqtSignal, QDateTime
import serial
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from collections import deque
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense
from tensorflow.keras.optimizers import Adam
from sklearn.preprocessing import MinMaxScaler

SECRET_KEY = "CQLTDA"

def decrypt_message(message):
    key_length = len(SECRET_KEY)
    decrypted = ''.join(chr(ord(char) ^ ord(SECRET_KEY[i % key_length])) for i, char in enumerate(message))
    return decrypted

def parse_message(decrypted_message):
    parsed_data = {}
    parts = decrypted_message.split(", ")
    for part in parts:
        if ": " in part:
            key, value = part.split(": ", 1)
            parsed_data[key.strip()] = value.strip()
    return parsed_data

class SerialReaderThread(QThread):
    new_message = pyqtSignal(str)

    def __init__(self, port, baudrate):
        super().__init__()
        self.serial_port = serial.Serial(port, baudrate, timeout=1)
        self.running = True

    def run(self):
        while self.running:
            if self.serial_port.in_waiting:
                raw_message = self.serial_port.readline().decode('utf-8').strip()
                decrypted_message = decrypt_message(raw_message)
                self.new_message.emit(decrypted_message)

    def stop(self):
        self.running = False
        self.serial_port.close()

class PlotWidget(QWidget):
    def __init__(self, title, ylabel, max_points=100):
        super().__init__()
        self.data = deque(maxlen=max_points)
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_title(title)
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel(ylabel)
        self.line, = self.ax.plot([], [], 'r-')

        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.warning_label = QPushButton("", self)
        self.warning_label.setStyleSheet("color: red;")
        self.warning_label.setEnabled(False)
        layout.addWidget(self.warning_label)
        self.back_button = QPushButton("Voltar")
        layout.addWidget(self.back_button)
        self.setLayout(layout)

    def update_plot(self, value):
        self.data.append(value)
        self.line.set_data(range(len(self.data)), self.data)
        self.ax.set_xlim(0, len(self.data))
        self.ax.set_ylim(min(self.data, default=0) - 10, max(self.data, default=10) + 10)
        self.canvas.draw()

    def show_warning(self, message):
        self.warning_label.setText(message)

class AnomalyDetector:
    def __init__(self):
        self.model = Sequential([
            Dense(32, input_dim=1, activation='relu'),
            Dense(32, activation='relu'),
            Dense(1, activation='sigmoid')
        ])
        self.model.compile(optimizer=Adam(learning_rate=0.001), loss='binary_crossentropy', metrics=['accuracy'])
        self.scaler = MinMaxScaler()

    def train(self, data, labels):
        scaled_data = self.scaler.fit_transform(data.reshape(-1, 1))
        self.model.fit(scaled_data, labels, epochs=20, batch_size=8, verbose=0)

    def predict(self, value):
        scaled_value = self.scaler.transform(np.array([[value]]))
        prediction = self.model.predict(scaled_value, verbose=0)[0][0]
        print(f"Valor recebido (original): {value}, Valor escalado: {scaled_value[0][0]}, Predição: {prediction}")  # Log para debug
        return prediction > 0.3  # Reduzido o limiar para aumentar sensibilidade

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Monitor de Sensores do Motor")

        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        self.main_menu = QWidget()
        main_menu_layout = QVBoxLayout()
        self.vibration_button = QPushButton("Vibração")
        self.temperature_button = QPushButton("Temperatura")
        self.microphone_button = QPushButton("Ruído")

        self.vibration_button.clicked.connect(lambda: self.show_data_page("Vib"))
        self.temperature_button.clicked.connect(lambda: self.show_data_page("Temp"))
        self.microphone_button.clicked.connect(lambda: self.show_data_page("Mic"))

        main_menu_layout.addWidget(self.vibration_button)
        main_menu_layout.addWidget(self.temperature_button)
        main_menu_layout.addWidget(self.microphone_button)
        self.main_menu.setLayout(main_menu_layout)

        self.vib_plot = PlotWidget("Vibração", "Valor do sensor")
        self.temp_plot = PlotWidget("Temperatura", "°C")
        self.mic_plot = PlotWidget("Ruído", "Valor do sensor")

        self.vib_plot.back_button.clicked.connect(self.show_main_menu)
        self.temp_plot.back_button.clicked.connect(self.show_main_menu)
        self.mic_plot.back_button.clicked.connect(self.show_main_menu)

        self.stacked_widget.addWidget(self.main_menu)
        self.stacked_widget.addWidget(self.vib_plot)
        self.stacked_widget.addWidget(self.temp_plot)
        self.stacked_widget.addWidget(self.mic_plot)

        self.show_main_menu()

        self.serial_thread = SerialReaderThread("/dev/cu.usbmodem14101", 9600)  # Update with the correct port
        self.serial_thread.new_message.connect(self.process_message)
        self.serial_thread.start()

        self.current_filter = None

        # Inicializar detectores de anomalia
        self.vib_detector = AnomalyDetector()
        self.temp_detector = AnomalyDetector()
        self.mic_detector = AnomalyDetector()

        self.alert_log = []

        # Simular dados para treinamento inicial
        self.train_detectors()

    def train_detectors(self):
        vib_data = np.concatenate([np.random.normal(500, 100, 900), np.random.normal(950, 50, 100)])
        vib_labels = (vib_data > 900).astype(int)
        self.vib_detector.train(vib_data, vib_labels)

        temp_data = np.concatenate([np.random.normal(25, 5, 900), np.random.normal(40, 5, 100)])
        temp_labels = (temp_data > 35).astype(int)
        self.temp_detector.train(temp_data, temp_labels)

        mic_data = np.concatenate([np.random.normal(75, 20, 900), np.random.normal(160, 10, 100)])
        mic_labels = (mic_data > 150).astype(int)
        self.mic_detector.train(mic_data, mic_labels)

    def show_main_menu(self):
        self.stacked_widget.setCurrentWidget(self.main_menu)

    def show_data_page(self, filter_type):
        self.current_filter = filter_type
        if filter_type == "Vib":
            self.stacked_widget.setCurrentWidget(self.vib_plot)
        elif filter_type == "Temp":
            self.stacked_widget.setCurrentWidget(self.temp_plot)
        elif filter_type == "Mic":
            self.stacked_widget.setCurrentWidget(self.mic_plot)

    def log_alert(self, message):
        timestamp = QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss")
        self.alert_log.append(f"[{timestamp}] {message}")

    def process_message(self, message):
        parsed_data = parse_message(message)

        if "Vib" in parsed_data and self.current_filter == "Vib":
            vib_value = int(parsed_data["Vib"])
            self.vib_plot.update_plot(vib_value)
            if self.vib_detector.predict(vib_value):
                alert_message = "ALERTA: Anomalia detectada na vibração!"
                self.vib_plot.show_warning(alert_message)
                self.log_alert(alert_message)
            else:
                self.vib_plot.show_warning("")
        elif "Temp" in parsed_data and self.current_filter == "Temp":
            temp_value = float(parsed_data["Temp"])
            self.temp_plot.update_plot(temp_value)
            if self.temp_detector.predict(temp_value):
                alert_message = "ALERTA: Anomalia detectada na temperatura!"
                self.temp_plot.show_warning(alert_message)
                self.log_alert(alert_message)
            else:
                self.temp_plot.show_warning("")
        elif "Mic" in parsed_data and self.current_filter == "Mic":
            mic_value = float(parsed_data["Mic"])
            self.mic_plot.update_plot(mic_value)
            if self.mic_detector.predict(mic_value):
                alert_message = "ALERTA: Anomalia detectada no ruído!"
                self.mic_plot.show_warning(alert_message)
                self.log_alert(alert_message)
            else:
                self.mic_plot.show_warning("")

    def closeEvent(self, event):
        self.serial_thread.stop()

        with open("alert_log.txt", "w") as log_file:
            log_file.write("\n".join(self.alert_log))

        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
