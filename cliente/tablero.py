from config import *
import pygame
import sys

# Inicializar tableros con agua ("~") para jugador y oponente
tablero_jugador = [["~" for _ in range(COLUMNAS)] for _ in range(FILAS)]
tablero_oponente = [["~" for _ in range(COLUMNAS)] for _ in range(FILAS)]

def dibujar_tablero(screen, tablero, offset_x, offset_y, es_oponente=False):
    # Dibuja el tablero en pantalla con un desplazamiento (offset) dado
    for fila_idx, fila_val in enumerate(tablero):
        for col_idx, celda_val in enumerate(fila_val):
            # Define el rectángulo de la celda en pantalla
            rect = pygame.Rect(
                offset_x + col_idx * ANCHO_CELDA, 
                offset_y + fila_idx * ANCHO_CELDA, 
                ANCHO_CELDA, ANCHO_CELDA
            )
            pygame.draw.rect(screen, COLOR_GRIS_CLARO, rect, 1)  # Dibuja borde de la celda
            
            # Color por defecto: agua
            color_celda = COLOR_AGUA 
            
            # Cambia color según el contenido de la celda y si es tablero propio o enemigo
            if celda_val == "B" and not es_oponente: 
                color_celda = COLOR_AGUA 
            elif celda_val == "X":  # Impacto 
                color_celda = COLOR_IMPACTO  # Rojo
            elif celda_val == "M":  # Agua 
                color_celda = COLOR_GRIS_CLARO  # Gris claro
            
            # Dibuja el interior de la celda con un margen para el borde
            pygame.draw.rect(screen, color_celda, rect.inflate(-2, -2))

def obtener_celda(pos, offset_x, offset_y):
    # Obtiene la fila y columna en el tablero según la posición del mouse y offsets
    x, y = pos
    # Verifica si la posición está dentro del área del tablero
    if offset_x <= x < offset_x + COLUMNAS * ANCHO_CELDA and \
       offset_y <= y < offset_y + FILAS * ANCHO_CELDA:
        col = (x - offset_x) // ANCHO_CELDA
        fila = (y - offset_y) // ANCHO_CELDA
        return fila, col  # Devuelve índice de fila y columna
    return None  # Fuera del tablero
