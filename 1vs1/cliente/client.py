import socket
import sys
from barcos import *
from tablero import *
from config import * 
from interfaz.interfaz import InterfazBatallaNaval 
from interfaz.menu import bucle_menu_principal

# Barcos y posiciones iniciales a colocar en el tablero (clase y coordenadas + orientación)
FLOTA_A_COLOCAR = [
    (PortaAviones, ()),
    (Buque,        ()),
    (Submarino,    ()),
    (Crucero,      ()),
    (Lancha,       ()),
]

def tableroConfigurado(socket_cliente, tablero_configurado_matriz):
    # Convierte la matriz del tablero en un string para enviar al servidor
    config_str_envio = ""
    for r in range(FILAS):
        for c in range(COLUMNAS):
            config_str_envio += tablero_configurado_matriz[r][c]
    
    try:
        print(f"CLIENTE: Enviando configuración al servidor: '{config_str_envio[:30]}...'")
        # Envía la configuración del tablero al servidor
        socket_cliente.sendall(f"{config_str_envio}\n".encode())
        # Espera confirmación del servidor
        confirmacion_servidor = socket_cliente.recv(1024).decode().strip()
        
        if confirmacion_servidor == "CONFIGURACION RECIBIDA":
            print("CLIENTE: Servidor confirmó la recepción de la configuración.")
            return True
        else:
            print(f"CLIENTE: Respuesta inesperada del servidor tras enviar config: '{confirmacion_servidor}'")
            return False
    except Exception as e:
        print(f"CLIENTE: Excepción durante envío/recepción de config: {e}")
        return False

