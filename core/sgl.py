"""Sistema Geodésico Local (SGL) do INCRA — área, distância e perímetro
no plano tangente local, conforme o Manual Técnico de Posicionamento:
georreferenciamento de imóveis rurais (1ª ed., 2013, capítulo 9) e a
NTGIR 3ª ed. (item 4.6).

A 2ª edição do Manual de Georreferenciamento NÃO serve de referência aqui
— naquela a área era calculada no plano UTM; o SGL só passou a valer a
partir da NTGIR 3ª ed. / SIGEF.

Sem dependência de GIS de propósito (só `math`): este módulo precisa
poder ser conferido célula a célula contra o Manual, sem a caixa-preta de
uma biblioteca de projeção por trás.

Decisão de projeto (diferente do item 4.2 do Manual, a pedido do
usuário): o Manual manda recusar vértice sem altitude elipsoidal em vez
de assumir h=0 — mas a grade deste app não distingue hoje "célula de h
vazia" de "usuário digitou 0" (mesmo comportamento de toda coluna
numérica, ver core/tabela_vertices.py), e parcelas litorâneas podem ter
h genuinamente perto de zero. Por pedido explícito, este módulo calcula
com o h que vier, sem bloquear por h=0.

Autointerseção do perímetro NÃO é checada aqui (exigiria shapely, fora
da lista de dependências permitidas) — quem chama (ui_qt/
visualizar_parcela_dialog.py) já roda core/validators/geometria.py::
verificar_autointersecao antes, com shapely.
"""
from __future__ import annotations

import math
import warnings

A_GRS80 = 6378137.0
F_GRS80 = 1 / 298.257222101
_B_GRS80 = A_GRS80 * (1 - F_GRS80)
_E2 = F_GRS80 * (2 - F_GRS80)
_E2_LINHA = _E2 / (1 - _E2)

_LIMITE_EXTENSAO_M = 50_000.0  # NBR 14166: plano tangente válido até ~50 km


def geod2geoc(lat_deg: float, lon_deg: float, h: float) -> tuple[float, float, float]:
    """Geodésicas (φ, λ, h) -> geocêntricas (X, Y, Z). Manual, item 9.1."""
    phi = math.radians(lat_deg)
    lam = math.radians(lon_deg)
    n = A_GRS80 / math.sqrt(1 - _E2 * math.sin(phi) ** 2)
    x = (n + h) * math.cos(phi) * math.cos(lam)
    y = (n + h) * math.cos(phi) * math.sin(lam)
    z = (n * (1 - _E2) + h) * math.sin(phi)
    return x, y, z


def geoc2geod(x: float, y: float, z: float) -> tuple[float, float, float]:
    """Geocêntricas (X, Y, Z) -> geodésicas (φ, λ, h). Forma fechada de
    Bowring (Resoluções IBGE 23/1989 e 01/2005), usada pra achar φ₀/λ₀ da
    origem do SGL (Manual, item 9.1)."""
    p = math.sqrt(x**2 + y**2)
    u = math.atan2(A_GRS80 * z, _B_GRS80 * p)
    lam = math.atan2(y, x)
    phi = math.atan2(
        z + _E2_LINHA * _B_GRS80 * math.sin(u) ** 3,
        p - _E2 * A_GRS80 * math.cos(u) ** 3,
    )
    n = A_GRS80 / math.sqrt(1 - _E2 * math.sin(phi) ** 2)
    h = p / math.cos(phi) - n
    return math.degrees(phi), math.degrees(lam), h


def origem_sgl(vertices: list[tuple[float, float, float]]) -> dict:
    """Origem do SGL (Manual, item 9.1, alíneas a e c): média das
    coordenadas GEOCÊNTRICAS dos vértices — não a média de φ/λ. φ₀/λ₀
    saem da conversão inversa dessa média.

    `vertices`: sequência de (lat_deg, lon_deg, h). Retorna
    {'X0','Y0','Z0','lat0','lon0','h0'}."""
    if not vertices:
        raise ValueError("é preciso pelo menos 1 vértice para calcular a origem do SGL")
    geocentricas = [geod2geoc(lat, lon, h) for lat, lon, h in vertices]
    m = len(geocentricas)
    x0 = sum(p[0] for p in geocentricas) / m
    y0 = sum(p[1] for p in geocentricas) / m
    z0 = sum(p[2] for p in geocentricas) / m
    lat0, lon0, h0 = geoc2geod(x0, y0, z0)
    return {"X0": x0, "Y0": y0, "Z0": z0, "lat0": lat0, "lon0": lon0, "h0": h0}


def geoc2enu(
    x: float, y: float, z: float, lat0: float, lon0: float, x0: float, y0: float, z0: float
) -> tuple[float, float, float]:
    """Geocêntricas -> cartesianas locais (e, n, u) do SGL. Manual, item 9.1."""
    phi0 = math.radians(lat0)
    lam0 = math.radians(lon0)
    dx, dy, dz = x - x0, y - y0, z - z0
    e = -math.sin(lam0) * dx + math.cos(lam0) * dy
    n = -math.sin(phi0) * math.cos(lam0) * dx - math.sin(phi0) * math.sin(lam0) * dy + math.cos(phi0) * dz
    u = math.cos(phi0) * math.cos(lam0) * dx + math.cos(phi0) * math.sin(lam0) * dy + math.sin(phi0) * dz
    return e, n, u


