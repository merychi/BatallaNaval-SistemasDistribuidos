import pygame
import socket
import sys
import json
import time
from barcos import *
from tablero import *
from interfaz.interfaz import InterfazBatallaNaval
from interfaz.menu import bucle_menu_principal

FLOTA_A_COLOCAR = [
    (PortaAviones, ()),
    (Buque, ()),
    (Submarino, ()),
    (Crucero, ()),
    (Lancha, ()),
]


def client():
    cliente_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_ip = "127.0.0.1"
    server_port = 5070

    try:
        cliente_socket.connect((server_ip, server_port))
        cliente_socket.setblocking(False)
    except socket.error as e:
        print(f"CLIENTE: No se pudo conectar al servidor: {e}")
        sys.exit()

    tablero_jugador_logico = [["~" for _ in range(COLUMNAS)] for _ in range(FILAS)]
    tablero_oponente_vista = [["?" for _ in range(COLUMNAS)] for _ in range(FILAS)]
    lista_barcos_del_jugador = []

    for ClaseBarco, _ in FLOTA_A_COLOCAR:
        barco_obj = ClaseBarco()
        lista_barcos_del_jugador.append(barco_obj)

    interfaz = InterfazBatallaNaval(
        tablero_jugador_logico, {}, lista_barcos_del_jugador
    )
    interfaz.actualizar_mensaje("Conectando al servidor...", tipo="conexion")

    coordenadas_ultimo_disparo_realizado = None
    buffer_recepcion = ""
    ships_placed_and_sent = False
    player_id = ""

    def send_json_message(sock, msg_type, payload={}):
        try:
            full_message = {"type": msg_type}
            full_message.update(payload)
            sock.sendall((json.dumps(full_message) + "\n").encode("utf-8"))
            return True
        except socket.error as e:
            print(f"CLIENTE: Error al enviar mensaje JSON: {e}")
            return False

    def send_ship_placements():
        for barco in lista_barcos_del_jugador:
            if barco.esta_colocado:
                coords = f"{chr(65 + barco.columna_inicial)}{barco.fila_inicial + 1}"
                orientation = "H" if barco.orientacion_colocacion == "h" else "V"

                if not send_json_message(
                    cliente_socket,
                    "PLACE_SHIP",
                    {
                        "ship_type": barco.nombre_tipo,
                        "coords": coords,
                        "orientation": orientation,
                    },
                ):
                    return False
        return True

    def manejar_disparo_desde_ui(fila, col, target_player):
        nonlocal coordenadas_ultimo_disparo_realizado

        print(f"Preparando disparo a {target_player} en ({fila},{col})")

        if not interfaz.turno_actual:
            interfaz.actualizar_mensaje("No es tu turno todavía", tipo="error")
            print("No es el turno del jugador")
            return

        # Preparar el mensaje de ataque
        mensaje_ataque = {
            "coords": f"{chr(65+col)}{fila+1}",
            "target_player": target_player,
        }
        print("Mensaje de ataque:", mensaje_ataque)

        if send_json_message(cliente_socket, "ATTACK", mensaje_ataque):
            interfaz.set_turno(False)
            coordenadas_ultimo_disparo_realizado = (fila, col)
            print("Disparo enviado correctamente")
        else:
            interfaz.actualizar_mensaje("Error al enviar ataque", tipo="error")
            print("Error al enviar disparo")

    while interfaz.ejecutando:
        interfaz.manejar_eventos(manejar_disparo_desde_ui)

        if interfaz.status == "READY" and not ships_placed_and_sent:
            print("Enviando datos, barcos de cliente listos")
            if send_ship_placements():
                send_json_message(cliente_socket, "GAME_STATE", {"status": "READY"})
                interfaz.actualizar_mensaje(
                    "Barcos colocados. Esperando a que el oponente esté listo...",
                    tipo="info",
                )
                interfaz.status = "WAITING"
                ships_placed_and_sent = True
            else:
                interfaz.actualizar_mensaje(
                    "Error al enviar barcos al servidor", tipo="error"
                )
                interfaz.ejecutando = False

        try:
            datos_nuevos = cliente_socket.recv(4096)
            if not datos_nuevos:
                print("CLIENTE: El servidor cerró la conexión.")
                interfaz.actualizar_mensaje("Servidor desconectado.", tipo="error")
                interfaz.ejecutando = False
                break

            buffer_recepcion += datos_nuevos.decode()

            while "\n" in buffer_recepcion:
                msg_completo, buffer_recepcion = buffer_recepcion.split("\n", 1)
                msg_completo = msg_completo.strip()

                if not msg_completo:
                    continue

                print(f"CLIENTE: Recibido JSON: '{msg_completo}'")

                try:
                    parsed_message = json.loads(msg_completo)
                    message_type = parsed_message.get("type")
                    payload = parsed_message

                    if message_type == "WELCOME":
                        player_id = payload.get("player_id", "")
                        interfaz.player_id = player_id
                        interfaz.actualizar_mensaje(
                            payload.get("message", "Bienvenido al juego."),
                            tipo="conexion",
                        )

                    elif message_type == "MATCH_CREATED":
                        interfaz.actualizar_mensaje(
                            payload.get(
                                "message",
                                "Has creado una nueva partida. Esperando al oponente...",
                            ),
                            tipo="conexion",
                        )

                    elif message_type == "MATCH_JOINED":
                        interfaz.player_id = payload["player_id"]
                        interfaz.actualizar_mensaje(
                            f"Unido a partida {payload['game_id']} ({payload['total_players']}/{payload['required_players']} jugadores)",
                            tipo="conexion",
                        )

                    elif (
                        message_type == "GAME_STATE" and payload.get("state") == "SETUP"
                    ):
                        interfaz.actualizar_mensaje(
                            payload.get(
                                "message", "Fase de configuración. Coloca tus barcos."
                            ),
                            tipo="info",
                        )
                        if not interfaz.all_ships_placed_visually:
                            interfaz.colocar_barcos_manual()

                    elif message_type == "SHIP_PLACED":
                        status = payload.get("status")
                        ship_type = payload.get("ship_type")
                        if status == "OK":
                            interfaz.actualizar_mensaje(
                                f"Barco {ship_type} colocado exitosamente.", tipo="info"
                            )
                        else:
                            interfaz.actualizar_mensaje(
                                f"Error al colocar {ship_type}: {payload.get('message')}",
                                tipo="error",
                            )
                            interfaz.ejecutando = False

                    elif (
                        message_type == "GAME_STATE"
                        and payload.get("state") == "PLAYING"
                    ):
                        interfaz.status = "PLAYING"
                        if payload.get("your_turn", False):
                            interfaz.set_turno(True)

                    elif message_type == "YOUR_TURN":
                        interfaz.status = "PLAYING"  # Forzar estado correcto
                        interfaz.set_turno(True)

                        # Actualizar el mensaje de turno primero
                        interfaz.actualizar_mensaje_turnos(
                            payload.get("message", "Es tu turno de atacar")
                        )

                        # Solo actualizar los targets si vienen en el payload
                        if "available_targets" in payload:
                            interfaz.actualizar_oponentes(payload["available_targets"])
                        else:
                            # Si no vienen targets, mantener los que ya teníamos
                            print(
                                "Mensaje YOUR_TURN sin targets, manteniendo los existentes"
                            )

                        print(
                            f"Turno activado para {interfaz.player_id}. Targets disponibles: {interfaz.target_players}"
                        )

                    elif message_type == "OPPONENT_TURN":
                        interfaz.status = "PLAYING"
                        interfaz.set_turno(False)
                        interfaz.actualizar_mensaje_turnos(
                            payload.get("message", "Espera el turno de tu oponente.")
                        )

                    elif message_type == "ATTACK":
                        coords_str = payload.get("coords")
                        result = payload.get("result")
                        sunk_ship = payload.get("sunk_ship")

                        col = ord(coords_str[0].upper()) - ord("A")
                        fila = int(coords_str[1:]) - 1

                        if result in ["HIT", "SUNK"]:
                            tablero_jugador_logico[fila][col] = "X"
                            if sunk_ship:
                                interfaz.actualizar_mensaje(
                                    f"¡Tu {sunk_ship} ha sido hundido por un ataque enemigo en {coords_str}!",
                                    tipo="ataque",
                                )
                            else:
                                interfaz.actualizar_mensaje(
                                    f"¡Te atacaron en {coords_str}! Fue un impacto.",
                                    tipo="ataque",
                                )
                        else:
                            tablero_jugador_logico[fila][col] = "M"
                            interfaz.actualizar_mensaje(
                                f"Te atacaron en {coords_str}. ¡Agua!", tipo="ataque"
                            )

                    elif message_type == "ATTACKED":
                        coords_str = payload.get("coords")
                        result = payload.get("result")
                        sunk_ship = payload.get("sunk_ship")

                        col = ord(coords_str[0].upper()) - ord("A")
                        fila = int(coords_str[1:]) - 1

                        if result in ["HIT", "SUNK"]:
                            tablero_jugador_logico[fila][col] = "X"
                            if sunk_ship:
                                interfaz.actualizar_mensaje(
                                    f"¡Tu {sunk_ship} ha sido hundido por un ataque enemigo en {coords_str}!",
                                    tipo="ataque",
                                )
                            else:
                                interfaz.actualizar_mensaje(
                                    f"¡Te atacaron en {coords_str}! Fue un impacto.",
                                    tipo="ataque",
                                )
                        else:
                            tablero_jugador_logico[fila][col] = "M"
                            interfaz.actualizar_mensaje(
                                f"Te atacaron en {coords_str}. ¡Agua!", tipo="ataque"
                            )

                    elif message_type == "ATTACK_RESULT":
                        coords_str = payload.get("coords")
                        result = payload.get("result")
                        sunk_ship = payload.get("sunk_ship")
                        target = payload.get("target")

                        if (
                            coordenadas_ultimo_disparo_realizado
                            and target in interfaz.tableros_oponentes
                        ):
                            try:
                                fila_tu_disp, col_tu_disp = (
                                    coordenadas_ultimo_disparo_realizado
                                )
                                if result in ["HIT", "SUNK"]:
                                    interfaz.tableros_oponentes[target][fila_tu_disp][
                                        col_tu_disp
                                    ] = "X"
                                    if sunk_ship:
                                        interfaz.actualizar_mensaje(
                                            f"¡Has hundido el {sunk_ship} enemigo en {coords_str}!",
                                            tipo="ataque",
                                        )
                                    else:
                                        interfaz.actualizar_mensaje(
                                            f"Tu disparo en {coords_str} fue un ¡IMPACTO!",
                                            tipo="ataque",
                                        )
                                else:
                                    interfaz.tableros_oponentes[target][fila_tu_disp][
                                        col_tu_disp
                                    ] = "M"
                                    interfaz.actualizar_mensaje(
                                        f"Tu disparo en {coords_str} fue ¡AGUA!",
                                        tipo="ataque",
                                    )

                                # Actualizar el tablero visual si es el objetivo actual
                                if (
                                    interfaz.target_players
                                    and interfaz.selected_target_index >= 0
                                ):
                                    current_target = interfaz.target_players[
                                        interfaz.selected_target_index
                                    ]
                                    if current_target == target:
                                        interfaz.tablero_oponente_actual = (
                                            interfaz.tableros_oponentes[target]
                                        )

                                coordenadas_ultimo_disparo_realizado = None
                            except Exception as e:
                                print(f"Error procesando ATTACK_RESULT: {e}")
                                interfaz.actualizar_mensaje(
                                    "Error procesando resultado de ataque", tipo="error"
                                )

                    elif message_type == "GAME_OVER":
                        winner_id = payload.get("winner")
                        message = payload.get("message", "El juego ha terminado.")
                        if winner_id == None:
                            interfaz.actualizar_mensaje(
                                f"¡PERDISTE! {message}", tipo="info"
                            )
                        else:
                            if winner_id == player_id:
                                interfaz.actualizar_mensaje(
                                    f"¡GANASTE! {message}", tipo="info"
                                )
                            else:
                                interfaz.actualizar_mensaje(
                                    f"¡PERDISTE! {message}", tipo="info"
                                )

                    elif message_type == "ERROR":
                        interfaz.actualizar_mensaje(
                            f"Error del servidor: {payload.get('message', 'Desconocido')}",
                            tipo="error",
                        )

                    elif message_type == "SERVER_SHUTDOWN":
                        interfaz.actualizar_mensaje(
                            payload.get("message", "El servidor se está apagando."),
                            tipo="conexion",
                        )
                        interfaz.ejecutando = False

                    elif message_type == "NEW_PLAYER":
                        interfaz.actualizar_mensaje_conexiones(
                            f"Nuevo jugador: {payload['player_id']} ({payload['total_players']}/{payload['required_players']})"
                        )

                    elif message_type == "BOARD_UPDATE":
                        # Actualizar tablero propio
                        if "my_board" in payload:
                            tablero_jugador_logico[:] = payload["my_board"]
                            interfaz.tablero_jugador = tablero_jugador_logico

                        # Actualizar vistas de oponentes
                        if "opponent_boards" in payload:
                            for opponent_id, board in payload[
                                "opponent_boards"
                            ].items():
                                if opponent_id not in interfaz.tableros_oponentes:
                                    interfaz.tableros_oponentes[opponent_id] = [
                                        row[:] for row in board
                                    ]
                                else:
                                    for i in range(FILAS):
                                        for j in range(COLUMNAS):
                                            if board[i][j] != "?":
                                                interfaz.tableros_oponentes[
                                                    opponent_id
                                                ][i][j] = board[i][j]

                            # Actualizar el tablero visual si hay un objetivo seleccionado
                            if (
                                interfaz.target_players
                                and interfaz.selected_target_index >= 0
                            ):
                                current_target = interfaz.target_players[
                                    interfaz.selected_target_index
                                ]
                                interfaz.tablero_oponente_actual = (
                                    interfaz.tableros_oponentes.get(current_target)
                                )

                    interfaz.dibujar()

                except json.JSONDecodeError:
                    interfaz.actualizar_mensaje(
                        "Error de comunicación con el servidor.", tipo="error"
                    )
                except Exception as e:
                    interfaz.actualizar_mensaje(
                        "Error interno. Desconectando.", tipo="error"
                    )
                    interfaz.ejecutando = False

        except BlockingIOError:
            pass
        except ConnectionResetError:
            interfaz.actualizar_mensaje(
                "Conexión perdida. Desconectando.", tipo="error"
            )
            interfaz.ejecutando = False
        except socket.error as e:
            interfaz.actualizar_mensaje("Error de red. Desconectando.", tipo="error")
            interfaz.ejecutando = False

        interfaz.dibujar()

    print("CLIENTE: Cerrando cliente...")
    try:
        cliente_socket.shutdown(socket.SHUT_RDWR)
    except (OSError, socket.error) as e:
        print(f"CLIENTE: Error durante shutdown del socket: {e}")
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
