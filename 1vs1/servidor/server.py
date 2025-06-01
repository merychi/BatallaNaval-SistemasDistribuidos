# servidor.py
import socket
from config import *

# Crea un tablero vacío lleno de agua (~)
def crear_tablero_vacio():
    return [["~" for _ in range(COLUMNAS)] for _ in range(FILAS)]

# Convierte el string de configuración del tablero en una matriz válida
def enviar_tablero(config_str, tablero_destino):
    if len(config_str) != FILAS * COLUMNAS:
        print(f"SERVIDOR: Error - Longitud de config ({len(config_str)}) != tamaño tablero ({FILAS*COLUMNAS}).")
        return False
    
    idx = 0
    for r in range(FILAS):
        for c in range(COLUMNAS):
            char_recibido = config_str[idx]
            if char_recibido in ['B', '~']:  # B = Barco, ~ = agua
                tablero_destino[r][c] = char_recibido
            else:
                print(f"SERVIDOR: Caracter inválido '{char_recibido}' en config. Se usará '~'.")
                tablero_destino[r][c] = '~'
            idx += 1
    print("SERVIDOR: Tablero parseado:")
    for fila_vista in tablero_destino:
        print(" ".join(fila_vista))
    return True

# Verifica si el juego terminó (no quedan barcos 'B' en el tablero)
def verificar_fin_juego_servidor(tablero_del_jugador_atacado):
    for fila in tablero_del_jugador_atacado:
        if "B" in fila: 
            return False 
    return True

