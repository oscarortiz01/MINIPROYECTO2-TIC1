import sys
import random
from time import sleep
import logging
import json
from datetime import datetime
from gpiozero import Button, TonalBuzzer
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import QThread, QObject, pyqtSignal, pyqtSlot, Qt
from PyQt5.QtGui import QFont

PINS = {
    "btns": {"red": 17, "green": 27, "blue": 22, "yellow": 10},
    "buzzer": 16
}

TONES = {
    "red": 262,
    "green": 330,
    "blue": 392,
    "yellow": 440
}
COLORS = ["red", "green", "blue", "yellow"]

DIFFICULTY_LEVELS = {
    1: (0.4, 0.2),
    2: (0.35, 0.18),
    3: (0.3, 0.15),
    4: (0.25, 0.12),
    5: (0.2, 0.1),
}

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

    def log_event(self, game_stage, event_type, score=0):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        
        log_data = {
            "game_stage": game_stage,
            "PlayerID": self.player_id,
            "GameID": self.game_id,
        }
        
        if event_type == "Win":
            log_data["Result"] = "Win"
            log_data["Score"] = score
        elif event_type == "Lose":
            log_data["Result"] = "Lose"
            log_data["Score"] = score
        else: 
            log_data["Result"] = event_type
            log_data["Score"] = score

        log_json = json.dumps(log_data)
        self.logger.info(f"{timestamp} {log_json}")

class GameWorker(QObject):
    status_signal = pyqtSignal(str)
    score_signal = pyqtSignal(int)
    highlight_signal = pyqtSignal(str) 
    game_over_signal = pyqtSignal() 
    physical_press_signal = pyqtSignal(str)

    def __init__(self, game_logger):
        super().__init__()
        self.state = "IDLE" 
        self.sequence = []
        self.player_index = 0
        self.score = 0
        self.running = True
        self.logger = game_logger
        self.init_gpio()
        self.physical_press_signal.connect(self.process_player_input)

    def init_gpio(self):
        self.buttons = {
            "red": Button(PINS["btns"]["red"], pull_up=True, bounce_time=0.1),
            "green": Button(PINS["btns"]["green"], pull_up=True, bounce_time=0.1),
            "blue": Button(PINS["btns"]["blue"], pull_up=True, bounce_time=0.1),
            "yellow": Button(PINS["btns"]["yellow"], pull_up=True, bounce_time=0.1)
        }
        self.buzzer = TonalBuzzer(PINS["buzzer"])

        self.buttons["red"].when_pressed = lambda: self.physical_press_signal.emit("red")
        self.buttons["green"].when_pressed = lambda: self.physical_press_signal.emit("green")
        self.buttons["blue"].when_pressed = lambda: self.physical_press_signal.emit("blue")
        self.buttons["yellow"].when_pressed = lambda: self.physical_press_signal.emit("yellow")

    @pyqtSlot()
    def start_game(self):
        try:
            if self.state != "IDLE":
                self.state = "IDLE"
                sleep(0.5) 
            
            self.sequence = []
            self.score = 0
            self.score_signal.emit(self.score)
            self.state = "COMPUTER"
            self.computer_turn()
        except Exception:
            self.game_over_signal.emit()

    def computer_turn(self):
        if not self.running: return

        try:
            if len(self.sequence) >= 5:
                self.game_win()
                return
            
            self.status_signal.emit("Observa...")
            
            self.sequence.append(random.choice(COLORS))
            self.score = len(self.sequence) 
            self.score_signal.emit(self.score)
            
            current_level = self.score
            if current_level in DIFFICULTY_LEVELS:
                note_duration, pause_duration = DIFFICULTY_LEVELS[current_level]
            else:
                note_duration, pause_duration = (0.2, 0.1)

            sleep(1.0) 
            
            for color in self.sequence:
                if not self.running: return
                self.play_color(color, duration=note_duration)
                sleep(pause_duration) 
                
            self.state = "PLAYER"
            self.player_index = 0
            self.status_signal.emit("¡Tu Turno!")
        except Exception:
            self.game_over_signal.emit()

    def play_color(self, color, duration):
        if not self.running: return
        try:
            self.highlight_signal.emit(color) 
            self.buzzer.play(TONES[color])
            sleep(duration)
            self.highlight_signal.emit("none")
            self.buzzer.stop()
        except Exception:
            self.buzzer.stop()

    @pyqtSlot(str)
    def gui_press_slot(self, color):
        self.process_player_input(color)

    @pyqtSlot(str)
    def process_player_input(self, color):
        if self.state != "PLAYER" or not self.running:
            return 
        try:
            self.play_color(color, duration=0.2) 

            if color == self.sequence[self.player_index]:
                self.player_index += 1
                if self.player_index == len(self.sequence):
                    self.state = "COMPUTER"
                    self.status_signal.emit("¡Correcto!")
                    sleep(1.0)
                    self.computer_turn() 
            else:
                self.game_over()
        except Exception:
            self.game_over_signal.emit()

    def game_win(self):
        self.state = "IDLE"
        self.status_signal.emit(f"¡GANASTE! (Nivel 5)")
        self.logger.log_event("R5", "Win", score=5)

        try:
            self.buzzer.play(TONES["red"]); sleep(0.1); self.buzzer.stop()
            sleep(0.05)
            self.buzzer.play(TONES["green"]); sleep(0.1); self.buzzer.stop()
            sleep(0.05)
            self.buzzer.play(TONES["blue"]); sleep(0.1); self.buzzer.stop()
            sleep(0.05)
            self.buzzer.play(TONES["yellow"]); sleep(0.15); self.buzzer.stop()
        except:
            pass
        
        self.game_over_signal.emit() 

    def game_over(self):
        self.state = "IDLE"
        final_score = self.score - 1
        current_stage = f"R{self.score}"
        self.status_signal.emit(f"¡Perdiste! Puntaje: {final_score}")
        self.logger.log_event(current_stage, "Lose", score=final_score)

        try:
            self.buzzer.play(150); sleep(0.5); self.buzzer.stop()
        except:
            pass
            
        self.game_over_signal.emit() 

    def stop(self):
        self.running = False
        try:
            for btn in self.buttons.values():
                btn.close()
            self.buzzer.close()
        except:
            pass

