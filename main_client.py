import time
import json
import os
import sys
import paramiko 

# ==========================================
# CONFIGURACIÓN DE RED Y RUTAS
# ==========================================
HOST_IP = "192.168.0.24"          # IP de la Raspberry del Profesor
HOST_USER = "minipc"              # Usuario SSH del Profesor
HOST_PASS = "P0ck3tM0nst3rs"      # Contraseña del Profesor

# Ruta base donde está la carpeta del proyecto en el PC del profesor
BASE_REMOTE_DIR = "/home/minipc/Desktop/Game_App/Player_logs"
HOST_LOG_PATH = f"{BASE_REMOTE_DIR}/Player_loggfgfs.log"

# Configuración Local
LOCAL_PLAYER_ID = "tonoto" 

# --- CORRECCIÓN IMPORTANTE: Debe llamarse igual que en los juegos ---
LOCAL_LOG_FILE = "eventos_minijuego1.log" 

# ==========================================
# MAPEO DE JUEGOS (GameID -> Archivo)
# ==========================================
JUEGOS_DISPONIBLES = {
    1: "simon.py",       
    2: "flappy_pkmn.py",      
    3: "lluvia_pkmn.py",      
    4: "supersonico.py",    
    99: "juego_supervivencia.py" 
}

# ==========================================
# FUNCIONES DE RED (PARAMIKO)
# ==========================================
def get_sftp_connection():
    """Crea y retorna una conexión SFTP usando Paramiko."""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(HOST_IP, username=HOST_USER, password=HOST_PASS, timeout=5)
        return ssh, ssh.open_sftp()
    except Exception as e:
        print(f"Error de conexión SSH: {e}")
        return None, None

def scp_upload_log():
    """Sube el log local intentando manejar errores de ruta."""
    ssh, sftp = get_sftp_connection()
    if not sftp:
        print("Error: No hay conexión para subir datos.")
        return

    try:
        try:
            sftp.chdir(BASE_REMOTE_DIR)
        except IOError:
            print(f"No encuentro '{BASE_REMOTE_DIR}'. Intentando subir a la raíz...")
        
        try:
            sftp.chdir("recibidos")
        except IOError:
            try:
                sftp.chdir(BASE_REMOTE_DIR)
            except IOError:
                print("No pude entrar a 'recibidos'. Subiendo en carpeta actual...")

        # El nombre con el que se guardará en el PC del profe
        remote_filename = f"player_{LOCAL_PLAYER_ID}.log"
        
        # Subimos el archivo local correcto
        sftp.put(LOCAL_LOG_FILE, remote_filename)
        print(f"Log enviado como {remote_filename}")
        
    except Exception as e:
        print(f"ERROR AL SUBIR LOG: {e}")
    finally:
        if sftp: sftp.close()
        if ssh: ssh.close()

# ==========================================
# FUNCIONES DE LÓGICA
# ==========================================
def escribir_log_local(stage, action, result=None, score=None):
    """Escribe en el formato JSON estricto del Anexo."""
    entry = {
        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
        "game_stage": stage,
        "PlayerID": LOCAL_PLAYER_ID,
        "Action": action
    }
    if result: entry["Result"] = result
    if score is not None: entry["Score"] = score
    
    # Modo 'a' para no borrar lo que escribieron los juegos
    with open(LOCAL_LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
    
    scp_upload_log()

def leer_ultima_orden_host():
    """
    Lee 'game_status.log' soportando formato SIN comillas (pseudo-JSON).
    """
    # Primero intentamos bajar el log del host para ver si hay órdenes nuevas
    ssh, sftp = get_sftp_connection()
    if sftp:
        try:
            sftp.get(HOST_LOG_PATH, "game_status.log")
        except:
            pass
        finally:
            sftp.close()
            ssh.close()

    if not os.path.exists("game_status.log"):
        return None

    last_order = None
    try:
        with open("game_status.log", "r") as f:
            for line in f:
                line = line.strip()
                start = line.find("{")
                end = line.rfind("}")
                
                if start != -1 and end != -1:
                    content = line[start+1:end] 
                    pairs = content.split(',')
                    data = {}
                    
                    for pair in pairs:
                        if ':' in pair:
                            k, v = pair.split(':', 1)
                            k = k.strip()
                            v = v.strip()
                            if v.isdigit():
                                v = int(v)
                            data[k] = v
                    if data:
                        last_order = data
    except Exception as e:
        print(f"Error leyendo orden: {e}")
        
    return last_order

def ejecutar_minijuego(game_id, sabotage_delay=0):
    script_name = JUEGOS_DISPONIBLES.get(game_id)
    if not script_name:
        print(f"Error: GameID {game_id} no reconocido en mi lista.")
        return

    print(f"Ejecutando: {script_name}")
    
    if sabotage_delay > 0:
        print(f"SABOTAJE ACTIVO: Retraso de {sabotage_delay} segundos...")
        time.sleep(sabotage_delay)

    try:
        # Ejecuta el juego y espera a que termine
        exit_code = os.system(f"{sys.executable} {script_name}")
        if exit_code != 0:
            print(f"El juego cerró con código: {exit_code}")
            
    except Exception as e:
        print(f"Error crítico ejecutando juego: {e}")
    
    # Al terminar el juego, subimos el log actualizado
    scp_upload_log()

# ==========================================
# BLOQUE PRINCIPAL (MAIN)
# ==========================================
def main():
    print("--- INICIANDO CLIENTE TIC IS AMONG US ---")
    
    print("Conectando al Lobby...")
    escribir_log_local("Lobby", "Join")
    
    conectado = False
    while not conectado:
        orden = leer_ultima_orden_host()
        if orden:
            print(f"Última orden: {orden}")
        
        if orden and orden.get("Action") == "Accepted" and str(orden.get("PlayerID")) == str(LOCAL_PLAYER_ID):
            print("¡Conexión Aceptada por el Host!")
            escribir_log_local("Lobby", "Ready")
            conectado = True
        else:
            print("Esperando confirmación del Host (Action: Accepted)...")
            time.sleep(3)

    print("Cliente listo. Esperando inicio de rondas...")
    last_game_id_played = -1
    sabotage_pending = 0
    
    while True:
        time.sleep(2)
        
        orden = leer_ultima_orden_host()
        if not orden: continue
            
        stage = orden.get("stage", "Lobby")
        if not stage: stage = orden.get("game_stage")

        action = orden.get("Action")
            
        if action == "Sabotage" and orden.get("Effect") == "Delay":
            sabotage_pending = orden.get("Value", 0)
            print(f"ALERTA: Sabotaje recibido. Retraso de {sabotage_pending}s.")

        if action == "Assign":
            game_id = orden.get("GameID")
            # Solo ejecutamos si es una misión nueva
            if game_id != last_game_id_played:
                print(f"Nueva misión recibida: Juego {game_id}")
                ejecutar_minijuego(game_id, sabotage_delay=sabotage_pending)
                last_game_id_played = game_id
                sabotage_pending = 0
            
        if stage == "Final":
            print("¡RONDA FINAL INICIADA!")
            ejecutar_minijuego(99)
            break 

if __name__ == "__main__":
    main()