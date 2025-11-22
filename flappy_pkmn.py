import sys
import random
import os
import logging
import json
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QGraphicsScene,
    QGraphicsPixmapItem, QGraphicsRectItem, QMessageBox,
    QLabel, QVBoxLayout, QWidget
)
from PyQt6.QtCore import QTimer, QRectF, Qt, QPointF
from PyQt6.QtGui import QBrush, QColor, QPixmap

# --- Constantes del Juego ---
SCREEN_WIDTH = 400
SCREEN_HEIGHT = 600
BIRD_SIZE = 60
GRAVITY = 0.4
FLAP_STRENGTH = -8
PIPE_WIDTH = 60
PIPE_GAP = 165
PIPE_SPEED = 3
GAME_TICK_RATE = 16 
PIPE_SPAWN_RATE = 1500 

# --- Ruta de Archivos ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_DIR = os.path.join(SCRIPT_DIR, "sprites")

# --- LOGGER ---
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
        elif event_type == "Lose":
            log_data["Result"] = "Lose"
        else: 
            log_data["Result"] = event_type
        
        log_data["Score"] = score
        json_str = json.dumps(log_data)
        self.logger.info(f"{timestamp} {json_str}")

# --- Lista de Pokémon ---
POKEMON_VOLADORES = [
    "pidgeot", "charizard", "aerodactyl", "articuno", "dodrio", "dragonite", 
    "moltres", "scyther", "spearow", "staraptor", "zapdos", "zubat"
]