class SimonGameGUI(QMainWindow):
    gui_press_signal = pyqtSignal(str)

    def __init__(self, game_logger): 
        super().__init__()
        self.worker = None
        self.thread = None
        self.logger = game_logger 
        
        self.styles = {
            "red_off": "background-color: #A00; border: 3px solid black; border-radius: 75px;",
            "red_on": "background-color: #F00; border: 3px solid white; border-radius: 75px;",
            "green_off": "background-color: #0A0; border: 3px solid black; border-radius: 75px;",
            "green_on": "background-color: #0F0; border: 3px solid white; border-radius: 75px;",
            "blue_off": "background-color: #00A; border: 3px solid black; border-radius: 75px;",
            "blue_on": "background-color: #00F; border: 3px solid white; border-radius: 75px;",
            "yellow_off": "background-color: #AA0; border: 3px solid black; border-radius: 75px;",
            "yellow_on": "background-color: #FF0; border: 3px solid white; border-radius: 75px;",
        }
        
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Juego de Simón")
        self.setGeometry(100, 100, 400, 500)
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        self.title_label = QLabel("Simón (Pi 5)")
        self.title_label.setFont(QFont("Arial", 24, QFont.Bold))
        self.title_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.title_label)

        self.status_txt = QLabel("Presiona 'Jugar' para empezar")
        self.status_txt.setFont(QFont("Arial", 18))
        self.status_txt.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.status_txt)

        self.score_txt = QLabel("Puntaje: 0")
        self.score_txt.setFont(QFont("Arial", 20, QFont.Bold))
        self.score_txt.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.score_txt)

        btn_layout_1 = QHBoxLayout()
        self.btn_green = self.create_color_button("green")
        self.btn_red = self.create_color_button("red")
        btn_layout_1.addWidget(self.btn_green)
        btn_layout_1.addWidget(self.btn_red)
        self.layout.addLayout(btn_layout_1)
        
        btn_layout_2 = QHBoxLayout()
        self.btn_yellow = self.create_color_button("yellow")
        self.btn_blue = self.create_color_button("blue")
        btn_layout_2.addWidget(self.btn_yellow)
        btn_layout_2.addWidget(self.btn_blue)
        self.layout.addLayout(btn_layout_2)

        self.start_button = QPushButton("Jugar")
        self.start_button.setFont(QFont("Arial", 18))
        self.start_button.clicked.connect(self.start_game)
        self.layout.addWidget(self.start_button)
        
        self.reset_button_styles()

    def create_color_button(self, color):
        button = QPushButton()
        button.setFixedSize(150, 150) 
        button.setStyleSheet(self.styles[f"{color}_off"])
        button.clicked.connect(lambda: self.gui_press_signal.emit(color))
        return button

    def reset_button_styles(self):
        self.btn_red.setStyleSheet(self.styles["red_off"])
        self.btn_green.setStyleSheet(self.styles["green_off"])
        self.btn_blue.setStyleSheet(self.styles["blue_off"])
        self.btn_yellow.setStyleSheet(self.styles["yellow_off"])

    def start_game(self):
        self.start_button.setEnabled(False)
        self.status_txt.setText("Iniciando...")

        self.thread = QThread()
        self.worker = GameWorker(self.logger) 
        
        self.gui_press_signal.connect(self.worker.gui_press_slot)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.start_game)
        self.worker.status_signal.connect(self.update_status)
        self.worker.score_signal.connect(self.update_score)
        self.worker.highlight_signal.connect(self.highlight_button)
        self.worker.game_over_signal.connect(self.on_game_over)
        
        self.worker.game_over_signal.connect(self.thread.quit)
        self.worker.game_over_signal.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()

    @pyqtSlot(str)
    def update_status(self, text):
        self.status_txt.setText(text)

    @pyqtSlot(int)
    def update_score(self, score):
        self.score_txt.setText(f"Puntaje: {score}")

    @pyqtSlot(str)
    def highlight_button(self, color):
        self.reset_button_styles()
        if color == "red":
            self.btn_red.setStyleSheet(self.styles["red_on"])
        elif color == "green":
            self.btn_green.setStyleSheet(self.styles["green_on"])
        elif color == "blue":
            self.btn_blue.setStyleSheet(self.styles["blue_on"])
        elif color == "yellow":
            self.btn_yellow.setStyleSheet(self.styles["yellow_on"])

    @pyqtSlot()
    def on_game_over(self):
        self.start_button.setEnabled(True)

    def closeEvent(self, event):
        if self.thread and self.thread.isRunning():
            self.worker.stop() 
            self.thread.quit()
            self.thread.wait() 
        event.accept()

if __name__ == '__main__':
    PLAYER_ID = 1 
    GAME_ID = "Simon_dice" 
    
    game_logger = GameLogger(game_id=GAME_ID, player_id=PLAYER_ID)
    
    app = QApplication(sys.argv)
    window = SimonGameGUI(game_logger)
    window.show()
    sys.exit(app.exec_())