"""Testes da aba de Importação persistente (ui_qt/importacao_tab.py):
cada arquivo importado vira uma sub-aba própria dentro da parcela, que
guarda o easting/northing original (se veio de UTM) e sabe recalcular
geodésica e mesclar (de novo, se precisar) na Tabela de Perímetro — ver
CLAUDE.md / mensagem do usuário pedindo essa persistência."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton

from core.parsing import parse_numero
from ui_qt.importacao_tab import AbaImportacao
from ui_qt.tema_qt import carregar_tema

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


def _dominios():
    with (CONFIG_DIR / "dominios.json").open("r", encoding="utf-8") as f:
        return json.load(f)


def _nova_aba(
    qtbot, dados, dados_utm_brutos=None, dados_geodesica_original=None,
    meridiano_inicial=-51.0, hemisferio_inicial="Sul", aplicar_na_parcela=None, remover_esta_aba=None,
):
    dominios = _dominios()
    aplicadas = []
    removidas = []
    aba = AbaImportacao(
        numero=1,
        dados=dados,
        dados_utm_brutos=dados_utm_brutos,
        dados_geodesica_original=dados_geodesica_original,
        meridiano_inicial=meridiano_inicial,
        hemisferio_inicial=hemisferio_inicial,
        meridianos_disponiveis=dominios["meridianos_centrais_brasil"],
        hemisferios_disponiveis=dominios["hemisferio"],
        tema=carregar_tema(),
        aplicar_na_parcela=aplicar_na_parcela or aplicadas.append,
        remover_esta_aba=remover_esta_aba or removidas.append,
    )
    qtbot.addWidget(aba)
    aba._chamadas_aplicar = aplicadas
    aba._chamadas_remover = removidas
    return aba


def _botao(aba, trecho: str) -> QPushButton:
    return next(b for b in aba.findChildren(QPushButton) if trecho in b.text())


def test_usar_chama_aplicar_na_parcela_com_dataframe_atual(qtbot):
    dados = pd.DataFrame({"codigo": ["AJ4-M-001"], "e_long": ["-48,5"], "n_lat": ["-27,5"]})
    aba = _nova_aba(qtbot, dados)

    _botao(aba, "Usar esta versão").click()

    assert len(aba._chamadas_aplicar) == 1
    assert aba._chamadas_aplicar[0].iloc[0]["codigo"] == "AJ4-M-001"
    assert aba._chamadas_remover == []


def test_remover_chama_remover_esta_aba_sem_aplicar(qtbot):
    dados = pd.DataFrame({"codigo": ["AJ4-M-001"], "e_long": ["-48,5"], "n_lat": ["-27,5"]})
    aba = _nova_aba(qtbot, dados)

    _botao(aba, "Remover esta importação").click()

    assert aba._chamadas_remover == [aba]
    assert aba._chamadas_aplicar == []


def test_sem_dados_utm_brutos_nao_mostra_botao_recalcular(qtbot):
    dados = pd.DataFrame({"codigo": ["AJ4-M-001"], "e_long": ["-48,5"], "n_lat": ["-27,5"]})
    aba = _nova_aba(qtbot, dados, dados_utm_brutos=None)

    assert not [b for b in aba.findChildren(QPushButton) if "Recalcular" in b.text()]
    assert not hasattr(aba, "combo_meridiano")


def test_recalcular_usa_meridiano_hemisferio_da_propria_aba_e_usar_propaga_correcao(qtbot):
    dados = pd.DataFrame({"codigo": ["AJ4-M-001"], "e_long": ["-48,5"], "n_lat": ["27,5"]})
    dados_utm_brutos = pd.DataFrame({"e_long": ["500000"], "n_lat": ["7000000"]})
    # hemisfério inicial errado de propósito — igual ao caso real: só se
    # percebe depois de já ter criado a importação.
    aba = _nova_aba(qtbot, dados, dados_utm_brutos=dados_utm_brutos, meridiano_inicial=-51.0, hemisferio_inicial="Norte")

    latitude_errada = aba._dataframe_atual().at[0, "n_lat"]

    aba.combo_hemisferio.setCurrentText("Sul")
    _botao(aba, "Recalcular geodésica").click()

    latitude_corrigida = aba._dataframe_atual().at[0, "n_lat"]
    assert latitude_corrigida != latitude_errada
    assert parse_numero(latitude_corrigida) < 0  # hemisfério Sul: latitude negativa

    _botao(aba, "Usar esta versão").click()
    assert aba._chamadas_aplicar[0].iloc[0]["n_lat"] == latitude_corrigida


def test_mostra_colunas_de_referencia_do_utm_original(qtbot):
    # pedido do usuário: manter visível o easting/northing importado, pra
    # conferência, mesmo depois de já convertido pra grau decimal.
    dados = pd.DataFrame({"codigo": ["AJ4-M-001"], "e_long": ["-48,5"], "n_lat": ["-27,5"]})
    dados_utm_brutos = pd.DataFrame({"e_long": ["500000"], "n_lat": ["7000000"]})
    aba = _nova_aba(qtbot, dados, dados_utm_brutos=dados_utm_brutos)

    rotulos = [aba.tabela.horizontalHeaderItem(c).text() for c in range(aba.tabela.columnCount())]
    assert "UTM E (original)" in rotulos
    assert "UTM N (original)" in rotulos
    col_e = rotulos.index("UTM E (original)")
    assert aba.tabela.item(0, col_e).text() == "500000"
    assert not aba.tabela.item(0, col_e).flags() & Qt.ItemFlag.ItemIsEditable


def test_mostra_colunas_de_referencia_da_geodesica_original_nao_decimal(qtbot):
    dados = pd.DataFrame({"codigo": ["AJ4-M-001"], "e_long": ["-48,5"], "n_lat": ["-27,5"]})
    dados_geo_original = pd.DataFrame({"e_long": ["48 30 00 W"], "n_lat": ["27 30 00 S"]})
    aba = _nova_aba(qtbot, dados, dados_geodesica_original=dados_geo_original)

    rotulos = [aba.tabela.horizontalHeaderItem(c).text() for c in range(aba.tabela.columnCount())]
    assert "E/Long (original)" in rotulos
    assert "N/Lat (original)" in rotulos
    col_n = rotulos.index("N/Lat (original)")
    assert aba.tabela.item(0, col_n).text() == "27 30 00 S"


def test_sem_referencia_nenhuma_nao_adiciona_coluna_extra(qtbot):
    dados = pd.DataFrame({"codigo": ["AJ4-M-001"], "e_long": ["-48,5"], "n_lat": ["-27,5"]})
    aba = _nova_aba(qtbot, dados)

    assert aba.tabela.columnCount() == len(dados.columns)
