import pygame
import sys
import os
from config import *

pygame.font.init()
class Boton:
    def __init__(self, x, y, ancho, alto, texto, color_normal, color_hover, fuente, callback_accion):
        # Define el rectángulo del botón y sus propiedades visuales y funcionales
        self.rect = pygame.Rect(x, y, ancho, alto)
        self.texto = texto
        self.color_normal = color_normal
        self.color_hover = color_hover
        self.color_actual = color_normal
        self.fuente = fuente
        self.callback_accion = callback_accion
        self.texto_renderizado = self.fuente.render(self.texto, True, COLOR_GRIS_CLARO)
        self.rect_texto = self.texto_renderizado.get_rect(center=self.rect.center)

    def dibujar(self, screen):
        # Dibuja el botón con su color actual y el borde morado, y renderiza el texto centrado
        pygame.draw.rect(screen, self.color_actual, self.rect, border_radius=10)
        pygame.draw.rect(screen, COLOR_MORADO, self.rect, 2, border_radius=10) 
        screen.blit(self.texto_renderizado, self.rect_texto)

    def manejar_evento(self, evento):
        # Cambia color cuando el mouse está encima y ejecuta acción al hacer click izquierdo
        if evento.type == pygame.MOUSEMOTION:
            if self.rect.collidepoint(evento.pos):
                self.color_actual = self.color_hover
            else:
                self.color_actual = self.color_normal
        elif evento.type == pygame.MOUSEBUTTONDOWN:
            if evento.button == 1 and self.rect.collidepoint(evento.pos):
                if self.callback_accion:
                    self.callback_accion()  # Ejecuta la función asociada al botón

def dividir_texto(texto, fuente, max_ancho):
    # Divide un texto en líneas para que quepan dentro de un ancho máximo
    palabras = texto.split(' ')
    lineas = []
    linea_actual = ""

    for palabra in palabras:
        test_linea = linea_actual + palabra + " "
        if fuente.size(test_linea)[0] <= max_ancho:
            linea_actual = test_linea
        else:
            lineas.append(linea_actual)
            linea_actual = palabra + " "
    if linea_actual:
        lineas.append(linea_actual)
    return lineas

