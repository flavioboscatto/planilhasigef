"""Entrypoint da versão desktop nativo (PySide6) do Gerador de Planilha
SIGEF — ver plano de migração (~/.claude/plans, ou peça pro Claude
recuperar) para o roteiro completo por fases.

Janela principal, menu, abas reais (Identificação + parcelas) que trocam
sem perder estado — diferente do Streamlit, um QWidget de aba fica vivo em
memória o tempo todo, não é recriado a cada clique. Menu Arquivo
(Novo/Abrir/Salvar/Gerar planilha) ainda não ligado a nada de verdade
(Fase 7/8).

Constrói ao lado de app.py (Streamlit) sem tocar nele — as duas versões
convivem até a migração terminar.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QMessageBox,
    QTabWidget,
    QToolBar,
)

from ui_qt.identificacao_tab import AbaIdentificacao
from ui_qt.perimetro_tab import AbaPerimetro
from ui_qt.tema_qt import carregar_tema

CONFIG_DIR = Path(__file__).resolve().parent / "config"


def _carregar_json(nome_arquivo: str):
    with (CONFIG_DIR / nome_arquivo).open("r", encoding="utf-8") as f:
        return json.load(f)


class JanelaPrincipal(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Gerador de Planilha SIGEF")
        self.resize(1100, 800)

        self._proxima_parcela = 1
        self.dominios = _carregar_json("dominios.json")
        self.municipios = _carregar_json("municipios.json")
        self.tema = carregar_tema()

        self.abas = QTabWidget()
        self.setCentralWidget(self.abas)

        self._criar_menu()
        self._criar_barra_ferramentas()

        self._adicionar_aba_identificacao()
        self._adicionar_aba_parcela()

    def _criar_menu(self) -> None:
        menu_arquivo = self.menuBar().addMenu("&Arquivo")

        acao_novo = menu_arquivo.addAction("Novo projeto")
        acao_novo.triggered.connect(self._nao_implementado)

        acao_abrir = menu_arquivo.addAction("Abrir...")
        acao_abrir.triggered.connect(self._nao_implementado)

        menu_arquivo.addSeparator()

        acao_salvar = menu_arquivo.addAction("Salvar")
        acao_salvar.triggered.connect(self._nao_implementado)

        acao_salvar_como = menu_arquivo.addAction("Salvar como...")
        acao_salvar_como.triggered.connect(self._nao_implementado)

        menu_arquivo.addSeparator()

        acao_gerar = menu_arquivo.addAction("Gerar planilha SIGEF (.ods)...")
        acao_gerar.triggered.connect(self._nao_implementado)

        menu_arquivo.addSeparator()

        acao_sair = menu_arquivo.addAction("Sair")
        acao_sair.triggered.connect(self.close)

    def _criar_barra_ferramentas(self) -> None:
        barra = QToolBar("Parcelas")
        barra.setMovable(False)
        self.addToolBar(barra)

        acao_adicionar = barra.addAction("+ Adicionar parcela")
        acao_adicionar.triggered.connect(self._adicionar_aba_parcela)

        acao_remover = barra.addAction("- Remover última parcela")
        acao_remover.triggered.connect(self._remover_ultima_parcela)

    def _adicionar_aba_identificacao(self) -> None:
        self.aba_identificacao = AbaIdentificacao(self.dominios, self.municipios, self.tema)
        self.abas.addTab(self.aba_identificacao, "Identificação")

    def _adicionar_aba_parcela(self) -> None:
        indice = self._proxima_parcela
        self._proxima_parcela += 1
        aba = AbaPerimetro(indice, self.dominios, self.tema)
        self.abas.addTab(aba, f"Parcela {indice}")
        self.abas.setCurrentWidget(aba)

    def _remover_ultima_parcela(self) -> None:
        # índice 0 é sempre a aba Identificação — só remove se sobrar
        # pelo menos uma parcela, igual à regra do app.py atual
        if self.abas.count() <= 2:
            return
        ultimo_indice = self.abas.count() - 1
        widget = self.abas.widget(ultimo_indice)
        self.abas.removeTab(ultimo_indice)
        widget.deleteLater()

    def _nao_implementado(self) -> None:
        QMessageBox.information(self, "Em construção", "Esta ação chega numa fase futura da migração.")


def main() -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    janela = JanelaPrincipal()
    janela.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
