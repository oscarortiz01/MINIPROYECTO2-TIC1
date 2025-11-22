import time
import json
import os
import sys
import paramiko 


# CONFIGURACIÓN DE RED

HOST_IP = "192.168.0.24"
HOST_USER = "minipc"
HOST_PASS = "P0ck3tM0nst3rs"

BASE_REMOTE_DIR = "/home/minipc/Desktop/Game_App/Player_logs"
HOST_LOG_PATH = f"{BASE_REMOTE_DIR}/Player_loggfgfs.log"

LOCAL_PLAYER_ID = "tonoto" 
LOCAL_LOG_FILE = "eventos_minijuego1.log" 


# MAPEO DE JUEGOS

JUEGOS_DISPONIBLES = {
    1: "simon.py",       
    2: "flappy_pkmn.py",      
    3: "lluvia_pkmn.py",      
    4: "supersonico.py",    
    99: "juego_supervivencia.py" 
}


# FUNCIONES DE CONEXIÓN

def get_sftp_connection():
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(HOST_IP, username=HOST_USER, password=HOST_PASS, timeout=5)
        return ssh, ssh.open_sftp()
    except Exception as e:
        print(f"Error de conexión SSH: {e}")
        return None, None

def scp_upload_log():
    ssh, sftp = get_sftp_connection()
    if not sftp:
        return

    try:
        try:
            sftp.chdir(BASE_REMOTE_DIR)
        except IOError:
            pass 
        
        try:
            sftp.chdir("recibidos")
        except IOError:
            try:
                sftp.chdir(BASE_REMOTE_DIR)
            except IOError:
                pass

        remote_filename = f"player_{LOCAL_PLAYER_ID}.log"
        sftp.put(LOCAL_LOG_FILE, remote_filename)
        print(f"Log enviado: {remote_filename}")
        
    except Exception as e:
        print(f"Error al subir log: {e}")
    finally:
        if sftp: sftp.close()
        if ssh: ssh.close()


# LÓGICA DEL CLIENTE

def escribir_log_local(stage, action, result=None, score=None):
    entry = {
        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
        "game_stage": stage,
        "PlayerID": LOCAL_PLAYER_ID,
        "Action": action
    }
    if result: entry["Result"] = result
    if score is not None: entry["Score"] = score
    
    with open(LOCAL_LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
    
    scp_upload_log()

def leer_ultima_orden_host():
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
                            if v.isdigit(): v = int(v)
                            data[k] = v
                    if data:
                        last_order = data
    except Exception:
        pass
        
    return last_order

def ejecutar_minijuego(game_id, sabotage_delay=0):
    script_name = JUEGOS_DISPONIBLES.get(game_id)
    if not script_name:
        print(f"ID {game_id} no reconocido.")
        return

    print(f"Ejecutando: {script_name}")
    
    if sabotage_delay > 0:
        print(f"SABOTAJE: Esperando {sabotage_delay}s...")
        time.sleep(sabotage_delay)

    try:
        os.system(f"{sys.executable} {script_name}")
    except Exception as e:
        print(f"Error ejecutando juego: {e}")
    
    scp_upload_log()


# MAIN

def main():
    print("--- CLIENTE INICIADO ---")
    escribir_log_local("Lobby", "Join")
    
    conectado = False
    while not conectado:
        orden = leer_ultima_orden_host()
        
        if orden and orden.get("Action") == "Accepted" and str(orden.get("PlayerID")) == str(LOCAL_PLAYER_ID):
            print("Conexión establecida.")
            escribir_log_local("Lobby", "Ready")
            conectado = True
        else:
            print("Esperando confirmación...")
            time.sleep(3)

    print("Esperando rondas...")
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
            print(f"Sabotaje: {sabotage_pending}s")

        if action == "Assign":
            game_id = orden.get("GameID")
            if game_id != last_game_id_played:
                ejecutar_minijuego(game_id, sabotage_delay=sabotage_pending)
                last_game_id_played = game_id
                sabotage_pending = 0
            
        if stage == "Final":
            print("RONDA FINAL")
            ejecutar_minijuego(99)
            break 

if __name__ == "__main__":
    main()