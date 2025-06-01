# Batalla Naval - Juego Multijugador  
**Proyecto de Sistemas Distribuidos**

## Descripción

Este proyecto es una implementación juego **Batalla Naval**, desarrollado en Python usando **sockets TCP**. El objetivo es crear una experiencia multijugador 1v1 en red, aplicando conceptos de **sistemas distribuidos** y comunicación entre procesos.

---

##  Objetivos del Proyecto

-  Crear un juego multijugador 1 contra 1.
-  Implementar la comunicación cliente-servidor con sockets.
-  Preparar la arquitectura para sesiones concurrentes con múltiples jugadores.
- Aplicar principios de redes y sistemas distribuidos.

---

## Fases del Desarrollo

### Paso 1: Juego 1v1 con Sockets
- Conexión entre dos clientes mediante un servidor.
- Intercambio de jugadas en tiempo real.
- Interfaz gráfica.

### Paso 2: Soporte para Múltiples Partidas 
- Extender el servidor para manejar varias sesiones.
- Gestión separada por pares de jugadores.
- Utilizar servidor multihilo

---

### ¿Cómo probar el programa?

1. Abre tu terminal.
2. Elige el modo de juego que deseas probar: `1vs1` o `1vsn`.
3. Sigue los siguientes pasos según el modo seleccionado (puedes reemplazar `1vs1` por `1vsn` en los comandos si es el caso):

#### Terminal 1 (Servidor):
  - cd 1vs1/servidor
  - python server.py

#### Terminal 2 (Cliente):
  - cd 1vs1/cliente
  - python client.py

####  Terminal 3 (Cliente 2):
Repite los pasos de la Terminal 2:
  - cd 1vs1/cliente
  - python client.py

  
## Tecnologías Utilizadas

- **Python 3**
- **Sockets TCP/IP**

