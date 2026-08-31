"""Testes da Fase 3 (grade de vértices) — cobrem exatamente os bugs que
motivaram a migração do Streamlit: checkbox que não marcava de primeira,
colar em bloco que engolia a primeira tentativa, célula que se perdia.
Aqui tudo é síncrono (sem rerun), então cada operação testada precisa
funcionar sempre, não "às vezes"."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication

from core.tabela_vertices import tabela_vazia
from ui_qt.tema_qt import carregar_tema
from ui_qt.vertices_table import TabelaVerticesModel, TabelaVerticesView

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


def _dominios():
    with (CONFIG_DIR / "dominios.json").open("r", encoding="utf-8") as f:
        return json.load(f)


def _nova_view(df: pd.DataFrame | None = None) -> TabelaVerticesView:
    dominios = _dominios()
    tema = carregar_tema()
    modelo = TabelaVerticesModel(
        tema=tema,
        opcoes_tipo_vertice=[t["codigo"] for t in dominios["tipos_vertice"]],
        opcoes_metodo=[m["codigo"] for m in dominios["metodos_posicionamento"]],
        opcoes_limite=[t["codigo"] for t in dominios["tipos_limite"]],
        df=df,
    )
    return TabelaVerticesView(modelo)


def test_grade_comeca_com_tres_linhas_e_renumerar_marcado(qtbot):
    view = _nova_view()
    qtbot.addWidget(view)
    modelo = view.model()

    assert modelo.rowCount() == 3
    for linha in range(3):
        indice = modelo.index(linha, 0)
        assert modelo.data(indice, Qt.ItemDataRole.CheckStateRole) == Qt.CheckState.Checked


def test_desmarcar_checkbox_renumerar_sempre_pega(qtbot):
    view = _nova_view()
    qtbot.addWidget(view)
    modelo = view.model()
    indice = modelo.index(0, 0)

    modelo.setData(indice, Qt.CheckState.Unchecked, Qt.ItemDataRole.CheckStateRole)

    assert modelo.data(indice, Qt.ItemDataRole.CheckStateRole) == Qt.CheckState.Unchecked
    assert bool(modelo.dataframe().at[0, "renumerar"]) is False


def test_digitar_codigo_reflete_no_dataframe(qtbot):
    view = _nova_view()
    qtbot.addWidget(view)
    modelo = view.model()
    coluna_codigo = modelo.dataframe().columns.get_loc("codigo")

    modelo.setData(modelo.index(0, coluna_codigo), "AJ4-M-9121", Qt.ItemDataRole.EditRole)

    assert modelo.dataframe().at[0, "codigo"] == "AJ4-M-9121"


def test_colar_bloco_preenche_varias_celulas_de_uma_vez(qtbot):
    view = _nova_view()
    qtbot.addWidget(view)
    modelo = view.model()
    col_codigo = modelo.dataframe().columns.get_loc("codigo")
    col_elong = modelo.dataframe().columns.get_loc("e_long")

    bloco = "AJ4-M-001\t-48,50\nAJ4-M-002\t-48,51\nAJ4-M-003\t-48,52"
    QGuiApplication.clipboard().setText(bloco)
    view.setCurrentIndex(modelo.index(0, col_codigo))

    view._colar()

    df = modelo.dataframe()
    assert list(df["codigo"]) == ["AJ4-M-001", "AJ4-M-002", "AJ4-M-003"]
    assert df.at[0, "e_long"] == "-48,50"
    assert df.at[2, "e_long"] == "-48,52"


def test_preencher_para_baixo_copia_valor_do_topo_da_selecao(qtbot):
    view = _nova_view()
    qtbot.addWidget(view)
    modelo = view.model()
    col_metodo = modelo.dataframe().columns.get_loc("metodo_posicionamento")
    modelo.setData(modelo.index(0, col_metodo), "GPS/GNSS", Qt.ItemDataRole.EditRole)

    selecao = view.selectionModel()
    for linha in range(3):
        selecao.select(
            modelo.index(linha, col_metodo),
            selecao.SelectionFlag.Select,
        )

    view._preencher_para_baixo()

    df = modelo.dataframe()
    assert list(df["metodo_posicionamento"]) == ["GPS/GNSS", "GPS/GNSS", "GPS/GNSS"]


def test_cores_por_grupo_de_coluna_batem_com_o_tema_oficial(qtbot):
    view = _nova_view()
    qtbot.addWidget(view)
    modelo = view.model()
    df = modelo.dataframe()
    tema = carregar_tema()

    col_codigo = df.columns.get_loc("codigo")
    col_cns = df.columns.get_loc("cns")

    cor_geral = modelo.data(modelo.index(0, col_codigo), Qt.ItemDataRole.BackgroundRole)
    cor_confrontante = modelo.data(modelo.index(0, col_cns), Qt.ItemDataRole.BackgroundRole)

    assert cor_geral.name() == tema["tabela_entrada_geral"].fundo.name()
    assert cor_confrontante.name() == tema["tabela_entrada_confrontante"].fundo.name()


def test_definir_coluna_preenche_todas_as_linhas(qtbot):
    view = _nova_view()
    qtbot.addWidget(view)
    modelo = view.model()

    modelo.definir_coluna("tipo_limite", "CO")

    assert list(modelo.dataframe()["tipo_limite"]) == ["CO", "CO", "CO"]


def test_inserir_e_remover_linha(qtbot):
    view = _nova_view()
    qtbot.addWidget(view)
    modelo = view.model()

    modelo.inserir_linha({"codigo": "NOVO-1"})
    assert modelo.rowCount() == 4
    assert modelo.dataframe().at[3, "codigo"] == "NOVO-1"

    modelo.remover_linhas([3])
    assert modelo.rowCount() == 3


def test_substituir_dataframe_inteiro():
    tema = carregar_tema()
    dominios = _dominios()
    modelo = TabelaVerticesModel(
        tema=tema,
        opcoes_tipo_vertice=[t["codigo"] for t in dominios["tipos_vertice"]],
        opcoes_metodo=[m["codigo"] for m in dominios["metodos_posicionamento"]],
        opcoes_limite=[t["codigo"] for t in dominios["tipos_limite"]],
    )
    nova = tabela_vazia(5)
    nova.at[0, "codigo"] = "X-1"

    modelo.substituir(nova)

    assert modelo.rowCount() == 5
    assert modelo.dataframe().at[0, "codigo"] == "X-1"
