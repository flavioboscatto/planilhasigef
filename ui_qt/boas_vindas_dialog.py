"""Tela de abertura (V4) — pede Novo projeto ou Abrir (com atalho pros
últimos projetos usados) antes do usuário começar a preencher, pra reduzir o
risco de trabalhar sem ter definido onde salvar. Modal, mostrada logo depois
da splash (app_qt.py::main).

Fechar sem escolher nada (X/Esc) rejeita o diálogo — decisão explícita do
usuário: nesse caso o app segue com o projeto em branco não salvo, do jeito
que já funcionava antes desta tela existir (ver app_qt.py::main).
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QVBoxLayout,
)


class BoasVindasDialog(QDialog):
    def __init__(self, recentes: list[str], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Planilha SIGEF")
        self.resize(420, 360)
        self._acao: str | None = None
        self._caminho: str | None = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<b>Comece um projeto novo ou continue um já existente:</b>"))

        linha_botoes = QHBoxLayout()
        btn_novo = QPushButton("Novo projeto")
        btn_novo.clicked.connect(self._escolher_novo)
        btn_abrir = QPushButton("Abrir projeto...")
        btn_abrir.clicked.connect(self._escolher_abrir)
        linha_botoes.addWidget(btn_novo)
        linha_botoes.addWidget(btn_abrir)
        layout.addLayout(linha_botoes)

        layout.addWidget(QLabel("Projetos recentes:"))
        self.lista_recentes = QListWidget()
        self.lista_recentes.addItems(recentes)
        self.lista_recentes.itemDoubleClicked.connect(self._abrir_recente)
        layout.addWidget(self.lista_recentes, 1)
        if not recentes:
            self.lista_recentes.setEnabled(False)
            self.lista_recentes.addItem("(nenhum projeto recente ainda)")

    def _escolher_novo(self) -> None:
        self._acao = "novo"
        self.accept()

    def _escolher_abrir(self) -> None:
        caminho, _ = QFileDialog.getOpenFileName(
            self, "Abrir projeto SIGEF", "", "Projeto SIGEF (*.sigefproj);;Todos os arquivos (*.*)"
        )
        if not caminho:
            return
        self._acao = "abrir"
        self._caminho = caminho
        self.accept()

    def _abrir_recente(self, item) -> None:
        caminho = item.text()
        if not Path(caminho).exists():
            return
        self._acao = "abrir"
        self._caminho = caminho
        self.accept()

    def resultado(self) -> tuple[str | None, str | None]:
        return self._acao, self._caminho
