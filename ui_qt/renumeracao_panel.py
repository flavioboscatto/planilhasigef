"""Painel de numeração de vértices (Qt) — equivalente a ui/renumeracao.py.
Faixa horizontal acima das abas (Proposta A escolhida em 2026-08-31 na
comparação de layouts), não mais um dock lateral: fica sempre visível
sem tomar largura da grade, e sem trocar de aba pra usar Renumerar/
Atualizar. Fica fora de qualquer aba porque a numeração corre entre
parcelas — usa `obter_abas_perimetro()` pra pegar as abas atuais na hora
do clique, já que parcelas podem ser adicionadas/removidas depois deste
painel existir.
"""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.numeracao import atualizar_tipos_parcelas, renumerar_parcelas
from ui_qt.tema_qt import botao_azul, botao_marrom, botao_perigo, botao_verde, botao_verde_destaque

_FORMATOS_NUMERO = ["1", "01", "001", "0001", "00001"]


def _campo_com_rotulo(rotulo: str, largura: int | None = None) -> tuple[QVBoxLayout, QLineEdit]:
    layout = QVBoxLayout()
    layout.setSpacing(2)
    etiqueta = QLabel(rotulo)
    etiqueta.setStyleSheet("font-size: 8.5pt; color: #55606b;")
    campo = QLineEdit("001")
    if largura:
        campo.setFixedWidth(largura)
    layout.addWidget(etiqueta)
    layout.addWidget(campo)
    return layout, campo


