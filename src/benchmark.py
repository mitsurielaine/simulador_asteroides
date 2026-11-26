"""
benchmark.py
------------
Mide FPS del calculo de fisica (sin dibujar): secuencial vs paralelo, con
1000, 3000 y 5000 asteroides. Cada equipo obtiene los numeros de SU hardware.

Uso:
    python benchmark.py          # 10 frames por prueba
    python benchmark.py 30       # 30 frames por prueba
"""

from __future__ import annotations

import sys
import time
from functools import reduce
from typing import Callable

from estado import EstadoJuego, crear_estado_inicial
from motor_paralelo import (
    actualizar_secuencial, actualizar_paralelo, crear_pool, info_sistema,
)

ANCHO, ALTO = 1100, 700
CANTIDADES = (1000, 3000, 5000)


def medir_fps(paso: Callable[[EstadoJuego], EstadoJuego], n: int, frames: int) -> float:
    """FPS promedio de `frames` pasos encadenados con reduce (sin mutar nada)."""
    calentado = paso(crear_estado_inicial(n, ANCHO, ALTO))   # frame en frio
    inicio = time.perf_counter()
    reduce(lambda estado, _: paso(estado), range(frames), calentado)
    transcurrido = time.perf_counter() - inicio
    return frames / transcurrido if transcurrido > 0 else 0.0


def correr_tabla(frames: int) -> None:
    info = info_sistema()
    print("=" * 56)
    print("  SIMULADOR NAVE vs ASTEROIDES - BENCHMARK")
    print("=" * 56)
    print(f"  Nucleos totales detectados : {info['nucleos_totales']}")
    print(f"  Workers (procesos) activos : {info['workers_activos']}")
    print(f"  Frames medidos por prueba  : {frames}")
    print("-" * 56)
    print(f"  {'Entidades':>10} | {'Secuencial':>13} | {'Paralelo':>13} | {'Mejora':>7}")
    print("-" * 56)
    with crear_pool() as pool:
        for n in CANTIDADES:
            seq = medir_fps(actualizar_secuencial, n, frames)
            par = medir_fps(lambda e: actualizar_paralelo(e, pool), n, frames)
            print(f"  {n:>10,} | {seq:>8.2f} FPS | {par:>8.2f} FPS | {par / seq:>5.2f}x")
    print("=" * 56)


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    correr_tabla(int(sys.argv[1]) if len(sys.argv) > 1 else 10)
