"""Entrypoint da versão desktop nativo (PySide6) do Gerador de Planilha
SIGEF.

Janela principal, menu, abas reais (Identificação + parcelas) que trocam
sem perder estado — um QWidget de aba fica vivo em memória o tempo todo,
não é recriado a cada clique.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QInputDialog,
    QMainWindow,
    QMenu,
    QMessageBox,
    QSplashScreen,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core import exportacao_txt, ods_writer, relatorio_docx
from core.projeto import ProjetoInvalidoError, desserializar, serializar
from core.template_loader import load_template
from ui_qt.boas_vindas_dialog import BoasVindasDialog
from ui_qt.estilo_qt import FOLHA_DE_ESTILO
from ui_qt.identificacao_tab import AbaIdentificacao
from ui_qt.perimetro_tab import AbaPerimetro
from ui_qt.preferencias_qt import obter_recentes, registrar_recente
from ui_qt.projeto_qt import aplicar_projeto, montar_projeto
from ui_qt.relatorio_qt import montar_dados_relatorio
from ui_qt.remover_parcela_dialog import RemoverParcelaDialog
from ui_qt.renumeracao_panel import PainelNumeracao
from ui_qt.tema_qt import carregar_tema

CONFIG_DIR = Path(__file__).resolve().parent / "config"
ICONE_APP = Path(__file__).resolve().parent / "assets" / "icone_app.ico"
ABERTURA_PNG = Path(__file__).resolve().parent / "assets" / "abertura.png"
TITULO_APP = "Planilha SIGEF por Prof. Flavio Boscatto - IFSC"
_DURACAO_MINIMA_ABERTURA_MS = 3000


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
        # Adicionar/Remover parcela: quem sabe montar/desmontar aba é a
        # janela (tem self.abas), o painel só expõe o botão — mesmo padrão
        # dos 3 acima.
        self.painel_numeracao.btn_adicionar_parcela.clicked.connect(self._adicionar_aba_parcela_com_prompt)
        self.painel_numeracao.btn_remover_parcela.clicked.connect(self._abrir_dialogo_remover_parcela)

        central = QWidget()
        layout_central = QVBoxLayout(central)
        layout_central.setContentsMargins(0, 0, 0, 0)
        layout_central.setSpacing(0)
        layout_central.addWidget(self.painel_numeracao)
        layout_central.addWidget(self.abas)
        self.setCentralWidget(central)

        # arrastar aba pra reordenar parcela (V4) — Identificação (índice 0)
        # fica travada em primeiro, ver _impedir_mover_identificacao.
        self.abas.tabBar().setMovable(True)
        self.abas.tabBar().tabMoved.connect(self._impedir_mover_identificacao)
        # clique direito na aba de parcela: renomear/remover só essa (V4) —
        # Identificação não ganha menu (tratado dentro do handler).
        self.abas.tabBar().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.abas.tabBar().customContextMenuRequested.connect(self._menu_contexto_aba)

        self._criar_menu()

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

    def _adicionar_aba_identificacao(self) -> None:
        self.aba_identificacao = AbaIdentificacao(self.dominios, self.municipios, self.tema)
        self.abas.addTab(self.aba_identificacao, "Identificação")

    def _adicionar_aba_parcela(self, nome: str | None = None) -> None:
        indice = self._proxima_parcela
        self._proxima_parcela += 1
        aba = AbaPerimetro(indice, self.dominios, self.tema, self.painel_numeracao)
        self.abas.addTab(aba, nome or f"Parcela {indice}")
        self.abas.setCurrentWidget(aba)

    def _adicionar_aba_parcela_com_prompt(self) -> None:
        sugestao = f"Parcela {self._proxima_parcela}"
        nome, ok = QInputDialog.getText(self, "Adicionar parcela", "Nome da parcela:", text=sugestao)
        if not ok:
            return
        self._adicionar_aba_parcela(nome.strip() or sugestao)

    def _remover_parcelas(self, indices: list[int]) -> None:
        # do maior índice pro menor, senão remover um invalida os índices
        # dos que ainda faltam remover. índice 0 (Identificação) nunca
        # entra em `indices` — quem chama já garante isso.
        for indice in sorted(indices, reverse=True):
            if self.abas.count() <= 2:  # sempre sobra Identificação + 1 parcela
                break
            widget = self.abas.widget(indice)
            self.abas.removeTab(indice)
            widget.deleteLater()

    def _abrir_dialogo_remover_parcela(self) -> None:
        nomes = [self.abas.tabText(i) for i in range(1, self.abas.count())]
        if not nomes:
            return
        dialogo = RemoverParcelaDialog(nomes, parent=self)
        if dialogo.exec() != QDialog.DialogCode.Accepted:
            return
        selecionados = dialogo.indices_selecionados()
        if not selecionados:
            return
        if len(selecionados) >= len(nomes):
            QMessageBox.warning(self, "Remover parcela", "Pelo menos uma parcela precisa continuar existindo.")
            return
        self._remover_parcelas([indice + 1 for indice in selecionados])

    def _menu_contexto_aba(self, pos) -> None:
        indice = self.abas.tabBar().tabAt(pos)
        if indice <= 0:  # 0 = Identificação (ou fora de qualquer aba), sem menu
            return
        menu = QMenu(self)
        acao_renomear = menu.addAction("Renomear parcela...")
        # ligado direto ao "triggered" de cada ação — não ao valor de
        # retorno de menu.exec() — pra não depender de comparar QAction por
        # identidade (e pra dar pra testar isto de verdade: um teste pode
        # disparar `acao.trigger()` sem precisar fechar o menu modal).
        acao_renomear.triggered.connect(lambda: self._renomear_parcela(indice))
        acao_remover = menu.addAction("Remover esta parcela...")
        acao_remover.triggered.connect(lambda: self._remover_parcela_unica(indice))
        menu.exec(self.abas.tabBar().mapToGlobal(pos))

    def _renomear_parcela(self, indice: int) -> None:
        atual = self.abas.tabText(indice)
        nome, ok = QInputDialog.getText(self, "Renomear parcela", "Novo nome:", text=atual)
        if ok and nome.strip():
            self.abas.setTabText(indice, nome.strip())

    def _remover_parcela_unica(self, indice: int) -> None:
        if self.abas.count() <= 2:
            QMessageBox.warning(self, "Remover parcela", "Pelo menos uma parcela precisa continuar existindo.")
            return
        self._remover_parcelas([indice])

    def _impedir_mover_identificacao(self, de: int, para: int) -> None:
        # Identificação (índice 0) fica sempre fixa em primeiro — se o
        # arraste envolveu o índice 0 de qualquer lado, desfaz a troca na
        # hora. blockSignals evita reentrar neste mesmo handler.
        if de == 0 or para == 0:
            barra = self.abas.tabBar()
            barra.blockSignals(True)
            barra.moveTab(para, de)
            barra.blockSignals(False)

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

    def _novo_projeto(self, confirmar: bool = True) -> None:
        if confirmar:
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
        self._abrir_projeto_de(caminho)

    def _abrir_projeto_de(self, caminho: str) -> None:
        try:
            dados = desserializar(Path(caminho).read_bytes())
        except (ProjetoInvalidoError, OSError) as exc:
            QMessageBox.critical(self, "Abrir projeto", f"Não consegui abrir {caminho}: {exc}")
            return
        aplicar_projeto(self, dados)
        self.caminho_projeto = caminho
        self._atualizar_titulo()
        registrar_recente(caminho)

    def _salvar_projeto(self) -> None:
        if not self.caminho_projeto:
            self._salvar_projeto_como()
            return
        try:
            Path(self.caminho_projeto).write_bytes(serializar(montar_projeto(self)))
        except OSError as exc:
            QMessageBox.critical(self, "Salvar projeto", f"Não consegui salvar em {self.caminho_projeto}: {exc}")
            return
        registrar_recente(self.caminho_projeto)
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
        registrar_recente(caminho)
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

    splash = None
    inicio = time.monotonic()
    if ABERTURA_PNG.exists():
        pixmap = QPixmap(str(ABERTURA_PNG))
        if pixmap.width() > 480:
            pixmap = pixmap.scaledToWidth(480, Qt.TransformationMode.SmoothTransformation)
        splash = QSplashScreen(pixmap)
        splash.show()
        # sem isto a splash só pinta na tela quando o loop de eventos rodar
        # de verdade (app.exec(), lá embaixo) — tarde demais, já que
        # JanelaPrincipal() ainda vai ser construída antes disso.
        app.processEvents()

    janela = JanelaPrincipal()

    def _mostrar_janela_principal() -> None:
        janela.showMaximized()  # aproveita a largura toda — motivo real da Proposta A
        if splash is not None:
            splash.finish(janela)
        _mostrar_boas_vindas()

    def _mostrar_boas_vindas() -> None:
        # pede Novo projeto/Abrir antes do usuário começar a preencher, pra
        # reduzir o risco de trabalhar sem ter definido onde salvar. Fechar
        # sem escolher (X/Esc) segue com o projeto em branco não salvo, do
        # jeito que já funcionava antes desta tela existir — decisão
        # explícita do usuário, não trava ninguém que já sabe o que faz.
        dialogo = BoasVindasDialog(obter_recentes(), parent=janela)
        if dialogo.exec() != QDialog.DialogCode.Accepted:
            return
        acao, caminho = dialogo.resultado()
        if acao == "novo":
            janela._novo_projeto(confirmar=False)
        elif acao == "abrir" and caminho:
            janela._abrir_projeto_de(caminho)

    if splash is not None:
        # 3s no total, ou o tempo que a abertura já tiver consumido até
        # aqui (import + construção da janela) — o que for maior, sem
        # cortar a splash antes da hora nem prender além do necessário.
        decorrido_ms = int((time.monotonic() - inicio) * 1000)
        QTimer.singleShot(max(0, _DURACAO_MINIMA_ABERTURA_MS - decorrido_ms), _mostrar_janela_principal)
    else:
        _mostrar_janela_principal()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
