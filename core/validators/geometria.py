"""Geometria do perímetro: reorganização (Etapa 4) e autointerseção
(Etapa 3, V3). Fechamento e cruzamento ENTRE abas/parcelas ainda não estão
aqui.
"""
from __future__ import annotations

from dataclasses import dataclass

from shapely.geometry import LineString

from core.models import Vertice


@dataclass(frozen=True)
class Cruzamento:
    """Um par de lados do perímetro que se cruzam. Não é o `Ocorrencia
    (severidade, aba, linha, campo, mensagem)` cogitado no CLAUDE.md pra
    validação futura — aquele formato é pra problema de UMA célula;
    autointerseção é uma relação entre DOIS lados (4 vértices), não cabe
    limpo nisso."""

    indice_a: int
    indice_b: int
    mensagem: str


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


def verificar_autointersecao(vertices: list[Vertice]) -> list[Cruzamento]:
    """Detecta lados do perímetro que se cruzam ("borboleta") — imóvel é
    polígono fechado, lados não-adjacentes nunca podem se tocar. Só
    topológico (via shapely, sem projeção métrica): grau decimal geodésico
    cru serve pra essa pergunta (sinal/cruzamento), mesmo não servindo pra
    distância/área real (ver core/geo.py::geodesica_para_utm, usado só pra
    desenhar).

    Lados ADJACENTES (compartilham vértice, ex. lado i e lado i+1) sempre
    se tocam nesse vértice comum — isso é normal, não é cruzamento.
    """
    n = len(vertices)
    if n < 3:
        return []

    pontos = [(v.e_long, v.n_lat) for v in vertices]
    lados = [LineString([pontos[i], pontos[(i + 1) % n]]) for i in range(n)]

    cruzamentos: list[Cruzamento] = []
    for i in range(n):
        for j in range(i + 1, n):
            adjacentes = j == (i + 1) % n or i == (j + 1) % n
            if adjacentes:
                continue
            if lados[i].intersects(lados[j]):
                a1, a2 = vertices[i].codigo, vertices[(i + 1) % n].codigo
                b1, b2 = vertices[j].codigo, vertices[(j + 1) % n].codigo
                cruzamentos.append(
                    Cruzamento(
                        indice_a=i, indice_b=j,
                        mensagem=f"O lado {a1}–{a2} cruza o lado {b1}–{b2}.",
                    )
                )
    return cruzamentos
