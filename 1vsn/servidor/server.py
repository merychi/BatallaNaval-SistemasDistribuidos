import socket
import threading
import queue
import json
import time
import select
from config import *


def crear_tablero_vacio():
    return [["~" for _ in range(COLUMNAS)] for _ in range(FILAS)]


def verificar_fin_juego_servidor(tablero_del_jugador_atacado):
    for r in range(FILAS):
        for c in range(COLUMNAS):
            if tablero_del_jugador_atacado[r][c] == "B":
                return False
    return True


class ConnectionAcceptor(threading.Thread):
    def __init__(self, host, port, client_socket_queue):
        super().__init__()
        self.host = host
        self.port = port
        self.client_socket_queue = client_socket_queue
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.settimeout(1.0)
        self.running = True
        print(f"ConnectionAcceptor: Inicializando en {host}:{port}")

    def run(self):
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            print("ConnectionAcceptor: Servidor escuchando conexiones...")
        except socket.error as e:
            print(f"ConnectionAcceptor: Error al iniciar servidor: {e}")
            self.running = False
            return

        while self.running:
            try:
                conn, addr = self.server_socket.accept()
                print(f"ConnectionAcceptor: Nueva conexión aceptada de {addr}")
                self.client_socket_queue.put((conn, addr))
            except socket.timeout:
                pass
            except Exception as e:
                print(f"ConnectionAcceptor: Error al aceptar conexión: {e}")
                if not self.running:
                    break
        print("ConnectionAcceptor: Hilo de aceptación de conexiones terminado.")
        self.server_socket.close()

    def stop(self):
        print("ConnectionAcceptor: Deteniendo hilo de aceptación...")
        self.running = False


class Ship:
    def __init__(self, ship_type, length, coords, orientation):
        self.ship_type = ship_type
        self.length = length
        self.coords = coords
        self.orientation = orientation
        self.hits = [False] * length
        self.sunk = False

    def check_sunk(self):
        self.sunk = all(self.hits)
        return self.sunk

    def is_hit_at(self, r, c):
        for i, (ship_r, ship_c) in enumerate(self.coords):
            if ship_r == r and ship_c == c:
                self.hits[i] = True
                return True
        return False


class Player:
    def __init__(self, player_id, client_socket, address):
        self.id = player_id
        self.socket = client_socket
        self.address = address
        self.my_board = crear_tablero_vacio()
        self.opponent_board_view = [
            ["?" for _ in range(COLUMNAS)] for _ in range(FILAS)
        ]
        self.opponent_views = {}
        self.ships = []
        self.ready_for_game = False
        self.turn = False
        self.buffer_recepcion = ""
        self.Game_id = ""

    def send_message(self, message_type, payload={}):
        try:
            full_message = {"type": message_type}
            full_message.update(payload)
            self.socket.sendall((json.dumps(full_message) + "\n").encode("utf-8"))
        except Exception as e:
            print(
                f"Error al enviar mensaje '{message_type}' a {self.id} ({self.address}): {e}"
            )
            return False
        return True

    def place_ship_on_board(self, ship_type_name, start_row, start_col, orientation):
        length = 0
        ship_mapping = {
            "PortaAviones": 5,
            "Buque": 4,
            "Submarino": 3,
            "Crucero": 3,
            "Lancha": 2,
        }

        length = ship_mapping.get(ship_type_name)
        if length is None:
            return False, "Tipo de barco desconocido."

        ship_coords = []
        for i in range(length):
            r, c = start_row, start_col
            if orientation == "H":
                c += i
            else:
                r += i

            if not (0 <= r < FILAS and 0 <= c < COLUMNAS):
                return False, "Barco fuera de límites."
            if self.my_board[r][c] != "~":
                return False, "Barco se superpone con otro o con una zona ya ocupada."
            ship_coords.append((r, c))

        new_ship = Ship(ship_type_name, length, ship_coords, orientation)
        for r, c in ship_coords:
            self.my_board[r][c] = "B"
        self.ships.append(new_ship)
        return True, "OK"

    def register_hit(self, r, c):

        for ship in self.ships:
            if ship.is_hit_at(r, c):
                self.my_board[r][c] = "X"
                if ship.check_sunk():
                    return "SUNK", ship.ship_type
                return "HIT", None
        self.my_board[r][c] = "M"
        return "MISS", None