# Lógica principal del servidor
def iniciarServidor():
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    host = '0.0.0.0'
    port = 5050

    servidor.bind((host, port))
    servidor.listen(2)
    print("Servidor escuchando clientes en el", port)

    # Aceptar conexión de ambos jugadores
    jugador1, addr1 = servidor.accept()
    print (f"Se ha conectado jugador 1 {addr1}")
    jugador2, addr2 = servidor.accept()
    print (f"Se ha conectado jugador 2 {addr2}")

    # Notificar a los jugadores que la partida comienza
    jugador1.send("PARTIDA INICIADA - ERES JUGADOR 1\n".encode())
    jugador2.send("PARTIDA INICIADA - ERES JUGADOR 2\n".encode())

    # Crear tableros vacíos para ambos jugadores
    tablero_j1 = crear_tablero_vacio() # Barcos del Jugador 1
    tablero_j2 = crear_tablero_vacio() # Barcos del Jugador 2

    print("SERVIDOR: Esperando configuración de tableros de los jugadores...")

    config_j1_ok = False
    config_j2_ok = False

    # Recibir configuración del Jugador 1
    try:
        print("SERVIDOR: Esperando config del Jugador 1...")
        datos_config_j1_bytes = jugador1.recv(FILAS * COLUMNAS + 5) 
        if not datos_config_j1_bytes:
            raise ConnectionError("Jugador 1 desconectado durante configuración.")
        config_j1_str = datos_config_j1_bytes.decode().strip()
        
        if enviar_tablero(config_j1_str, tablero_j1):
            jugador1.send("CONFIGURACION RECIBIDA\n".encode())
            config_j1_ok = True
            print("SERVIDOR: Configuración J1 OK.")
        else:
            jugador1.send("ERROR CONFIGURACION\n".encode())
            print("SERVIDOR: Error en configuración J1.")
    except Exception as e:
        print(f"SERVIDOR: Excepción con config J1: {e}")

    # Recibir configuración del Jugador 2 (solo si J1 fue correcto)
    if config_j1_ok: 
        try:
            print("SERVIDOR: Esperando config del Jugador 2...")
            datos_config_j2_bytes = jugador2.recv(FILAS * COLUMNAS + 5)
            if not datos_config_j2_bytes:
                raise ConnectionError("Jugador 2 desconectado durante configuración.")
            config_j2_str = datos_config_j2_bytes.decode().strip()

            if enviar_tablero(config_j2_str, tablero_j2):
                jugador2.send("CONFIGURACION RECIBIDA\n".encode())
                config_j2_ok = True
                print("SERVIDOR: Configuración J2 OK.")
            else:
                jugador2.send("ERROR CONFIGURACION\n".encode())
                print("SERVIDOR: Error en configuración J2.")
        except Exception as e:
            print(f"SERVIDOR: Excepción con config J2: {e}")

    # Si alguna configuración falló, cerrar conexiones
    if not (config_j1_ok and config_j2_ok):
        print("SERVIDOR: Falló la configuración de uno o ambos jugadores. Terminando partida.")
        try: jugador1.send("FALLO_CONFIG_TERMINANDO\n".encode())
        except: pass
        try: jugador2.send("FALLO_CONFIG_TERMINANDO\n".encode())
        except: pass
        jugador1.close()
        jugador2.close()
        servidor.close()
        return

    print("SERVIDOR: Configuración de ambos jugadores recibida. Iniciando turnos.")

    turno_jugador1 = True

    # Bucle principal de juego por turnos
    while True:
        # Determina el turno actual y el jugador objetivo
        tablero_objetivo_actual = None
        jugador_actual = None
        otro_jugador = None
        num_jugador_actual_str = ""
        nombre_jugador_objetivo_str = ""

        if turno_jugador1: 
            jugador_actual = jugador1
            otro_jugador = jugador2
            num_jugador_actual = "1"
            tablero_objetivo_actual = tablero_j2
            nombre_jugador_objetivo_str = "2"
        else:
            jugador_actual = jugador2
            otro_jugador = jugador1
            num_jugador_actual = "2"
            tablero_objetivo_actual = tablero_j1
            nombre_jugador_objetivo_str = "1"

        # Enviar instrucciones a los jugadores
        jugador_actual.send("TURNO\n".encode())
        otro_jugador.send("ESPERA\n".encode())

        # Recibir disparo del jugador actual
        try:
            datos_recibidos = jugador_actual.recv(1024)
            if not datos_recibidos: 
                print(f"Jugador {num_jugador_actual} se desconectó")
                try:
                    otro_jugador.send(f"OPONENTE DESCONECTADO\n".encode())
                except:
                    pass 
                break
            datos = datos_recibidos.decode().strip() 
        except ConnectionResetError:
            print(f"Jugador {num_jugador_actual} se desconectó (ConnectionResetError)")
            try:
                otro_jugador.send(f"OPONENTE DESCONECTADO\n".encode())
            except:
                pass
            break
        except socket.error as e:
            print(f"Error de socket con jugador {num_jugador_actual}: {e}")
            try:
                otro_jugador.send(f"OPONENTE DESCONECTADO\n".encode())
            except:
                pass
            break

        print(f"Disparo recibido de jugador {num_jugador_actual}: {datos}")
        resultado = "error"

        # Procesar disparo
        try:
            partes = datos.split(',')
            if len(partes) != 2:
                raise ValueError("Formato de coordenadas incorrecto")
            
            fila_disparo = int(partes[0])
            col_disparo = int(partes[1])

            if not (0 <= fila_disparo < FILAS and 0 <= col_disparo < COLUMNAS):
                print(f"SERVIDOR: Coordenadas fuera de rango.")
                resultado_disparo = "agua"
            else:
                celda = tablero_objetivo_actual[fila_disparo][col_disparo]

                if celda == "B":
                    resultado_disparo = "impacto"
                    tablero_objetivo_actual[fila_disparo][col_disparo] = "X"
                    print(f"SERVIDOR: ¡IMPACTO! en ({fila_disparo},{col_disparo})")

                    if verificar_fin_juego_servidor(tablero_objetivo_actual):
                        print(f"SERVIDOR: ¡JUEGO TERMINADO! Jugador {num_jugador_actual} GANA.")
                        jugador_actual.send(f"GANASTE-Todos los barcos enemigos hundidos\n".encode())
                        otro_jugador.send(f"PERDISTE-Todos tus barcos han sido hundidos\n".encode())
                        break
                
                elif celda == "~":
                    resultado_disparo = "agua"
                    tablero_objetivo_actual[fila_disparo][col_disparo] = "M"
                    print(f"SERVIDOR: AGUA en ({fila_disparo},{col_disparo})")
                
                elif celda == "X":
                    resultado_disparo = "impacto"  # disparo repetido sobre barco
                    print(f"SERVIDOR: Disparo REPETIDO a impacto")
                
                elif celda == "M":
                    resultado_disparo = "agua"  # disparo repetido sobre agua
                    print(f"SERVIDOR: Disparo REPETIDO a agua")
                else:
                    print(f"SERVIDOR: Estado de celda desconocido")
                    resultado_disparo = "agua"

        except ValueError:
            print(f"SERVIDOR: Error parseando coordenadas")
            resultado_disparo = "agua"

        # Notificar resultado del disparo a ambos jugadores
        jugador_actual.send(f"RESULTADO-{resultado_disparo}\n".encode())
        otro_jugador.send(f"DISPARO-{datos}-{resultado_disparo}\n".encode())

        # Cambiar turno
        turno_jugador1 = not turno_jugador1

    # Cierre de conexiones y limpieza
    print("Cerrando conexiones...")
    jugador1.close()
    jugador2.close()
    servidor.close()
    print("Servidor Cerrado")

# Punto de entrada del programa
if __name__ == "__main__":
    iniciarServidor()
