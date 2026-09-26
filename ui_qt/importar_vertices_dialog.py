"""Importação de vértices de arquivo (Qt) — equivalente a
ui/importar_vertices.py. Este diálogo só cuida de escolher o arquivo,
separador e mapeamento de coluna; ao clicar "Criar versão a partir deste
arquivo", quem vira dono do resultado é uma sub-aba nova e persistente
dentro da parcela (ui_qt/importacao_tab.py::AbaImportacao) — reaproveitando
core/importacao.py e core/geo.py sem mudança.

Diferença real: aqui o arquivo é escolhido por QFileDialog nativo — sem
precisar do hack de subprocess que usamos no Streamlit local (aquele
existia só por causa do tkinter rodar fora da thread principal do
Streamlit; Qt não tem esse problema).
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable

import pandas as pd
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.geo import utm_para_geodesica
from core.parsing import (
    ValorInvalidoError,
    normaliza_decimal,
    parse_coordenada,
    parse_geodesica_compacta,
    parse_geodesica_grau_minuto,
    parse_numero,
)
from importers.delimitado import SEPARADORES, ler_arquivo
from importers.planilha import ler_planilha, nomes_das_abas

_CAMPOS_NUMERICOS = {"sigma_long", "sigma_lat", "h", "sigma_h"}

_FORMATO_GEO_DECIMAL = "Decimal (grau decimal, ex.: -27,508333)"

_PARSERS_GEODESICA = {
    _FORMATO_GEO_DECIMAL: parse_numero,
    "GMS — símbolos ou espaços (ex.: 27 30 30 S)": parse_coordenada,
    "Grau + minuto decimal, sem segundos (ex.: 27 30,500 S)": parse_geodesica_grau_minuto,
    "Compactado GG,MMSS (ex.: -27,3030)": parse_geodesica_compacta,
}

_CAMPOS_VERTICE = {
    "(ignorar)": None,
    "Código do vértice": "codigo",
    "E / Longitude": "e_long",
    "Sigma Long/E": "sigma_long",
    "N / Latitude": "n_lat",
    "Sigma Lat/N": "sigma_lat",
    "h (altitude elipsoidal)": "h",
    "Sigma h": "sigma_h",
    "Método de Posicionamento": "metodo_posicionamento",
    "Tipo de Limite": "tipo_limite",
    "CNS": "cns",
    "Matrícula/Reg.Imóveis": "matricula",
    "Descritivo": "descritivo",
}


class ImportarVerticesDialog(QDialog):
    def __init__(
        self,
        opcoes_tipo_vertice: list[str],
        opcoes_metodo: list[str],
        opcoes_limite: list[str],
        meridianos_disponiveis: list[int],
        hemisferios_disponiveis: list[str],
        meridiano_inicial: float,
        hemisferio_inicial: str,
        tema: dict,
        casas: dict,
        criar_aba_importacao: Callable[[pd.DataFrame, pd.DataFrame | None, pd.DataFrame | None, float, str], None],
        formato: str = "texto",
        parent=None,
    ) -> None:
        super().__init__(parent)
        # formato="planilha" (XLS/XLSX/ODS) reaproveita este mesmo diálogo —
        # prévia/mapeamento de coluna/sistema de coordenadas/"Criar versão"
        # já são agnósticos de formato de origem (core/tabela_vertices.py
        # nem entra aqui, tudo trabalha em cima do DataFrame cru). Só muda
        # como o arquivo é escolhido/lido (ver _escolher_arquivo/_recarregar_preview).
        self._formato = formato
        self.setWindowTitle(
            "Importar vértices de uma planilha (XLS/XLSX/ODS)"
            if formato == "planilha"
            else "Importar vértices de um arquivo (TXT/CSV)"
        )
        self.resize(900, 700)
        self._opcoes_tipo_vertice = opcoes_tipo_vertice
        self._opcoes_metodo = opcoes_metodo
        self._opcoes_limite = opcoes_limite
        self._meridianos_disponiveis = meridianos_disponiveis
        self._hemisferios_disponiveis = hemisferios_disponiveis
        self._tema = tema
        self._casas = casas
        self._criar_aba_importacao = criar_aba_importacao
        self._df_bruto: pd.DataFrame | None = None
        self._extensao_arquivo: str | None = None
        self._combos_mapeamento: dict[str, QComboBox] = {}

        layout_geral = QVBoxLayout(self)

        linha_arquivo = QHBoxLayout()
        self.rotulo_arquivo = QLabel("Nenhum arquivo escolhido.")
        btn_escolher = QPushButton("Escolher arquivo...")
        btn_escolher.clicked.connect(self._escolher_arquivo)
        linha_arquivo.addWidget(btn_escolher)
        linha_arquivo.addWidget(self.rotulo_arquivo, stretch=1)
        layout_geral.addLayout(linha_arquivo)

        linha_opcoes = QHBoxLayout()
        self.rotulo_separador = QLabel("Separador:")
        self.combo_separador = QComboBox()
        self.combo_separador.addItems([*SEPARADORES, "Outro"])
        self.combo_separador.currentTextChanged.connect(self._recarregar_preview)
        self.campo_separador_customizado = QLineEdit()
        self.campo_separador_customizado.setPlaceholderText("separador")
        self.campo_separador_customizado.setVisible(False)
        self.campo_separador_customizado.textChanged.connect(self._recarregar_preview)
        self.combo_separador.currentTextChanged.connect(
            lambda texto: self.campo_separador_customizado.setVisible(
                texto == "Outro" and self._formato == "texto"
            )
        )
        # só relevante pra planilha (pode ter mais de uma aba); populado em
        # _escolher_arquivo depois de escolhido o arquivo.
        self.rotulo_aba_planilha = QLabel("Aba da planilha:")
        self.combo_aba_planilha = QComboBox()
        self.combo_aba_planilha.currentTextChanged.connect(self._recarregar_preview)
        self.checa_cabecalho = QCheckBox("Arquivo tem linha de cabeçalho")
        self.checa_cabecalho.setChecked(True)
        self.checa_cabecalho.toggled.connect(self._recarregar_preview)
        linha_opcoes.addWidget(self.rotulo_separador)
        linha_opcoes.addWidget(self.combo_separador)
        linha_opcoes.addWidget(self.campo_separador_customizado)
        linha_opcoes.addWidget(self.rotulo_aba_planilha)
        linha_opcoes.addWidget(self.combo_aba_planilha)
        linha_opcoes.addWidget(self.checa_cabecalho)
        layout_geral.addLayout(linha_opcoes)

        eh_planilha = self._formato == "planilha"
        self.rotulo_separador.setVisible(not eh_planilha)
        self.combo_separador.setVisible(not eh_planilha)
        self.rotulo_aba_planilha.setVisible(eh_planilha)
        self.combo_aba_planilha.setVisible(eh_planilha)

        layout_geral.addWidget(QLabel("Prévia (5 primeiras linhas):"))
        self.tabela_previa = QTableWidget()
        self.tabela_previa.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabela_previa.setMaximumHeight(160)
        layout_geral.addWidget(self.tabela_previa)

        layout_geral.addWidget(QLabel("Diga o que cada coluna do arquivo significa:"))
        self.area_mapeamento = QWidget()
        self.layout_mapeamento = QFormLayout(self.area_mapeamento)
        layout_geral.addWidget(self.area_mapeamento)

        linha_sistema = QHBoxLayout()
        self.combo_sistema = QComboBox()
        self.combo_sistema.addItems(["Geodésica", "UTM"])
        self.combo_formato_geo = QComboBox()
        self.combo_formato_geo.addItems(list(_PARSERS_GEODESICA))
        self.combo_sistema.currentTextChanged.connect(
            lambda texto: self.combo_formato_geo.setVisible(texto == "Geodésica")
        )
        linha_sistema.addWidget(QLabel("Sistema de coordenadas no arquivo:"))
        linha_sistema.addWidget(self.combo_sistema)
        linha_sistema.addWidget(self.combo_formato_geo)
        layout_geral.addLayout(linha_sistema)

        # Meridiano/Hemisfério ficam editáveis aqui dentro (não só uma
        # referência fixa ao que estava na aba Perímetro quando o diálogo
        # abriu) — errou a escolha? Troca aqui e usa "Recalcular geodésica"
        # em cada versão pendente, sem precisar reimportar o arquivo do zero.
        self.linha_utm = QWidget()
        layout_linha_utm = QHBoxLayout(self.linha_utm)
        layout_linha_utm.setContentsMargins(0, 0, 0, 0)
        self.combo_meridiano = QComboBox()
        self.combo_meridiano.addItems([str(m) for m in meridianos_disponiveis])
        self.combo_meridiano.setCurrentText(str(int(meridiano_inicial)))
        self.combo_hemisferio = QComboBox()
        self.combo_hemisferio.addItems(hemisferios_disponiveis)
        self.combo_hemisferio.setCurrentText(hemisferio_inicial)
        layout_linha_utm.addWidget(QLabel("Meridiano Central (°):"))
        layout_linha_utm.addWidget(self.combo_meridiano)
        layout_linha_utm.addWidget(QLabel("Hemisfério:"))
        layout_linha_utm.addWidget(self.combo_hemisferio)
        layout_geral.addWidget(self.linha_utm)

        self.aviso_utm = QLabel(
            "Zona/hemisfério errado aqui sai sem aviso: o número parece válido, só "
            "que aponta pro lugar errado. Se perceber depois de criar a "
            "importação, corrija o Meridiano/Hemisfério na aba \"Importação N\" "
            "criada e use \"Recalcular geodésica\" lá."
        )
        self.aviso_utm.setWordWrap(True)
        self.aviso_utm.setVisible(False)
        self.combo_sistema.currentTextChanged.connect(self._atualizar_aviso_utm)
        layout_geral.addWidget(self.aviso_utm)

        btn_criar_versao = QPushButton("Criar versão a partir deste arquivo")
        btn_criar_versao.clicked.connect(self._criar_versao)
        layout_geral.addWidget(btn_criar_versao)

        self.rotulo_status = QLabel(
            "Cada arquivo importado vira uma aba própria (\"Importação N\") ao "
            "lado da Tabela de Perímetro — pode importar mais de um arquivo "
            "nesta mesma janela."
        )
        self.rotulo_status.setWordWrap(True)
        layout_geral.addWidget(self.rotulo_status)
        layout_geral.addStretch()

        self._atualizar_aviso_utm(self.combo_sistema.currentText())

    # --- arquivo / prévia / mapeamento ---

    def _separador_atual(self) -> str:
        escolha = self.combo_separador.currentText()
        if escolha == "Outro":
            return self.campo_separador_customizado.text()
        return SEPARADORES[escolha]

    def _escolher_arquivo(self) -> None:
        if self._formato == "planilha":
            filtro = "Planilha (*.xls *.xlsx *.ods);;Todos os arquivos (*.*)"
        else:
            filtro = "Texto/CSV (*.txt *.csv);;Todos os arquivos (*.*)"
        caminho, _ = QFileDialog.getOpenFileName(self, "Escolher arquivo de vértices", "", filtro)
        if not caminho:
            return
        self._caminho_arquivo = caminho
        self._extensao_arquivo = Path(caminho).suffix
        self.rotulo_arquivo.setText(caminho)

        if self._formato == "planilha":
            try:
                with open(caminho, "rb") as f:
                    abas = nomes_das_abas(f.read(), self._extensao_arquivo)
            except Exception as exc:
                QMessageBox.critical(self, "Erro ao ler planilha", f"Não consegui abrir o arquivo: {exc}")
                self._df_bruto = None
                return
            # bloqueia sinal durante a repopulação — currentTextChanged
            # dispararia _recarregar_preview no meio da troca, antes da
            # lista de abas estar completa.
            self.combo_aba_planilha.blockSignals(True)
            self.combo_aba_planilha.clear()
            self.combo_aba_planilha.addItems(abas)
            self.combo_aba_planilha.blockSignals(False)

        self._recarregar_preview()

    def _recarregar_preview(self) -> None:
        if not getattr(self, "_caminho_arquivo", None):
            return
        try:
            with open(self._caminho_arquivo, "rb") as f:
                conteudo = f.read()
            if self._formato == "planilha":
                if not self.combo_aba_planilha.currentText():
                    return
                self._df_bruto = ler_planilha(
                    conteudo, self._extensao_arquivo, self.combo_aba_planilha.currentText(),
                    self.checa_cabecalho.isChecked(),
                )
            else:
                if not self._separador_atual():
                    return
                self._df_bruto = ler_arquivo(conteudo, self._separador_atual(), self.checa_cabecalho.isChecked())
        except Exception as exc:
            QMessageBox.critical(self, "Erro ao ler arquivo", f"Não consegui ler o arquivo: {exc}")
            self._df_bruto = None
            return
        self._preencher_previa()
        self._preencher_mapeamento()

    def _preencher_previa(self) -> None:
        df = self._df_bruto.head()
        self.tabela_previa.setRowCount(len(df))
        self.tabela_previa.setColumnCount(len(df.columns))
        self.tabela_previa.setHorizontalHeaderLabels([str(c) for c in df.columns])
        for linha in range(len(df)):
            for coluna in range(len(df.columns)):
                self.tabela_previa.setItem(linha, coluna, QTableWidgetItem(str(df.iat[linha, coluna])))

    def _preencher_mapeamento(self) -> None:
        while self.layout_mapeamento.rowCount():
            self.layout_mapeamento.removeRow(0)
        self._combos_mapeamento.clear()
        for coluna in self._df_bruto.columns:
            combo = QComboBox()
            combo.addItems(list(_CAMPOS_VERTICE))
            self._combos_mapeamento[str(coluna)] = combo
            self.layout_mapeamento.addRow(str(coluna), combo)

    def _atualizar_aviso_utm(self, sistema: str) -> None:
        self.combo_formato_geo.setVisible(sistema == "Geodésica")
        self.linha_utm.setVisible(sistema == "UTM")
        self.aviso_utm.setVisible(sistema == "UTM")

    # --- criar versão ---

    def _mapeamento_atual(self) -> dict[str, str]:
        return {
            coluna: _CAMPOS_VERTICE[combo.currentText()]
            for coluna, combo in self._combos_mapeamento.items()
            if _CAMPOS_VERTICE[combo.currentText()] is not None
        }

    def _converter_utm(self, easting_col, northing_col, meridiano: float, hemisferio: str) -> tuple[list[str], list[str]]:
        longitudes, latitudes = [], []
        for easting_txt, northing_txt in zip(easting_col, northing_col):
            longitude, latitude = utm_para_geodesica(
                parse_numero(easting_txt), parse_numero(northing_txt), meridiano, hemisferio,
            )
            longitudes.append(longitude)
            latitudes.append(latitude)
        return (
            [normaliza_decimal(str(v)) for v in longitudes],
            [normaliza_decimal(str(v)) for v in latitudes],
        )

    def _converter_coordenadas(self, dados: pd.DataFrame, sistema: str) -> None:
        if sistema == "UTM":
            if not {"e_long", "n_lat"} <= set(dados.columns):
                raise ValueError("importação em UTM precisa das colunas de E/Long e N/Lat juntas")
            meridiano = float(self.combo_meridiano.currentText())
            hemisferio = self.combo_hemisferio.currentText()
            dados["e_long"], dados["n_lat"] = self._converter_utm(dados["e_long"], dados["n_lat"], meridiano, hemisferio)
            return

        parser = _PARSERS_GEODESICA[self.combo_formato_geo.currentText()]
        if "e_long" in dados.columns:
            dados["e_long"] = [normaliza_decimal(str(-abs(parser(v)))) for v in dados["e_long"]]
        if "n_lat" in dados.columns:
            dados["n_lat"] = [normaliza_decimal(str(parser(v))) for v in dados["n_lat"]]

    def _criar_versao(self) -> None:
        if self._df_bruto is None:
            QMessageBox.warning(self, "Importar vértices", "Escolha um arquivo válido primeiro.")
            return
        mapeamento = self._mapeamento_atual()
        if len(set(mapeamento.values())) != len(mapeamento.values()):
            QMessageBox.critical(self, "Importar vértices", "Duas colunas do arquivo não podem apontar para o mesmo campo.")
            return
        if "codigo" not in mapeamento.values():
            QMessageBox.warning(self, "Importar vértices", "Escolha qual coluna é o código do vértice — é a chave da importação.")
            return

        dados = self._df_bruto.rename(columns=mapeamento)[list(mapeamento.values())].copy()
        tem_coordenada = {"e_long", "n_lat"} & set(dados.columns)
        sistema = self.combo_sistema.currentText()
        # guarda o E/Long e N/Lat originais (easting/northing) ANTES de
        # sobrescrever com o resultado da conversão — sem isso, perceber
        # que o hemisfério estava errado depois de criar a versão não tem
        # conserto: o dado de origem já teria sido descartado.
        dados_utm_brutos = dados[["e_long", "n_lat"]].copy() if (tem_coordenada and sistema == "UTM") else None
        # mesma ideia do UTM acima, pro caso Geodésica-não-decimal (GMS, grau
        # +minuto, compactado): sem guardar o texto original antes de
        # converter pra grau decimal solto, ele se perdia — pedido do
        # usuário pra manter a forma como veio do arquivo, só pra conferência.
        formato_geo = self.combo_formato_geo.currentText()
        dados_geodesica_original = (
            dados[["e_long", "n_lat"]].copy()
            if (tem_coordenada and sistema == "Geodésica" and formato_geo != _FORMATO_GEO_DECIMAL)
            else None
        )
        if tem_coordenada:
            try:
                self._converter_coordenadas(dados, sistema)
            except (ValorInvalidoError, ValueError) as exc:
                QMessageBox.critical(self, "Importar vértices", f"Não consegui interpretar as coordenadas: {exc}")
                return

        for campo in dados.columns:
            if campo in _CAMPOS_NUMERICOS:
                dados[campo] = dados[campo].map(normaliza_decimal)

        meridiano = float(self.combo_meridiano.currentText()) if sistema == "UTM" else 0.0
        hemisferio = self.combo_hemisferio.currentText() if sistema == "UTM" else ""
        self._criar_aba_importacao(dados, dados_utm_brutos, dados_geodesica_original, meridiano, hemisferio)
        self.rotulo_status.setText(
            f"Nova aba de importação criada ({len(dados)} linha(s)) ao lado da Tabela de Perímetro."
        )