def enu2geoc(
    e: float, n: float, u: float, lat0: float, lon0: float, x0: float, y0: float, z0: float
) -> tuple[float, float, float]:
    """Cartesianas locais (e, n, u) -> geocêntricas. Transposta da matriz
    de geoc2enu, mais a translação de volta. Manual, item 9.2."""
    phi0 = math.radians(lat0)
    lam0 = math.radians(lon0)
    x = -math.sin(lam0) * e - math.sin(phi0) * math.cos(lam0) * n + math.cos(phi0) * math.cos(lam0) * u + x0
    y = math.cos(lam0) * e - math.sin(phi0) * math.sin(lam0) * n + math.cos(phi0) * math.sin(lam0) * u + y0
    z = math.cos(phi0) * n + math.sin(phi0) * u + z0
    return x, y, z


def vertices_para_sgl(
    vertices: list[tuple[float, float, float]], origem: dict | None = None
) -> tuple[list[tuple[float, float, float]], dict]:
    """Converte (lat, lon, h) de cada vértice para (e, n, u). Sem `origem`,
    calcula pela média geocêntrica (origem_sgl). Devolve (pontos_enu, origem)."""
    if origem is None:
        origem = origem_sgl(vertices)
    pontos_enu = [
        geoc2enu(*geod2geoc(lat, lon, h), origem["lat0"], origem["lon0"], origem["X0"], origem["Y0"], origem["Z0"])
        for lat, lon, h in vertices
    ]
    return pontos_enu, origem


def _validar_poligono(vertices: list[tuple[float, float, float]]) -> None:
    if len(vertices) < 3:
        raise ValueError("é preciso pelo menos 3 vértices para calcular área")
    m = len(vertices)
    for i in range(m):
        atual, proximo = vertices[i], vertices[(i + 1) % m]
        if atual[0] == proximo[0] and atual[1] == proximo[1]:
            raise ValueError(f"vértices consecutivos {i} e {(i + 1) % m} têm a mesma coordenada")


def area_sgl(vertices: list[tuple[float, float, float]]) -> dict:
    """Área da parcela pela fórmula de Gauss ("cadarço") sobre (e, n) do
    SGL. Manual, item 9.3 + NTGIR 3ª ed., item 4.6.

    Pré-condições verificadas aqui: polígono fechado por índice (não
    repete o primeiro vértice no fim da lista), mínimo 3 vértices, sem
    vértices coincidentes consecutivos. Autointerseção NÃO é checada
    aqui — ver docstring do módulo.

    Devolve {'area_m2', 'area_ha', 'origem', 'enu', 'sentido'}, sentido
    em {'horario', 'antihorario'} a partir do sinal do somatório."""
    _validar_poligono(vertices)
    pontos_enu, origem = vertices_para_sgl(vertices)

    _avisar_se_extensao_excede_limite(pontos_enu)

    m = len(pontos_enu)
    soma = sum(
        pontos_enu[i][0] * pontos_enu[(i + 1) % m][1] - pontos_enu[(i + 1) % m][0] * pontos_enu[i][1]
        for i in range(m)
    )
    area_m2 = abs(soma) / 2
    sentido = "horario" if soma < 0 else "antihorario"
    return {
        "area_m2": area_m2,
        "area_ha": area_m2 / 10_000,
        "origem": origem,
        "enu": pontos_enu,
        "sentido": sentido,
    }


def _avisar_se_extensao_excede_limite(pontos_enu: list[tuple[float, float, float]]) -> None:
    # NBR 14166: plano tangente do SGL só é válido até ~50 km x 50 km.
    es = [p[0] for p in pontos_enu]
    ns = [p[1] for p in pontos_enu]
    if max(es) - min(es) > _LIMITE_EXTENSAO_M or max(ns) - min(ns) > _LIMITE_EXTENSAO_M:
        warnings.warn(
            "a parcela ultrapassa ~50 km de extensão — o plano tangente do SGL (NBR 14166) "
            "deixa de ser uma aproximação confiável nessa escala",
            stacklevel=3,
        )


def distancia_horizontal(v1: tuple[float, float, float], v2: tuple[float, float, float]) -> float:
    """Distância horizontal entre dois vértices geodésicos, descontando a
    diferença de altitude elipsoidal — NÃO é a distância plana (e, n).
    Manual, item 9.4. Metros."""
    x1, y1, z1 = geod2geoc(*v1)
    x2, y2, z2 = geod2geoc(*v2)
    dh = v1[2] - v2[2]
    # max(0.0, ...): quando a distância horizontal real é ~0 (mesma
    # posição, só h diferente), arredondamento de ponto flutuante nas
    # trigonométricas de geod2geoc pode deixar o argumento uma fração
    # ínfima negativa (ex.: -1e-8) em vez de exatamente zero.
    quadrado = max(0.0, (x1 - x2) ** 2 + (y1 - y2) ** 2 + (z1 - z2) ** 2 - dh**2)
    return math.sqrt(quadrado)


def perimetro(vertices: list[tuple[float, float, float]]) -> float:
    """Soma das distâncias horizontais (item 9.4) entre vértices
    consecutivos, fechando a poligonal (último -> primeiro). Metros."""
    if len(vertices) < 2:
        return 0.0
    m = len(vertices)
    return sum(distancia_horizontal(vertices[i], vertices[(i + 1) % m]) for i in range(m))


def azimute_puissant(v1: tuple[float, float, float], v2: tuple[float, float, float]) -> float:
    """Problema Geodésico Inverso segundo Puissant (Manual, item 9.5).

    Não implementado nesta rodada — a especificação fornecida não trazia
    a fórmula fechada de Puissant, e um azimute geodésico errado é pior
    que a ausência da função (entra em memorial descritivo). Explícito
    de propósito (pedido da própria especificação) em vez de aproximar
    silenciosamente por atan2(Δe, Δn)."""
    raise NotImplementedError(
        "azimute_puissant ainda não implementado — ver core/sgl.py e a especificação do item 9.5"
    )
