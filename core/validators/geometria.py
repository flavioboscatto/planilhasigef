"""Geometria do perímetro. Por ora só a reorganização (Etapa 4); o resto
da Etapa 3 (fechamento, autointerseção, cruzamento entre abas) ainda não
está aqui.
"""
from __future__ import annotations

from core.models import Vertice


def reordena_norte_horario(vertices: list[Vertice]) -> list[Vertice]:
    """Rotaciona a lista para começar no vértice mais ao norte (maior
    n_lat; empate resolvido pelo mais a oeste, menor e_long) e inverte a
    ordem se estiver no sentido anti-horário.

    Funciona igual em UTM ou Geográfica: em ambos os sistemas, maior n_lat
    é mais ao norte e menor e_long é mais a oeste dentro da mesma área.
    """
    if len(vertices) < 3:
        return list(vertices)

    indice_norte = min(
        range(len(vertices)), key=lambda i: (-vertices[i].n_lat, vertices[i].e_long)
    )
    rotacionado = vertices[indice_norte:] + vertices[:indice_norte]

    n = len(rotacionado)
    area2 = sum(
        rotacionado[i].e_long * rotacionado[(i + 1) % n].n_lat
        - rotacionado[(i + 1) % n].e_long * rotacionado[i].n_lat
        for i in range(n)
    )
    sentido_horario = area2 < 0
    if not sentido_horario:
        rotacionado = [rotacionado[0]] + list(reversed(rotacionado[1:]))
    return rotacionado
