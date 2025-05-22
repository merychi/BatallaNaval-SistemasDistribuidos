ANCHO_CELDA = 30             # Tamaño de cada celda del tablero
FILAS = COLUMNAS = 10        # Número de filas y columnas del tablero

ANCHO_VENTANA = COLUMNAS * ANCHO_CELDA + 200  # Ancho ventana con margen extra
ALTO_VENTANA = FILAS * ANCHO_CELDA * 2.5 + 1  # Alto ventana para dos tableros y espacio adicional

COLOR_AGUA = (56, 80, 187)       # Color del agua en el tablero
COLOR_IMPACTO = (255, 0, 0)      # Color para impactos (disparos acertados)
COLOR_AGUA_FALLO = (200, 200, 200) # Color para agua donde no hubo impacto

# Posiciones relativas para dibujar los tableros
OFFSET_X_MI_TABLERO = 50         
OFFSET_Y_MI_TABLERO = FILAS * ANCHO_CELDA + 100

OFFSET_X_TABLERO_OPONENTE = 50
OFFSET_Y_TABLERO_OPONENTE = 80
OFFSET_JUGADOR_Y = FILAS * ANCHO_CELDA

# Colores usados en el menú y textos
COLOR_BLANCO = (255, 255, 255)
COLOR_NEGRO = (0, 0, 0)
COLOR_GRIS_CLARO = (200, 200, 200)
COLOR_GRIS_OSCURO = (100, 100, 100)
COLOR_AZUL_MARINO = (0, 0, 128)
COLOR_CIAN_CLARO = (173, 216, 230)
COLOR_MORADO = (34, 32, 110)

# Fuentes usadas en la interfaz
FUENTE = "fonts/Pacifico-Regular.ttf"
FUENTE2 = "fonts/Poppins-Italic.ttf"
ICONO = "sprites/icono.png"