def mostrar_como_jugar(screen, reloj, fuente_titulo, fuente_texto):
    # Muestra la pantalla con las instrucciones de cómo jugar
    ejecutando_como_jugar = True

    textos_instrucciones = [
        "Cómo Jugar Batalla Naval:",
        "",
        "1. El objetivo es hundir todos los barcos del oponente.",
        "2. Coloca tus barcos estrategicamente en el tablero",
        "3. En tu turno, haz clic en una casilla del tablero",
        "   enemigo para disparar.",
        "4. 'X' significa impacto, 'M' significa agua.",
        "5. Gana quien hunda todos los barcos del rival.",
        "",
    ]

    fuente_instrucciones = pygame.font.Font(FUENTE2, 20)

    # Intenta cargar la imagen de fondo; si falla usa un fondo sólido
    try:
        imagen_fondo = pygame.image.load("cliente/sprites/BatallaNavalFondo.png")
        imagen_fondo = pygame.transform.scale(imagen_fondo, (ANCHO_VENTANA, ALTO_VENTANA))
    except Exception as e:
        print("No se pudo cargar el fondo:", e)
        imagen_fondo = None

    # Botón para volver al menú principal
    btn_volver = Boton(
        ANCHO_VENTANA // 2 - 100, ALTO_VENTANA - 60, 200, 40, "Volver",
        COLOR_NEGRO, COLOR_GRIS_CLARO, fuente_texto,
        lambda: setattr(sys.modules[__name__], 'accion_menu_actual', "volver_menu")
    )
    setattr(sys.modules[__name__], 'accion_menu_actual', None)

    while ejecutando_como_jugar:
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            btn_volver.manejar_evento(evento)  # Maneja eventos del botón Volver
            if getattr(sys.modules[__name__], 'accion_menu_actual') == "volver_menu":
                ejecutando_como_jugar = False  # Sale del loop para volver al menú

        # Dibuja fondo o color sólido
        if imagen_fondo:
            screen.blit(imagen_fondo, (0, 0))
        else:
            screen.fill(COLOR_CIAN_CLARO)

        # Dibuja título
        titulo_font = pygame.font.Font(FUENTE, 40)
        titulo_surf = titulo_font.render("Instrucciones", True, COLOR_BLANCO)
        titulo_rect = titulo_surf.get_rect(center=(ANCHO_VENTANA // 2, 40))
        screen.blit(titulo_surf, titulo_rect)

        # Dibuja texto con ajuste de línea y margen izquierdo
        x_text = 40
        y_text = 90
        max_ancho_texto = ANCHO_VENTANA - 80  # Margen total horizontal
        interlineado = 6  # Espacio entre líneas

        for linea in textos_instrucciones:
            lineas_partidas = dividir_texto(linea, fuente_instrucciones, max_ancho_texto)
            for sublinea in lineas_partidas:
                texto_surf = fuente_instrucciones.render(sublinea.strip(), True, COLOR_GRIS_CLARO)
                screen.blit(texto_surf, (x_text, y_text))
                y_text += fuente_instrucciones.get_linesize() + interlineado

        btn_volver.dibujar(screen)  # Dibuja el botón Volver

        pygame.display.flip()
        reloj.tick(30)

# Variable global para controlar acción seleccionada en menú
accion_menu_actual = None

# Funciones que modifican la variable global según acción del menú
def accion_jugar():
    global accion_menu_actual
    accion_menu_actual = "jugar"

def accion_como_jugar_desde_menu():
    global accion_menu_actual
    accion_menu_actual = "como_jugar"

def accion_salir():
    global accion_menu_actual
    accion_menu_actual = "salir"

def bucle_menu_principal():
    # Inicializa Pygame, ventana y fuentes; muestra menú principal con botones
    global accion_menu_actual
    pygame.init()
    screen = pygame.display.set_mode((ANCHO_VENTANA, ALTO_VENTANA))
    pygame.display.set_caption("Batalla Naval - Merry-am Blanco - Mariana Mora")
    reloj = pygame.time.Clock()
    
    tipo_titulo = FUENTE
    tipo_menu = FUENTE2
    tam_titulo = 100
    tam_texto = 30
    imagen_fondo = None 

    # Intenta cargar imagen de fondo y escalarla
    try: 
        imagen_cargada_desde_archivo = pygame.image.load("cliente/sprites/BatallaNavalFondo.png") 
        imagen_fondo = pygame.transform.scale(imagen_cargada_desde_archivo, (ANCHO_VENTANA, ALTO_VENTANA))
        print("Imagen de fondo cargada y escalada exitosamente.")
    except pygame.error as e:
        print(f"Error al cargar o escalar la imagen de fondo: {e}")
    except FileNotFoundError:
        print(f"Archivo de imagen no encontrado en: {'cliente/sprites/BatallaNavalFondo.png'}")

    # Carga la fuente para título, usa fuente por defecto si falla
    try:
        fuente_titulo_personalizada = pygame.font.Font(tipo_titulo, tam_titulo)
    except pygame.error as e:
        print(f"Error al cargar la fuente personalizada para el título: {e}")
        print("Usando fuente por defecto para el título.")
        fuente_titulo_personalizada = pygame.font.Font(tipo_titulo, tam_titulo)

    fuente_botones_menu = pygame.font.Font(tipo_menu , 30)

    # Renderiza el título dividido en dos palabras
    titulo_batalla_surf = fuente_titulo_personalizada.render("Batalla", True, COLOR_BLANCO)
    titulo_naval_surf = fuente_titulo_personalizada.render("Naval", True, COLOR_BLANCO)

    # Posiciona los títulos centrados verticalmente uno debajo del otro
    titulo_batalla_rect = titulo_batalla_surf.get_rect(center=(ANCHO_VENTANA // 2, ALTO_VENTANA // 4))
    titulo_naval_rect = titulo_naval_surf.get_rect(center=(ANCHO_VENTANA // 2, titulo_batalla_rect.bottom + 10))

    # Configura dimensiones y posiciones para botones del menú
    ancho_boton = 250
    alto_boton = 60
    espacio_botones = 20
    x_botones = ANCHO_VENTANA // 2 - ancho_boton // 2
    y_inicial_botones = (ALTO_VENTANA // 2 - (alto_boton * 1.5 + espacio_botones)) + 150

    # Crea los botones con sus acciones asociadas
    botones = [
        Boton(x_botones, y_inicial_botones, ancho_boton, alto_boton, "Jugar",
              COLOR_NEGRO, COLOR_GRIS_OSCURO, fuente_botones_menu, accion_jugar),
        Boton(x_botones, y_inicial_botones + alto_boton + espacio_botones, ancho_boton, alto_boton, "Cómo Jugar",
              COLOR_NEGRO, COLOR_GRIS_OSCURO, fuente_botones_menu, accion_como_jugar_desde_menu),
        Boton(x_botones, y_inicial_botones + 2 * (alto_boton + espacio_botones), ancho_boton, alto_boton, "Salir",
              COLOR_NEGRO, COLOR_GRIS_OSCURO, fuente_botones_menu, accion_salir)
    ]

    ejecutando_menu = True
    while ejecutando_menu:
        accion_menu_actual = None  # Resetea acción cada ciclo
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                accion_salir()  # Marca salir si cierra ventana

            # Procesa eventos para cada botón
            for boton in botones:
                boton.manejar_evento(evento)
            
            if accion_menu_actual:
                ejecutando_menu = False  # Sale del loop si se selecciona acción

        # Dibuja fondo o color sólido
        if imagen_fondo is not None:
            screen.blit(imagen_fondo, (0, 0))
        else:
            screen.fill(COLOR_CIAN_CLARO)

        # Dibuja títulos
        screen.blit(titulo_batalla_surf, titulo_batalla_rect)
        screen.blit(titulo_naval_surf, titulo_naval_rect)

        # Dibuja los botones
        for boton in botones:
            boton.dibujar(screen)

        pygame.display.flip()  # Actualiza la pantalla
        reloj.tick(30)  # Limita a 30 FPS

        # Lógica para mostrar pantalla de "Cómo jugar" o salir del menú
        if accion_menu_actual == "como_jugar":
            mostrar_como_jugar(screen, reloj, fuente_titulo_personalizada, fuente_botones_menu)
            ejecutando_menu = True
            accion_menu_actual = None
        elif accion_menu_actual:
            break
            
    return accion_menu_actual