class Bird(QGraphicsPixmapItem):
    def __init__(self, pokemon_name):
        image_path = os.path.join(IMAGE_DIR, f"{pokemon_name}.png")
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            print(f"ADVERTENCIA: No se encontró '{image_path}'.")
            pixmap = QPixmap(BIRD_SIZE, BIRD_SIZE)
            pixmap.fill(QColor("yellow"))
        
        scaled_pixmap = pixmap.scaled(
            BIRD_SIZE, BIRD_SIZE,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        super().__init__(scaled_pixmap)
        self.setPos(50, SCREEN_HEIGHT / 2)
        self.velocity_y = 0

    def update_physics(self):
        self.velocity_y += GRAVITY
        self.setY(self.y() + self.velocity_y)

    def flap(self):
        self.velocity_y = FLAP_STRENGTH

class Pipe(QGraphicsPixmapItem):
    def __init__(self, x, y, w, h, is_top_pipe=False):
        super().__init__()
        self.width = w
        self.height = h
        self.is_top_pipe = is_top_pipe

        image_name = "pipe2.png" if self.is_top_pipe else "pipe.png"
        pipe_image_path = os.path.join(IMAGE_DIR, image_name)
        base_pixmap = QPixmap(pipe_image_path)

        if base_pixmap.isNull():
            replacement_pixmap = QPixmap(w, h)
            replacement_pixmap.fill(QColor("green"))
            self.setPixmap(replacement_pixmap)
            self.setPos(x, y)
        else:
            scaled_pixmap = base_pixmap.scaledToWidth(
                self.width,
                Qt.TransformationMode.SmoothTransformation
            )
            if scaled_pixmap.height() < h:
                scaled_pixmap = scaled_pixmap.scaled(
                    self.width, h,
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
            self.setPixmap(scaled_pixmap)
            if self.is_top_pipe:
                self.setPos(x, h - scaled_pixmap.height())
            else:
                self.setPos(x, y)
        self.passed = False

    def move(self):
        self.setX(self.x() - PIPE_SPEED)

class GoalLine(QGraphicsRectItem):
    def __init__(self, x, y, w, h):
        super().__init__(0, 0, w, h)
        self.setPos(x, y)
        self.setBrush(QBrush(QColor("gold")))
    
    def move(self):
        self.setX(self.x() - PIPE_SPEED)

class MainWindow(QMainWindow):
    def __init__(self, game_logger):
        super().__init__()
        self.logger = game_logger
        self.setWindowTitle("Flappy Pokémon")
        self.setFixedSize(SCREEN_WIDTH, SCREEN_HEIGHT + 75) 

        self.scene = QGraphicsScene(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)
        self.view = QGraphicsView(self.scene, self)
        self.view.setFixedSize(SCREEN_WIDTH, SCREEN_HEIGHT)

        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)

        self.pokemon_label = QLabel("Pokémon: N/A")
        self.pokemon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pokemon_label.setStyleSheet("font-size: 22px; font-weight: bold;")

        self.score_label = QLabel("Puntaje: 0")
        self.score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.score_label.setStyleSheet("font-size: 20px;")

        self.timer_label = QLabel("Tiempo: 20s")
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timer_label.setStyleSheet("font-size: 20px; color: #333;")

        layout.addWidget(self.pokemon_label)
        layout.addWidget(self.score_label)
        layout.addWidget(self.timer_label)
        layout.addWidget(self.view)

        self.setCentralWidget(central_widget)

        self.game_timer = QTimer(self) 
        self.game_timer.timeout.connect(self.game_loop)
        self.pipe_timer = QTimer(self) 
        self.pipe_timer.timeout.connect(self.spawn_pipe)
        self.level_timer = QTimer(self) 
        self.level_timer.setSingleShot(True)
        self.level_timer.timeout.connect(self.on_level_end)
        self.ui_update_timer = QTimer(self)
        self.ui_update_timer.timeout.connect(self.update_countdown_label)
        
        self.goal_line = None
        self.start_game()

    def start_game(self):
        self.scene.clear()
        self.pipes = []
        self.score = 0
        self.score_label.setText("Puntaje: 0")
        self.goal_line = None
        self.remaining_time = 15
        self.timer_label.setText("Tiempo: 15s")

        self.current_pokemon = random.choice(POKEMON_VOLADORES)
        self.pokemon_label.setText(f"Pokémon: {self.current_pokemon}")

        self.bird = Bird(self.current_pokemon)
        self.scene.addItem(self.bird)

        self.game_timer.start(GAME_TICK_RATE)
        self.pipe_timer.start(PIPE_SPAWN_RATE)
        self.level_timer.start(15000)
        self.ui_update_timer.start(1000)

    def update_countdown_label(self):
        self.remaining_time -= 1
        self.timer_label.setText(f"Tiempo: {self.remaining_time}s")
        if self.remaining_time <= 0:
            self.ui_update_timer.stop()
            self.timer_label.setText("¡A la meta!")

    def on_level_end(self):
        self.pipe_timer.stop()
        self.spawn_goal()

    def spawn_goal(self):
        self.goal_line = GoalLine(SCREEN_WIDTH, 0, 30, SCREEN_HEIGHT)
        self.scene.addItem(self.goal_line)

    def game_loop(self):
        self.bird.update_physics()
        if self.bird.y() < 0 or self.bird.y() > (SCREEN_HEIGHT - BIRD_SIZE):
            self.game_over(won=False)
            return

        pipes_to_remove = []
        for pipe in self.pipes:
            pipe.move()
            if pipe.collidesWithItem(self.bird):
                self.game_over(won=False)
                return
            if not pipe.passed and pipe.x() + PIPE_WIDTH < self.bird.x():
                pipe.passed = True
                if pipe.is_top_pipe:
                    self.score += 1
                    self.score_label.setText(f"Puntaje: {self.score}")
            if pipe.x() < -PIPE_WIDTH:
                pipes_to_remove.append(pipe)

        for pipe in pipes_to_remove:
            self.scene.removeItem(pipe)
            self.pipes.remove(pipe)

        if self.goal_line is not None:
            self.goal_line.move()
            if self.goal_line.collidesWithItem(self.bird):
                self.game_over(won=True)
                return

    def spawn_pipe(self):
        gap_y = random.randint(PIPE_GAP, SCREEN_HEIGHT - (PIPE_GAP * 2))
        top_pipe = Pipe(SCREEN_WIDTH, 0, PIPE_WIDTH, gap_y, is_top_pipe=True)
        self.scene.addItem(top_pipe)
        self.pipes.append(top_pipe)
        bottom_pipe_y = gap_y + PIPE_GAP
        bottom_pipe_h = SCREEN_HEIGHT - bottom_pipe_y
        bottom_pipe = Pipe(SCREEN_WIDTH, bottom_pipe_y, PIPE_WIDTH, bottom_pipe_h, is_top_pipe=False)
        self.scene.addItem(bottom_pipe)
        self.pipes.append(bottom_pipe)

    def game_over(self, won=False):
        self.game_timer.stop()
        self.pipe_timer.stop()
        self.level_timer.stop()
        self.ui_update_timer.stop()
        msg_box = QMessageBox(self)
        
        if won:
            self.logger.log_event(game_stage="Meta", event_type="Win", score=self.score)
            msg_box.setWindowTitle("¡Felicidades!")
            msg_box.setText(f"¡{self.current_pokemon} llegó a la meta!\nPuntaje final: {self.score}\n\n¿Quieres jugar de nuevo?")
        else:
            self.logger.log_event(game_stage=f"Score_{self.score}", event_type="Lose", score=self.score)
            msg_box.setWindowTitle("¡Juego Terminado!")
            msg_box.setText(f"¡{self.current_pokemon} no pudo más!\nPuntaje final: {self.score}\n\n¿Quieres jugar de nuevo?")

        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if msg_box.exec() == QMessageBox.StandardButton.Yes:
            self.start_game()
        else:
            self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Space:
            self.bird.flap()
        if event.key() == Qt.Key.Key_R:
            self.start_game()
        if event.key() == Qt.Key.Key_Q:
            self.close()

if __name__ == "__main__":
    PLAYER_ID = 1 
    GAME_ID = "Flappy_Pokemon" 
    game_logger = GameLogger(game_id=GAME_ID, player_id=PLAYER_ID)
    app = QApplication(sys.argv)
    window = MainWindow(game_logger) 
    window.show()
    sys.exit(app.exec())