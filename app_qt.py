"""Entrypoint da versão desktop nativo (PySide6) do Gerador de Planilha
SIGEF.

Janela principal, menu, abas reais (Identificação + parcelas) que trocam
sem perder estado — um QWidget de aba fica vivo em memória o tempo todo,
não é recriado a cada clique.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from core import exportacao_txt, ods_writer, relatorio_docx
from core.projeto import ProjetoInvalidoError, desserializar, serializar
from core.template_loader import load_template
from ui_qt.estilo_qt import FOLHA_DE_ESTILO
from ui_qt.identificacao_tab import AbaIdentificacao
from ui_qt.perimetro_tab import AbaPerimetro
from ui_qt.projeto_qt import aplicar_projeto, montar_projeto
from ui_qt.relatorio_qt import montar_dados_relatorio
from ui_qt.renumeracao_panel import PainelNumeracao
from ui_qt.tema_qt import carregar_tema

CONFIG_DIR = Path(__file__).resolve().parent / "config"
ICONE_APP = Path(__file__).resolve().parent / "assets" / "icone_app.ico"
TITULO_APP = "Planilha SIGEF por Prof. Flavio Boscatto - IFSC"


def _carregar_json(nome_arquivo: str):
    with (CONFIG_DIR / nome_arquivo).open("r", encoding="utf-8") as f:
        return json.load(f)


class JanelaPrincipal(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(TITULO_APP)
        self.resize(1100, 800)

        self._proxima_parcela = 1
        self.nome_projeto = ""
        self.caminho_projeto: str | None = None
        self.dominios = _carregar_json("dominios.json")
        self.municipios = _carregar_json("municipios.json")
        self.tema = carregar_tema()

        # faixa horizontal (Numeração) acima das abas, não dock lateral —
        # Proposta A da comparação de layouts: a grade de vértices fica com
        # 100% da largura da janela, e Renumerar/Atualizar continuam a um
        # clique, sem disputar espaço nem exigir trocar de aba.
        self.abas = QTabWidget()
        self.painel_numeracao = PainelNumeracao(
            self.dominios, self._abas_perimetro, self._aba_perimetro_atual, self.tema
        )
        # os botões de exportação moram no painel (espaço compartilhado,
        # acima das abas), mas quem sabe gerar o arquivo é a janela — tem a
        # Identificação, o diálogo de salvar e todas as parcelas.
        self.painel_numeracao.btn_exportar_planilha.clicked.connect(self._gerar_planilha)
        self.painel_numeracao.btn_exportar_txt.clicked.connect(self._exportar_txt)
        self.painel_numeracao.btn_gerar_relatorio.clicked.connect(self._gerar_relatorio)

        central = QWidget()
        layout_central = QVBoxLayout(central)
        layout_central.setContentsMargins(0, 0, 0, 0)
        layout_central.setSpacing(0)
        layout_central.addWidget(self.painel_numeracao)
        layout_central.addWidget(self.abas)
        self.setCentralWidget(central)

        self._criar_menu()
        self._criar_barra_ferramentas()

        self._adicionar_aba_identificacao()
        self._adicionar_aba_parcela()

    def _abas_perimetro(self) -> list[AbaPerimetro]:
        return [self.abas.widget(i) for i in range(1, self.abas.count())]

    def _aba_perimetro_atual(self) -> AbaPerimetro | None:
        widget = self.abas.currentWidget()
        return widget if isinstance(widget, AbaPerimetro) else None

    def _criar_menu(self) -> None:
        menu_arquivo = self.menuBar().addMenu("&Arquivo")

        acao_novo = menu_arquivo.addAction("Novo projeto")
        acao_novo.triggered.connect(self._novo_projeto)

        acao_abrir = menu_arquivo.addAction("Abrir...")
        acao_abrir.triggered.connect(self._abrir_projeto)

        menu_arquivo.addSeparator()

        acao_salvar = menu_arquivo.addAction("Salvar")
        acao_salvar.triggered.connect(self._salvar_projeto)

        acao_salvar_como = menu_arquivo.addAction("Salvar como...")
        acao_salvar_como.triggered.connect(self._salvar_projeto_como)

        menu_arquivo.addSeparator()

        acao_gerar = menu_arquivo.addAction("Gerar planilha SIGEF (.ods)...")
        acao_gerar.triggered.connect(self._gerar_planilha)

        acao_exportar_txt = menu_arquivo.addAction("Exportar Tabela SIGEF em TXT...")
        acao_exportar_txt.triggered.connect(self._exportar_txt)

        acao_relatorio = menu_arquivo.addAction("Gerar Relatório em DOCX...")
        acao_relatorio.triggered.connect(self._gerar_relatorio)

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
        aba = AbaPerimetro(indice, self.dominios, self.tema, self.painel_numeracao)
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

    def _gerar_planilha(self) -> None:
        identificacao = self.aba_identificacao.modelo()
        perimetros = [aba.modelo() for aba in self._abas_perimetro()]
        try:
            saida = ods_writer.write(identificacao, perimetros, load_template())
        except Exception as exc:  # noqa: BLE001 — qualquer falha de geração vira mensagem, não crash
            QMessageBox.critical(self, "Gerar planilha", f"Não consegui gerar a planilha: {exc}")
            return

        caminho, _ = QFileDialog.getSaveFileName(
            self, "Salvar planilha SIGEF", "sigef_gerado.ods", "Planilha ODS (*.ods);;Todos os arquivos (*.*)"
        )
        if not caminho:
            return
        try:
            Path(caminho).write_bytes(saida)
        except OSError as exc:
            QMessageBox.critical(self, "Gerar planilha", f"Não consegui salvar em {caminho}: {exc}")
            return
        QMessageBox.information(
            self, "Gerar planilha",
            f"Planilha gerada ({len(saida)} bytes) em {caminho}.\nConfira no LibreOffice com F3.",
        )

    def _exportar_txt(self) -> None:
        perimetros = [aba.modelo() for aba in self._abas_perimetro()]
        saida = exportacao_txt.gerar_txt(perimetros, self.dominios["limites_coordenadas"])

        caminho, _ = QFileDialog.getSaveFileName(
            self, "Exportar Tabela SIGEF em TXT", "tabela_sigef.txt", "Texto (*.txt);;Todos os arquivos (*.*)"
        )
        if not caminho:
            return
        try:
            Path(caminho).write_text(saida, encoding="utf-8")
        except OSError as exc:
            QMessageBox.critical(self, "Exportar TXT", f"Não consegui salvar em {caminho}: {exc}")
            return
        QMessageBox.information(self, "Exportar TXT", f"Tabela exportada em {caminho}.")

    def _gerar_relatorio(self) -> None:
        identificacao = self.aba_identificacao.modelo()
        parcelas = montar_dados_relatorio(self)
        try:
            saida = relatorio_docx.gerar_relatorio(identificacao, parcelas, self.dominios["limites_coordenadas"])
        except Exception as exc:  # noqa: BLE001 — qualquer falha de geração vira mensagem, não crash
            QMessageBox.critical(self, "Gerar relatório", f"Não consegui gerar o relatório: {exc}")
            return

        caminho, _ = QFileDialog.getSaveFileName(
            self, "Salvar relatório", "relatorio_sigef.docx", "Documento Word (*.docx);;Todos os arquivos (*.*)"
        )
        if not caminho:
            return
        try:
            Path(caminho).write_bytes(saida)
        except OSError as exc:
            QMessageBox.critical(self, "Gerar relatório", f"Não consegui salvar em {caminho}: {exc}")
            return
        QMessageBox.information(self, "Gerar relatório", f"Relatório gerado em {caminho}.")

    def _atualizar_titulo(self) -> None:
        nome = Path(self.caminho_projeto).name if self.caminho_projeto else "sem arquivo salvo"
        self.setWindowTitle(f"{TITULO_APP} — {nome}")

    def _novo_projeto(self) -> None:
        resposta = QMessageBox.question(
            self, "Novo projeto",
            "Isso substitui tudo o que está preenchido agora, sem salvar antes. Continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if resposta != QMessageBox.StandardButton.Yes:
            return
        aplicar_projeto(self, {"identificacao": {}, "num_parcelas": 1, "parcelas": [{"vertices": []}], "numeracao": {}})
        self.caminho_projeto = None
        self._atualizar_titulo()
        # já pergunta onde salvar, igual ao "Criar projeto" da versão web —
        # se cancelar, o projeto (em branco) continua, só sem lugar salvo
        # ainda (dá pra usar Salvar/Salvar como depois).
        self._salvar_projeto_como()

    def _abrir_projeto(self) -> None:
        caminho, _ = QFileDialog.getOpenFileName(
            self, "Abrir projeto SIGEF", "", "Projeto SIGEF (*.sigefproj);;Todos os arquivos (*.*)"
        )
        if not caminho:
            return
        try:
            dados = desserializar(Path(caminho).read_bytes())
        except (ProjetoInvalidoError, OSError) as exc:
            QMessageBox.critical(self, "Abrir projeto", f"Não consegui abrir {caminho}: {exc}")
            return
        aplicar_projeto(self, dados)
        self.caminho_projeto = caminho
        self._atualizar_titulo()

    def _salvar_projeto(self) -> None:
        if not self.caminho_projeto:
            self._salvar_projeto_como()
            return
        try:
            Path(self.caminho_projeto).write_bytes(serializar(montar_projeto(self)))
        except OSError as exc:
            QMessageBox.critical(self, "Salvar projeto", f"Não consegui salvar em {self.caminho_projeto}: {exc}")
            return
        self.statusBar().showMessage(f"Projeto salvo em {self.caminho_projeto}", 5000)

    def _salvar_projeto_como(self) -> None:
        sugestao = f"{self.nome_projeto or 'projeto_sigef'}.sigefproj"
        caminho, _ = QFileDialog.getSaveFileName(
            self, "Salvar projeto SIGEF como", sugestao, "Projeto SIGEF (*.sigefproj);;Todos os arquivos (*.*)"
        )
        if not caminho:
            return
        self.nome_projeto = Path(caminho).stem
        self.caminho_projeto = caminho
        try:
            Path(caminho).write_bytes(serializar(montar_projeto(self)))
        except OSError as exc:
            QMessageBox.critical(self, "Salvar projeto", f"Não consegui salvar em {caminho}: {exc}")
            return
        self._atualizar_titulo()


def main() -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    # Fusion, não o estilo nativo do Windows: o nativo ignora várias regras
    # de QSS (a borda de foco, principalmente) — era por isso que o campo
    # de texto ficava sem contraste, só um traço fino ao focar.
    app.setStyle("Fusion")
    app.setStyleSheet(FOLHA_DE_ESTILO)
    if ICONE_APP.exists():
        # setWindowIcon na QApplication vale pra toda janela sem ícone
        # próprio (barra de título, barra de tarefas, Alt+Tab) — o ícone do
        # próprio .exe (sigef_qt.spec: icon=...) só cobre o Explorer, não a
        # janela em si.
        app.setWindowIcon(QIcon(str(ICONE_APP)))
    janela = JanelaPrincipal()
    janela.showMaximized()  # aproveita a largura toda — motivo real da Proposta A
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