class GameMatch:
    def __init__(self, game_id):
        self.game_id = game_id
        self.players = []
        self.players_in_turn_rotation = []
        self.current_turn_player_index = 0
        self.game_state = "WAITING_FOR_PLAYERS"
        self.required_players = 2
        print(f"GameMatch {self.game_id}: Creada. Estado inicial: {self.game_state}")

    def add_player(self, player):
        if len(self.players) < MAX_PLAYERS_PER_GAME:
            for p in self.players:
                p.send_message(
                    "NEW_PLAYER",
                    {
                        "player_id": player.id,
                        "total_players": len(self.players) + 1,
                        "required_players": self.required_players,
                    },
                )
            self.players.append(player)
            player.send_message(
                "MATCH_JOINED",
                {
                    "game_id": self.game_id,
                    "player_id": player.id,
                    "total_players": len(self.players),
                    "required_players": self.required_players,
                },
            )

            if len(self.players) >= self.required_players:
                self.start_game_setup(player)

            return True, self.game_id
        player.send_message("ERROR", {"message": "La partida está llena."})
        return False, "La partida está llena"

    def start_game_setup(self, extra_player={}):
        self.game_state = "SETUP"
        for player in self.players:
            player.send_message(
                "GAME_STATE",
                {
                    "state": "SETUP",
                    "message": f"Coloca tus barcos ({len(self.players)} jugadores listos)",
                },
            )

    def check_and_start_playing(self):
        required_ships = ["PortaAviones", "Buque", "Submarino", "Crucero", "Lancha"]
        all_players_ready = True

        for p in self.players:
            if not p.ready_for_game:
                all_players_ready = False
                continue

            placed_ship_types = {ship.ship_type for ship in p.ships}
            if not all(ship_type in placed_ship_types for ship_type in required_ships):
                p.ready_for_game = False
                p.send_message(
                    "ERROR",
                    {
                        "message": "Faltan barcos por colocar. Envía todos los barcos requeridos."
                    },
                )
                all_players_ready = False

        if all_players_ready and len(self.players) >= self.required_players:
            self.players_in_turn_rotation = self.players.copy()
            self.game_state = "PLAYING"
            self.current_turn_player_index = 0
            self.start_turn()
            print(
                f"GameMatch {self.game_id}: Todos los jugadores listos. Iniciando juego."
            )

    def send_board_updates(self):
        for player in self.players:
            # Enviar el tablero propio del jugador
            player.send_message("BOARD_UPDATE", {"my_board": player.my_board})

            # Enviar las vistas de todos los oponentes
            opponent_boards = {}
            for opponent in self.players:
                if opponent != player:
                    if opponent.id in player.opponent_views:
                        opponent_boards[opponent.id] = player.opponent_views[
                            opponent.id
                        ]
                    else:
                        # Si no hay vista previa, crear una nueva
                        player.opponent_views[opponent.id] = [
                            ["?" for _ in range(COLUMNAS)] for _ in range(FILAS)
                        ]
                        opponent_boards[opponent.id] = player.opponent_views[
                            opponent.id
                        ]

            player.send_message("BOARD_UPDATE", {"opponent_boards": opponent_boards})

    def start_turn(self):
        current_player = self.players_in_turn_rotation[self.current_turn_player_index]
        self.players_in_turn_rotation[self.current_turn_player_index].turn = True
        self.players[self.current_turn_player_index].turn = True
        # Enviar información de oponentes disponibles
        targets = [
            p.id
            for p in self.players
            if p != current_player and not self.has_all_ships_sunk(p)
        ]

        current_player.send_message(
            "YOUR_TURN",
            {"message": "Es tu turno de atacar", "available_targets": targets},
        )

        # Notificar a otros jugadores
        for p in self.players:
            if p != current_player:
                p.send_message(
                    "OPPONENT_TURN",
                    {
                        "message": f"Turno de {current_player.id}",
                        "current_player": current_player.id,
                    },
                )

    def process_attack(self, acting_player, target_player_id, row, col):
        target_player = next(
            (p for p in self.players if p.id == target_player_id), None
        )
        if not target_player or target_player == acting_player:
            acting_player.send_message(
                "ERROR", {"message": "Jugador objetivo no válido"}
            )
            return False

        # Inicializar vista si no existe
        if target_player_id not in acting_player.opponent_views:
            acting_player.opponent_views[target_player_id] = [
                ["?" for _ in range(COLUMNAS)] for _ in range(FILAS)
            ]

        # Procesar ataque
        result, sunk_ship = target_player.register_hit(row, col)
        coords = f"{chr(65+col)}{row+1}"

        # Actualizar vista del atacante para este oponente específico
        if result in ["HIT", "SUNK"]:
            acting_player.opponent_views[target_player_id][row][col] = "X"
        else:
            acting_player.opponent_views[target_player_id][row][col] = "M"

        # Enviar mensajes
        acting_player.send_message(
            "ATTACK_RESULT",
            {
                "target": target_player_id,
                "coords": coords,
                "result": result,
                "sunk_ship": sunk_ship,
            },
        )

        target_player.send_message(
            "ATTACKED",
            {
                "attacker": acting_player.id,
                "coords": coords,
                "result": result,
                "sunk_ship": sunk_ship,
            },
        )

        self.send_board_updates()

        if self.check_victory():
            return True

        if self.has_all_ships_sunk(target_player):
            target_player.send_message(
                "GAME_OVER",
                {
                    "winner": None,
                    "message": f"Has perdido. Toda tu flota ha sido hundida.",
                },
            )

        if result == "MISS":
            self.next_turn()
        else:
            # Mantener el turno del mismo jugador para otro ataque
            acting_player.send_message(
                "YOUR_TURN",
                {
                    "message": "¡Impacto! Dispara de nuevo",
                    "available_targets": [target_player_id],
                },
            )
            for p in self.players:
                if p != acting_player:
                    p.send_message(
                        "OPPONENT_TURN",
                        {
                            "message": f"{acting_player.id} tuvo un impacto y dispara de nuevo"
                        },
                    )

        return

    def check_victory(self):
        """Verifica si algún jugador ha ganado al hundir todos los barcos del oponente"""
        active_players = [
            p for p in self.players_in_turn_rotation if not self.has_all_ships_sunk(p)
        ]

        if len(active_players) == 1:
            winner = active_players[0]
            self.declare_victory(winner)
            return True
        return False

    def has_all_ships_sunk(self, player):
        """Verifica si todos los barcos de un jugador han sido hundidos"""
        for ship in player.ships:
            if not ship.sunk:
                return False
        return True

    def declare_victory(self, winner):
        """Anuncia la victoria y termina el juego"""
        self.game_state = "GAME_OVER"
        for p in self.players:
            if p == winner:
                p.send_message(
                    "GAME_OVER",
                    {
                        "winner": winner.id,
                        "message": "¡Felicidades, has ganado!",
                        "your_board": p.my_board,
                        "opponent_board": p.opponent_board_view,
                    },
                )
            else:
                p.send_message(
                    "GAME_OVER",
                    {
                        "winner": winner.id,
                        "message": f"{winner.id} ha ganado la partida.",
                        "your_board": p.my_board,
                        "opponent_board": p.opponent_board_view,
                    },
                )

    def process_action(self, player_socket, parsed_data):
        acting_player = next(
            (p for p in self.players if p.socket == player_socket), None
        )

        if not acting_player:
            print(f"GameMatch {self.game_id}: Jugador no encontrado para el socket")
            return

        print(
            f"GameMatch {self.game_id}: Procesando acción {parsed_data.get('type')} de {acting_player.id} en estado {self.game_state}"
        )

        action_type = parsed_data.get("type")
        status_type = parsed_data.get("status")

        if action_type == "PLACE_SHIP":
            if acting_player.ready_for_game:
                acting_player.send_message(
                    "ERROR", {"message": "Ya has configurado tus barcos."}
                )
                return

            ship_type_name = parsed_data.get("ship_type")
            start_coords_str = parsed_data.get("coords")
            orientation = parsed_data.get("orientation")

            col = ord(start_coords_str[0].upper()) - ord("A")
            row = int(start_coords_str[1:]) - 1

            success, message = acting_player.place_ship_on_board(
                ship_type_name, row, col, orientation
            )
            if success:
                acting_player.send_message(
                    "SHIP_PLACED",
                    {
                        "ship_type": ship_type_name,
                        "coords": start_coords_str,
                        "status": "OK",
                        "message": message,
                    },
                )
                acting_player.send_message(
                    "BOARD_UPDATE", {"my_board": acting_player.my_board}
                )
            else:
                acting_player.send_message(
                    "ERROR",
                    {"message": f"Error al colocar {ship_type_name}: {message}"},
                )
            return

        elif action_type == "GAME_STATE" and status_type == "READY":
            if acting_player.ready_for_game:
                acting_player.send_message("ERROR", {"message": "Ya estás listo."})
                return

            acting_player.ready_for_game = True
            acting_player.send_message(
                "STATUS", {"message": "Estás listo! Esperando a que el juego comience."}
            )

            for p in self.players:
                if p != acting_player:
                    p.send_message("PLAYER_READY", {"player_id": acting_player.id})

            self.check_and_start_playing()
            return

        if self.game_state == "PLAYING":
            print("jugando")
            if not acting_player.turn:
                acting_player.send_message("ERROR", {"message": "No es tu turno."})
                print("No es tu turno")
                return

            if action_type == "ATTACK":
                target_player_id = parsed_data.get("target_player")
                target_coords_str = parsed_data.get("coords")
                print(
                    f"Recibiendo ataque de {acting_player.id} HACIA {target_player_id}"
                )
                target_col = ord(target_coords_str[0].upper()) - ord("A")
                target_row = int(target_coords_str[1:]) - 1

                if not target_player_id:
                    acting_player.send_message(
                        "ERROR", {"message": "Debes especificar un objetivo"}
                    )
                    return

                self.process_attack(
                    acting_player, target_player_id, target_row, target_col
                )
                return

    def next_turn(self):
        print("jugador a turno(next_turn): ", self.current_turn_player_index)
        if len(self.players_in_turn_rotation) == 0:
            return
        self.players_in_turn_rotation[self.current_turn_player_index].turn = False
        self.players[self.current_turn_player_index].turn = False
        next_index = (self.current_turn_player_index + 1) % len(
            self.players_in_turn_rotation
        )
        self.current_turn_player_index = next_index
        self.players_in_turn_rotation[self.current_turn_player_index].turn = True
        self.players[self.current_turn_player_index].turn = True
        print(
            f"GameMatch {self.game_id}: Cambiando turno a {self.players_in_turn_rotation[self.current_turn_player_index].id}"
        )
        self.start_turn()

        print("jugador a turno: ", self.current_turn_player_index)
        if self.game_state != "PLAYING" or not self.players_in_turn_rotation:
            return
        current_player = self.players_in_turn_rotation[self.current_turn_player_index]
        if self.has_all_ships_sunk(current_player):
            self.next_turn()
            return

        for p in self.players:
            if p == current_player:
                p.send_message("YOUR_TURN", {"message": "Es tu turno de atacar!"})
            else:
                p.send_message(
                    "OPPONENT_TURN",
                    {"message": f"Es el turno de {current_player.id}."},
                )

    def remove_player_from_match(self, player_socket):
        player_to_remove = next(
            (p for p in self.players if p.socket == player_socket), None
        )
        if player_to_remove:
            self.players.remove(player_to_remove)
            if player_to_remove in self.players_in_turn_rotation:
                self.players_in_turn_rotation.remove(player_to_remove)
                if self.current_turn_player_index >= len(self.players_in_turn_rotation):
                    self.current_turn_player_index = 0

                if (
                    player_to_remove.turn
                    and self.game_state == "PLAYING"
                    and self.players_in_turn_rotation
                ):
                    self.next_turn()

            if self.game_state == "PLAYING" and len(self.players_in_turn_rotation) == 1:
                remaining_player = self.players_in_turn_rotation[0]
                remaining_player.send_message(
                    "GAME_OVER",
                    {
                        "winner": remaining_player.id,
                        "message": "Tu oponente se ha desconectado. ¡Has ganado por abandono!",
                        "your_board": remaining_player.my_board,
                        "opponent_board": remaining_player.opponent_board_view,
                    },
                )
                self.game_state = "GAME_OVER"
            elif len(self.players) == 0:
                self.game_state = "GAME_OVER"

            return True
        return False


