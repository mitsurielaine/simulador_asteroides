"""
motor_paralelo.py
-----------------
Motor de actualizacion: version secuencial (1 nucleo) y version paralela
(multiprocessing). Ambas devuelven un EstadoJuego nuevo, por lo que la
comparativa de rendimiento es justa.

Flujo paralelo:
    1. Segmentacion   -> partir la tupla de asteroides en bloques.
    2. Mapeo paralelo -> pool.map(actualizar_segmento, tareas).
    3. Consolidacion  -> pool.map espera a todos los hijos; se unen los
                         resultados y se construye el nuevo estado congelado.

El Pool NO es una variable global: se crea en la capa exterior (juego.py /
benchmark.py) y se recibe como argumento.
"""

from __future__ import annotations

import os
import multiprocessing as mp
from dataclasses import replace
from typing import Tuple

from estado import (
    EstadoJuego, Asteroide, Eventos, PARALELO,
    actualizar_segmento, transformar_asteroide, resolver_impactos,
    aplicar_eventos, registrar_frame,
)

N_NUCLEOS: int = os.cpu_count() or 1
N_WORKERS: int = max(1, N_NUCLEOS - 1)   # un nucleo libre para SO y render


def crear_pool():
    """Crea el Pool de procesos; quien lo llame lo cierra con `with`."""
    return mp.Pool(processes=N_WORKERS)


def info_sistema() -> dict:
    return {"nucleos_totales": N_NUCLEOS, "workers_activos": N_WORKERS}


def segmentar(
    asteroides: Tuple[Asteroide, ...], n_partes: int
) -> Tuple[Tuple[Asteroide, ...], ...]:
    """Parte la tupla en como maximo `n_partes` bloques contiguos (division techo)."""
    total = len(asteroides)
    if total == 0:
        return ((),)
    tam = -(-total // n_partes)          # ceil(total / n_partes)
    return tuple(asteroides[i:i + tam] for i in range(0, total, tam))


def _cerrar_frame(estado: EstadoJuego, asteroides) -> EstadoJuego:
    nave, golpes = resolver_impactos(estado.nave, asteroides)
    return replace(
        estado,
        asteroides=asteroides,
        nave=nave,
        impactos=estado.impactos + golpes,
        frame=estado.frame + 1,
    )


def actualizar_paralelo(estado: EstadoJuego, pool) -> EstadoJuego:
    segmentos = segmentar(estado.asteroides, N_WORKERS)
    tareas = tuple((seg, estado.asteroides, estado.ancho, estado.alto)
                   for seg in segmentos)
    resultados = pool.map(actualizar_segmento, tareas)      # espera a los hijos
    nuevos = tuple(a for parte in resultados for a in parte)
    return _cerrar_frame(estado, nuevos)


def actualizar_secuencial(estado: EstadoJuego) -> EstadoJuego:
    nuevos = tuple(
        transformar_asteroide(a, estado.asteroides, estado.ancho, estado.alto)
        for a in estado.asteroides
    )
    return _cerrar_frame(estado, nuevos)


def actualizar(estado: EstadoJuego, eventos: Eventos, dt: float, pool) -> EstadoJuego:
    """update(state, events, dt, pool) -> GameState: punto de entrada del frame."""
    base = aplicar_eventos(estado, eventos)
    fisica = (actualizar_paralelo(base, pool) if base.modo == PARALELO
              else actualizar_secuencial(base))
    return replace(
        fisica,
        metricas=registrar_frame(fisica.metricas, dt,
                                 len(fisica.asteroides), fisica.modo),
    )
