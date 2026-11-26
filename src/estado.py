"""
estado.py
---------
Nucleo funcional del simulador "Nave vs Asteroides".

Todo el estado vive en estructuras inmutables (@dataclass(frozen=True)) y
todas las transformaciones son funciones puras: reciben un estado y
devuelven uno nuevo. No hay variables globales mutables, ni objetos que
se modifiquen a si mismos, ni bucles que muten colecciones.

Incluye tambien el generador pseudoaleatorio PURO (la semilla se recibe y
se devuelve, en lugar de usar el estado oculto del modulo `random`) y las
metricas de FPS como datos inmutables dentro del propio EstadoJuego.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from itertools import accumulate
from typing import Tuple
import math


# ---------------------------------------------------------------------------
# Constantes (valores que nunca cambian)
# ---------------------------------------------------------------------------

RADIO_ASTEROIDE_MIN = 4.0
RADIO_ASTEROIDE_MAX = 11.0
VEL_ASTEROIDE_MAX   = 2.2

RADIO_REPULSION     = 26.0
FUERZA_REPULSION    = 0.55
RADIO_NAVE          = 14.0
FRAMES_INVULNERABLE = 60
DISTANCIA_SEGURA    = 120.0   # separacion minima nave-asteroide al crear

VENTANA_FPS = 60              # frames que se promedian para los FPS

SECUENCIAL = "secuencial"
PARALELO   = "paralelo"


# ---------------------------------------------------------------------------
# Estructuras de datos inmutables
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Asteroide:
    x: float
    y: float
    vx: float
    vy: float
    radio: float


@dataclass(frozen=True)
class Nave:
    x: float
    y: float
    vidas: int = 5
    invulnerable: int = 0


@dataclass(frozen=True)
class Eventos:
    """Entrada del usuario en un frame, ya convertida a datos inmutables."""
    dx: float = 0.0
    dy: float = 0.0
    alternar_modo: bool = False
    reiniciar_con: int = 0        # 0 = no reiniciar; >0 = nueva cantidad


@dataclass(frozen=True)
class Metricas:
    """Tiempos de los ultimos frames y tabla (n, modo, fps) ya medida."""
    tiempos:  Tuple[float, ...] = ()
    registro: Tuple[Tuple[int, str, float], ...] = ()


@dataclass(frozen=True)
class EstadoJuego:
    nave:       Nave
    asteroides: Tuple[Asteroide, ...]
    frame:      int
    modo:       str
    ancho:      int
    alto:       int
    semilla:    int = 42
    impactos:   int = 0
    metricas:   Metricas = Metricas()


# ---------------------------------------------------------------------------
# Generador pseudoaleatorio puro (LCG de Knuth, 64 bits)
# ---------------------------------------------------------------------------

_MODULO = 2 ** 64


def siguiente_semilla(semilla: int) -> int:
    return (6364136223846793005 * semilla + 1442695040888963407) % _MODULO


def uniforme(semilla: int, minimo: float, maximo: float) -> Tuple[float, int]:
    """Devuelve (valor en [minimo, maximo), nueva semilla)."""
    nueva = siguiente_semilla(semilla)
    return minimo + (maximo - minimo) * (nueva / _MODULO), nueva


# ---------------------------------------------------------------------------
# Construccion del estado inicial
# ---------------------------------------------------------------------------

def crear_asteroide(
    semilla: int, ancho: int, alto: int, nave: Nave
) -> Tuple[Asteroide, int]:
    """Crea un asteroide lejos de la nave. Devuelve (asteroide, nueva semilla)."""
    x, s1 = uniforme(semilla, 0.0, float(ancho))
    y, s2 = uniforme(s1, 0.0, float(alto))
    if math.hypot(x - nave.x, y - nave.y) <= DISTANCIA_SEGURA:
        return crear_asteroide(s2, ancho, alto, nave)   # reintento recursivo
    angulo, s3 = uniforme(s2, 0.0, 2 * math.pi)
    rapidez, s4 = uniforme(s3, 0.4, VEL_ASTEROIDE_MAX)
    radio, s5 = uniforme(s4, RADIO_ASTEROIDE_MIN, RADIO_ASTEROIDE_MAX)
    return Asteroide(x, y, math.cos(angulo) * rapidez,
                     math.sin(angulo) * rapidez, radio), s5


def crear_asteroides(
    n: int, ancho: int, alto: int, nave: Nave, semilla: int
) -> Tuple[Asteroide, ...]:
    """Encadena la semilla con `accumulate` (sin bucles ni mutacion)."""
    pasos = accumulate(
        range(n),
        lambda par, _: crear_asteroide(par[1], ancho, alto, nave),
        initial=(None, semilla),
    )
    return tuple(par[0] for par in tuple(pasos)[1:])


def crear_estado_inicial(
    n_asteroides: int,
    ancho: int,
    alto: int,
    modo: str = SECUENCIAL,
    semilla: int = 42,
    metricas: Metricas = Metricas(),
) -> EstadoJuego:
    nave = Nave(x=ancho / 2, y=alto / 2)
    return EstadoJuego(
        nave=nave,
        asteroides=crear_asteroides(n_asteroides, ancho, alto, nave, semilla),
        frame=0,
        modo=modo,
        ancho=ancho,
        alto=alto,
        semilla=semilla,
        impactos=0,
        metricas=replace(metricas, tiempos=()),
    )


# ---------------------------------------------------------------------------
# Fisica (funciones puras)
# ---------------------------------------------------------------------------

def _envolver(valor: float, limite: int) -> float:
    """Pantalla toroidal: salir por un borde = entrar por el opuesto."""
    if valor < 0:
        return valor + limite
    if valor >= limite:
        return valor - limite
    return valor


def mover_asteroide(a: Asteroide, ancho: int, alto: int) -> Asteroide:
    return replace(a, x=_envolver(a.x + a.vx, ancho), y=_envolver(a.y + a.vy, alto))


def empuje(a: Asteroide, b: Asteroide) -> Tuple[float, float]:
    """Aceleracion que `b` le causa a `a` (0,0 si estan lejos o son el mismo)."""
    dx = a.x - b.x
    dy = a.y - b.y
    d2 = dx * dx + dy * dy
    if 0.0 < d2 < RADIO_REPULSION * RADIO_REPULSION:
        d = math.sqrt(d2)
        fuerza = FUERZA_REPULSION * (1.0 - d / RADIO_REPULSION)
        return (dx / d * fuerza, dy / d * fuerza)
    return (0.0, 0.0)


def limitar_rapidez(vx: float, vy: float) -> Tuple[float, float]:
    tope = VEL_ASTEROIDE_MAX * 1.5
    rapidez = math.hypot(vx, vy)
    if rapidez > tope:
        factor = tope / rapidez
        return (vx * factor, vy * factor)
    return (vx, vy)


def interaccion_repulsion(a: Asteroide, vecinos: Tuple[Asteroide, ...]) -> Asteroide:
    """
    Suma los empujes de todos los vecinos (calculo O(n^2) en total, el mas
    costoso del frame) y devuelve el asteroide con su velocidad ajustada.
    """
    empujes = tuple(empuje(a, b) for b in vecinos)
    vx, vy = limitar_rapidez(
        a.vx + sum(e[0] for e in empujes),
        a.vy + sum(e[1] for e in empujes),
    )
    return replace(a, vx=vx, vy=vy)


def transformar_asteroide(
    a: Asteroide, todos: Tuple[Asteroide, ...], ancho: int, alto: int
) -> Asteroide:
    return mover_asteroide(interaccion_repulsion(a, todos), ancho, alto)


def actualizar_segmento(args: tuple) -> Tuple[Asteroide, ...]:
    """Unidad de trabajo de cada worker: funcion pura sobre un segmento."""
    segmento, todos, ancho, alto = args
    return tuple(transformar_asteroide(a, todos, ancho, alto) for a in segmento)


# ---------------------------------------------------------------------------
# Nave y colisiones
# ---------------------------------------------------------------------------

def hay_colision(nave: Nave, a: Asteroide) -> bool:
    return math.hypot(nave.x - a.x, nave.y - a.y) < (RADIO_NAVE + a.radio)


def resolver_impactos(nave: Nave, asteroides: Tuple[Asteroide, ...]) -> Tuple[Nave, int]:
    if nave.invulnerable > 0:
        return replace(nave, invulnerable=nave.invulnerable - 1), 0
    if any(hay_colision(nave, a) for a in asteroides):
        return replace(nave, vidas=max(0, nave.vidas - 1),
                       invulnerable=FRAMES_INVULNERABLE), 1
    return nave, 0


def mover_nave(nave: Nave, dx: float, dy: float, ancho: int, alto: int) -> Nave:
    nx = max(RADIO_NAVE, min(float(ancho) - RADIO_NAVE, nave.x + dx))
    ny = max(RADIO_NAVE, min(float(alto) - RADIO_NAVE, nave.y + dy))
    return replace(nave, x=nx, y=ny)


# ---------------------------------------------------------------------------
# Eventos y metricas (funciones puras)
# ---------------------------------------------------------------------------

def cambiar_modo(estado: EstadoJuego) -> EstadoJuego:
    nuevo = PARALELO if estado.modo == SECUENCIAL else SECUENCIAL
    return replace(estado, modo=nuevo, metricas=replace(estado.metricas, tiempos=()))


def aplicar_eventos(estado: EstadoJuego, ev: Eventos) -> EstadoJuego:
    """Aplica la entrada del frame y devuelve un estado nuevo."""
    e1 = cambiar_modo(estado) if ev.alternar_modo else estado
    e2 = (
        crear_estado_inicial(ev.reiniciar_con, e1.ancho, e1.alto,
                             e1.modo, e1.semilla, e1.metricas)
        if ev.reiniciar_con > 0 else e1
    )
    nave = (mover_nave(e2.nave, ev.dx, ev.dy, e2.ancho, e2.alto)
            if (ev.dx or ev.dy) else e2.nave)
    return replace(e2, nave=nave)


def fps_de(tiempos: Tuple[float, ...]) -> float:
    promedio = sum(tiempos) / len(tiempos) if tiempos else 0.0
    return 1.0 / promedio if promedio > 0 else 0.0


def registrar_frame(m: Metricas, dt: float, n: int, modo: str) -> Metricas:
    """Agrega el tiempo del frame; con la ventana llena, guarda los FPS en la tabla."""
    tiempos = (m.tiempos + (dt,))[-VENTANA_FPS:]
    if len(tiempos) < VENTANA_FPS:
        return replace(m, tiempos=tiempos)
    registro = tuple(r for r in m.registro if r[:2] != (n, modo)) \
        + ((n, modo, round(fps_de(tiempos), 1)),)
    return replace(m, tiempos=tiempos, registro=registro)


def consultar_registro(m: Metricas, n: int, modo: str) -> str:
    valor = next((r[2] for r in m.registro if r[:2] == (n, modo)), None)
    return f"{valor:.1f}" if valor is not None else "---"