class GameThread(threading.Thread):
    def __init__(self, client_socket_queue):
        super().__init__()
        self.client_socket_queue = client_socket_queue
        self.active_players = {}
        self.active_matches = {}
        self.next_player_id = 1
        self.next_game_id = 1
        self.running = True
        print("GameThread: Hilo del juego iniciado.")

    def run(self):
        while self.running:
            self._handle_new_connections()
            self._process_player_inputs()
            self._cleanup_finished_matches_and_players()
            time.sleep(0.01)
        print("GameThread: Hilo del juego terminado.")
        self.cleanup_connections()

    def _handle_new_connections(self):
        while not self.client_socket_queue.empty():
            new_socket, addr = self.client_socket_queue.get()
            new_socket.setblocking(False)

            player_id = f"Player_{self.next_player_id}"
            self.next_player_id += 1
            new_player = Player(player_id, new_socket, addr)
            self.active_players[new_socket] = new_player
            new_player.send_message(
                "WELCOME",
                {"message": f"Bienvenido, {player_id}!", "player_id": player_id},
            )

            assigned_to_match = False
            for match_id, match in self.active_matches.items():
                if (
                    len(match.players) < MAX_PLAYERS_PER_GAME
                    and match.game_state != "GAME_OVER"
                ):
                    result_bool, game_id = match.add_player(new_player)
                    if result_bool:
                        self.active_players[new_socket].Game_id = game_id
                        assigned_to_match = True
                        break

            if not assigned_to_match:
                new_match_id = f"Game_{self.next_game_id}"
                self.next_game_id += 1
                new_match = GameMatch(new_match_id)
                new_match.add_player(new_player)
                self.active_players[new_socket].Game_id = new_match_id
                self.active_matches[new_match_id] = new_match
                new_player.send_message(
                    "MATCH_CREATED",
                    {
                        "game_id": new_match_id,
                        "message": "Has creado una nueva partida. Esperando al oponente...",
                    },
                )

    def _process_player_inputs(self):
        sockets_to_read = [player.socket for player in self.active_players.values()]
        if not sockets_to_read:
            return

        try:
            readable_sockets, _, _ = select.select(sockets_to_read, [], [], 0)
        except Exception as e:
            print(f"GameThread: Error en select: {e}")
            self._cleanup_finished_matches_and_players()
            return

        for sock in readable_sockets:
            player = self.active_players.get(sock)
            if not player:
                continue

            try:
                data = sock.recv(4096).decode("utf-8")
                if not data:
                    print(
                        f"GameThread: Jugador desconectado (recv 0 bytes): {player.id} ({player.address})"
                    )
                    self._remove_player(sock)
                    continue

                player.buffer_recepcion += data
                while "\n" in player.buffer_recepcion:
                    msg_complete, player.buffer_recepcion = (
                        player.buffer_recepcion.split("\n", 1)
                    )
                    if msg_complete.strip():
                        try:
                            parsed_data = json.loads(msg_complete)
                            self._distribute_player_action(sock, parsed_data)
                        except json.JSONDecodeError:
                            print(
                                f"GameThread: JSON inválido de {player.id}: {msg_complete}"
                            )
                            player.send_message(
                                "ERROR",
                                {
                                    "message": "Formato de mensaje inválido (no es JSON válido)."
                                },
                            )
            except BlockingIOError:
                pass
            except ConnectionResetError:
                print(
                    f"GameThread: Jugador desconectado (ConnectionResetError): {player.id} ({player.address})"
                )
                self._remove_player(sock)
            except Exception as e:
                print(
                    f"GameThread: Error inesperado al procesar datos de {player.id}: {e}"
                )
                self._remove_player(sock)

    def _distribute_player_action(self, player_socket, parsed_data):
        acting_player = self.active_players.get(player_socket)
        if not acting_player:
            return

        target_match = None
        for match in self.active_matches.values():
            if acting_player in match.players:
                target_match = match
                break

        if target_match:
            target_match.process_action(player_socket, parsed_data)
        else:
            acting_player.send_message(
                "ERROR", {"message": "No estás en una partida activa."}
            )

    def _remove_player(self, player_socket):
        player_to_remove = self.active_players.pop(player_socket, None)
        if player_to_remove:
            player_socket.close()
            print(f"GameThread: Socket de {player_to_remove.id} cerrado.")
            for match in list(self.active_matches.values()):
                if match.remove_player_from_match(player_socket):
                    pass

    def _cleanup_finished_matches_and_players(self):
        matches_to_remove = []
        for match_id, match in self.active_matches.items():
            if match.game_state == "GAME_OVER" and not match.players:
                matches_to_remove.append(match_id)

        for match_id in matches_to_remove:
            del self.active_matches[match_id]
            print(f"GameThread: Partida {match_id} completamente limpia.")

    def cleanup_connections(self):
        print("GameThread: Limpiando todas las conexiones activas y partidas...")
        for sock in list(self.active_players.keys()):
            player = self.active_players.get(sock)
            if player:
                try:
                    player.send_message(
                        "SERVER_SHUTDOWN",
                        {"message": "El servidor se está apagando. ¡Adiós!"},
                    )
                    sock.close()
                except Exception as e:
                    print(
                        f"GameThread: Error al cerrar socket de {player.id} durante la limpieza: {e}"
                    )
        self.active_players.clear()
        self.active_matches.clear()
        print("GameThread: Limpieza completa.")

    def stop(self):
        print("GameThread: Señalando para detener hilo del juego...")
        self.running = False


def main_server():
    client_socket_queue = queue.Queue()
    acceptor_thread = ConnectionAcceptor("127.0.0.1", 5070, client_socket_queue)
    acceptor_thread.start()
    game_thread = GameThread(client_socket_queue)
    game_thread.start()

    print("Servidor principal iniciado. Presiona Ctrl+C para detener.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nDeteniendo servidor...")
    finally:
        acceptor_thread.stop()
        game_thread.stop()
        acceptor_thread.join()
        game_thread.join()
        print("Todos los hilos del servidor han terminado. Servidor apagado.")


if __name__ == "__main__":
    main_server()
