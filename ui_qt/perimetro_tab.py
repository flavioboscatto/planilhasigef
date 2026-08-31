"""Aba Perímetro (Qt) — equivalente a ui/aba_perimetro.py: campos de
cabeçalho da parcela + a grade de vértices (ui_qt/vertices_table.py) +
botões (Reorganizar, Marcar/Desmarcar todos, Preencher em lote).

Sem a prévia colorida à parte que a versão Streamlit precisava: aqui a
própria grade editável já é colorida (ver ui_qt/vertices_table.py).
"""
from __future__ import annotations

import pandas as pd
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

from PySide6.QtCore import Qt

from core.geo import utm_para_geodesica
from core.importacao import mesclar_por_codigo
from core.models import Perimetro
from core.parsing import normaliza_decimal, parse_numero
from core.tabela_vertices import linha_para_vertice, preenchido, vertice_para_linha
from core.validators.geometria import reordena_norte_horario
from ui_qt.importar_vertices_dialog import ImportarVerticesDialog
from ui_qt.tema_qt import Papel, titulo_secao
from ui_qt.vertices_table import COLUNAS_VERTICE, TabelaVerticesModel, TabelaVerticesView

_CAMPOS_LOTE = {
    "Tipo": "tipo_vertice",
    "Método de Posicionamento": "metodo_posicionamento",
    "Tipo de Limite": "tipo_limite",
}


def _combo(itens: list[str]) -> QComboBox:
    caixa = QComboBox()
    caixa.addItems(itens)
    caixa.setMaxVisibleItems(20)
    return caixa


def _botao_verde(texto: str, tema: dict) -> QPushButton:
    """Botões de ação desta aba em verde claro (mesma cor de
    "perimetro_entrada" no modelo oficial) — pedido do usuário pra
    diferenciar visualmente as ações da aba Perímetro do resto do app."""
    cor = tema["perimetro_entrada"].fundo
    botao = QPushButton(texto)
    botao.setStyleSheet(
        f"QPushButton {{ background: {cor.name()}; border: 1px solid {cor.darker(140).name()}; }}"
        f"QPushButton:hover {{ background: {cor.darker(108).name()}; }}"
        f"QPushButton:pressed {{ background: {cor.darker(120).name()}; }}"
    )
    return botao


def _form(rotulo: str, campo: QWidget) -> QVBoxLayout:
    layout = QVBoxLayout()
    layout.addWidget(QLabel(rotulo))
    layout.addWidget(campo)
    return layout


