"""Entrypoint da versão desktop nativo (PySide6) do Gerador de Planilha
SIGEF — ver plano de migração (~/.claude/plans, ou peça pro Claude
recuperar) para o roteiro completo por fases.

Fase 1: só o esqueleto — janela principal, menu, abas reais (Identificação
+ parcelas) que trocam sem perder estado (diferente do Streamlit, um
QWidget de aba fica vivo em memória o tempo todo, não é recriado a cada
clique). Conteúdo de cada aba ainda vem nas próximas fases.

Constrói ao lado de app.py (Streamlit) sem tocar nele — as duas versões
convivem até a migração terminar.
"""
from __future__ import annotations

import sys

from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QMessageBox,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)


class JanelaPrincipal(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Gerador de Planilha SIGEF")
        self.resize(1100, 800)

        self._proxima_parcela = 1

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
        # placeholder — Fase 2 troca por ui_qt/identificacao_tab.py
        conteudo = QWidget()
        layout = QVBoxLayout(conteudo)
        layout.addWidget(QLabel("Identificação (em construção — Fase 2)"))
        self.abas.addTab(conteudo, "Identificação")

    def _adicionar_aba_parcela(self) -> None:
        indice = self._proxima_parcela
        self._proxima_parcela += 1
        # placeholder — Fase 4 troca por ui_qt/perimetro_tab.py
        conteudo = QWidget()
        layout = QVBoxLayout(conteudo)
        layout.addWidget(QLabel(f"Parcela {indice} (em construção — Fase 4)"))
        self.abas.addTab(conteudo, f"Parcela {indice}")
        self.abas.setCurrentWidget(conteudo)

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
