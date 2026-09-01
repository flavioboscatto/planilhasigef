"""Testes de core/sgl.py (área/distância/perímetro no Sistema Geodésico
Local do INCRA) — vetor numérico de referência e testes de invariância da
especificação fornecida pelo usuário (Manual Técnico de Posicionamento,
cap. 9 + NTGIR 3ª ed., item 4.6)."""
from __future__ import annotations

import math

import pytest

from core.sgl import (
    area_sgl,
    distancia_horizontal,
    enu2geoc,
    geoc2geod,
    geod2geoc,
    origem_sgl,
    perimetro,
)

# vetor numérico de referência (SIRGAS 2000, altitudes elipsoidais)
_PARCELA_REFERENCIA = [
    (-27.500000, -48.500000, 100.000),
    (-27.500000, -48.490000, 120.000),
    (-27.510000, -48.490000, 150.000),
    (-27.510000, -48.500000, 130.000),
]


def test_geod2geoc_e_volta_bate_com_original():
    pontos = [
        (-27.5, -48.5, 100.0),
        (-26.0, -53.0, 0.0),
        (-28.0, -48.0, 1500.0),
        (-27.123456, -49.987654, 823.4),
    ]
    for lat, lon, h in pontos:
        x, y, z = geod2geoc(lat, lon, h)
        lat2, lon2, h2 = geoc2geod(x, y, z)
        assert lat2 == pytest.approx(lat, abs=1e-9)
        assert lon2 == pytest.approx(lon, abs=1e-9)
        assert h2 == pytest.approx(h, abs=1e-6)


def test_enu2geoc_e_volta_bate_com_original():
    origem = origem_sgl(_PARCELA_REFERENCIA)
    for lat, lon, h in _PARCELA_REFERENCIA:
        x, y, z = geod2geoc(lat, lon, h)
        from core.sgl import geoc2enu

        e, n, u = geoc2enu(x, y, z, origem["lat0"], origem["lon0"], origem["X0"], origem["Y0"], origem["Z0"])
        x2, y2, z2 = enu2geoc(e, n, u, origem["lat0"], origem["lon0"], origem["X0"], origem["Y0"], origem["Z0"])
        assert x2 == pytest.approx(x, abs=1e-6)
        assert y2 == pytest.approx(y, abs=1e-6)
        assert z2 == pytest.approx(z, abs=1e-6)


def test_origem_sgl_bate_com_vetor_de_referencia():
    origem = origem_sgl(_PARCELA_REFERENCIA)

    assert origem["lat0"] == pytest.approx(-27.505000103, abs=1e-9)
    assert origem["lon0"] == pytest.approx(-48.494999992, abs=1e-9)
    assert origem["h0"] == pytest.approx(124.9567, abs=1e-3)


def test_enu_bate_com_vetor_de_referencia():
    resultado = area_sgl(_PARCELA_REFERENCIA)
    enu_esperado = [
        (-494.0692, 554.0676, -25.0000),
        (494.0692, 554.0694, -5.0000),
        (494.0269, -554.0694, 25.0000),
        (-494.0269, -554.0676, 5.0000),
    ]

    for (e, n, u), (e_esp, n_esp, u_esp) in zip(resultado["enu"], enu_esperado):
        assert e == pytest.approx(e_esp, abs=1e-3)
        assert n == pytest.approx(n_esp, abs=1e-3)
        assert u == pytest.approx(u_esp, abs=1e-3)


def test_area_bate_com_vetor_de_referencia():
    resultado = area_sgl(_PARCELA_REFERENCIA)

    assert resultado["area_m2"] == pytest.approx(1_094_945.7868, abs=1e-1)
    assert resultado["area_ha"] == pytest.approx(109.4946, abs=1e-4)


def test_perimetro_bate_com_vetor_de_referencia():
    assert perimetro(_PARCELA_REFERENCIA) == pytest.approx(4192.466, abs=1e-2)


def test_h_zerado_muda_area_em_43_m2():
    # controle de sensibilidade da especificação: garante que h está
    # sendo efetivamente usado no cálculo, não ignorado.
    parcela_sem_h = [(lat, lon, 0.0) for lat, lon, _ in _PARCELA_REFERENCIA]

    area_com_h = area_sgl(_PARCELA_REFERENCIA)["area_m2"]
    area_sem_h = area_sgl(parcela_sem_h)["area_m2"]

    assert area_sem_h == pytest.approx(1_094_902.7872, abs=1e-1)
    assert area_com_h - area_sem_h == pytest.approx(43.00, abs=0.1)


def test_area_invariante_a_falsa_origem():
    resultado_normal = area_sgl(_PARCELA_REFERENCIA)

    # falsa origem (E0=150000, N0=250000) não é uma operação do módulo
    # (§4.4 diz que é opcional e nunca deve ser aplicada antes do cálculo
    # de área) — a invariância real testada aqui é a que o módulo de fato
    # oferece: resultado igual não importa a ordem de entrada dos vértices
    # (rotação da lista, já que a origem SGL é a média de todos eles).
    rotacionada = _PARCELA_REFERENCIA[2:] + _PARCELA_REFERENCIA[:2]
    resultado_rotacionado = area_sgl(rotacionada)

    assert resultado_rotacionado["area_m2"] == pytest.approx(resultado_normal["area_m2"], abs=1e-3)


def test_area_invariante_ao_sentido_de_percurso():
    resultado_normal = area_sgl(_PARCELA_REFERENCIA)
    resultado_invertido = area_sgl(list(reversed(_PARCELA_REFERENCIA)))

    assert resultado_invertido["area_m2"] == pytest.approx(resultado_normal["area_m2"], abs=1e-3)
    assert resultado_invertido["sentido"] != resultado_normal["sentido"]


def test_distancia_horizontal_desconta_diferenca_de_altitude():
    v1 = (-27.5, -48.5, 100.0)
    v2_mesma_posicao_mas_mais_alto = (-27.5, -48.5, 110.0)

    # mesma posição geodésica, só h diferente — item 9.4 desconta a
    # diferença de altitude, então a distância horizontal deve ser ~0
    assert distancia_horizontal(v1, v2_mesma_posicao_mas_mais_alto) == pytest.approx(0.0, abs=1e-6)


def test_area_recusa_menos_de_3_vertices():
    with pytest.raises(ValueError):
        area_sgl(_PARCELA_REFERENCIA[:2])


def test_area_recusa_vertices_consecutivos_coincidentes():
    vertices = _PARCELA_REFERENCIA[:2] + [_PARCELA_REFERENCIA[1]] + _PARCELA_REFERENCIA[2:]
    with pytest.raises(ValueError):
        area_sgl(vertices)


def test_extensao_grande_emite_aviso():
    # 4 pontos separados por mais de 50 km de longitude
    parcela_grande = [
        (-27.0, -50.0, 100.0),
        (-27.0, -49.0, 100.0),
        (-26.5, -49.0, 100.0),
        (-26.5, -50.0, 100.0),
    ]
    with pytest.warns(UserWarning):
        area_sgl(parcela_grande)


def test_azimute_puissant_nao_implementado_e_explicito():
    from core.sgl import azimute_puissant

    with pytest.raises(NotImplementedError):
        azimute_puissant((-27.5, -48.5, 100.0), (-27.6, -48.6, 100.0))