def client():
    # Crear socket TCP cliente
    cliente_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_ip = '127.0.0.1' 
    server_port = 5050

    try:
        # Conectar al servidor
        cliente_socket.connect((server_ip, server_port))
    except socket.error as e:
        print(f"No se pudo conectar al servidor: {e}")
        sys.exit()

    try:
        # Recibir mensaje inicial del servidor 
        initial_msg_bytes = cliente_socket.recv(1024)
        if not initial_msg_bytes:
            print("El servidor cerró la conexión prematuramente.")
            cliente_socket.close()
            sys.exit()
        nJugador_msg = initial_msg_bytes.decode().strip()
        print(nJugador_msg)
    except socket.error as e:
        print(f"Error recibiendo mensaje inicial: {e}")
        cliente_socket.close()
        sys.exit()

    # --- Inicializar tableros y barcos ---
    tablero_jugador_logico = [["~" for _ in range(COLUMNAS)] for _ in range(FILAS)]
    tablero_oponente_vista = [["~" for _ in range(COLUMNAS)] for _ in range(FILAS)]
    lista_barcos_del_jugador = []

    # Instanciar objetos barco según la flota definida
    for ClaseBarco, _ in FLOTA_A_COLOCAR:
        barco_obj = ClaseBarco()
        lista_barcos_del_jugador.append(barco_obj)

    print("CLIENTE: Tablero lógico del jugador configurado:")
    for fila_vista in tablero_jugador_logico:
        print(" ".join(fila_vista))

    # --- Crear interfaz gráfica y pedir colocar barcos manualmente ---
    interfaz = InterfazBatallaNaval(tablero_jugador_logico, tablero_oponente_vista, lista_barcos_del_jugador)
    interfaz.actualizar_mensaje("Coloca tus barcos manualmente...")
    interfaz.colocar_barcos_manual()

    # Enviar configuración del tablero al servidor
    cliente_socket.setblocking(True) # Modo bloqueante para enviar/recibir config
    if not tableroConfigurado(cliente_socket, tablero_jugador_logico):
        interfaz.actualizar_mensaje("Error configurando tablero con servidor.")
        interfaz.dibujar() 
        interfaz.cerrar()
        cliente_socket.close()
        sys.exit()
    cliente_socket.setblocking(False) # Volver a no bloqueante

    interfaz.actualizar_mensaje("Tablero configurado.\n Esperando inicio...")

    # Guarda las coordenadas del último disparo para actualizar la interfaz al recibir resultado
    coordenadas_ultimo_disparo_realizado = None 
    buffer_recepcion = ""

    # --- Función callback para manejar disparos hechos por el usuario desde la interfaz ---
    def manejar_disparo_desde_ui(fila, col):
        nonlocal coordenadas_ultimo_disparo_realizado
        
        coords_str = f"{fila},{col}"
        try:
            cliente_socket.send(f"{coords_str}\n".encode()) # Enviar coordenadas al servidor
            print(f"CLIENTE: Disparo enviado a {coords_str}")
            interfaz.actualizar_mensaje("Disparo enviado. \nEsperando resultado...")
            interfaz.set_turno(False) # Termina turno tras disparar
            coordenadas_ultimo_disparo_realizado = (fila, col)
        except socket.error as e:
            print(f"CLIENTE: Error al enviar disparo: {e}")
            interfaz.actualizar_mensaje("Error de red. Desconectando.")
            interfaz.ejecutando = False

    # --- Bucle principal que mantiene la interfaz y recibe mensajes del servidor ---
    while interfaz.ejecutando:
        interfaz.manejar_eventos(manejar_disparo_desde_ui) # Procesa eventos de UI

        try:
            datos_nuevos = cliente_socket.recv(4096)
            if not datos_nuevos:
                print("CLIENTE: El servidor cerró la conexión.")
                interfaz.actualizar_mensaje("Servidor desconectado.")
                interfaz.ejecutando = False
                break
            
            buffer_recepcion += datos_nuevos.decode()

            # Procesar cada mensaje completo recibido separado por salto de línea
            while "\n" in buffer_recepcion:
                msg_completo, buffer_recepcion = buffer_recepcion.split("\n", 1)
                msg_completo = msg_completo.strip()

                if not msg_completo:
                    continue

                print(f"CLIENTE Recibido: '{msg_completo}'")

                # Manejo de diferentes mensajes del servidor:
                if msg_completo == "TURNO":
                    interfaz.set_turno(True)
                    interfaz.actualizar_mensaje("¡Es tu turno!")
                elif msg_completo == "ESPERA":
                    interfaz.set_turno(False)
                    interfaz.actualizar_mensaje("Espera...")
                elif msg_completo.startswith("DISPARO"): # El oponente disparó
                    try:
                        _, coords_str, resultado_disp_op = msg_completo.split("-")
                        fila_impactada, col_impactada = map(int, coords_str.split(","))
                        
                        # Actualizar tablero lógico con el impacto o agua
                        if resultado_disp_op == "impacto":
                            tablero_jugador_logico[fila_impactada][col_impactada] = "X"
                            for barco_obj in lista_barcos_del_jugador:
                                if barco_obj.registrar_impacto(fila_impactada, col_impactada):
                                    if barco_obj.esta_hundido():
                                        print(f"CLIENTE: ¡Tu {barco_obj.nombre_tipo} ha sido hundido!")
                                    break
                        elif resultado_disp_op == "agua":
                            tablero_jugador_logico[fila_impactada][col_impactada] = "M"
                        else: # hundido
                            tablero_jugador_logico[fila_impactada][col_impactada] = "X"
                            print(f"CLIENTE: Oponente hundió un barco en ({fila_impactada},{col_impactada})")

                        interfaz.actualizar_mensaje(f"Oponente disparó en ({fila_impactada},{col_impactada}): {resultado_disp_op}")
                    except ValueError:
                        print(f"CLIENTE: Error parseando mensaje DISPARO: {msg_completo}")

                elif msg_completo.startswith("RESULTADO"): # Resultado de tu disparo
                    try:
                        _, resultado_mi_disp = msg_completo.split("-")
                        if coordenadas_ultimo_disparo_realizado:
                            fila_tu_disp, col_tu_disp = coordenadas_ultimo_disparo_realizado
                            # Actualizar vista del tablero oponente según resultado
                            if resultado_mi_disp in ["impacto", "hundido"]:
                                tablero_oponente_vista[fila_tu_disp][col_tu_disp] = "X"
                            elif resultado_mi_disp == "agua":
                                tablero_oponente_vista[fila_tu_disp][col_tu_disp] = "M"
                            
                            coordenadas_ultimo_disparo_realizado = None # Resetear para siguiente disparo
                        
                        interfaz.actualizar_mensaje(f"Tu disparo fue: {resultado_mi_disp}. Esperando...")
                    except ValueError:
                        print(f"CLIENTE: Error parseando mensaje RESULTADO: {msg_completo}")
                
                elif msg_completo == "GANASTE":
                    interfaz.actualizar_mensaje("¡GANASTE! :)")
                    interfaz.ejecutando = False
                elif msg_completo == "PERDISTE":
                    interfaz.actualizar_mensaje("PERDISTE :(")
                    interfaz.ejecutando = False

        except BlockingIOError:
            pass
        except ConnectionResetError:
            print("CLIENTE: Se perdió la conexión con el servidor (ConnectionResetError).")
            interfaz.actualizar_mensaje("Conexión perdida. Desconectando.")
            interfaz.ejecutando = False
        except socket.error as e:
            print(f"CLIENTE: Error de socket recibiendo datos: {e}")
            interfaz.actualizar_mensaje("Error de red. Desconectando.")
            interfaz.ejecutando = False
        
        interfaz.dibujar() # Refrescar pantalla

    print("CLIENTE: Cerrando cliente...")
    try:
        if "GANASTE" in interfaz.mensaje_estado or "PERDISTE" in interfaz.mensaje_estado:
            import time
            time.sleep(3)

        cliente_socket.shutdown(socket.SHUT_RDWR)
    except (OSError, socket.error) as e:
        print(f"CLIENTE: Error durante shutdown del socket (puede ser normal si ya está cerrado): {e}")
    finally:
        cliente_socket.close()
    
    interfaz.cerrar() 
    sys.exit()

if __name__ == "__main__":
    while True:
        accion = bucle_menu_principal()

        if accion == "jugar":
            print("CLIENTE: Iniciando juego...")
            client()
            print("CLIENTE: Juego terminado. Volviendo al menú o saliendo...")

        elif accion == "salir":
            print("CLIENTE: Saliendo del juego desde el menú.")
            break 

    pygame.quit()
    sys.exit()
