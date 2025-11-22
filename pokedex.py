import sys
import json
import random
import os
from PyQt6.QtWidgets import (QApplication, QWidget, QLabel, QPushButton, 
                             QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox, 
                             QSizePolicy, QFrame)
from PyQt6.QtGui import QPixmap, QFont, QColor, QPalette, QBrush
from PyQt6.QtCore import Qt, QSize
from gpiozero import RGBLED 

# CONFIGURACIÓN DEL HARDWARE
# LED 1: Izquierda
led_izquierda = RGBLED(red=26, green=6, blue=5)

# LED 2: Derecha
led_derecha = RGBLED(red=17, green=27, blue=22)

class PokedexApp(QWidget):
    def __init__(self):
        super().__init__()
        self.pokemon_data = []
        self.current_index = 0
        
        # --- RUTA DE IMÁGENES ---
        # Busca la carpeta "Pokemon todas gen" en el mismo lugar donde está este script
        self.img_folder_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Pokemon todas gen")
        
        self.init_ui()
        self.load_data()
        
    def init_ui(self):
        self.setWindowTitle("Pokedex - Mini")
        self.setGeometry(100, 100, 320, 560) 
        
        self.setStyleSheet("""
            QWidget {
                background-color: #D32F2F; 
                color: white;
                font-family: 'Press Start 2P', 'Courier New', monospace;
                border-radius: 10px; 
            }
            QLabel { color: white; }
            QGroupBox {
                font-size: 10px;
                font-weight: bold;
                color: white;
                border: 2px solid #9A0007;
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 10px;
            }
            QPushButton {
                background-color: #4CAF50; 
                color: white;
                border: 2px solid #388E3C;
                border-radius: 6px;
                padding: 4px;
                font-size: 9px;
                font-weight: bold;
                text-transform: uppercase;
            }
            QPushButton:hover { background-color: #66BB6A; }
            QPushButton:pressed { background-color: #2E7D32; border-style: inset; }
            
            #blueButton {
                background-color: #2196F3; 
                border: 2px solid #1976D2;
                font-size: 8px;
                padding: 2px;
            }
            #blueButton:hover { background-color: #64B5F6; }
            #blueButton:pressed { background-color: #1976D2; }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        # --- PANEL SUPERIOR ---
        top_panel = QFrame(self)
        top_panel.setFrameShape(QFrame.Shape.NoFrame)
        top_panel_layout = QVBoxLayout(top_panel)
        top_panel_layout.setContentsMargins(5, 5, 5, 5)
        top_panel_layout.setSpacing(5)
        top_panel.setStyleSheet("background-color: #C62828; border-radius: 8px;")

        blue_button = QPushButton("", top_panel)
        blue_button.setFixedSize(24, 24)
        blue_button.setStyleSheet("background-color: #2196F3; border-radius: 12px; border: 2px solid #1976D2;")
        
        green_dots_layout = QHBoxLayout()
        for _ in range(3):
            dot = QLabel("", top_panel)
            dot.setFixedSize(8, 8)
            dot.setStyleSheet("background-color: #4CAF50; border-radius: 4px; border: 1px solid #388E3C;")
            green_dots_layout.addWidget(dot)
        green_dots_layout.addStretch(1) 

        header_layout = QHBoxLayout()
        header_layout.addWidget(blue_button, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        header_layout.addLayout(green_dots_layout)
        top_panel_layout.addLayout(header_layout)

        self.screen_frame = QFrame(top_panel)
        self.screen_frame.setFixedSize(240, 190)
        self.screen_frame.setStyleSheet("background-color: #000000; border: 3px inset #424242; border-radius: 6px;")
        screen_layout = QVBoxLayout(self.screen_frame)
        screen_layout.setContentsMargins(5, 5, 5, 5)
        
        self.image_label = QLabel(self.screen_frame)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setFixedSize(220, 150)
        self.image_label.setStyleSheet("background-color: black; border: none;") 
        
        self.name_label = QLabel("---", self.screen_frame)
        self.name_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setStyleSheet("color: #FFEB3B; background-color: transparent;") 
        
        screen_layout.addWidget(self.image_label)
        screen_layout.addWidget(self.name_label)
        top_panel_layout.addWidget(self.screen_frame, alignment=Qt.AlignmentFlag.AlignCenter)

        controls_layout = QHBoxLayout()
        
        dpad_frame = QFrame(top_panel)
        dpad_frame.setFixedSize(60, 60)
        dpad_frame.setStyleSheet("background-color: #424242; border: 2px solid #212121; border-radius: 8px;")
        dpad_layout = QGridLayout(dpad_frame)
        dpad_layout.setSpacing(0)
        dpad_layout.setContentsMargins(0,0,0,0)

        btn_size = 18
        btn_up = QPushButton("", dpad_frame); btn_up.setFixedSize(btn_size,btn_size); btn_up.setStyleSheet("background-color: #616161; border: none;")
        btn_down = QPushButton("", dpad_frame); btn_down.setFixedSize(btn_size,btn_size); btn_down.setStyleSheet("background-color: #616161; border: none;")
        btn_left = QPushButton("", dpad_frame); btn_left.setFixedSize(btn_size,btn_size); btn_left.setStyleSheet("background-color: #616161; border: none;")
        btn_right = QPushButton("", dpad_frame); btn_right.setFixedSize(btn_size,btn_size); btn_right.setStyleSheet("background-color: #616161; border: none;")
        btn_center = QLabel("", dpad_frame); btn_center.setFixedSize(btn_size,btn_size); btn_center.setStyleSheet("background-color: #424242; border: none;") 

        dpad_layout.addWidget(btn_up, 0, 1); dpad_layout.addWidget(btn_left, 1, 0); dpad_layout.addWidget(btn_center, 1, 1)
        dpad_layout.addWidget(btn_right, 1, 2); dpad_layout.addWidget(btn_down, 2, 1)
        
        btn_left.clicked.connect(self.show_prev)
        btn_right.clicked.connect(self.show_next)

        ab_buttons_layout = QHBoxLayout()
        self.btn_b = QPushButton("B", top_panel)
        self.btn_b.setFixedSize(30, 30)
        self.btn_b.setStyleSheet("background-color: #4CAF50; border-radius: 15px; border: 2px solid #388E3C; font-size: 12px;")
        
        self.btn_a = QPushButton("A", top_panel)
        self.btn_a.setFixedSize(30, 30) 
        self.btn_a.setStyleSheet("background-color: #4CAF50; border-radius: 15px; border: 2px solid #388E3C; font-size: 12px;")
        
        self.btn_a.clicked.connect(self.show_next)
        self.btn_b.clicked.connect(self.show_prev)

        ab_buttons_layout.addStretch(1) 
        ab_buttons_layout.addWidget(self.btn_b)
        ab_buttons_layout.addSpacing(10) 
        ab_buttons_layout.addWidget(self.btn_a)
        
        controls_layout.addWidget(dpad_frame)
        controls_layout.addLayout(ab_buttons_layout)
        top_panel_layout.addLayout(controls_layout)
        main_layout.addWidget(top_panel)

        # --- PANEL INFERIOR ---
        bottom_panel = QFrame(self)
        bottom_panel.setFrameShape(QFrame.Shape.NoFrame)
        bottom_panel_layout = QVBoxLayout(bottom_panel)
        bottom_panel_layout.setContentsMargins(10, 10, 10, 10)
        bottom_panel_layout.setSpacing(8)
        bottom_panel.setStyleSheet("background-color: #C62828; border-radius: 8px;") 

        blue_buttons_area = QHBoxLayout()
        for i in range(5):
            btn = QPushButton(f"B{i+1}", bottom_panel)
            btn.setObjectName("blueButton") 
            btn.setFixedSize(45, 25)
            blue_buttons_area.addWidget(btn)
        bottom_panel_layout.addLayout(blue_buttons_area)

        self.text_screen_frame = QFrame(bottom_panel)
        self.text_screen_frame.setFixedHeight(90)
        self.text_screen_frame.setStyleSheet("background-color: #004D40; border: 3px inset #00251A; border-radius: 5px;") 
        text_screen_layout = QVBoxLayout(self.text_screen_frame)
        text_screen_layout.setContentsMargins(5, 5, 5, 5)
        
        self.type_label = QLabel("TIPO: ???", self.text_screen_frame)
        self.type_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        self.type_label.setStyleSheet("color: #80CBC4; background-color: transparent;") 
        
        self.desc_label = QLabel("...", self.text_screen_frame)
        self.desc_label.setWordWrap(True)
        self.desc_label.setFont(QFont("Arial", 8))
        self.desc_label.setStyleSheet("color: #B2DFDB; background-color: transparent;") 
        self.desc_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        text_screen_layout.addWidget(self.type_label)
        text_screen_layout.addWidget(self.desc_label)
        self.text_screen_frame.setLayout(text_screen_layout)
        bottom_panel_layout.addWidget(self.text_screen_frame)

        nav_buttons_layout = QHBoxLayout()
        self.btn_random = QPushButton("RANDOM", bottom_panel) 
        self.btn_random.setFixedSize(80, 30) 
        self.btn_random.setStyleSheet("background-color: #5D4037; border: 2px solid #3E2723; border-radius: 8px; font-size: 9px;") 
        self.btn_random.clicked.connect(self.show_random)

        nav_buttons_layout.addStretch(1)
        nav_buttons_layout.addWidget(self.btn_random)
        nav_buttons_layout.addStretch(1)
        bottom_panel_layout.addLayout(nav_buttons_layout)

        main_layout.addWidget(bottom_panel)
        self.setLayout(main_layout)

    def load_data(self):
        try:
            with open('pokedex.json', 'r', encoding='utf-8') as f:
                self.pokemon_data = json.load(f)
            if self.pokemon_data:
                self.update_ui()
            else:
                self.name_label.setText("JSON VACÍO")
        except FileNotFoundError:
            self.name_label.setText("NO JSON")

    def update_ui(self):
        poke = self.pokemon_data[self.current_index]
        
        self.name_label.setText(poke['nombre'].upper())
        
        tipo_data = poke['tipo']
        if isinstance(tipo_data, list):
            texto_tipo = "/".join(tipo_data)
        else:
            texto_tipo = str(tipo_data)
            
        self.type_label.setText(f"TIPO: {texto_tipo.upper()}")
        self.desc_label.setText(poke['descripcion'])
        
        img_full_path = os.path.join(self.img_folder_path, poke['imagen'])
        pixmap = QPixmap(img_full_path)
        
        if not pixmap.isNull():
            self.image_label.setPixmap(pixmap.scaled(self.image_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            self.image_label.setText("NO IMG")
        
        self.update_leds(poke['tipo'])

    def update_leds(self, data_tipo):
        colores = {
            "fuego":     (1.0, 0.0, 0.0),  
            "planta":    (0.0, 1.0, 0.0),  
            "agua":      (0.0, 0.0, 1.0),  
            "electrico": (1.0, 1.0, 0.0),  
            "hielo":     (0.0, 1.0, 1.0),  
            "psiquico":  (1.0, 0.0, 1.0),  
            "veneno":    (0.5, 0.0, 1.0),  
            "hada":      (1.0, 0.2, 0.5),  
            "bicho":     (0.5, 1.0, 0.0),  
            "dragon":    (0.2, 0.0, 0.8),  
            "fantasma":  (0.3, 0.0, 0.6),  
            "volador":   (0.6, 0.8, 1.0),  
            "tierra":    (1.0, 0.3, 0.0),  
            "roca":      (0.6, 0.4, 0.0),  
            "lucha":     (1.0, 0.5, 0.0),  
            "normal":    (0.5, 0.5, 0.5),  
            "acero":     (0.6, 0.8, 0.9),  
            "siniestro": (0.2, 0.0, 0.0),  
        }
        
        tipos_procesados = []
        if isinstance(data_tipo, list):
            tipos_procesados = [str(t).lower() for t in data_tipo]
        elif isinstance(data_tipo, str):
            clean_str = data_tipo.replace(',', '/')
            if "/" in clean_str:
                tipos_procesados = [t.strip().lower() for t in clean_str.split("/")]
            else:
                tipos_procesados = [clean_str.strip().lower()]
        
        c1 = (0,0,0)
        c2 = (0,0,0)
        
        if len(tipos_procesados) == 1:
            tipo = tipos_procesados[0]
            c1 = c2 = colores.get(tipo, (0.5, 0.5, 0.5))
            
        elif len(tipos_procesados) >= 2:
            c1 = colores.get(tipos_procesados[0], (0.5, 0.5, 0.5))
            c2 = colores.get(tipos_procesados[1], (0.5, 0.5, 0.5))
            
        led_izquierda.color = c1
        led_derecha.color = c2
        
    def show_next(self):
        if self.pokemon_data:
            self.current_index = (self.current_index + 1) % len(self.pokemon_data)
            self.update_ui()

    def show_prev(self):
        if self.pokemon_data:
            self.current_index = (self.current_index - 1 + len(self.pokemon_data)) % len(self.pokemon_data)
            self.update_ui()

    def show_random(self):
        if self.pokemon_data:
            self.current_index = random.randint(0, len(self.pokemon_data) - 1)
            self.update_ui()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = PokedexApp()
    window.show()
    sys.exit(app.exec())