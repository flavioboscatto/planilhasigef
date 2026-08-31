"""Testes da Fase 6 (painel de numeração): renumerar entre parcelas,
respeitar "Renumerar?", e o botão Atualizar (só o Tipo)."""
from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox

from ui_qt.perimetro_tab import AbaPerimetro
from ui_qt.renumeracao_panel import PainelNumeracao
from ui_qt.tema_qt import carregar_tema

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


def _dominios():
    with (CONFIG_DIR / "dominios.json").open("r", encoding="utf-8") as f:
        return json.load(f)


def _nova_aba(indice: int, qtbot) -> AbaPerimetro:
    aba = AbaPerimetro(indice, _dominios(), carregar_tema())
    qtbot.addWidget(aba)
    return aba


def _silenciar_message_box(monkeypatch) -> None:
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)


def test_renumerar_atribui_codigo_e_avanca_contador_entre_parcelas(qtbot, monkeypatch):
    _silenciar_message_box(monkeypatch)
    aba1 = _nova_aba(1, qtbot)
    aba2 = _nova_aba(2, qtbot)

    aba1.modelo_tabela.setData(aba1.modelo_tabela.index(0, 2), "X", 2)
    aba1.modelo_tabela.setData(aba1.modelo_tabela.index(0, 1), "M", 2)
    aba2.modelo_tabela.setData(aba2.modelo_tabela.index(0, 2), "Y", 2)
    aba2.modelo_tabela.setData(aba2.modelo_tabela.index(0, 1), "M", 2)

    painel = PainelNumeracao(_dominios(), lambda: [aba1, aba2])
    qtbot.addWidget(painel)
    painel.campo_credenciado.setText("ajq")

    painel._renumerar()

    assert aba1.modelo_tabela.dataframe().at[0, "codigo"] == "AJQ-M-001"
    assert aba2.modelo_tabela.dataframe().at[0, "codigo"] == "AJQ-M-002"
    assert painel._campos_numero["M"].text() == "003"


def test_renumerar_sem_credenciado_avisa_e_nao_altera(qtbot, monkeypatch):
    avisos = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: avisos.append(a))
    aba = _nova_aba(1, qtbot)
    aba.modelo_tabela.setData(aba.modelo_tabela.index(0, 2), "X", 2)

    painel = PainelNumeracao(_dominios(), lambda: [aba])
    qtbot.addWidget(painel)

    painel._renumerar()

    assert avisos
    assert aba.modelo_tabela.dataframe().at[0, "codigo"] == "X"


def test_linha_desmarcada_nao_e_renumerada(qtbot, monkeypatch):
    _silenciar_message_box(monkeypatch)
    aba = _nova_aba(1, qtbot)
    aba.modelo_tabela.setData(aba.modelo_tabela.index(0, 2), "X", 2)
    aba.modelo_tabela.setData(aba.modelo_tabela.index(0, 1), "M", 2)
    aba.modelo_tabela.setData(aba.modelo_tabela.index(0, 0), Qt.CheckState.Unchecked, Qt.ItemDataRole.CheckStateRole)

    painel = PainelNumeracao(_dominios(), lambda: [aba])
    qtbot.addWidget(painel)
    painel.campo_credenciado.setText("AJQ")

    painel._renumerar()

    assert aba.modelo_tabela.dataframe().at[0, "codigo"] == "X"


def test_atualizar_tipos_reescreve_so_o_segmento_de_tipo(qtbot, monkeypatch):
    _silenciar_message_box(monkeypatch)
    aba = _nova_aba(1, qtbot)
    aba.modelo_tabela.setData(aba.modelo_tabela.index(0, 2), "AJQ-M-001", 2)
    aba.modelo_tabela.setData(aba.modelo_tabela.index(0, 1), "P", 2)

    painel = PainelNumeracao(_dominios(), lambda: [aba])
    qtbot.addWidget(painel)

    painel._atualizar_tipos()

    assert aba.modelo_tabela.dataframe().at[0, "codigo"] == "AJQ-P-001"


def test_formato_do_numero_afeta_largura_do_zero_a_esquerda(qtbot, monkeypatch):
    _silenciar_message_box(monkeypatch)
    aba = _nova_aba(1, qtbot)
    aba.modelo_tabela.setData(aba.modelo_tabela.index(0, 2), "X", 2)
    aba.modelo_tabela.setData(aba.modelo_tabela.index(0, 1), "M", 2)

    painel = PainelNumeracao(_dominios(), lambda: [aba])
    qtbot.addWidget(painel)
    painel.campo_credenciado.setText("AJQ")
    painel.combo_formato.setCurrentText("00001")
    painel._campos_numero["M"].setText("1")

    painel._renumerar()

    assert aba.modelo_tabela.dataframe().at[0, "codigo"] == "AJQ-M-00001"
