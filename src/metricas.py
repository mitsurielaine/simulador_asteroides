"""
metricas.py
-----------
Dibujo del panel de informacion (HUD). Solo LEE el estado: los FPS y la
tabla comparativa viven como datos inmutables en `estado.metricas`.
"""

from __future__ import annotations

import pygame

from estado import (
    EstadoJuego, SECUENCIAL, PARALELO, fps_de, consultar_registro,
)

C_TITULO = (250, 200, 35)
C_VALOR  = (240, 240, 245)
C_SEQ    = (235, 110, 110)
C_PAR    = (110, 220, 150)
C_GRIS   = (150, 155, 170)

CANTIDADES_TABLA = (1000, 3000, 5000)


def crear_fuentes() -> tuple:
    """(titulo, normal, mini): se crean una sola vez al iniciar."""
    return (pygame.font.SysFont("consolas", 14, bold=True),
            pygame.font.SysFont("consolas", 13),
            pygame.font.SysFont("consolas", 12))


def dibujar_metricas(pantalla, estado: EstadoJuego, info_sistema: dict, fuentes: tuple) -> None:
    f_titulo, f_normal, f_mini = fuentes
    n = len(estado.asteroides)
    fps = fps_de(estado.metricas.tiempos)
    ms = (1000.0 / fps) if fps > 0 else 0.0

    color_modo = C_PAR if estado.modo == PARALELO else C_SEQ
    lineas = (
        (f"MODO: {estado.modo.upper()}", color_modo),
        (f"FPS: {fps:.1f}", C_VALOR),
        (f"ms/frame: {ms:.1f}", C_VALOR),
        (f"Asteroides: {n:,}", C_VALOR),
        (f"Nucleos: {info_sistema['nucleos_totales']}  Workers: {info_sistema['workers_activos']}", C_GRIS),
        (f"Vidas nave: {estado.nave.vidas}", C_TITULO),
        (f"Impactos: {estado.impactos}", C_SEQ),
        (f"Frame: {estado.frame}", C_GRIS),
    )
    tuple(pantalla.blit(f_normal.render(t, True, c), (10, 10 + i * 18))
          for i, (t, c) in enumerate(lineas))

    ancho_tabla = 330
    tx = pantalla.get_width() - ancho_tabla - 10
    ty = 10
    col = ancho_tabla // 3
    pantalla.blit(f_titulo.render("TABLA COMPARATIVA (FPS)", True, C_TITULO), (tx, ty))
    tuple(pantalla.blit(f_mini.render(h, True, C_TITULO), (tx + j * col, ty + 20))
          for j, h in enumerate(("Entidades", "Secuencial", "Paralelo")))
    pygame.draw.line(pantalla, C_GRIS, (tx, ty + 36), (tx + ancho_tabla, ty + 36), 1)

    def fila(i_cant):
        i, cantidad = i_cant
        datos = (f"{cantidad:,}",
                 consultar_registro(estado.metricas, cantidad, SECUENCIAL),
                 consultar_registro(estado.metricas, cantidad, PARALELO))
        colores = (C_VALOR, C_SEQ, C_PAR)
        return tuple(pantalla.blit(f_mini.render(v, True, c),
                                   (tx + j * col, ty + 42 + i * 18))
                     for j, (v, c) in enumerate(zip(datos, colores)))
    tuple(map(fila, enumerate(CANTIDADES_TABLA)))

    ayuda = "[Flechas] Mover   [P] Secuencial/Paralelo   [1/3/5] 1k/3k/5k   [ESC] Salir"
    pantalla.blit(f_mini.render(ayuda, True, C_GRIS), (10, pantalla.get_height() - 22))
