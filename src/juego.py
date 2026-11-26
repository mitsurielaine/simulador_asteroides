"""
juego.py
--------
Capa exterior (imperativa) del simulador: lee el teclado, llama a la
funcion pura `actualizar(estado, eventos, dt, pool)` y dibuja con Pygame.
Todo el calculo del juego esta en estado.py / motor_paralelo.py.

Controles:
    Flechas    -> mover la nave
    P          -> alternar modo secuencial / paralelo
    1 / 3 / 5  -> reiniciar con 1000 / 3000 / 5000 asteroides
    ESC        -> salir
"""

from __future__ import annotations

import sys

import pygame

from estado import EstadoJuego, Eventos, crear_estado_inicial, SECUENCIAL, RADIO_NAVE
from motor_paralelo import actualizar, crear_pool, info_sistema
from metricas import crear_fuentes, dibujar_metricas

ANCHO, ALTO = 1100, 700
TITULO   = "Nave vs Asteroides - Paralelismo Funcional"
FPS_TOPE = 60
VEL_NAVE = 5.0
CANTIDAD_INICIAL = 1000

C_FONDO       = (10, 12, 24)
C_ASTEROIDE   = (170, 170, 185)
C_ASTEROIDE_B = (90, 92, 110)
C_NAVE        = (250, 200, 35)
C_NAVE_HIT    = (235, 90, 90)

TECLAS_CANTIDAD = {pygame.K_1: 1000, pygame.K_3: 3000, pygame.K_5: 5000}


def leer_entrada() -> tuple:
    """Convierte los eventos de Pygame en un `Eventos` inmutable. Devuelve (Eventos, salir)."""
    crudos = tuple(pygame.event.get())
    pulsadas = tuple(e.key for e in crudos if e.type == pygame.KEYDOWN)
    salir = any(e.type == pygame.QUIT for e in crudos) or pygame.K_ESCAPE in pulsadas
    teclas = pygame.key.get_pressed()
    eventos = Eventos(
        dx=(teclas[pygame.K_RIGHT] - teclas[pygame.K_LEFT]) * VEL_NAVE,
        dy=(teclas[pygame.K_DOWN] - teclas[pygame.K_UP]) * VEL_NAVE,
        alternar_modo=pygame.K_p in pulsadas,
        reiniciar_con=next((TECLAS_CANTIDAD[k] for k in pulsadas if k in TECLAS_CANTIDAD), 0),
    )
    return eventos, salir


def dibujar_asteroides(pantalla, estado: EstadoJuego) -> None:
    def circulo(a):
        pygame.draw.circle(pantalla, C_ASTEROIDE, (int(a.x), int(a.y)), int(a.radio))
        pygame.draw.circle(pantalla, C_ASTEROIDE_B, (int(a.x), int(a.y)), int(a.radio), 1)
    tuple(map(circulo, estado.asteroides))


def dibujar_nave(pantalla, estado: EstadoJuego) -> None:
    nave = estado.nave
    if nave.invulnerable > 0 and (nave.invulnerable // 5) % 2 == 0:
        return   # parpadeo tras un golpe
    color = C_NAVE_HIT if nave.invulnerable > 0 else C_NAVE
    pygame.draw.polygon(pantalla, color, [
        (nave.x, nave.y - RADIO_NAVE),
        (nave.x - RADIO_NAVE * 0.8, nave.y + RADIO_NAVE),
        (nave.x + RADIO_NAVE * 0.8, nave.y + RADIO_NAVE),
    ])


def dibujar(pantalla, estado, info, fuentes) -> None:
    pantalla.fill(C_FONDO)
    dibujar_asteroides(pantalla, estado)
    dibujar_nave(pantalla, estado)
    dibujar_metricas(pantalla, estado, info, fuentes)
    pygame.display.flip()


def ejecutar() -> None:
    pygame.init()
    pygame.display.set_caption(TITULO)
    pantalla = pygame.display.set_mode((ANCHO, ALTO))
    reloj    = pygame.time.Clock()
    fuentes  = crear_fuentes()
    info     = info_sistema()

    estado = crear_estado_inicial(CANTIDAD_INICIAL, ANCHO, ALTO, modo=SECUENCIAL)
    dt = 1.0 / FPS_TOPE

    with crear_pool() as pool:          # el Pool vive solo dentro de este bloque
        salir = False
        while not salir:
            eventos, salir = leer_entrada()
            estado = actualizar(estado, eventos, dt, pool)   # estado nuevo
            dibujar(pantalla, estado, info, fuentes)
            dt = reloj.tick(FPS_TOPE) / 1000.0

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    ejecutar()
