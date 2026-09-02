"""Testes de ui_qt/remover_parcela_dialog.py (V4): lista de parcelas com
caixa de marcação, permitindo remover uma ou várias de uma vez."""
from __future__ import annotations

from PySide6.QtCore import Qt

from ui_qt.remover_parcela_dialog import RemoverParcelaDialog


def test_lista_uma_linha_por_parcela(qtbot):
    dialogo = RemoverParcelaDialog(["Parcela 1", "Parcela 2", "Parcela 3"])
    qtbot.addWidget(dialogo)

    assert dialogo.lista.count() == 3
    assert dialogo.lista.item(1).text() == "Parcela 2"


def test_nenhuma_marcada_por_padrao(qtbot):
    dialogo = RemoverParcelaDialog(["Parcela 1", "Parcela 2"])
    qtbot.addWidget(dialogo)

    assert dialogo.indices_selecionados() == []


def test_indices_selecionados_reflete_as_caixas_marcadas(qtbot):
    dialogo = RemoverParcelaDialog(["Parcela 1", "Parcela 2", "Parcela 3"])
    qtbot.addWidget(dialogo)

    dialogo.lista.item(0).setCheckState(Qt.CheckState.Checked)
    dialogo.lista.item(2).setCheckState(Qt.CheckState.Checked)

    assert dialogo.indices_selecionados() == [0, 2]
