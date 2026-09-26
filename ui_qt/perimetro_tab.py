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
    QPushButton,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.importacao import mesclar_por_codigo
from core.models import Perimetro, Vertice
from core.tabela_vertices import linha_para_vertice, preenchido, tabela_vazia, vertice_para_linha
from core.validators.geometria import reordena_norte_horario, verificar_autointersecao
from ui_qt.importacao_tab import AbaImportacao
from ui_qt.importar_vertices_dialog import ImportarVerticesDialog
from ui_qt.tema_qt import MAX_ITENS_VISIVEIS_COMBO, Papel, botao_verde, botao_verde_destaque, titulo_secao
from ui_qt.vertices_table import TabelaVerticesModel, TabelaVerticesView
from ui_qt.visualizar_parcela_dialog import VisualizarParcelaDialog

_CAMPOS_LOTE = {
    "Tipo": "tipo_vertice",
    "Método de Posicionamento": "metodo_posicionamento",
    "Tipo de Limite": "tipo_limite",
}


def _combo(itens: list[str]) -> QComboBox:
    caixa = QComboBox()
    caixa.addItems(itens)
    caixa.setMaxVisibleItems(MAX_ITENS_VISIVEIS_COMBO)
    # sem isto, um domínio de opções curtas (Sul/Norte, Externo/Interno...)
    # deixava a caixa estreita — texto e seta ficavam espremidos contra a
    # borda ("embolado"). Largura mínima por número de caracteres, não
    # pixels fixos, pra acompanhar fonte/DPI.
    caixa.setMinimumContentsLength(12)
    caixa.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
    return caixa


def _form(rotulo: str, campo: QWidget) -> QVBoxLayout:
    layout = QVBoxLayout()
    layout.addWidget(QLabel(rotulo))
    layout.addWidget(campo)
    return layout


