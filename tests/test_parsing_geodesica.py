"""Testes dos parsers de coordenada geodésica (core/parsing.py) — cada
formato que o diálogo de importação oferece (ui_qt/importar_vertices_dialog.py
::_PARSERS_GEODESICA) precisa converter certo isoladamente, antes de entrar
no fluxo de importação inteiro (coberto em test_importar_vertices_dialog.py)."""
from __future__ import annotations

import pytest

from core.parsing import ValorInvalidoError, parse_geodesica_grau_minuto


def test_grau_minuto_decimal_com_virgula_e_sufixo_sul():
    valor = parse_geodesica_grau_minuto("27 30,500 S")
    assert valor == pytest.approx(-(27 + 30.5 / 60))


def test_grau_minuto_decimal_com_ponto_e_simbolo_de_grau():
    valor = parse_geodesica_grau_minuto("27°30.5'S")
    assert valor == pytest.approx(-(27 + 30.5 / 60))


def test_grau_minuto_decimal_sem_sufixo_respeita_sinal_do_grau():
    valor = parse_geodesica_grau_minuto("-48 30,0")
    assert valor == pytest.approx(-(48 + 30 / 60))


def test_grau_minuto_decimal_sufixo_norte_ou_leste_fica_positivo():
    assert parse_geodesica_grau_minuto("27 30,5 N") > 0
    assert parse_geodesica_grau_minuto("48 30,0 E") > 0


def test_grau_minuto_decimal_vazio_e_zero():
    assert parse_geodesica_grau_minuto("") == 0.0


def test_grau_minuto_decimal_com_segundos_nao_e_aceito():
    # isto é GMS completo, não grau+minuto — tem que cair no parser certo
    with pytest.raises(ValorInvalidoError):
        parse_geodesica_grau_minuto("27 30 30 S")
