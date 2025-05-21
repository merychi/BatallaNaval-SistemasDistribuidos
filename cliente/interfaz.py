# interfaz.py
import pygame
from config import *
from tablero import *

class InterfazBatallaNaval:
    def __init__(self, tablero_jugador, tablero_oponente, lista_barcos):
        pygame.init()
        self.screen = pygame.display.set_mode((ANCHO_VENTANA, ALTO_VENTANA))  # Crear ventana
        pygame.display.set_caption("Batalla Naval - Merry-am Blanco - Mariana Mora")
        self.reloj = pygame.time.Clock()
        self.tablero_jugador = tablero_jugador
        self.tablero_oponente = tablero_oponente
        self.lista_barcos = lista_barcos
        self.turno_actual = False
        self.ultima_celda_disparada = None
        self.mensaje_estado = "Esperando..."
        self.ejecutando = True
        self.fondo = pygame.image.load("cliente/sprites/BatallaNavalTableroFondo.png").convert()  # Fondo

    def dibujar(self):
        self.screen.blit(self.fondo, (0, 0))  # Dibujar fondo
        # Dibujar tableros oponente y jugador con offset y flag para ocultar barcos enemigos
        dibujar_tablero(self.screen, self.tablero_oponente, OFFSET_X_TABLERO_OPONENTE, OFFSET_Y_TABLERO_OPONENTE, es_oponente=True)
        dibujar_tablero(self.screen, self.tablero_jugador, OFFSET_X_MI_TABLERO, OFFSET_Y_MI_TABLERO, es_oponente=False)

        for barco in self.lista_barcos:
            barco.dibujar(self.screen)  # Dibujar barcos en pantalla

        # Configurar fuente para texto
        fuente = pygame.font.Font(FUENTE, 36)

        # Parámetros para texto con salto de línea automático
        x_text = OFFSET_X_TABLERO_OPONENTE
        y_text = 10
        max_ancho_texto = ANCHO_VENTANA - 80  # Margen horizontal
        interlineado = 2

        # Dividir mensaje en líneas que caben en pantalla
        lineas = self.dividir_texto(self.mensaje_estado, fuente, max_ancho_texto)

        y_offset = y_text
        for linea in lineas:
            texto_renderizado = fuente.render(linea, True, COLOR_BLANCO)
            self.screen.blit(texto_renderizado, (x_text, y_offset))
            y_offset += fuente.get_height() + interlineado

        pygame.display.flip()  # Actualizar pantalla
        self.reloj.tick(30)    # Limitar FPS

    def dividir_texto(self, texto, fuente, max_ancho):
        # Divide texto en líneas para que no excedan el ancho máximo
        palabras = texto.split(' ')
        lineas_finales = []
        linea_actual = ""

        for palabra in palabras:
            ancho_palabra_sola = fuente.size(palabra)[0]

            if ancho_palabra_sola > max_ancho:
                # Si palabra es muy larga, dividir por caracteres
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
                # Añadir palabra a línea actual si cabe, sino crear línea nueva
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

    def manejar_eventos(self, callback_disparo):
        # Maneja eventos pygame como cerrar ventana y disparos en el tablero oponente
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                self.ejecutando = False
            elif evento.type == pygame.MOUSEBUTTONDOWN and self.turno_actual:
                pos = pygame.mouse.get_pos()
                # Verificar si clic está dentro del tablero oponente
                if OFFSET_X_TABLERO_OPONENTE <= pos[0] < OFFSET_X_TABLERO_OPONENTE + COLUMNAS * ANCHO_CELDA and \
                   OFFSET_Y_TABLERO_OPONENTE <= pos[1] < OFFSET_Y_TABLERO_OPONENTE + FILAS * ANCHO_CELDA:
                    fila, col = obtener_celda(pos, OFFSET_X_TABLERO_OPONENTE, OFFSET_Y_TABLERO_OPONENTE)
                    if self.tablero_oponente[fila][col] == "~":  # Solo disparar a agua
                        self.ultima_celda_disparada = (fila, col)
                        callback_disparo(fila, col)

    def cerrar(self):
        pygame.quit()  # Cerrar pygame

    def actualizar_mensaje(self, mensaje):
        self.mensaje_estado = mensaje  # Actualiza texto mostrado

    def set_turno(self, es_turno):
        self.turno_actual = es_turno  # Cambia turno

    def get_disparo(self):
        return self.ultima_celda_disparada  # Retorna última celda disparada

    def resetear_disparo(self):
        self.ultima_celda_disparada = None  # Limpia disparo previo

    def colocar_barcos_manual(self):
        idx_barco = 0
        sentido = "h"  # Sentido inicial horizontal

        while idx_barco < len(self.lista_barcos):
            barco = self.lista_barcos[idx_barco]
            self.screen.blit(self.fondo, (0, 0))  # Fondo
            dibujar_tablero(self.screen, self.tablero_jugador, OFFSET_X_MI_TABLERO, OFFSET_Y_MI_TABLERO)  # Dibujar tablero propio

            # Dibujar barcos ya colocados
            for b in self.lista_barcos:
                if b.esta_colocado:
                    b.dibujar(self.screen)

            # Obtener celda bajo el mouse
            mouse_x, mouse_y = pygame.mouse.get_pos()
            pos_celda = obtener_celda((mouse_x, mouse_y), OFFSET_X_MI_TABLERO, OFFSET_Y_MI_TABLERO)
            if pos_celda is None:
                # Manejar eventos sin intentar dibujar fuera del tablero
                pygame.display.flip()
                for evento in pygame.event.get():
                    if evento.type == pygame.QUIT:
                        self.ejecutando = False
                        return
                    elif evento.type == pygame.KEYDOWN:
                        if evento.key == pygame.K_r:
                            sentido = "v" if sentido == "h" else "h"  # Rotar barco
                    elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                        pass  # Clic fuera del tablero, ignorar
                continue

            fila, col = pos_celda

            # Mostrar previsualización del barco actual en el tablero
            if 0 <= fila < FILAS and 0 <= col < COLUMNAS:
                barco.sentido_actual = sentido
                barco._preparar_sprite_activo(ANCHO_CELDA)
                if barco.sprite_escalado_activo:
                    pos_x = OFFSET_X_MI_TABLERO + col * ANCHO_CELDA
                    pos_y = OFFSET_Y_MI_TABLERO + fila * ANCHO_CELDA
                    self.screen.blit(barco.sprite_escalado_activo, (pos_x, pos_y))

            # Mostrar texto de instrucciones
            fuente = pygame.font.Font(FUENTE, 28)
            texto = fuente.render(f"Coloca el barco: {barco.nombre_tipo} (R para rotar)", True, COLOR_BLANCO)
            self.screen.blit(texto, (OFFSET_X_MI_TABLERO, 10))
            pygame.display.flip()

            # Manejar eventos para colocar barco o rotar
            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    self.ejecutando = False
                    return
                elif evento.type == pygame.KEYDOWN:
                    if evento.key == pygame.K_r:
                        sentido = "v" if sentido == "h" else "h"  # Cambiar orientación
                elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:  # Clic izquierdo
                    # Intentar colocar barco lógicamente y actualizar sprite
                    if barco.colocar_logicamente_y_preparar_sprite(
                        fila, col, sentido,
                        self.tablero_jugador,
                        ANCHO_CELDA,
                        OFFSET_X_MI_TABLERO, OFFSET_Y_MI_TABLERO
                    ):
                        idx_barco += 1  # Pasar al siguiente barco
