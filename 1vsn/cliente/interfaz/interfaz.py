# interfaz.py
import pygame
from config import *
from tablero import *  # Assuming dibujar_tablero and obtener_celda are here

COLOR_VERDE = (0, 255, 0)
COLOR_ROJO = (255, 0, 0)
COLOR_AZUL = (0, 0, 255)
COLOR_BLANCO = (255, 255, 255)
COLOR_AMARILLO_RESALTE = (255, 255, 0)


class InterfazBatallaNaval:
    def __init__(self, tablero_jugador, tablero_oponente, lista_barcos):
        pygame.init()
        self.screen = pygame.display.set_mode((ANCHO_VENTANA, ALTO_VENTANA))
        icono = pygame.image.load(ICONO)
        pygame.display.set_icon(icono)
        pygame.display.set_caption("Batalla Naval - Merry-am Blanco - Mariana Mora")
        self.reloj = pygame.time.Clock()
        self.tablero_jugador = tablero_jugador
        self.tablero_oponente = tablero_oponente

        self.tableros_oponentes = {}
        self.tablero_oponente_actual = None

        self.lista_barcos = lista_barcos
        self.turno_actual = False
        self.ultima_celda_disparada = None
        self.ejecutando = True
        self.fondo = pygame.image.load(FONDO_INTERFAZ).convert()
        self.status = "PREPARING"
        self.player_id = ""

        self.target_players = []  # Lista de jugadores disponibles para atacar
        self.selected_target_index = 0

        # Mensaje de estado actual (no se guarda en registro)
        self.mensaje_estado = ""
        # Sistema de registro de mensajes
        self.registro_mensajes = []
        self.max_mensajes_visibles = 3
        self.scroll_offset = 0

        # Variables para colocación de barcos
        self.placement_mode = False
        self.current_ship_to_place_index = 0
        self.current_hover_coords = (0, 0)
        self.current_ship_orientation = "h"
        self.all_ships_placed_visually = False
        # Nuevo: Mensaje de coordenadas durante colocación
        self.coords_message = ""
        self.current_ship_info = ""
        # Nuevo: Mensaje de turno
        self.turn_message = ""

        if isinstance(tablero_oponente, dict):
            self.tableros_oponentes = tablero_oponente
        elif tablero_oponente:  # Si es una matriz (para compatibilidad)
            self.tablero_oponente_actual = tablero_oponente

    def _dibujar_seleccion_oponente(self):
        """Dibuja los botones para seleccionar qué jugador atacar"""
        fuente = pygame.font.Font(FUENTE, 16)
        area_x = OFFSET_X_TABLERO_OPONENTE
        area_y = OFFSET_Y_TABLERO_OPONENTE - 40

        for i, player_id in enumerate(self.target_players):
            color = COLOR_VERDE if i == self.selected_target_index else COLOR_BLANCO
            texto = fuente.render(player_id, True, color)
            rect = pygame.Rect(area_x + i * 120, area_y, 110, 30)
            pygame.draw.rect(self.screen, color, rect, 2)
            self.screen.blit(texto, (area_x + i * 120 + 10, area_y + 5))

    def actualizar_oponentes(self, oponentes):
        """Actualiza la lista de jugadores que pueden ser atacados"""
        self.target_players = oponentes
        self.selected_target_index = 0 if oponentes else -1

        # Asegurarse de que todos los oponentes tienen tablero
        for oponente in oponentes:
            if oponente not in self.tableros_oponentes:
                self.tableros_oponentes[oponente] = [
                    ["?" for _ in range(COLUMNAS)] for _ in range(FILAS)
                ]

        # Actualizar tablero actual
        if self.target_players:
            self.tablero_oponente_actual = self.tableros_oponentes[
                self.target_players[self.selected_target_index]
            ]
        else:
            self.tablero_oponente_actual = None

    def dibujar(self):
        self.screen.blit(self.fondo, (0, 0))

        fuente_id = pygame.font.Font(FUENTE, 16)
        texto_id = fuente_id.render(f"Jugador: {self.player_id}", True, COLOR_BLANCO)
        self.screen.blit(texto_id, (20, 20))

        if len(self.target_players) >= 1 and self.turno_actual:
            self._dibujar_seleccion_oponente()

        if self.status == "PLAYING" and self.tablero_oponente_actual is not None:
            dibujar_tablero(
                self.screen,
                self.tablero_oponente_actual,  # Usar el tablero actual
                OFFSET_X_TABLERO_OPONENTE,
                OFFSET_Y_TABLERO_OPONENTE,
                es_oponente=True,
            )

        dibujar_tablero(
            self.screen,
            self.tablero_jugador,
            OFFSET_X_MI_TABLERO,
            OFFSET_Y_MI_TABLERO,
            es_oponente=False,
        )

        for barco in self.lista_barcos:
            if barco.esta_colocado:
                barco.dibujar(self.screen)

        # Dibujar previsualización del barco durante colocación
        if self.placement_mode and self.current_ship_to_place_index < len(
            self.lista_barcos
        ):
            current_ship = self.lista_barcos[self.current_ship_to_place_index]
            start_row, start_col = self.current_hover_coords

            current_ship.sentido_actual = self.current_ship_orientation
            current_ship._preparar_sprite_activo(ANCHO_CELDA)

            if current_ship.sprite_escalado_activo:
                preview_x = OFFSET_X_MI_TABLERO + start_col * ANCHO_CELDA
                preview_y = OFFSET_Y_MI_TABLERO + start_row * ANCHO_CELDA
                self.screen.blit(
                    current_ship.sprite_escalado_activo, (preview_x, preview_y)
                )

            for i in range(current_ship.tam_casillas):
                r, c = start_row, start_col
                if self.current_ship_orientation == "h":
                    c += i
                else:
                    r += i

                if 0 <= r < FILAS and 0 <= c < COLUMNAS:
                    x = OFFSET_X_MI_TABLERO + c * ANCHO_CELDA
                    y = OFFSET_Y_MI_TABLERO + r * ANCHO_CELDA
                    pygame.draw.rect(
                        self.screen,
                        COLOR_AMARILLO_RESALTE,
                        (x, y, ANCHO_CELDA, ANCHO_CELDA),
                        3,
                    )

        # Dibujar información de colocación (en lugar de usar mensajes)
        if self.placement_mode:
            fuente = pygame.font.Font(FUENTE, 14)

            # Dibujar información del barco actual
            if self.current_ship_info:
                texto_info = fuente.render(self.current_ship_info, True, COLOR_BLANCO)
                self.screen.blit(texto_info, (20, 50))

            # Dibujar coordenadas actuales
            if self.coords_message:
                texto_coords = fuente.render(
                    self.coords_message, True, COLOR_AMARILLO_RESALTE
                )
                self.screen.blit(texto_coords, (20, 70))

            # Dibujar instrucciones
            instrucciones = fuente.render(
                "Clic para colocar - R para rotar", True, COLOR_BLANCO
            )
            self.screen.blit(instrucciones, (20, 90))

        # Dibujar mensaje de estado principal
        if self.mensaje_estado and not self.placement_mode:
            fuente = pygame.font.Font(FUENTE, 10)
            x_text = OFFSET_X_TABLERO_OPONENTE
            y_text = 10
            max_ancho_texto = ANCHO_VENTANA - 80
            interlineado = 2

            lineas = self.dividir_texto(self.mensaje_estado, fuente, max_ancho_texto)

            y_offset = y_text
            for linea in lineas:
                texto_renderizado = fuente.render(linea, True, COLOR_BLANCO)
                self.screen.blit(texto_renderizado, (x_text, y_offset))
                y_offset += fuente.get_height() + interlineado

        # Dibujar mensaje de turno
        if self.turn_message:
            fuente = pygame.font.Font(FUENTE, 14)
            texto_turno = fuente.render(self.turn_message, True, COLOR_BLANCO)
            self.screen.blit(texto_turno, (40, 50))

        self._dibujar_registro_mensajes()
        pygame.display.flip()
        self.reloj.tick(30)

    def dividir_texto(self, texto, fuente, max_ancho):
        palabras = texto.split(" ")
        lineas_finales = []
        linea_actual = ""

        for palabra in palabras:
            if fuente.size(palabra)[0] > max_ancho:
                if linea_actual:
                    lineas_finales.append(linea_actual)
                    linea_actual = ""

                trozo_para_linea_actual = ""
                for caracter in palabra:
                    test_trozo = trozo_para_linea_actual + caracter
                    if fuente.size(test_trozo)[0] <= max_ancho:
                        trozo_para_linea_actual = test_trozo
                    else:
                        if trozo_para_linea_actual:
                            lineas_finales.append(trozo_para_linea_actual)
                        trozo_para_linea_actual = caracter
                        if fuente.size(trozo_para_linea_actual)[0] > max_ancho:
                            lineas_finales.append(trozo_para_linea_actual)
                            trozo_para_linea_actual = ""
                linea_actual = trozo_para_linea_actual
            else:
                if not linea_actual:
                    linea_actual = palabra
                else:
                    test_linea = linea_actual + " " + palabra
                    if fuente.size(test_linea)[0] <= max_ancho:
                        linea_actual = test_linea
                    else:
                        lineas_finales.append(linea_actual)
                        linea_actual = palabra

        if linea_actual:
            lineas_finales.append(linea_actual)

        return lineas_finales

    def cambiar_objetivo(self, incremento):
        """Cambia el objetivo seleccionado y actualiza la vista"""
        if len(self.target_players) > 1:
            self.selected_target_index = (
                self.selected_target_index + incremento
            ) % len(self.target_players)
            self.tablero_oponente_actual = self.tableros_oponentes[
                self.target_players[self.selected_target_index]
            ]
            self.dibujar()

    def manejar_eventos(self, callback_disparo):
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                self.ejecutando = False

            # Manejar scroll del registro de mensajes
            if evento.type == pygame.MOUSEWHEEL:
                if evento.y > 0 and self.scroll_offset > 0:
                    self.scroll_offset -= 1
                elif evento.y < 0 and self.scroll_offset < max(
                    0, len(self.registro_mensajes) - self.max_mensajes_visibles
                ):
                    self.scroll_offset += 1

            # Manejar disparos durante el turno del jugador
            if self.turno_actual and not self.placement_mode:
                if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                    pos = pygame.mouse.get_pos()

                    if (
                        OFFSET_X_TABLERO_OPONENTE
                        <= pos[0]
                        < OFFSET_X_TABLERO_OPONENTE + COLUMNAS * ANCHO_CELDA
                        and OFFSET_Y_TABLERO_OPONENTE
                        <= pos[1]
                        < OFFSET_Y_TABLERO_OPONENTE + FILAS * ANCHO_CELDA
                    ):

                        if not self.target_players:
                            continue

                        fila, col = obtener_celda(
                            pos, OFFSET_X_TABLERO_OPONENTE, OFFSET_Y_TABLERO_OPONENTE
                        )
                        target = self.target_players[self.selected_target_index]

                        # Verificar en el tablero del oponente específico
                        if target in self.tableros_oponentes:
                            if self.tableros_oponentes[target][fila][col] not in (
                                "~",
                                "?",
                            ):
                                self.actualizar_mensaje(
                                    "Ya has disparado aquí", tipo="error"
                                )
                                continue

                        callback_disparo(fila, col, target)
            # Manejar selección de objetivo con clic en el selector
            if self.turno_actual and len(self.target_players) >= 1:
                if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                    mouse_x, mouse_y = evento.pos
                    area_y = OFFSET_Y_TABLERO_OPONENTE - 40
                    if area_y <= mouse_y < area_y + 30:
                        for i in range(len(self.target_players)):
                            if (
                                OFFSET_X_TABLERO_OPONENTE + i * 120
                                <= mouse_x
                                < OFFSET_X_TABLERO_OPONENTE + (i + 1) * 120
                            ):
                                self.selected_target_index = i
                                # Actualizar inmediatamente el tablero que se muestra
                                self.tablero_oponente_actual = self.tableros_oponentes[
                                    self.target_players[i]
                                ]
                                print(
                                    f"Objetivo seleccionado: {self.target_players[i]}"
                                )
                                self.dibujar()  # Forzar redibujado inmediato
                                break
            # Manejar colocación de barcos durante la fase de preparación
            if self.placement_mode:
                if evento.type == pygame.MOUSEMOTION:
                    mouse_x, mouse_y = evento.pos
                    if (
                        OFFSET_X_MI_TABLERO
                        <= mouse_x
                        < OFFSET_X_MI_TABLERO + COLUMNAS * ANCHO_CELDA
                        and OFFSET_Y_MI_TABLERO
                        <= mouse_y
                        < OFFSET_Y_MI_TABLERO + FILAS * ANCHO_CELDA
                    ):

                        col = (mouse_x - OFFSET_X_MI_TABLERO) // ANCHO_CELDA
                        fila = (mouse_y - OFFSET_Y_MI_TABLERO) // ANCHO_CELDA
                        self.current_hover_coords = (fila, col)
                        self.coords_message = f"Posición: {chr(65+col)}{fila+1}"

                        if (
                            not self.current_ship_info
                            and self.current_ship_to_place_index
                            < len(self.lista_barcos)
                        ):
                            ship = self.lista_barcos[self.current_ship_to_place_index]
                            self.current_ship_info = f"Colocando: {ship.nombre_tipo} (Largo: {ship.tam_casillas})"

                elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                    mouse_x, mouse_y = evento.pos
                    if (
                        OFFSET_X_MI_TABLERO
                        <= mouse_x
                        < OFFSET_X_MI_TABLERO + COLUMNAS * ANCHO_CELDA
                        and OFFSET_Y_MI_TABLERO
                        <= mouse_y
                        < OFFSET_Y_MI_TABLERO + FILAS * ANCHO_CELDA
                    ):

                        fila, col = obtener_celda(
                            (mouse_x, mouse_y), OFFSET_X_MI_TABLERO, OFFSET_Y_MI_TABLERO
                        )

                        if self.current_ship_to_place_index < len(self.lista_barcos):
                            current_ship = self.lista_barcos[
                                self.current_ship_to_place_index
                            ]

                            if current_ship.colocar_logicamente_y_preparar_sprite(
                                fila,
                                col,
                                self.current_ship_orientation,
                                self.tablero_jugador,
                                ANCHO_CELDA,
                                OFFSET_X_MI_TABLERO,
                                OFFSET_Y_MI_TABLERO,
                            ):
                                self.agregar_mensaje(
                                    f"Barco {current_ship.nombre_tipo} colocado en {chr(65+col)}{fila+1}",
                                    "info",
                                )
                                self.current_ship_to_place_index += 1
                                self.current_ship_info = ""

                                if self.current_ship_to_place_index < len(
                                    self.lista_barcos
                                ):
                                    next_ship = self.lista_barcos[
                                        self.current_ship_to_place_index
                                    ]
                                    self.current_ship_info = f"Colocando: {next_ship.nombre_tipo} (Largo: {next_ship.tam_casillas})"
                                else:
                                    self.actualizar_mensaje(
                                        "Todos los barcos colocados. Esperando confirmación del servidor."
                                    )
                                    self.status = "READY"
                                    self.placement_mode = False
                                    self.all_ships_placed_visually = True

                elif evento.type == pygame.KEYDOWN:
                    if evento.key == pygame.K_r and self.placement_mode:
                        self.current_ship_orientation = (
                            "v" if self.current_ship_orientation == "h" else "h"
                        )
                        print(
                            f"Orientación cambiada a: {'Vertical' if self.current_ship_orientation == 'v' else 'Horizontal'}"
                        )
                    elif (
                        evento.key == pygame.K_LEFT
                        and self.turno_actual
                        and len(self.target_players) > 1
                    ):
                        self.cambiar_objetivo(-1)  # Cambiar al objetivo anterior
                    elif (
                        evento.key == pygame.K_RIGHT
                        and self.turno_actual
                        and len(self.target_players) > 1
                    ):
                        self.cambiar_objetivo(1)  # Cambiar al siguiente objetivo

                elif evento.type == pygame.KEYDOWN:
                    if evento.key == pygame.K_r:
                        self.current_ship_orientation = (
                            "v" if self.current_ship_orientation == "h" else "h"
                        )
                        print(
                            f"Orientación cambiada a: {'Vertical' if self.current_ship_orientation == 'v' else 'Horizontal'}"
                        )

    def _dibujar_registro_mensajes(self):
        area_ancho = 190
        area_alto = 60
        area_x = ANCHO_VENTANA - area_ancho - 20
        area_y = 10

        s = pygame.Surface((area_ancho, area_alto), pygame.SRCALPHA)
        s.fill((0, 0, 0, 180))
        self.screen.blit(s, (area_x, area_y))

        pygame.draw.rect(
            self.screen, COLOR_BLANCO, (area_x, area_y, area_ancho, area_alto), 2
        )

        fuente_normal = pygame.font.Font(FUENTE, 10)
        interlineado = 2
        margen = 10

        mensajes_a_mostrar = self.registro_mensajes[
            self.scroll_offset : self.scroll_offset + self.max_mensajes_visibles
        ]

        y_pos = area_y + margen
        for msg in mensajes_a_mostrar:
            tipo = msg.get("tipo", "info")
            texto = msg["texto"]

            if tipo == "turno":
                color = COLOR_VERDE
                prefijo = "[TURNO] "
            elif tipo == "ataque":
                color = COLOR_ROJO
                prefijo = "[ATAQUE] "
            elif tipo == "conexion":
                color = COLOR_AZUL
                prefijo = "[CONEXIÓN] "
            else:
                color = COLOR_BLANCO
                prefijo = ""

            lineas = []
            linea_actual = ""
            for palabra in (prefijo + texto).split():
                test_linea = linea_actual + " " + palabra if linea_actual else palabra
                if fuente_normal.size(test_linea)[0] < area_ancho - 2 * margen:
                    linea_actual = test_linea
                else:
                    if linea_actual:
                        lineas.append(linea_actual)
                    linea_actual = palabra
            if linea_actual:
                lineas.append(linea_actual)

            for linea in lineas:
                texto_render = fuente_normal.render(linea, True, color)
                self.screen.blit(texto_render, (area_x + margen, y_pos))
                y_pos += fuente_normal.get_height() + interlineado

                if y_pos > area_y + area_alto - margen:
                    break

    def agregar_mensaje(self, texto, tipo="info"):
        self.registro_mensajes.insert(0, {"texto": texto, "tipo": tipo})
        if len(self.registro_mensajes) > 50:
            self.registro_mensajes = self.registro_mensajes[:50]

    def actualizar_mensaje(self, mensaje, tipo="info"):
        self.agregar_mensaje(mensaje, tipo)

    def actualizar_mensaje_turnos(self, mensaje):
        self.turn_message = mensaje  # Actualizar el mensaje de turno

    def actualizar_mensaje_conexiones(self, mensaje):
        self.agregar_mensaje(mensaje, "conexion")

    def cerrar(self):
        pygame.quit()

    def set_turno(self, es_turno):
        self.turno_actual = es_turno
        self.turn_message = "Es tu turno" if es_turno else "Es el turno del oponente"

    def get_disparo(self):
        return self.ultima_celda_disparada

    def resetear_disparo(self):
        self.ultima_celda_disparada = None

    def colocar_barcos_manual(self):
        self.placement_mode = True
        self.current_ship_to_place_index = 0
        self.current_ship_orientation = "h"
        self.all_ships_placed_visually = False
        self.current_ship_info = ""
        self.coords_message = ""

        if self.lista_barcos:
            first_ship = self.lista_barcos[0]
            self.current_ship_info = f"Colocando: {first_ship.nombre_tipo} (Largo: {first_ship.tam_casillas})"