class PainelNumeracao(QWidget):
    def __init__(
        self,
        dominios: dict,
        obter_abas_perimetro: Callable[[], list],
        obter_aba_atual: Callable[[], object | None],
        tema: dict,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._obter_abas = obter_abas_perimetro
        self._obter_aba_atual = obter_aba_atual
        self._campos_numero: dict[str, QLineEdit] = {}

        linha = QHBoxLayout(self)
        linha.setContentsMargins(10, 6, 10, 6)

        # Credenciado/Formato/Próximo nº (por tipo) ficam à ESQUERDA; o
        # bloco de botões (numeração + reorganização) fica à DIREITA, dois
        # a dois — assim pedido pelo usuário depois de usar a versão de
        # botões todos em fileira única.
        layout_cred, self.campo_credenciado = _campo_com_rotulo("Credenciado", largura=110)
        self.campo_credenciado.setText("")
        linha.addLayout(layout_cred)
        # sem isto, a fileira inteira (agora mais alta — 3 fileiras de
        # botão à direita) esticava este bloco pra preencher a altura toda,
        # e o rótulo ia pro topo enquanto a caixa ia pro fundo, com um vão
        # feio entre os dois. AlignTop mantém o bloco no tamanho natural,
        # rótulo colado na caixa — pedido do usuário.
        linha.setAlignment(layout_cred, Qt.AlignmentFlag.AlignTop)

        layout_formato = QVBoxLayout()
        layout_formato.setSpacing(2)
        layout_formato.addWidget(self._rotulo_pequeno("Formato"))
        self.combo_formato = QComboBox()
        self.combo_formato.addItems(_FORMATOS_NUMERO)
        self.combo_formato.setCurrentText("001")
        self.combo_formato.setFixedWidth(80)
        layout_formato.addWidget(self.combo_formato)
        linha.addLayout(layout_formato)
        linha.setAlignment(layout_formato, Qt.AlignmentFlag.AlignTop)

        linha.addSpacing(12)
        linha.addWidget(self._separador_vertical())
        linha.addSpacing(12)

        rotulo_proximo = QLabel("Próximo nº:")
        linha.addWidget(rotulo_proximo)
        linha.setAlignment(rotulo_proximo, Qt.AlignmentFlag.AlignTop)
        for tipo in dominios["tipos_vertice"]:
            layout_tipo, campo = _campo_com_rotulo(tipo["codigo"], largura=55)
            campo.setToolTip(tipo["descricao"])
            self._campos_numero[tipo["codigo"]] = campo
            linha.addLayout(layout_tipo)
            linha.setAlignment(layout_tipo, Qt.AlignmentFlag.AlignTop)

        linha.addSpacing(12)
        linha.addWidget(self._separador_vertical())
        linha.addSpacing(12)

        # fonte/altura levemente menores só aqui (pedido do usuário — 3
        # fileiras de botão deixaram este painel mais alto do que o bloco
        # de Credenciado/Próximo nº à esquerda) — acrescenta por cima do
        # style de cor já pronto (QSS aceita 2 blocos QPushButton{} pro
        # mesmo widget; o de baixo, com padding/font-size, vence por vir
        # depois, sem precisar duplicar a cor de cada variante).
        _AJUSTE_COMPACTO = "QPushButton { padding: 4px 8px; font-size: 9pt; }"

        def _compacto(botao: QPushButton) -> QPushButton:
            botao.setStyleSheet(botao.styleSheet() + _AJUSTE_COMPACTO)
            botao.setMinimumWidth(170)
            botao.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            return botao

        def _botao_bloco(texto: str, destaque: bool = False, icone: str | None = None) -> QPushButton:
            return _compacto((botao_verde_destaque if destaque else botao_verde)(texto, tema, icone))

        def _botao_exportar(texto: str, icone: str | None = None) -> QPushButton:
            return _compacto(botao_marrom(texto, tema, icone))

        def _botao_azul(texto: str, icone: str | None = None) -> QPushButton:
            return _compacto(botao_azul(texto, tema, icone))

        def _botao_perigo(texto: str, icone: str | None = None) -> QPushButton:
            return _compacto(botao_perigo(texto, tema, icone))

        layout_botoes_direita = QVBoxLayout()
        layout_botoes_direita.setSpacing(4)

        # 3 fileiras, ordem pedida pelo usuário (uma 4ª fileira quebrava a
        # estética junto do bloco de Credenciado/Próximo nº à esquerda):
        # 1) Importar + Adicionar/Remover parcela (monta a estrutura);
        # 2) exportações georreferenciadas (azul) + Limpar Parcela (rosa) +
        #    Desfazer; 3) exportações do SIGEF (marrom). Quem conecta os
        # cliques de Adicionar/Remover parcela e das exportações
        # georreferenciadas é o dono da janela (app_qt.py: tem a
        # Identificação, os diálogos de salvar e as demais parcelas, que
        # este painel não enxerga sozinho) — Desfazer também ganhou um
        # ícone equivalente na barra de ferramentas (app_qt.py), mas
        # continua aqui também, a pedido do usuário.
        linha1 = QHBoxLayout()
        btn_importar = _botao_bloco("Importar TXT/CSV", destaque=True, icone="fa5s.file-csv")
        btn_importar.setToolTip("Importa vértices de um arquivo TXT/CSV para a parcela aberta agora.")
        btn_importar.clicked.connect(self._importar_atual)
        linha1.addWidget(btn_importar)

        self.btn_importar_planilha = _botao_bloco("Importar XLS/XLSX/ODS", destaque=True, icone="fa5s.file-excel")
        self.btn_importar_planilha.setToolTip("Importa vértices de uma planilha pra parcela aberta agora.")
        self.btn_importar_planilha.clicked.connect(self._importar_planilha_atual)
        linha1.addWidget(self.btn_importar_planilha)

        self.btn_adicionar_parcela = _botao_bloco("Adicionar parcela", icone="fa5s.plus")
        linha1.addWidget(self.btn_adicionar_parcela)

        self.btn_remover_parcela = _botao_bloco("Remover parcela...", icone="fa5s.minus")
        linha1.addWidget(self.btn_remover_parcela)
        layout_botoes_direita.addLayout(linha1)

        linha2 = QHBoxLayout()
        self.btn_exportar_kml = _botao_azul("Exportar Projeto em KML", icone="mdi.earth")
        self.btn_exportar_kml.setToolTip(
            "Exporta todas as parcelas em KML (Google Earth) — uma camada por parcela, "
            "polígono do perímetro e um ponto por vértice."
        )
        linha2.addWidget(self.btn_exportar_kml)

        self.btn_exportar_shapefile = _botao_azul("Exportar Shapefile", icone="fa5s.map")
        self.btn_exportar_shapefile.setToolTip(
            "Exporta pontos (vértices, com todos os atributos da planilha + área SGL) e "
            "polígonos (perímetro por parcela), zipados num arquivo só."
        )
        linha2.addWidget(self.btn_exportar_shapefile)

        self.btn_limpar_parcela = _botao_perigo("Limpar Parcela", icone="fa5s.broom")
        self.btn_limpar_parcela.setToolTip("Apaga todos os vértices da Tabela de Perímetro da parcela aberta agora.")
        self.btn_limpar_parcela.clicked.connect(self._limpar_parcela_atual)
        linha2.addWidget(self.btn_limpar_parcela)

        btn_desfazer = _botao_bloco("Desfazer (Ctrl+Z)", icone="fa5s.undo")
        btn_desfazer.setToolTip(
            "Volta a grade da parcela aberta agora pro estado de antes da "
            "última mudança — edição de célula, colar, Reorganizar etc."
        )
        btn_desfazer.clicked.connect(self._desfazer_atual)
        linha2.addWidget(btn_desfazer)
        layout_botoes_direita.addLayout(linha2)

        linha3 = QHBoxLayout()
        self.btn_exportar_planilha = _botao_exportar("Exportar SIGEF (ods)", icone="fa5s.table")
        self.btn_exportar_planilha.setToolTip("Gera a planilha oficial do SIGEF (.ods), pronta pra certificação.")
        self.btn_exportar_txt = _botao_exportar("Exportar SIGEF (TXT)", icone="fa5s.file-alt")
        self.btn_exportar_txt.setToolTip("Exporta a Tabela de Perímetro em texto (mesmas colunas oficiais).")
        self.btn_exportar_xlsx = _botao_exportar("Exportar SIGEF (xlsx)", icone="fa5s.file-excel")
        self.btn_exportar_xlsx.setToolTip("Exporta a Tabela de Perímetro em Excel (mesmas colunas oficiais).")
        self.btn_gerar_relatorio = _botao_exportar("Relatório (docx)", icone="fa5s.file-word")
        self.btn_gerar_relatorio.setToolTip("Gera o Relatório em Word (identificação + planilha por parcela).")
        linha3.addWidget(self.btn_exportar_planilha)
        linha3.addWidget(self.btn_exportar_txt)
        linha3.addWidget(self.btn_exportar_xlsx)
        linha3.addWidget(self.btn_gerar_relatorio)
        layout_botoes_direita.addLayout(linha3)

        linha.addLayout(layout_botoes_direita, 1)

    def _rotulo_pequeno(self, texto: str) -> QLabel:
        etiqueta = QLabel(texto)
        etiqueta.setStyleSheet("font-size: 8.5pt; color: #55606b;")
        return etiqueta

    def _separador_vertical(self) -> QWidget:
        linha = QWidget()
        linha.setFixedWidth(1)
        linha.setStyleSheet("background: #c7ced6;")
        return linha

    def _largura(self) -> int:
        return len(self.combo_formato.currentText())

    def _numero_de(self, campo: QLineEdit) -> int:
        bruto = campo.text().strip()
        try:
            return max(1, int(bruto))
        except ValueError:
            return 1

    def _exigir_aba_atual(self):
        aba = self._obter_aba_atual()
        if aba is None:
            QMessageBox.warning(self, "Numeração", "Abra uma aba de Parcela primeiro.")
        return aba

    def _importar_atual(self) -> None:
        aba = self._exigir_aba_atual()
        if aba is not None:
            aba._abrir_importador()

    def _importar_planilha_atual(self) -> None:
        aba = self._exigir_aba_atual()
        if aba is not None:
            aba._abrir_importador_planilha()

    def _desfazer_atual(self) -> None:
        aba = self._exigir_aba_atual()
        if aba is not None and not aba.modelo_tabela.desfazer():
            QMessageBox.information(self, "Desfazer", "Não há mudança para desfazer nesta parcela.")

    def _limpar_parcela_atual(self) -> None:
        aba = self._exigir_aba_atual()
        if aba is not None:
            aba._limpar_parcela()

    def _renumerar(self) -> None:
        credenciado = self.campo_credenciado.text().strip().upper()
        if not credenciado:
            QMessageBox.warning(self, "Numeração", "Informe o código do credenciado antes de renumerar.")
            return

        abas = self._obter_abas()
        tabelas = [aba.modelo_tabela.dataframe() for aba in abas]
        inicio_por_tipo = {codigo: self._numero_de(campo) for codigo, campo in self._campos_numero.items()}

        atualizadas, proximos, avisos, total = renumerar_parcelas(
            tabelas, credenciado, inicio_por_tipo, self._largura()
        )
        for aba, tabela in zip(abas, atualizadas):
            aba.modelo_tabela.substituir(tabela)
        for codigo, valor in proximos.items():
            if codigo in self._campos_numero:
                self._campos_numero[codigo].setText(f"{valor:0{self._largura()}d}")

        for aviso in avisos:
            QMessageBox.warning(self, "Numeração", aviso)
        if total > 0:
            QMessageBox.information(self, "Numeração", f"{total} vértice(s) renumerado(s).")
        elif not avisos:
            QMessageBox.warning(
                self, "Numeração",
                'Nenhum vértice foi renumerado — confira se "Renumerar?" está '
                'marcado e se "Tipo" está preenchido nas linhas desejadas.',
            )

    def _atualizar_tipos(self) -> None:
        abas = self._obter_abas()
        tabelas = [aba.modelo_tabela.dataframe() for aba in abas]

        atualizadas, avisos, total = atualizar_tipos_parcelas(tabelas)
        for aba, tabela in zip(abas, atualizadas):
            aba.modelo_tabela.substituir(tabela)

        for aviso in avisos:
            QMessageBox.warning(self, "Numeração", aviso)
        if total > 0:
            QMessageBox.information(self, "Numeração", f"{total} código(s) atualizado(s).")
        elif not avisos:
            QMessageBox.warning(
                self, "Numeração",
                'Nenhum código foi atualizado — confira "Renumerar?", se o Tipo '
                "mudou de verdade, e se o código já está no formato "
                "CREDENCIADO-TIPO-NUMERO.",
            )
