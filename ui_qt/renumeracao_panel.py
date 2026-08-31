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
    QVBoxLayout,
    QWidget,
)

from core.numeracao import atualizar_tipos_parcelas, renumerar_parcelas

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
    def __init__(self, dominios: dict, obter_abas_perimetro: Callable[[], list], parent=None) -> None:
        super().__init__(parent)
        self._obter_abas = obter_abas_perimetro
        self._campos_numero: dict[str, QLineEdit] = {}

        linha = QHBoxLayout(self)
        linha.setContentsMargins(10, 6, 10, 6)

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

        btn_renumerar = QPushButton("Renumerar vértices marcados")
        btn_renumerar.setToolTip(
            'Só linhas com "Renumerar?" marcado recebem código novo, em todas '
            "as parcelas abertas — desmarque vértices que não são seus."
        )
        btn_renumerar.clicked.connect(self._renumerar)
        linha.addWidget(btn_renumerar)

        btn_atualizar = QPushButton("🔄 Atualizar código (só o Tipo)")
        btn_atualizar.setToolTip(
            "Já renumerou e corrigiu o Tipo de algum vértice na grade? Isto "
            "reescreve só o pedaço do Tipo no código, sem reatribuir número."
        )
        btn_atualizar.clicked.connect(self._atualizar_tipos)
        linha.addWidget(btn_atualizar)

        linha.addStretch()

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
