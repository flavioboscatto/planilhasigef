"""Diálogo "Remover parcela" (V4) — lista todas as parcelas abertas com
caixa de marcação, permitindo remover uma ou várias de uma vez. Substitui o
antigo botão "Remover última parcela" (app_qt.py), que só deixava tirar a
parcela mais recente.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
)


class RemoverParcelaDialog(QDialog):
    def __init__(self, nomes_parcelas: list[str], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Remover parcela")
        self.resize(360, 320)

        layout = QVBoxLayout(self)
        self.lista = QListWidget()
        for nome in nomes_parcelas:
            item = QListWidgetItem(nome)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.lista.addItem(item)
        layout.addWidget(self.lista)

        botoes = QDialogButtonBox()
        botao_remover = botoes.addButton("Remover selecionadas", QDialogButtonBox.ButtonRole.AcceptRole)
        botoes.addButton("Cancelar", QDialogButtonBox.ButtonRole.RejectRole)
        botao_remover.clicked.connect(self.accept)
        botoes.rejected.connect(self.reject)
        layout.addWidget(botoes)

    def indices_selecionados(self) -> list[int]:
        return [i for i in range(self.lista.count()) if self.lista.item(i).checkState() == Qt.CheckState.Checked]