class AbaPerimetro(QWidget):
    def __init__(
        self, indice: int, dominios: dict, tema: dict[str, Papel], painel_numeracao=None
    ) -> None:
        super().__init__()
        self.indice = indice
        self._dominios = dominios
        self._tema = tema
        # Renumerar/Atualizar código continuam contando entre TODAS as
        # parcelas (core/numeracao.py) — os campos de Credenciado/Formato/
        # Próximo nº moram só no painel compartilhado (ui_qt/
        # renumeracao_panel.py), então o botão daqui só delega pra lá, não
        # duplica estado por parcela.
        self._painel_numeracao = painel_numeracao
        self._proxima_importacao = 1
        self._dialogo_importacao: ImportarVerticesDialog | None = None
        self._dialogo_importacao_planilha: ImportarVerticesDialog | None = None
        self._dialogo_visualizacao: VisualizarParcelaDialog | None = None

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

        layout.addWidget(
            QLabel(
                "E/Long e N/Lat aceitam grau decimal (-48,548) ou GMS (48 32 52,8 W). "
                "Ctrl+C/Ctrl+V copiam e colam em bloco; Ctrl+D preenche a seleção com o "
                "valor da linha de cima."
            )
        )

        # Marcar todos/Desmarcar todos/Desfazer moraram aqui antes — subiram
        # pro painel de Numeração (faixa horizontal acima das abas), lado a
        # lado com Renumerar/Atualizar, a pedido do usuário. Reorganizar fez
        # o caminho inverso (voltou pra cá, ver barra_visualizacao mais
        # abaixo): já nasce dentro da aba que afeta.

        linha_lote = QHBoxLayout()
        self.combo_coluna_lote = _combo(list(_CAMPOS_LOTE))
        self.combo_valor_lote = QComboBox()
        self.combo_valor_lote.setMaxVisibleItems(MAX_ITENS_VISIVEIS_COMBO)
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

        def _botao_grade(texto: str, destaque: bool = False, icone: str | None = None) -> QPushButton:
            # destaque=True (negrito + borda mais grossa): pedido da
            # turma-teste pra ressaltar as ações mais usadas/importantes
            # (Renumerar, Reorganizar, Visualizar parcela) das demais.
            botao = (botao_verde_destaque if destaque else botao_verde)(texto, tema, icone)
            botao.setMinimumWidth(150)
            botao.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            return botao

        # 8 botões em 2 fileiras de 4: Marcar/Desmarcar/Atualizar/Renumerar
        # (vieram do painel de Numeração pra cá, a pedido do usuário — ficam
        # junto da grade que eles afetam) em cima de Adicionar/Remover/
        # Subir/Descer, que já moravam aqui.
        barra_numeracao = QHBoxLayout()
        btn_marcar = _botao_grade("Marcar todos", icone="fa5s.check-square")
        btn_marcar.setToolTip('Marca "Renumerar?" em toda a grade desta parcela.')
        btn_marcar.clicked.connect(lambda: self.modelo_tabela.definir_coluna("renumerar", True))
        btn_desmarcar = _botao_grade("Desmarcar todos", icone="fa5.square")
        btn_desmarcar.setToolTip('Desmarca "Renumerar?" em toda a grade desta parcela.')
        btn_desmarcar.clicked.connect(lambda: self.modelo_tabela.definir_coluna("renumerar", False))
        btn_atualizar = _botao_grade("Atualizar código (só o Tipo)", icone="fa5s.sync")
        btn_atualizar.setToolTip(
            "Já renumerou e corrigiu o Tipo de algum vértice na grade? Isto "
            "reescreve só o pedaço do Tipo no código, sem reatribuir número."
        )
        btn_atualizar.clicked.connect(self._atualizar_tipos)
        btn_renumerar = _botao_grade("Renumerar vértices marcados", destaque=True, icone="fa5s.sort-numeric-down")
        btn_renumerar.setToolTip(
            'Só linhas com "Renumerar?" marcado recebem código novo, em todas '
            "as parcelas abertas — desmarque vértices que não são seus."
        )
        btn_renumerar.clicked.connect(self._renumerar)
        barra_numeracao.addWidget(btn_marcar)
        barra_numeracao.addWidget(btn_desmarcar)
        barra_numeracao.addWidget(btn_atualizar)
        barra_numeracao.addWidget(btn_renumerar)
        layout_aba_tabela.addLayout(barra_numeracao)

        barra_linhas = QHBoxLayout()
        btn_add_linha = _botao_grade("Adicionar vértice", icone="fa5s.plus-circle")
        btn_remove_linha = _botao_grade("Remover vértice(s) selecionado(s)", icone="fa5s.minus-circle")
        btn_subir_linha = _botao_grade("Subir linha selecionada", icone="fa5s.arrow-up")
        btn_descer_linha = _botao_grade("Descer linha selecionada", icone="fa5s.arrow-down")
        btn_add_linha.clicked.connect(lambda: self.modelo_tabela.inserir_linha())
        btn_remove_linha.clicked.connect(self._remover_linhas_selecionadas)
        btn_subir_linha.clicked.connect(lambda: self._mover_linha_selecionada(-1))
        btn_descer_linha.clicked.connect(lambda: self._mover_linha_selecionada(1))
        barra_linhas.addWidget(btn_add_linha)
        barra_linhas.addWidget(btn_remove_linha)
        barra_linhas.addWidget(btn_subir_linha)
        barra_linhas.addWidget(btn_descer_linha)
        layout_aba_tabela.addLayout(barra_linhas)

        # fileira própria, não mexe no 2x4 já fechado a pedido do usuário —
        # Reorganizar/Visualizar são conferência/arrumação do perímetro, não
        # ações de linha da grade. Reorganizar morava no painel de Numeração
        # (agia só na aba "atual" por indireção) — desceu pra cá porque já
        # nasce dentro da aba que afeta, sem precisar dessa indireção.
        barra_visualizacao = QHBoxLayout()
        btn_reorganizar = _botao_grade("Reorganizar vértices", destaque=True, icone="fa5s.sync-alt")
        btn_reorganizar.setToolTip("Reorganiza a grade desta parcela (mais ao norte, sentido horário).")
        btn_reorganizar.clicked.connect(self._reorganizar)
        barra_visualizacao.addWidget(btn_reorganizar)

        btn_visualizar = _botao_grade("Visualizar parcela", destaque=True, icone="fa5s.search")
        btn_visualizar.setToolTip(
            "Desenha os vértices e o perímetro fechado desta parcela, avisando se "
            "algum lado se cruza com outro."
        )
        btn_visualizar.clicked.connect(self._abrir_visualizacao)
        barra_visualizacao.addWidget(btn_visualizar)
        layout_aba_tabela.addLayout(barra_visualizacao)

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

    def _renumerar(self) -> None:
        if self._painel_numeracao is not None:
            self._painel_numeracao._renumerar()

    def _atualizar_tipos(self) -> None:
        if self._painel_numeracao is not None:
            self._painel_numeracao._atualizar_tipos()

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
        # "renumerar" e "pt_original" (nenhum dos dois existe em Vertice, só
        # na grade — core/tabela_vertices.py) acompanham o vértice até a
        # nova posição. Bug relatado: "pt_original" sumia depois de
        # Reorganizar, antes mesmo de renumerar — o profissional perdia a
        # referência de qual vértice importado era qual.
        renumerar_por_id = {id(v): bool(linha["renumerar"]) for (_, linha), v in zip(preenchidas, vertices)}
        pt_original_por_id = {id(v): linha["pt_original"] for (_, linha), v in zip(preenchidas, vertices)}
        reordenados = reordena_norte_horario(vertices)

        novas_linhas = []
        for v in reordenados:
            nova = vertice_para_linha(v)
            nova["renumerar"] = renumerar_por_id[id(v)]
            nova["pt_original"] = pt_original_por_id[id(v)]
            novas_linhas.append(nova)
        # linhas sem código (vagas em branco, pra próximo vértice) não
        # entram no reordenamento — sem isto, elas simplesmente
        # desapareciam da tabela depois de Reorganizar.
        for pos, linha in df.iterrows():
            if not preenchido(linha["codigo"]):
                novas_linhas.append(dict(linha))
        self.modelo_tabela.substituir(pd.DataFrame(novas_linhas))

        # Reorganizar só rotaciona/inverte a ordem existente — se os
        # vértices já estavam fora de sequência (perímetro "borboleta"),
        # isso continua depois de reorganizado; avisa mas não bloqueia.
        cruzamentos = verificar_autointersecao(reordenados)
        if cruzamentos:
            mensagens = "\n".join(c.mensagem for c in cruzamentos)
            QMessageBox.warning(
                self, "Reorganizar",
                f"Atenção: o perímetro reorganizado tem lados que se cruzam.\n\n{mensagens}",
            )

    def _limpar_parcela(self) -> None:
        # apaga só a grade de vértices (Tabela de Perímetro) — cabeçalho
        # (Denominação/Parcela número/Lado/etc.) e sub-abas de importação
        # continuam intactos, já que "limpar" aqui é sobre o conteúdo da
        # planilha, não sobre a identidade da parcela. Confirmação porque é
        # destrutivo (ainda que desfazível com Ctrl+Z, via
        # modelo_tabela.substituir -> _guardar_para_desfazer).
        resposta = QMessageBox.question(
            self, "Limpar parcela",
            "Isso apaga todos os vértices da Tabela de Perímetro desta parcela "
            "(dá pra desfazer com Ctrl+Z logo em seguida). Continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if resposta != QMessageBox.StandardButton.Yes:
            return
        self.modelo_tabela.substituir(tabela_vazia())

    def _vertices_preenchidos(self) -> list[Vertice]:
        df = self.modelo_tabela.dataframe()
        return [linha_para_vertice(linha) for _, linha in df.iterrows() if preenchido(linha["codigo"])]

    def _abrir_visualizacao(self) -> None:
        # não-modal, mesmo motivo de _abrir_importador: segura a referência
        # viva (senão o Python coletaria o objeto e a janela sumiria
        # sozinha) e deixa o usuário continuar editando a grade por trás,
        # clicando "Atualizar" no diálogo pra ver o resultado novo.
        self._dialogo_visualizacao = VisualizarParcelaDialog(
            obter_vertices=self._vertices_preenchidos,
            meridiano_central=float(self.meridiano_central.currentText()),
            hemisferio=self.hemisferio.currentText(),
            parent=self,
        )
        self._dialogo_visualizacao.setModal(False)
        self._dialogo_visualizacao.show()

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

    def _abrir_importador_planilha(self) -> None:
        # mesmo diálogo de _abrir_importador, só com formato="planilha"
        # (XLS/XLSX/ODS em vez de TXT/CSV) — a prévia/mapeamento de coluna/
        # "Criar versão a partir deste arquivo" são os mesmos, então reusar
        # a classe evita duplicar toda essa lógica. Instância própria (não
        # a mesma de _dialogo_importacao) pra dar pra ter os dois diálogos
        # abertos ao mesmo tempo.
        self._dialogo_importacao_planilha = ImportarVerticesDialog(
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
            formato="planilha",
            parent=self,
        )
        self._dialogo_importacao_planilha.setModal(False)
        self._dialogo_importacao_planilha.show()

    def _criar_aba_importacao(
        self,
        dados: pd.DataFrame,
        dados_utm_brutos: pd.DataFrame | None,
        dados_geodesica_original: pd.DataFrame | None,
        meridiano: float,
        hemisferio: str,
    ) -> None:
        numero = self._proxima_importacao
        self._proxima_importacao += 1

        aba = AbaImportacao(
            numero=numero,
            dados=dados,
            dados_utm_brutos=dados_utm_brutos,
            dados_geodesica_original=dados_geodesica_original,
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