class AbaPerimetro(QWidget):
    def __init__(self, indice: int, dominios: dict, tema: dict[str, Papel]) -> None:
        super().__init__()
        self.indice = indice
        self._dominios = dominios
        self._tema = tema

        opcoes_tipo_vertice = [t["codigo"] for t in dominios["tipos_vertice"]]
        opcoes_metodo = [m["codigo"] for m in dominios["metodos_posicionamento"]]
        opcoes_limite = [t["codigo"] for t in dominios["tipos_limite"]]

        layout = QVBoxLayout(self)
        layout.addWidget(
            titulo_secao(f"Tabela de Perímetro — Parcela {indice}", tema["perimetro_titulo"])
        )

        linha_cabecalho = QHBoxLayout()
        self.denominacao = QLineEdit(f"Parte {indice}")
        self.parcela_numero = QLineEdit(f"{indice:03d}")
        linha_cabecalho.addLayout(_form("Denominação", self.denominacao))
        linha_cabecalho.addLayout(_form("Parcela número", self.parcela_numero))

        self.lado = _combo(dominios["lado"])
        self.tipo_coordenada = _combo(dominios["tipo_coordenada"])
        linha_cabecalho.addLayout(_form("Lado", self.lado))
        linha_cabecalho.addLayout(_form("Tipo de Coordenada", self.tipo_coordenada))

        self.meridiano_central = _combo([str(m) for m in dominios["meridianos_centrais_brasil"]])
        self.meridiano_central.setCurrentText("-51")
        self.hemisferio = _combo(dominios["hemisferio"])
        self.hemisferio.setCurrentText("Sul")
        linha_cabecalho.addLayout(_form("Meridiano Central (°)", self.meridiano_central))
        linha_cabecalho.addLayout(_form("Hemisfério", self.hemisferio))
        layout.addLayout(linha_cabecalho)

        linha_importar = QHBoxLayout()
        btn_importar = _botao_verde("Importar vértices de um arquivo (TXT/CSV)...", tema)
        btn_importar.clicked.connect(self._abrir_importador)
        linha_importar.addWidget(btn_importar, 2)
        btn_recalcular_utm = _botao_verde("🔄 Recalcular geodésica (vértices de UTM)", tema)
        btn_recalcular_utm.setToolTip(
            "Vértices trazidos de uma importação UTM guardam o easting/northing "
            "original — mudou o Meridiano Central ou o Hemisfério acima? Clique "
            "aqui pra recalcular E/Long e N/Lat sem reimportar o arquivo."
        )
        btn_recalcular_utm.clicked.connect(self._recalcular_utm)
        linha_importar.addWidget(btn_recalcular_utm, 1)
        layout.addLayout(linha_importar)

        layout.addWidget(
            QLabel(
                "E/Long e N/Lat aceitam grau decimal (-48,548) ou GMS (48 32 52,8 W). "
                "Ctrl+C/Ctrl+V copiam e colam em bloco; Ctrl+D preenche a seleção com o "
                "valor da linha de cima."
            )
        )

        # Reorganizar/Marcar todos/Desmarcar todos/Desfazer moraram aqui
        # antes — subiram pro painel de Numeração (faixa horizontal acima
        # das abas), lado a lado com Renumerar/Atualizar, a pedido do
        # usuário. Os métodos continuam aqui (_reorganizar, modelo_tabela.
        # desfazer()) porque o painel chama neles na aba atualmente aberta.

        linha_lote = QHBoxLayout()
        self.combo_coluna_lote = _combo(list(_CAMPOS_LOTE))
        self.combo_valor_lote = QComboBox()
        self.combo_coluna_lote.currentTextChanged.connect(self._atualizar_opcoes_lote)
        btn_aplicar_lote = _botao_verde("Aplicar a todas as linhas", tema)
        btn_aplicar_lote.clicked.connect(self._aplicar_lote)
        linha_lote.addWidget(QLabel("Preencher em lote:"))
        linha_lote.addWidget(self.combo_coluna_lote)
        linha_lote.addWidget(self.combo_valor_lote)
        linha_lote.addWidget(btn_aplicar_lote)
        layout.addLayout(linha_lote)
        self._atualizar_opcoes_lote(self.combo_coluna_lote.currentText())

        self.modelo_tabela = TabelaVerticesModel(
            tema=tema,
            opcoes_tipo_vertice=opcoes_tipo_vertice,
            opcoes_metodo=opcoes_metodo,
            opcoes_limite=opcoes_limite,
            casas=dominios["limites_coordenadas"],
        )
        self.grade = TabelaVerticesView(self.modelo_tabela)
        layout.addWidget(self.grade)

        barra_linhas = QHBoxLayout()
        btn_add_linha = _botao_verde("+ Adicionar vértice", tema)
        btn_remove_linha = _botao_verde("- Remover vértice(s) selecionado(s)", tema)
        btn_add_linha.clicked.connect(lambda: self.modelo_tabela.inserir_linha())
        btn_remove_linha.clicked.connect(self._remover_linhas_selecionadas)
        barra_linhas.addWidget(btn_add_linha)
        barra_linhas.addWidget(btn_remove_linha)
        layout.addLayout(barra_linhas)

    def _atualizar_opcoes_lote(self, escolha: str) -> None:
        mapa_opcoes = {
            "Tipo": [t["codigo"] for t in self._dominios["tipos_vertice"]],
            "Método de Posicionamento": [m["codigo"] for m in self._dominios["metodos_posicionamento"]],
            "Tipo de Limite": [t["codigo"] for t in self._dominios["tipos_limite"]],
        }
        self.combo_valor_lote.clear()
        self.combo_valor_lote.addItems(mapa_opcoes[escolha])

    def _aplicar_lote(self) -> None:
        campo = _CAMPOS_LOTE[self.combo_coluna_lote.currentText()]
        self.modelo_tabela.definir_coluna(campo, self.combo_valor_lote.currentText())

    def _remover_linhas_selecionadas(self) -> None:
        linhas = {indice.row() for indice in self.grade.selectionModel().selectedIndexes()}
        self.modelo_tabela.remover_linhas(sorted(linhas))

    def _reorganizar(self) -> None:
        df = self.modelo_tabela.dataframe()
        preenchidas = [(pos, linha) for pos, linha in df.iterrows() if preenchido(linha["codigo"])]
        if len(preenchidas) < 3:
            QMessageBox.warning(
                self, "Reorganizar",
                "Precisa de pelo menos 3 vértices com código preenchido para reorganizar.",
            )
            return

        vertices = [linha_para_vertice(linha) for _, linha in preenchidas]
        # reordena_norte_horario só reordena/inverte a lista (não cria Vertice
        # novo), então id(v) ainda identifica a linha original — é assim que
        # "renumerar" e as colunas internas de UTM (nenhuma das duas existe
        # em Vertice, só na grade) acompanham o vértice até a nova posição.
        renumerar_por_id = {id(v): bool(linha["renumerar"]) for (_, linha), v in zip(preenchidas, vertices)}
        utm_por_id = {
            id(v): (linha.get("_utm_easting", ""), linha.get("_utm_northing", ""))
            for (_, linha), v in zip(preenchidas, vertices)
        }
        reordenados = reordena_norte_horario(vertices)

        novas_linhas = []
        for v in reordenados:
            nova = vertice_para_linha(v)
            nova["renumerar"] = renumerar_por_id[id(v)]
            nova["_utm_easting"], nova["_utm_northing"] = utm_por_id[id(v)]
            novas_linhas.append(nova)
        # linhas sem código (vagas em branco, pra próximo vértice) não
        # entram no reordenamento — sem isto, elas simplesmente
        # desapareciam da tabela depois de Reorganizar.
        for pos, linha in df.iterrows():
            if not preenchido(linha["codigo"]):
                novas_linhas.append(dict(linha))
        self.modelo_tabela.substituir(pd.DataFrame(novas_linhas))

    def _abrir_importador(self) -> None:
        dialogo = ImportarVerticesDialog(
            opcoes_tipo_vertice=[t["codigo"] for t in self._dominios["tipos_vertice"]],
            opcoes_metodo=[m["codigo"] for m in self._dominios["metodos_posicionamento"]],
            opcoes_limite=[t["codigo"] for t in self._dominios["tipos_limite"]],
            meridianos_disponiveis=self._dominios["meridianos_centrais_brasil"],
            hemisferios_disponiveis=self._dominios["hemisferio"],
            meridiano_inicial=float(self.meridiano_central.currentText()),
            hemisferio_inicial=self.hemisferio.currentText(),
            tema=self._tema,
            casas=self._dominios["limites_coordenadas"],
            aplicar_versao=self._aplicar_versao_importada,
            parent=self,
        )
        dialogo.exec()

    def _aplicar_versao_importada(self, dados_importados: pd.DataFrame) -> None:
        # mesclar_por_codigo copia QUALQUER coluna presente em
        # dados_importados, inclusive as internas de UTM (ver
        # ui_qt/vertices_table.py) — não precisa de nada especial aqui.
        tabela_mesclada, avisos = mesclar_por_codigo(self.modelo_tabela.dataframe(), dados_importados)
        self.modelo_tabela.substituir(tabela_mesclada)
        for aviso in avisos:
            QMessageBox.warning(self, "Importar vértices", aviso)

    def _recalcular_utm(self) -> None:
        linhas = self.modelo_tabela.linhas_com_utm_bruto()
        if not linhas:
            QMessageBox.information(
                self, "Recalcular geodésica",
                "Nenhum vértice desta parcela veio de uma importação UTM ainda "
                "(ou os que vieram não guardam mais o dado original).",
            )
            return
        meridiano = float(self.meridiano_central.currentText())
        hemisferio = self.hemisferio.currentText()
        col_elong = COLUNAS_VERTICE.index("e_long")
        col_nlat = COLUNAS_VERTICE.index("n_lat")
        for pos in linhas:
            easting, northing = self.modelo_tabela.utm_bruto(pos)
            longitude, latitude = utm_para_geodesica(parse_numero(easting), parse_numero(northing), meridiano, hemisferio)
            self.modelo_tabela.setData(self.modelo_tabela.index(pos, col_elong), normaliza_decimal(str(longitude)), Qt.ItemDataRole.EditRole)
            self.modelo_tabela.setData(self.modelo_tabela.index(pos, col_nlat), normaliza_decimal(str(latitude)), Qt.ItemDataRole.EditRole)
        QMessageBox.information(
            self, "Recalcular geodésica",
            f"{len(linhas)} vértice(s) recalculado(s) com Meridiano {meridiano:g}° / Hemisfério {hemisferio}.",
        )

    def modelo(self) -> Perimetro:
        df = self.modelo_tabela.dataframe()
        vertices = [linha_para_vertice(linha) for _, linha in df.iterrows() if preenchido(linha["codigo"])]
        return Perimetro(
            denominacao=self.denominacao.text(),
            parcela_numero=self.parcela_numero.text(),
            lado=self.lado.currentText(),
            tipo_coordenada=self.tipo_coordenada.currentText(),
            meridiano_central=float(self.meridiano_central.currentText()),
            hemisferio=self.hemisferio.currentText(),
            vertices=vertices,
        )

    def carregar_cabecalho(self, dados: Perimetro) -> None:
        self.denominacao.setText(dados.denominacao)
        self.parcela_numero.setText(dados.parcela_numero)
        self.lado.setCurrentText(dados.lado)
        self.tipo_coordenada.setCurrentText(dados.tipo_coordenada)
        if dados.meridiano_central is not None:
            self.meridiano_central.setCurrentText(str(int(dados.meridiano_central)))
        self.hemisferio.setCurrentText(dados.hemisferio)
