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
from ui_qt.tema_qt import botao_marrom, botao_verde

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

        layout_formato = QVBoxLayout()
        layout_formato.setSpacing(2)
        layout_formato.addWidget(self._rotulo_pequeno("Formato"))
        self.combo_formato = QComboBox()
        self.combo_formato.addItems(_FORMATOS_NUMERO)
        self.combo_formato.setCurrentText("001")
        self.combo_formato.setFixedWidth(80)
        layout_formato.addWidget(self.combo_formato)
        linha.addLayout(layout_formato)

        linha.addSpacing(12)
        linha.addWidget(self._separador_vertical())
        linha.addSpacing(12)

        linha.addWidget(QLabel("Próximo nº:"))
        for tipo in dominios["tipos_vertice"]:
            layout_tipo, campo = _campo_com_rotulo(tipo["codigo"], largura=55)
            campo.setToolTip(tipo["descricao"])
            self._campos_numero[tipo["codigo"]] = campo
            linha.addLayout(layout_tipo)

        linha.addSpacing(12)
        linha.addWidget(self._separador_vertical())
        linha.addSpacing(12)

        def _botao_bloco(texto: str) -> QPushButton:
            botao = botao_verde(texto, tema)
            botao.setMinimumWidth(190)
            botao.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            return botao

        def _botao_exportar(texto: str) -> QPushButton:
            botao = botao_marrom(texto, tema)
            botao.setMinimumWidth(190)
            botao.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            return botao

        layout_botoes_direita = QVBoxLayout()
        layout_botoes_direita.setSpacing(4)

        # Exportações em marrom (sai um arquivo), sempre em cima —
        # separadas visualmente das ações verdes (mexem só no que está na
        # tela) de baixo. Quem conecta os cliques é o dono da janela
        # (app_qt.py: tem a Identificação, o diálogo de salvar e as demais
        # parcelas, que este painel não enxerga sozinho).
        linha_exportar = QHBoxLayout()
        self.btn_exportar_planilha = _botao_exportar("Exportar planilha SIGEF (.ods)")
        self.btn_exportar_txt = _botao_exportar("Exportar Tabela SIGEF em TXT")
        self.btn_gerar_relatorio = _botao_exportar("Gerar Relatório em DOCX")
        linha_exportar.addWidget(self.btn_exportar_planilha)
        linha_exportar.addWidget(self.btn_exportar_txt)
        linha_exportar.addWidget(self.btn_gerar_relatorio)
        layout_botoes_direita.addLayout(linha_exportar)

        # Renumerar/Atualizar/Marcar/Desmarcar/Reorganizar desceram pra junto
        # da grade que eles afetam (ui_qt/perimetro_tab.py), a pedido do
        # usuário — aqui ficam as ações que mexem em TODAS as abas
        # (Adicionar/Remover parcela, junto de Renumerar/Exportar acima) ou
        # que não têm "dono" de uma parcela só (Desfazer/Importar agem na
        # aba ATUAL). Quem sabe adicionar/remover aba é a janela
        # (app_qt.py), não este painel — só expõe os botões, quem conecta
        # o clique é ela (mesmo padrão dos botões de exportação acima).
        linha_botoes = QHBoxLayout()
        self.btn_adicionar_parcela = _botao_bloco("+ Adicionar parcela")
        linha_botoes.addWidget(self.btn_adicionar_parcela)

        self.btn_remover_parcela = _botao_bloco("- Remover parcela...")
        linha_botoes.addWidget(self.btn_remover_parcela)

        btn_desfazer = _botao_bloco("↶ Desfazer (Ctrl+Z)")
        btn_desfazer.setToolTip(
            "Volta a grade da parcela aberta agora pro estado de antes da "
            "última mudança — edição de célula, colar, Reorganizar etc."
        )
        btn_desfazer.clicked.connect(self._desfazer_atual)
        linha_botoes.addWidget(btn_desfazer)

        btn_importar = _botao_bloco("Importar vértices de um arquivo (TXT/CSV)...")
        btn_importar.setToolTip("Importa vértices de um arquivo para a parcela aberta agora.")
        btn_importar.clicked.connect(self._importar_atual)
        linha_botoes.addWidget(btn_importar)
        layout_botoes_direita.addLayout(linha_botoes)

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

    def _desfazer_atual(self) -> None:
        aba = self._exigir_aba_atual()
        if aba is not None and not aba.modelo_tabela.desfazer():
            QMessageBox.information(self, "Desfazer", "Não há mudança para desfazer nesta parcela.")

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
