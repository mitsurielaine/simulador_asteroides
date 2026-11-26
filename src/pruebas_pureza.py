"""
pruebas_pureza.py
-----------------
Evidencia de pureza funcional para la defensa. Uso: python pruebas_pureza.py
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import FrozenInstanceError

from estado import crear_estado_inicial, Eventos
from motor_paralelo import (
    actualizar, actualizar_secuencial, actualizar_paralelo, segmentar,
    crear_pool, N_WORKERS,
)

SIN_EVENTOS = Eventos()


def intenta_mutar(objeto, campo, valor) -> bool:
    try:
        setattr(objeto, campo, valor)
        return False
    except FrozenInstanceError:
        return True


def verificar(nombre: str, condicion: bool) -> None:
    print(f"  [{'OK' if condicion else 'FALLA'}] {nombre}")


def main() -> None:
    estado = crear_estado_inicial(300, 1100, 700)
    print("PRUEBAS DE PUREZA FUNCIONAL")

    verificar("EstadoJuego es inmutable",
              intenta_mutar(estado, "frame", 99))
    verificar("Asteroide es inmutable",
              intenta_mutar(estado.asteroides[0], "x", 0.0))
    verificar("Los asteroides viven en una tupla (no lista)",
              isinstance(estado.asteroides, tuple))

    antes = deepcopy(estado)
    nuevo = actualizar_secuencial(estado)
    verificar("actualizar NO muta el estado original", estado == antes)
    verificar("actualizar devuelve un objeto nuevo", nuevo is not estado)
    verificar("Determinismo: mismo estado -> mismo resultado",
              actualizar_secuencial(estado) == nuevo)
    verificar("Semilla fija: dos estados iniciales identicos",
              crear_estado_inicial(300, 1100, 700) == estado)

    partes = segmentar(estado.asteroides, N_WORKERS)
    verificar("segmentar: la union de los bloques reproduce la tupla",
              tuple(a for p in partes for a in p) == estado.asteroides)
    verificar(f"segmentar: no genera mas de {N_WORKERS} bloques",
              len(partes) <= N_WORKERS)

    with crear_pool() as pool:
        paralelo = actualizar_paralelo(estado, pool)
        verificar("Secuencial y paralelo producen EXACTAMENTE el mismo estado",
                  paralelo == nuevo)
        completo = actualizar(estado, SIN_EVENTOS, 1 / 60, pool)
        verificar("actualizar(estado, eventos, dt, pool) avanza un frame",
                  completo.frame == estado.frame + 1)


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    main()
