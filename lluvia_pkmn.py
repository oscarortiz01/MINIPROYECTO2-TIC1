import sys
import random
import os
import json
import logging
from datetime import datetime
from PyQt6.QtWidgets import QApplication, QWidget, QLabel
from PyQt6.QtCore import QTimer, Qt, QCoreApplication
from PyQt6.QtGui import QPixmap

# --- RUTAS ---
script_dir = os.path.dirname(os.path.abspath(__file__))
img_folder = os.path.join(script_dir, "img")

QCoreApplication.setApplicationName("JuegoPokemon")

# ====================================================================
# --- CLASE GAMELOGGER (Estandarizada) ---
# ====================================================================
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
# ====================================================================


class PokemonRainGame(QWidget):
    def __init__(self, game_logger):
        super().__init__()
        self.logger = game_logger 
        
        # --- Configuración del Juego ---
        self.tiempo_limite = 20
        self.tiempo_restante = self.tiempo_limite
        self.puntaje = 0
        self.juego_activo = False
        self.ancho_juego = 800
        self.alto_juego = 600
        self.player_speed = 12 
        
        self.pokemon_buenos = [
            (os.path.join(img_folder, "pikachu.png"), "bueno", 100),
            (os.path.join(img_folder, "eevee.png"), "bueno", 100),
            (os.path.join(img_folder, "charmander.png"), "bueno", 100),
            (os.path.join(img_folder, "mudkip.png"), "bueno", 100),
            (os.path.join(img_folder, "pika.png"), "bueno", 100),
            (os.path.join(img_folder, "weydelteamrocket.png"), "bueno", 100)]
        
        self.pokemon_malos = [
            (os.path.join(img_folder, "voltorb.png"), "malo", -100),
            (os.path.join(img_folder, "dark.png"), "malo", -200)]
        
        self.teclas_presionadas = set()
        self.objetos_en_pantalla = [] 

        self.init_ui()
        self.iniciar_juego()

    def init_ui(self):
        self.setWindowTitle("Lluvia de Pokemon")
        self.setFixedSize(self.ancho_juego, self.alto_juego)
        self.setStyleSheet("background-color: #2c3e50;")

        self.tiempo_label = QLabel(f"Tiempo: {self.tiempo_restante}s", self)
        self.tiempo_label.setFont(self.font())
        self.tiempo_label.font().setPointSize(20)
        self.tiempo_label.setStyleSheet("color: white; font-weight: bold;")
        self.tiempo_label.setGeometry(10, 10, 200, 40)

        self.puntaje_label = QLabel(f"Puntaje: {self.puntaje}", self)
        self.puntaje_label.setFont(self.font())
        self.puntaje_label.font().setPointSize(20)
        self.puntaje_label.setStyleSheet("color: white; font-weight: bold;")
        self.puntaje_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.puntaje_label.setGeometry(self.ancho_juego - 210, 10, 200, 40)
        
        ruta_jugador = os.path.join(img_folder, "pokeball.png") 
        if os.path.exists(ruta_jugador):
            self.player_pixmap = QPixmap(ruta_jugador).scaled(105, 135, Qt.AspectRatioMode.KeepAspectRatio)
        else:
            self.player_pixmap = QPixmap(105, 135)
            self.player_pixmap.fill(Qt.GlobalColor.red)

        self.player = QLabel(self)
        self.player.setPixmap(self.player_pixmap)
        self.player.setGeometry(370, self.alto_juego - 140, 105, 135)
        
        self.show()
        self.setFocus()

    def iniciar_juego(self):
        self.juego_activo = True

        self.game_timer = QTimer(self)
        self.game_timer.timeout.connect(self.actualizar_juego)
        self.game_timer.start(16)

        self.second_timer = QTimer(self)
        self.second_timer.timeout.connect(self.actualizar_segundo)
        self.second_timer.start(1000)

        self.spawn_timer = QTimer(self)
        self.spawn_timer.timeout.connect(self.generar_objeto)
        self.spawn_timer.start(900)

    def actualizar_juego(self):
        if not self.juego_activo:
            return

        player_x = self.player.x()
        if Qt.Key.Key_Left in self.teclas_presionadas:
            player_x = max(0, player_x - self.player_speed)
        if Qt.Key.Key_Right in self.teclas_presionadas:
            player_x = min(self.ancho_juego - self.player.width(), player_x + self.player_speed)
        self.player.move(player_x, self.player.y())

        for objeto_data in reversed(self.objetos_en_pantalla):
            label, tipo, puntos, velocidad = objeto_data
            label.move(label.x(), label.y() + velocidad)
            
            if label.geometry().intersects(self.player.geometry()):
                self.actualizar_puntaje(puntos, tipo)
                label.deleteLater() 
                self.objetos_en_pantalla.remove(objeto_data)
                continue 
            
            if label.y() > self.alto_juego:
                if tipo == "bueno":
                    self.actualizar_puntaje(-50, "fallo") 
                label.deleteLater()
                self.objetos_en_pantalla.remove(objeto_data)

    def generar_objeto(self):
        if not self.juego_activo:
            return

        if random.randint(1, 4) != 1:
            asset = random.choice(self.pokemon_buenos)
        else:
            asset = random.choice(self.pokemon_malos)
            
        path, tipo, puntos = asset
        
        if os.path.exists(path):
            pixmap = QPixmap(path).scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio)
        else:
            pixmap = QPixmap(80, 80)
            pixmap.fill(Qt.GlobalColor.yellow if tipo == "bueno" else Qt.GlobalColor.black)

        label = QLabel(self)
        label.setPixmap(pixmap)
        x_inicial = random.randint(0, self.ancho_juego - 80)
        velocidad = random.randint(4, 8)
        label.setGeometry(x_inicial, -80, 80, 80)
        label.show()
        self.objetos_en_pantalla.append([label, tipo, puntos, velocidad])

    def actualizar_puntaje(self, cantidad, tipo):
        self.puntaje += cantidad
        self.puntaje_label.setText(f"Puntaje: {self.puntaje}")
        
        color = "white"
        if tipo == "bueno": color = "#2ecc71"
        elif tipo == "malo": color = "#e74c3c"
        elif tipo == "fallo": color = "#f1c40f"
        
        self.puntaje_label.setStyleSheet(f"color: {color}; font-weight: bold;")
        QTimer.singleShot(300, lambda: self.puntaje_label.setStyleSheet("color: white; font-weight: bold;"))

    def actualizar_segundo(self):
        self.tiempo_restante -= 1
        self.tiempo_label.setText(f"Tiempo: {self.tiempo_restante}s")
        
        if self.tiempo_restante <= 0:
            self.terminar_juego()

    def terminar_juego(self):
        self.juego_activo = False
        self.game_timer.stop()
        self.spawn_timer.stop()
        self.second_timer.stop()

        self.logger.log_event("End", "Result", score=self.puntaje)

        self.player.hide()
        for obj in self.objetos_en_pantalla:
            obj[0].hide()

        self.tiempo_label.setText("JUEGO TERMINADO!")
        self.tiempo_label.setGeometry(0, 200, self.ancho_juego, 50)
        self.tiempo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.puntaje_label.setGeometry(0, 250, self.ancho_juego, 50)
        self.puntaje_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        QTimer.singleShot(3000, self.close)

    def keyPressEvent(self, event):
        if not self.juego_activo or event.isAutoRepeat():
            return
        self.teclas_presionadas.add(event.key())

    def keyReleaseEvent(self, event):
        if event.key() in self.teclas_presionadas:
            self.teclas_presionadas.remove(event.key())

if __name__ == '__main__':
    PLAYER_ID = 1 
    GAME_ID = "LluviaPokemon"
    game_logger = GameLogger(game_id=GAME_ID, player_id=PLAYER_ID)

    app = QApplication(sys.argv)
    ventana = PokemonRainGame(game_logger) 
    sys.exit(app.exec())