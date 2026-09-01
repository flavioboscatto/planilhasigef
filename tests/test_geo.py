"""Testes de core/geo.py — conversão UTM <-> Geodésica (SIRGAS2000). Sem
teste dedicado até agora; geodesica_para_utm (V3, usada só pra desenhar a
parcela em proporção real) é nova."""
from __future__ import annotations

import pytest

from core.geo import geodesica_para_utm, utm_para_geodesica


def test_geodesica_para_utm_e_volta_bate_com_original():
    # ponto no litoral de SC, hemisfério Sul, meridiano central -51
    longitude_original, latitude_original = -48.5, -27.5
    meridiano_central, hemisferio = -51.0, "Sul"

    easting, northing = geodesica_para_utm(longitude_original, latitude_original, meridiano_central, hemisferio)
    longitude_volta, latitude_volta = utm_para_geodesica(easting, northing, meridiano_central, hemisferio)

    assert longitude_volta == pytest.approx(longitude_original, abs=1e-6)
    assert latitude_volta == pytest.approx(latitude_original, abs=1e-6)


def test_geodesica_para_utm_no_hemisferio_norte():
    easting, northing = geodesica_para_utm(-51.0, 2.0, -51.0, "Norte")
    longitude_volta, latitude_volta = utm_para_geodesica(easting, northing, -51.0, "Norte")

    assert longitude_volta == pytest.approx(-51.0, abs=1e-6)
    assert latitude_volta == pytest.approx(2.0, abs=1e-6)


def test_easting_northing_tem_ordem_de_grandeza_de_metros_utm():
    # ponto perto do meridiano central -> easting perto de 500000 (falso
    # easting padrão UTM); longe do equador -> northing na casa dos milhões
    easting, northing = geodesica_para_utm(-51.0, -27.5, -51.0, "Sul")

    assert 400000 < easting < 600000
    assert northing > 1_000_000
