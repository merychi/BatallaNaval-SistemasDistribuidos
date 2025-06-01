# barcos.py
import pygame
from config import *

class Barco:
    def __init__(self, nombre_tipo, tam_casillas, sprite_path_h=None, sprite_path_v=None):
        self.nombre_tipo = nombre_tipo                    # Nombre del barco
        self.tam_casillas = tam_casillas                  # Tamaño en casillas
        self.posiciones_en_tablero = []                    # Posiciones ocupadas en el tablero
        self.segmentos_tocados = [False] * tam_casillas   # Estado de impacto por segmento
        self.sentido_actual = "h"                          # Orientación: horizontal por defecto
        self.esta_colocado = False                         # Indica si está colocado en el tablero

        self.sprite_original_h = None                       # Sprite original horizontal
        self.sprite_original_v = None                       # Sprite original vertical
        self.sprite_escalado_activo = None                  # Sprite escalado para renderizado
        self.posicion_renderizado_sprite = (0, 0)           # Posición de renderizado en píxeles

        # Carga sprite horizontal si existe
        if sprite_path_h:
            try:
                self.sprite_original_h = pygame.image.load(sprite_path_h).convert_alpha()
            except pygame.error as e:
                print(f"Error al cargar sprite horizontal '{sprite_path_h}' para {self.nombre_tipo}: {e}")
                self.sprite_original_h = None

        # Carga sprite vertical si existe, o genera rotado del horizontal
        if sprite_path_v:
            try:
                self.sprite_original_v = pygame.image.load(sprite_path_v).convert_alpha()
            except pygame.error as e:
                print(f"Error al cargar sprite vertical '{sprite_path_v}' para {self.nombre_tipo}: {e}")
                self.sprite_original_v = None
        elif self.sprite_original_h:
            try:
                self.sprite_original_v = pygame.transform.rotate(self.sprite_original_h, 90)
            except pygame.error as e:
                print(f"Error al rotar sprite horizontal para {self.nombre_tipo}: {e}")
                self.sprite_original_v = None
        else:
            self.sprite_original_v = None

    def _preparar_sprite_activo(self, ancho_celda_px):
        self.sprite_escalado_activo = None

        if self.sentido_actual == "h" and self.sprite_original_h:
            try:
                nuevo_ancho = self.tam_casillas * ancho_celda_px
                nuevo_alto = ancho_celda_px
                self.sprite_escalado_activo = pygame.transform.scale(self.sprite_original_h, (int(nuevo_ancho), int(nuevo_alto)))
            except pygame.error as e:
                print(f"Error al escalar sprite horizontal para {self.nombre_tipo}: {e}")

        elif self.sentido_actual == "v" and self.sprite_original_v:
            try:
                nuevo_ancho = ancho_celda_px
                nuevo_alto = self.tam_casillas * ancho_celda_px
                self.sprite_escalado_activo = pygame.transform.scale(self.sprite_original_v, (int(nuevo_ancho), int(nuevo_alto)))
            except pygame.error as e:
                print(f"Error al escalar sprite vertical para {self.nombre_tipo}: {e}")

    def colocar_logicamente_y_preparar_sprite(self, fila_inicio, col_inicio, sentido,
                                             tablero_logico_matriz,
                                             ancho_celda_px,
                                             offset_x_tablero_px, offset_y_tablero_px):
        self.sentido_actual = sentido                      # Definir orientación
        propuestas_posiciones = []

        # Calcular posiciones ocupadas
        for i in range(self.tam_casillas):
            if self.sentido_actual == "h":
                r_actual, c_actual = fila_inicio, col_inicio + i
            else:
                r_actual, c_actual = fila_inicio + i, col_inicio

            # Validar límites del tablero
            if not (0 <= r_actual < FILAS and 0 <= c_actual < COLUMNAS):
                print(f"Error: '{self.nombre_tipo}' fuera de límites en ({r_actual},{c_actual})")
                self.esta_colocado = False
                return False

            # Validar superposición con otro barco
            if tablero_logico_matriz[r_actual][c_actual] == "B":
                print(f"Error: Superposición de '{self.nombre_tipo}' en ({r_actual},{c_actual})")
                self.esta_colocado = False
                return False

            propuestas_posiciones.append((r_actual, c_actual))

        # Confirmar posiciones y actualizar matriz
        self.posiciones_en_tablero = propuestas_posiciones
        for r, c in self.posiciones_en_tablero:
            tablero_logico_matriz[r][c] = "B"

        self.esta_colocado = True

        # Preparar sprite para renderizado
        self._preparar_sprite_activo(ancho_celda_px)
        if self.sprite_escalado_activo:
            self.posicion_renderizado_sprite = (offset_x_tablero_px + col_inicio * ancho_celda_px,
                                                offset_y_tablero_px + fila_inicio * ancho_celda_px)
        else:
            if (self.sentido_actual == "h" and self.sprite_original_h) or \
               (self.sentido_actual == "v" and self.sprite_original_v):
                print(f"Advertencia: Falló escalado del sprite de '{self.nombre_tipo}'")

        return True

    def dibujar(self, screen):
        if self.esta_colocado and self.sprite_escalado_activo:
            screen.blit(self.sprite_escalado_activo, self.posicion_renderizado_sprite)

    def registrar_impacto(self, fila_impacto, col_impacto):
        if not self.esta_colocado:
            return False

        pos_impacto = (fila_impacto, col_impacto)
        if pos_impacto in self.posiciones_en_tablero:
            idx = self.posiciones_en_tablero.index(pos_impacto)
            if not self.segmentos_tocados[idx]:
                self.segmentos_tocados[idx] = True
                print(f"Barco '{self.nombre_tipo}' impactado en segmento {idx} en {pos_impacto}")
            return True
        return False

    def esta_hundido(self):
        return self.esta_colocado and all(self.segmentos_tocados)

# Clases específicas para cada tipo de barco
class PortaAviones(Barco):
    def __init__(self):
        super().__init__("PortaAviones", 5, sprite_path_h="sprites/portaaviones.png")

class Buque(Barco):
    def __init__(self):
        super().__init__("Buque", 4, sprite_path_h="sprites/buque.png")

class Submarino(Barco):
    def __init__(self):
        super().__init__("Submarino", 3, sprite_path_h="sprites/submarino.png")

class Crucero(Barco):
    def __init__(self):
        super().__init__("Crucero", 3, sprite_path_h="sprites/crucero.png")

class Lancha(Barco):
    def __init__(self):
        super().__init__("Lancha", 2, sprite_path_h="sprites/lancha.png")
