import sys
import random
from time import sleep, time
import logging
import json
from datetime import datetime
from gpiozero import DistanceSensor, LED, TonalBuzzer
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import QThread, QObject, pyqtSignal, Qt
from PyQt5.QtGui import QFont

# --- Configuración de PINES ---
PIN_ECHO = 24
PIN_TRIGGER = 23
PIN_LED_ROJO = 17
PIN_LED_VERDE = 27
PIN_BUZZER = 16
DISTANCIA_ACTIVACION_CM = 10.0

# --- Configuración del Logger ---
LOG_FILE = 'eventos_minijuego1.log'

def setup_logger():
    logging.getLogger().handlers = []
    logger = logging.getLogger('GameLogger')
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(LOG_FILE, mode='a', encoding='utf-8')
    formatter = logging.Formatter('%(message)s')
    handler.setFormatter(formatter)
    if not logger.hasHandlers():
        logger.addHandler(handler)
    return logger

class GameLogger:
    def __init__(self, game_id, player_id):
        self.logger = setup_logger()
        self.game_id = game_id
        self.player_id = player_id

    def log_event(self, game_stage, event_type, score=None, reaction_time=None):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        log_data = {
            "game_stage": game_stage,
            "PlayerID": self.player_id,
            "GameID": self.game_id,
        }
        if event_type == "Result":
            log_data["Result"] = "Win" if reaction_time <= 450 else "Lose"
            log_data["Score"] = score
        elif event_type == "Error":
             log_data["Result"] = "Error"
             log_data["Score"] = 0
        else:
            log_data["Result"] = event_type
            log_data["Score"] = 0

        log_json = json.dumps(log_data)
        self.logger.info(f"{timestamp} {log_json}")

# -----------------------------------------------------------------
# --- CLASE WORKER (Lógica del juego en otro hilo) ---
# -----------------------------------------------------------------
class GameWorker(QObject):
    instruction_signal = pyqtSignal(str, str)
    result_signal = pyqtSignal(str, str, str, str) 
    finished_signal = pyqtSignal()            

    def __init__(self, game_logger):
        super().__init__()
        self.running = True
        self.logger = game_logger

    def run_game(self):
        current_stage = "R1" 
        sensor = DistanceSensor(echo=PIN_ECHO, trigger=PIN_TRIGGER)
        led_rojo = LED(PIN_LED_ROJO)
        led_verde = LED(PIN_LED_VERDE)
        buzzer = TonalBuzzer(PIN_BUZZER)
        
        try:
            self.logger.log_event(current_stage, "Start")

            # 1. Preparación
            self.instruction_signal.emit("Prepárate... retira la mano.", "black")
            led_rojo.off()
            led_verde.on()
            
            while sensor.distance * 100 < DISTANCIA_ACTIVACION_CM:
                if not self.running: return 
                sleep(0.1)
            
            self.instruction_signal.emit("¡Sensor listo!", "green")
            buzzer.play(523); sleep(0.1); buzzer.stop()
            
            # 2. Espera aleatoria
            sleep(random.uniform(2.0, 5.0))
            if not self.running: return

            # 3. ¡La señal para actuar!
            self.instruction_signal.emit("¡¡¡YA!!!", "red")
            led_verde.off()
            led_rojo.on()
            buzzer.play(440) 
            tiempo_inicio = time()

            # 4. Esperar a que el jugador ponga la mano
            while sensor.distance * 100 > DISTANCIA_ACTIVACION_CM:
                if not self.running: return
                sleep(0.001)
            
            tiempo_fin = time()
            led_rojo.off()
            buzzer.stop()
            if not self.running: return

            # 5. Calcular resultado
            tiempo_reaccion = (tiempo_fin - tiempo_inicio) * 1000
            time_str = f"{tiempo_reaccion:.2f} ms"
            
            puntos = 0
            if tiempo_reaccion <= 500:
                puntos = 1000 
            else:
                puntos = max(0, int(1000 - (tiempo_reaccion - 500)))
            
            score_str = f"Puntos: {puntos}"
            self.logger.log_event(current_stage, "Result", score=puntos, reaction_time=tiempo_reaccion)

            msg = ""
            color = ""
            if tiempo_reaccion <= 500:
                msg = " ¡Perfecto! ¡Puntaje máximo! "
                color = "green"
                buzzer.play(523); sleep(0.1); buzzer.stop(); sleep(0.05)
                buzzer.play(659); sleep(0.1); buzzer.stop(); sleep(0.05)
                buzzer.play(784); sleep(0.15); buzzer.stop()
            elif tiempo_reaccion <= 750: 
                msg = "¡Muy bien! Cerca del objetivo."
                color = "blue"
                buzzer.play(392); sleep(0.15); buzzer.stop()
            else:
                msg = " Demasiado lento. ¡Inténtalo de nuevo! "
                color = "orange"
                buzzer.play(330); sleep(0.15); buzzer.stop(); sleep(0.05)
                buzzer.play(261); sleep(0.2); buzzer.stop()

            self.result_signal.emit(time_str, score_str, msg, color)
            sleep(1) 

        except Exception as e:
            self.logger.log_event(current_stage, "Error")
            self.instruction_signal.emit(f"Error: {e}", "red")
        finally:
            led_rojo.off()
            led_verde.off()
            buzzer.stop()
            sensor.close()
            led_rojo.close()
            led_verde.close()
            buzzer.close()
            self.finished_signal.emit() 

    def stop(self):
        self.running = False

