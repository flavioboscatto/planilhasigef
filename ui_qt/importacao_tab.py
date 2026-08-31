"""Aba de Importação (Qt) — cada arquivo importado (ver
ui_qt/importar_vertices_dialog.py) vira uma sub-aba própria e persistente
dentro da parcela ("Importação 1", "Importação 2", ...), ao invés de um
bloco que desaparecia da tela assim que usado.

Mostra os dados EXATAMENTE como vieram do arquivo mapeado — tabela simples
(QTableWidget), sem cor de fundo, sem formato GMS, sem preencher com as
colunas do SIGEF que não vieram do arquivo. É só uma conferência do que foi
importado; o formato oficial (cor, GMS, domínios em combo) só se aplica na
Tabela de Perímetro, depois de "Usar esta versão".

Guarda o easting/northing original (se a origem foi UTM) e tem seu próprio
Meridiano Central/Hemisfério, então dá pra reconferir e recalcular
geodésica a qualquer momento sem reimportar o arquivo — inclusive depois
de já ter mesclado na Tabela de Perímetro: "Usar esta versão" pode ser
clicado de novo, e mescla por código sobrescreve os valores anteriores.
"""
from __future__ import annotations

from typing import Callable

import pandas as pd
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.geo import utm_para_geodesica
from core.parsing import normaliza_decimal, parse_numero
from ui_qt.tema_qt import Papel, botao_verde
from ui_qt.vertices_table import _ROTULOS


class AbaImportacao(QWidget):
    def __init__(
        self,
        numero: int,
        dados: pd.DataFrame,
        dados_utm_brutos: pd.DataFrame | None,
        meridiano_inicial: float,
        hemisferio_inicial: str,
        meridianos_disponiveis: list[int],
        hemisferios_disponiveis: list[str],
        tema: dict[str, Papel],
        aplicar_na_parcela: Callable[[pd.DataFrame], None],
        remover_esta_aba: Callable[["AbaImportacao"], None],
        parent=None,
    ) -> None:
        super().__init__(parent)
        # posição na linha == posição em dados_utm_brutos: esta grade nunca
        # reordena/insere/remove linha (isso só existe na Tabela de
        # Perímetro), então o índice sempre bate — sem precisar de coluna
        # interna nem dicionário à parte pra religar um com o outro.
        self._dados_utm_brutos = dados_utm_brutos
        self._aplicar_na_parcela = aplicar_na_parcela
        self._remover_esta_aba = remover_esta_aba
        self._colunas = list(dados.columns)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            f"<b>Importação {numero}</b> — {len(dados)} linha(s), exatamente como vieram do "
            "arquivo mapeado (sem cor nem formato da planilha SIGEF). Use \"Usar esta versão\" "
            "pra levar pra Tabela de Perímetro."
        ))

        self.tabela = QTableWidget(len(dados), len(self._colunas))
        self.tabela.setHorizontalHeaderLabels([_ROTULOS.get(c, c) for c in self._colunas])
        for linha in range(len(dados)):
            for coluna, campo in enumerate(self._colunas):
                valor = dados.iat[linha, coluna]
                self.tabela.setItem(linha, coluna, QTableWidgetItem("" if pd.isna(valor) else str(valor)))
        layout.addWidget(self.tabela)

        linha_acoes = QHBoxLayout()

        if dados_utm_brutos is not None:
            linha_acoes.addWidget(QLabel("Meridiano Central (°):"))
            self.combo_meridiano = QComboBox()
            self.combo_meridiano.addItems([str(m) for m in meridianos_disponiveis])
            self.combo_meridiano.setCurrentText(str(int(meridiano_inicial)))
            linha_acoes.addWidget(self.combo_meridiano)
            linha_acoes.addWidget(QLabel("Hemisfério:"))
            self.combo_hemisferio = QComboBox()
            self.combo_hemisferio.addItems(hemisferios_disponiveis)
            self.combo_hemisferio.setCurrentText(hemisferio_inicial)
            linha_acoes.addWidget(self.combo_hemisferio)

            btn_recalcular = botao_verde("🔄 Recalcular geodésica", tema)
            btn_recalcular.setToolTip(
                "Reconverte E/Long e N/Lat a partir do easting/northing original "
                "desta importação, com o Meridiano/Hemisfério acima — sem "
                "precisar reimportar o arquivo. Depois, clique em \"Usar esta "
                "versão\" de novo para levar o valor corrigido à Tabela de "
                "Perímetro."
            )
            btn_recalcular.clicked.connect(self._recalcular)
            linha_acoes.addWidget(btn_recalcular)

        btn_usar = botao_verde("Usar esta versão na planilha definitiva", tema)
        btn_usar.setToolTip(
            "Mescla os dados desta aba na Tabela de Perímetro pelo código do "
            "vértice — pode clicar de novo depois de editar ou recalcular, "
            "para atualizar o que já foi mesclado."
        )
        btn_usar.clicked.connect(self._usar)
        linha_acoes.addWidget(btn_usar)

        btn_remover = QPushButton("Remover esta importação")
        btn_remover.clicked.connect(lambda: self._remover_esta_aba(self))
        linha_acoes.addWidget(btn_remover)

        linha_acoes.addStretch()
        layout.addLayout(linha_acoes)

    def _dataframe_atual(self) -> pd.DataFrame:
        linhas = []
        for linha in range(self.tabela.rowCount()):
            registro = {}
            for coluna, campo in enumerate(self._colunas):
                item = self.tabela.item(linha, coluna)
                registro[campo] = item.text() if item is not None else ""
            linhas.append(registro)
        return pd.DataFrame(linhas, columns=self._colunas)

    def _recalcular(self) -> None:
        meridiano = float(self.combo_meridiano.currentText())
        hemisferio = self.combo_hemisferio.currentText()
        coluna_e = self._colunas.index("e_long")
        coluna_n = self._colunas.index("n_lat")
        for linha, (easting_txt, northing_txt) in enumerate(
            zip(self._dados_utm_brutos["e_long"], self._dados_utm_brutos["n_lat"])
        ):
            longitude, latitude = utm_para_geodesica(
                parse_numero(easting_txt), parse_numero(northing_txt), meridiano, hemisferio,
            )
            self.tabela.item(linha, coluna_e).setText(normaliza_decimal(str(longitude)))
            self.tabela.item(linha, coluna_n).setText(normaliza_decimal(str(latitude)))

    def _usar(self) -> None:
        self._aplicar_na_parcela(self._dataframe_atual())
