"""Aba Perímetro (Qt) — equivalente a ui/aba_perimetro.py: campos de
cabeçalho da parcela + a grade de vértices (ui_qt/vertices_table.py) +
botões (Reorganizar, Marcar/Desmarcar todos, Preencher em lote).

Sem a prévia colorida à parte que a versão Streamlit precisava: aqui a
própria grade editável já é colorida (ver ui_qt/vertices_table.py).

Cada arquivo importado (ui_qt/importar_vertices_dialog.py) vira uma
sub-aba própria e persistente aqui dentro ("Importação 1", "Importação
2", ...), ao lado da "Tabela de Perímetro" — ver ui_qt/importacao_tab.py.
"""
from __future__ import annotations

import pandas as pd
from PySide6.QtCore import QItemSelection, QItemSelectionModel
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.importacao import mesclar_por_codigo
from core.models import Perimetro
from core.tabela_vertices import linha_para_vertice, preenchido, vertice_para_linha
from core.validators.geometria import reordena_norte_horario
from ui_qt.importacao_tab import AbaImportacao
from ui_qt.importar_vertices_dialog import ImportarVerticesDialog
from ui_qt.tema_qt import Papel, botao_verde, titulo_secao
from ui_qt.vertices_table import TabelaVerticesModel, TabelaVerticesView

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
        self._proxima_importacao = 1
        self._dialogo_importacao: ImportarVerticesDialog | None = None

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

        btn_importar = botao_verde("Importar vértices de um arquivo (TXT/CSV)...", tema)
        btn_importar.clicked.connect(self._abrir_importador)
        layout.addWidget(btn_importar)

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
        # usuário. O método continua aqui (_reorganizar) porque o painel
        # chama nele na aba atualmente aberta.

        linha_lote = QHBoxLayout()
        self.combo_coluna_lote = _combo(list(_CAMPOS_LOTE))
        self.combo_valor_lote = QComboBox()
        self.combo_coluna_lote.currentTextChanged.connect(self._atualizar_opcoes_lote)
        btn_aplicar_lote = botao_verde("Aplicar a todas as linhas", tema)
        btn_aplicar_lote.clicked.connect(self._aplicar_lote)
        linha_lote.addWidget(QLabel("Preencher em lote:"))
        linha_lote.addWidget(self.combo_coluna_lote)
        linha_lote.addWidget(self.combo_valor_lote)
        linha_lote.addWidget(btn_aplicar_lote)
        layout.addLayout(linha_lote)
        self._atualizar_opcoes_lote(self.combo_coluna_lote.currentText())

        self.subabas = QTabWidget()
        layout.addWidget(self.subabas)

        aba_tabela = QWidget()
        layout_aba_tabela = QVBoxLayout(aba_tabela)
        layout_aba_tabela.setContentsMargins(0, 6, 0, 0)

        self.modelo_tabela = TabelaVerticesModel(
            tema=tema,
            opcoes_tipo_vertice=opcoes_tipo_vertice,
            opcoes_metodo=opcoes_metodo,
            opcoes_limite=opcoes_limite,
            casas=dominios["limites_coordenadas"],
        )
        self.grade = TabelaVerticesView(self.modelo_tabela)
        layout_aba_tabela.addWidget(self.grade)

        barra_linhas = QHBoxLayout()
        btn_add_linha = botao_verde("+ Adicionar vértice", tema)
        btn_remove_linha = botao_verde("- Remover vértice(s) selecionado(s)", tema)
        btn_subir_linha = botao_verde("↑ Subir linha selecionada", tema)
        btn_descer_linha = botao_verde("↓ Descer linha selecionada", tema)
        btn_add_linha.clicked.connect(lambda: self.modelo_tabela.inserir_linha())
        btn_remove_linha.clicked.connect(self._remover_linhas_selecionadas)
        btn_subir_linha.clicked.connect(lambda: self._mover_linha_selecionada(-1))
        btn_descer_linha.clicked.connect(lambda: self._mover_linha_selecionada(1))
        barra_linhas.addWidget(btn_add_linha)
        barra_linhas.addWidget(btn_remove_linha)
        barra_linhas.addWidget(btn_subir_linha)
        barra_linhas.addWidget(btn_descer_linha)
        layout_aba_tabela.addLayout(barra_linhas)

        self.subabas.addTab(aba_tabela, "Tabela de Perímetro")

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

    def _mover_linha_selecionada(self, deslocamento: int) -> None:
        linhas = {indice.row() for indice in self.grade.selectionModel().selectedIndexes()}
        if len(linhas) != 1:
            QMessageBox.warning(self, "Mover vértice", "Selecione uma única linha para subir/descer.")
            return
        nova_pos = self.modelo_tabela.mover_linha(next(iter(linhas)), deslocamento)
        if nova_pos is None:
            return
        # sem isto, a seleção fica na posição antiga (agora ocupada pela
        # linha vizinha) e parece que o clique não fez nada
        linha_esq = self.modelo_tabela.index(nova_pos, 0)
        linha_dir = self.modelo_tabela.index(nova_pos, self.modelo_tabela.columnCount() - 1)
        self.grade.selectionModel().select(
            QItemSelection(linha_esq, linha_dir), QItemSelectionModel.SelectionFlag.ClearAndSelect
        )

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
        # "renumerar" (que não existe em Vertice, só na grade) acompanha o
        # vértice até a nova posição.
        renumerar_por_id = {id(v): bool(linha["renumerar"]) for (_, linha), v in zip(preenchidas, vertices)}
        reordenados = reordena_norte_horario(vertices)

        novas_linhas = []
        for v in reordenados:
            nova = vertice_para_linha(v)
            nova["renumerar"] = renumerar_por_id[id(v)]
            novas_linhas.append(nova)
        # linhas sem código (vagas em branco, pra próximo vértice) não
        # entram no reordenamento — sem isto, elas simplesmente
        # desapareciam da tabela depois de Reorganizar.
        for pos, linha in df.iterrows():
            if not preenchido(linha["codigo"]):
                novas_linhas.append(dict(linha))
        self.modelo_tabela.substituir(pd.DataFrame(novas_linhas))

    def _abrir_importador(self) -> None:
        # não-modal (.show(), não .exec()): o usuário precisa poder ir até a
        # sub-aba "Importação N" recém-criada (recalcular, mesclar) sem
        # precisar fechar o diálogo antes — e pode voltar aqui pra importar
        # mais um arquivo na sequência. self._dialogo_importacao segura a
        # referência viva (senão o Python coletaria o objeto e a janela
        # sumiria sozinha).
        self._dialogo_importacao = ImportarVerticesDialog(
            opcoes_tipo_vertice=[t["codigo"] for t in self._dominios["tipos_vertice"]],
            opcoes_metodo=[m["codigo"] for m in self._dominios["metodos_posicionamento"]],
            opcoes_limite=[t["codigo"] for t in self._dominios["tipos_limite"]],
            meridianos_disponiveis=self._dominios["meridianos_centrais_brasil"],
            hemisferios_disponiveis=self._dominios["hemisferio"],
            meridiano_inicial=float(self.meridiano_central.currentText()),
            hemisferio_inicial=self.hemisferio.currentText(),
            tema=self._tema,
            casas=self._dominios["limites_coordenadas"],
            criar_aba_importacao=self._criar_aba_importacao,
            parent=self,
        )
        self._dialogo_importacao.setModal(False)
        self._dialogo_importacao.show()

    def _criar_aba_importacao(
        self,
        dados: pd.DataFrame,
        dados_utm_brutos: pd.DataFrame | None,
        meridiano: float,
        hemisferio: str,
    ) -> None:
        numero = self._proxima_importacao
        self._proxima_importacao += 1

        aba = AbaImportacao(
            numero=numero,
            dados=dados,
            dados_utm_brutos=dados_utm_brutos,
            meridiano_inicial=meridiano,
            hemisferio_inicial=hemisferio,
            meridianos_disponiveis=self._dominios["meridianos_centrais_brasil"],
            hemisferios_disponiveis=self._dominios["hemisferio"],
            tema=self._tema,
            aplicar_na_parcela=self._aplicar_versao_importada,
            remover_esta_aba=self._remover_aba_importacao,
        )
        self.subabas.addTab(aba, f"Importação {numero}")
        self.subabas.setCurrentWidget(aba)

    def _remover_aba_importacao(self, aba: AbaImportacao) -> None:
        indice = self.subabas.indexOf(aba)
        if indice != -1:
            self.subabas.removeTab(indice)
        aba.deleteLater()

    def _aplicar_versao_importada(self, dados_importados: pd.DataFrame) -> None:
        tabela_mesclada, avisos = mesclar_por_codigo(self.modelo_tabela.dataframe(), dados_importados)
        self.modelo_tabela.substituir(tabela_mesclada)
        for aviso in avisos:
            QMessageBox.warning(self, "Importar vértices", aviso)
        QMessageBox.information(
            self, "Importar vértices",
            f"{len(dados_importados)} vértice(s) mesclado(s) na Tabela de Perímetro.",
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
