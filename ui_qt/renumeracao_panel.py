"""Painel de numeração de vértices (Qt) — equivalente a ui/renumeracao.py.
Fica fora de qualquer aba (dock lateral), porque a numeração corre entre
parcelas: usa `obter_abas_perimetro()` pra pegar as abas atuais na hora do
clique, já que parcelas podem ser adicionadas/removidas depois deste
painel existir.
"""
from __future__ import annotations

from typing import Callable

from PySide6.QtWidgets import (
    QComboBox,
    QDockWidget,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.numeracao import atualizar_tipos_parcelas, renumerar_parcelas

_FORMATOS_NUMERO = ["1", "01", "001", "0001", "00001"]


class PainelNumeracao(QDockWidget):
    def __init__(self, dominios: dict, obter_abas_perimetro: Callable[[], list], parent=None) -> None:
        super().__init__("Numeração de vértices", parent)
        self._obter_abas = obter_abas_perimetro
        self._campos_numero: dict[str, QLineEdit] = {}

        conteudo = QWidget()
        layout = QVBoxLayout(conteudo)

        layout.addWidget(QLabel("Código do credenciado"))
        self.campo_credenciado = QLineEdit()
        layout.addWidget(self.campo_credenciado)

        layout.addWidget(QLabel("Formato do número"))
        self.combo_formato = QComboBox()
        self.combo_formato.addItems(_FORMATOS_NUMERO)
        self.combo_formato.setCurrentText("001")
        layout.addWidget(self.combo_formato)

        layout.addWidget(
            QLabel(
                "Próximo número livre de cada tipo — o mesmo contador da vida "
                "profissional, não reinicia por parcela nem por serviço:"
            )
        )
        for tipo in dominios["tipos_vertice"]:
            layout.addWidget(QLabel(f"{tipo['codigo']} — {tipo['descricao']}"))
            campo = QLineEdit("001")
            self._campos_numero[tipo["codigo"]] = campo
            layout.addWidget(campo)

        btn_renumerar = QPushButton("Renumerar vértices marcados")
        btn_renumerar.clicked.connect(self._renumerar)
        layout.addWidget(btn_renumerar)

        layout.addWidget(
            QLabel(
                'Só linhas com "Renumerar?" marcado recebem código novo — '
                "desmarque vértices que não são seus."
            )
        )

        btn_atualizar = QPushButton("🔄 Atualizar código (só o Tipo)")
        btn_atualizar.clicked.connect(self._atualizar_tipos)
        layout.addWidget(btn_atualizar)

        layout.addWidget(
            QLabel(
                "Já renumerou e corrigiu o Tipo de algum vértice na grade? Isto "
                "reescreve só o pedaço do Tipo no código, sem reatribuir número."
            )
        )

        layout.addStretch()
        self.setWidget(conteudo)

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