# -----------------------------------------------------------------
# --- CLASE GUI (Ventana principal) ---
# -----------------------------------------------------------------
class ReactionGameGUI(QMainWindow):
    def __init__(self, game_logger):
        super().__init__()
        self.worker = None
        self.thread = None
        self.logger = game_logger
        self.initUI()

    def initUI(self):
        self.setWindowTitle(" Reflejos Ultrasónicos ")
        self.setGeometry(200, 200, 450, 400) 
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setAlignment(Qt.AlignTop)

        self.title_label = QLabel("Juego de Reflejos")
        self.title_label.setFont(QFont("Arial", 20, QFont.Bold))
        self.title_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.title_label)

        self.instruccion_txt = QLabel("Presiona 'Jugar' para empezar")
        self.instruccion_txt.setFont(QFont("Arial", 16))
        self.instruccion_txt.setAlignment(Qt.AlignCenter)
        self.instruccion_txt.setWordWrap(True)
        self.layout.addWidget(self.instruccion_txt)

        self.layout.addStretch(1) 

        self.resultado_txt = QLabel("")
        self.resultado_txt.setFont(QFont("Arial", 26, QFont.Bold))
        self.resultado_txt.setAlignment(Qt.AlignCenter)
        self.resultado_txt.setWordWrap(True)
        self.layout.addWidget(self.resultado_txt)

        self.score_label = QLabel("")
        self.score_label.setFont(QFont("Arial", 22, QFont.Bold))
        self.score_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.score_label) 

        self.layout.addStretch(2) 

        self.boton_inicio = QPushButton("Jugar")
        self.boton_inicio.setFont(QFont("Arial", 18))
        self.boton_inicio.setMinimumHeight(60)
        self.boton_inicio.clicked.connect(self.start_game)
        self.layout.addWidget(self.boton_inicio)

    def start_game(self):
        self.boton_inicio.setEnabled(False)
        self.instruccion_txt.setText("Iniciando...")
        self.resultado_txt.setText("")
        self.score_label.setText("") 

        self.thread = QThread()
        self.worker = GameWorker(self.logger)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run_game)
        self.worker.instruction_signal.connect(self.update_instruction)
        self.worker.result_signal.connect(self.update_result) 
        self.worker.finished_signal.connect(self.game_finished)
        self.worker.finished_signal.connect(self.thread.quit)
        self.worker.finished_signal.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()

    def update_instruction(self, text, color):
        self.instruccion_txt.setText(text)
        self.instruccion_txt.setStyleSheet(f"color: {color};")

    def update_result(self, time_str, score_str, msg, color):
        self.resultado_txt.setText(f"{time_str}\n{msg}")
        self.resultado_txt.setStyleSheet(f"color: {color};")
        self.score_label.setText(score_str)
        self.score_label.setStyleSheet(f"color: {color};") 

    def game_finished(self):
        self.instruccion_txt.setText("Presiona 'Jugar' para otra ronda")
        self.instruccion_txt.setStyleSheet("color: black;")
        self.boton_inicio.setEnabled(True)

    def closeEvent(self, event):
        if self.thread and self.thread.isRunning():
            self.worker.stop()  
            self.thread.quit()  
            self.thread.wait()  
        event.accept()

if __name__ == '__main__':
    PLAYER_ID = 1 
    GAME_ID = "UltraReflex" 
    
    game_logger = GameLogger(game_id=GAME_ID, player_id=PLAYER_ID)
    
    app = QApplication(sys.argv)
    window = ReactionGameGUI(game_logger)
    window.show()
    sys.exit(app.exec_())