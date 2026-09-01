"""Grade de vértices (Qt) — o coração desta migração. Equivalente a
ui/grid.py (Streamlit), mas resolvendo o motivo real da migração: aqui
colar em bloco, preencher pra baixo e marcar checkbox são só estado local
de widget, sem round-trip nenhum — nunca "engolem" a primeira tentativa
nem perdem célula digitada, porque não existe "primeira tentativa que se
perde num rerun": o clique já é o estado final.

Também resolve de graça duas limitações que o Streamlit nunca teve como
resolver com um componente só:
- a MESMA grade fica colorida (Qt.BackgroundRole) E editável ao mesmo
  tempo — lá precisava de duas grades (editável sem cor + prévia colorida
  só-leitura);
- a MESMA célula mostra o valor formatado como sai na planilha final (GMS
  pra coordenada, casas decimais certas pra sigma/h — Qt.DisplayRole) mas
  edita em decimal solto, sem vírgula obrigatória nem símbolo (Qt.EditRole)
  — lá também precisava da prévia à parte só pra mostrar o formato final.
"""
from __future__ import annotations

import pandas as pd
from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, QTimer
from PySide6.QtGui import QGuiApplication, QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHeaderView,
    QStyledItemDelegate,
    QTableView,
)

from core.ods_writer import _fmt_decimal, _fmt_geografica
from core.parsing import ValorInvalidoError, parse_coordenada, parse_numero
from core.tabela_vertices import COLUNAS_VERTICE, tabela_vazia
from ui_qt.tema_qt import MAX_ITENS_VISIVEIS_COMBO, Papel

_COLUNAS_COORDENADA = {"e_long": ("E", "W"), "n_lat": ("N", "S")}
_COLUNAS_SIGMA = {"sigma_long", "sigma_lat", "sigma_h"}

_ROTULOS = {
    "pt_original": "Pt.Original",
    "renumerar": "Renum.",
    "tipo_vertice": "Tipo",
    "codigo": "Vértice",
    "e_long": "E/Long",
    "sigma_long": "Sigma Long",
    "n_lat": "N/Lat",
    "sigma_lat": "Sigma Lat",
    "h": "h",
    "sigma_h": "Sigma h",
    "metodo_posicionamento": "Met. Posic.",
    "tipo_limite": "Tipo Limite",
    "cns": "CNS",
    "matricula": "Matrícula",
    "descritivo": "Descritivo",
}

# mesmos grupos de coluna de ui/grid.py — cor por grupo, igual ao modelo
# oficial (config/theme_tokens.json)
_COLUNAS_GERAL = {
    "codigo", "e_long", "sigma_long", "n_lat", "sigma_lat", "h", "sigma_h",
    "metodo_posicionamento",
}
_COLUNAS_CONFRONTANTE = {"tipo_limite", "cns", "matricula", "descritivo"}

# colunas com o _ComboDelegate (editor de combo) — recebem uma setinha "▾"
# no DisplayRole (célula não editada não tinha nenhuma pista visual de que
# abre um combo, só se descobria clicando) e abrem o editor com um clique
# direto nessa área, não só duplo clique/tecla (ver TabelaVerticesView).
_COLUNAS_COMBO = {"tipo_vertice", "metodo_posicionamento", "tipo_limite"}
_LARGURA_SETA = 20

_MARCADO = {Qt.CheckState.Checked, Qt.CheckState.Checked.value, 2}


def _normalizar_colunas(df: pd.DataFrame) -> pd.DataFrame:
    """Reordena pra ordem exata de COLUNAS_VERTICE, por NOME — nunca
    confiar na ordem que um DataFrame chegou. `pd.DataFrame(lista_de_dicts)`
    usa a ordem das chaves de cada dict, que pode não bater com
    COLUNAS_VERTICE (foi assim que o Reorganizar corrompeu a tabela: a
    grade lê/escreve célula por POSIÇÃO, não por nome de coluna — uma ordem
    diferente faz cada coluna mostrar o dado da vizinha). Coluna ausente
    (ex.: importação que só mapeou algumas colunas do arquivo) ganha o
    padrão em vez de quebrar — só a ORDEM é exigida, não o conjunto
    completo."""
    df = df.reset_index(drop=True)
    for coluna in COLUNAS_VERTICE:
        if coluna not in df.columns:
            df[coluna] = False if coluna == "renumerar" else ""
    return df[COLUNAS_VERTICE]


class TabelaVerticesModel(QAbstractTableModel):
    def __init__(
        self,
        tema: dict[str, Papel],
        opcoes_tipo_vertice: list[str],
        opcoes_metodo: list[str],
        opcoes_limite: list[str],
        casas: dict,
        df: pd.DataFrame | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._tema = tema
        self.opcoes_tipo_vertice = opcoes_tipo_vertice
        self.opcoes_metodo = opcoes_metodo
        self.opcoes_limite = opcoes_limite
        self._casas_segundos = casas["segundos_gms_casas_decimais"]
        self._casas_sigma = casas["sigma_casas_decimais"]
        self._casas_h = casas["h_casas_decimais"]
        self._df = _normalizar_colunas(df if df is not None else tabela_vazia())
        self._pilha_desfazer: list[pd.DataFrame] = []

    # --- leitura/escrita em bloco (usado por quem envolve a grade) ---

    def dataframe(self) -> pd.DataFrame:
        return self._df.copy()

    def _guardar_para_desfazer(self) -> None:
        self._pilha_desfazer.append(self._df.copy())
        if len(self._pilha_desfazer) > 50:
            self._pilha_desfazer.pop(0)

    def desfazer(self) -> bool:
        """Ctrl+Z — volta pro estado de antes da última mudança (edição de
        célula, colar, Reorganizar, Renumerar, Preencher em lote...). Sem
        isso, um resultado errado de qualquer ferramenta que reescreve a
        tabela inteira só se resolvia fechando e abrindo o programa de
        novo."""
        if not self._pilha_desfazer:
            return False
        anterior = self._pilha_desfazer.pop()
        self.beginResetModel()
        self._df = anterior
        self.endResetModel()
        return True

    def substituir(self, df: pd.DataFrame) -> None:
        self._guardar_para_desfazer()
        self.beginResetModel()
        self._df = _normalizar_colunas(df)
        self.endResetModel()

    def inserir_linha(self, valores: dict | None = None) -> None:
        self._guardar_para_desfazer()
        nova = {c: "" for c in COLUNAS_VERTICE}
        nova["renumerar"] = True
        if valores:
            nova.update(valores)
        pos = len(self._df)
        self.beginInsertRows(QModelIndex(), pos, pos)
        self._df.loc[pos] = nova
        self.endInsertRows()

    def mover_linha(self, pos: int, deslocamento: int) -> int | None:
        """Troca a linha `pos` de lugar com a vizinha logo acima
        (deslocamento=-1) ou abaixo (deslocamento=+1) — devolve a nova
        posição, ou None se `pos` já está na ponta correspondente (sem
        vizinha pra trocar). beginMoveRows/endMoveRows (não
        beginResetModel) pra a seleção na QTableView acompanhar a linha
        movida, em vez de se perder."""
        destino = pos + deslocamento
        if not (0 <= pos < len(self._df)) or not (0 <= destino < len(self._df)):
            return None
        self._guardar_para_desfazer()
        # Qt conta a posição de destino ANTES da remoção da linha de
        # origem — mover pra baixo precisa de +1 a mais que o índice final
        # de fato, senão vira exceção ("destinationChild out of bounds").
        destino_qt = destino if deslocamento < 0 else destino + 1
        self.beginMoveRows(QModelIndex(), pos, pos, QModelIndex(), destino_qt)
        ordem = list(range(len(self._df)))
        ordem[pos], ordem[destino] = ordem[destino], ordem[pos]
        self._df = self._df.iloc[ordem].reset_index(drop=True)
        self.endMoveRows()
        return destino

    def remover_linhas(self, posicoes: list[int]) -> None:
        self._guardar_para_desfazer()
        for pos in sorted(set(posicoes), reverse=True):
            if 0 <= pos < len(self._df):
                self.beginRemoveRows(QModelIndex(), pos, pos)
                self._df = self._df.drop(self._df.index[pos]).reset_index(drop=True)
                self.endRemoveRows()

    def definir_coluna(self, campo: str, valor) -> None:
        """Preenche uma coluna inteira de uma vez (equivalente ao
        "Preencher em lote" do Streamlit) — uma emissão de dataChanged só,
        não uma por célula."""
        self._guardar_para_desfazer()
        coluna = COLUNAS_VERTICE.index(campo)
        self._df[campo] = valor
        if len(self._df):
            topo_esq = self.index(0, coluna)
            baixo_dir = self.index(len(self._df) - 1, coluna)
            self.dataChanged.emit(topo_esq, baixo_dir, [Qt.ItemDataRole.DisplayRole])

    def definir_coluna_valores(self, campo: str, valores: list) -> None:
        """Como definir_coluna, mas um valor por linha (não o mesmo valor
        repetido) — usado pra recalcular E/Long e N/Lat de uma importação
        UTM sem mexer nas outras colunas já editadas na grade."""
        self._guardar_para_desfazer()
        coluna = COLUNAS_VERTICE.index(campo)
        self._df[campo] = list(valores)
        if len(self._df):
            topo_esq = self.index(0, coluna)
            baixo_dir = self.index(len(self._df) - 1, coluna)
            self.dataChanged.emit(topo_esq, baixo_dir, [Qt.ItemDataRole.DisplayRole])

    # --- QAbstractTableModel ---

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._df)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(COLUNAS_VERTICE)

    def _campo(self, index: QModelIndex) -> str:
        return COLUNAS_VERTICE[index.column()]

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        campo = self._campo(index)
        valor = self._df.iat[index.row(), index.column()]

        if campo == "renumerar":
            if role == Qt.ItemDataRole.CheckStateRole:
                return Qt.CheckState.Checked if bool(valor) else Qt.CheckState.Unchecked
            return None

        texto = "" if pd.isna(valor) else str(valor)

        if role == Qt.ItemDataRole.EditRole:
            return texto

        if role == Qt.ItemDataRole.DisplayRole:
            if campo in _COLUNAS_COMBO:
                return f"{texto} ▾" if texto.strip() else "▾"
            if texto.strip():
                if campo in _COLUNAS_COORDENADA:
                    sufixo_pos, sufixo_neg = _COLUNAS_COORDENADA[campo]
                    try:
                        return _fmt_geografica(parse_coordenada(texto), sufixo_pos, sufixo_neg, self._casas_segundos)
                    except ValorInvalidoError:
                        return texto
                if campo in _COLUNAS_SIGMA:
                    try:
                        return _fmt_decimal(parse_numero(texto), self._casas_sigma)
                    except ValorInvalidoError:
                        return texto
                if campo == "h":
                    try:
                        return _fmt_decimal(parse_numero(texto), self._casas_h)
                    except ValorInvalidoError:
                        return texto
            return texto

        if role == Qt.ItemDataRole.BackgroundRole:
            if campo in _COLUNAS_GERAL:
                return self._tema["tabela_entrada_geral"].fundo
            if campo in _COLUNAS_CONFRONTANTE:
                return self._tema["tabela_entrada_confrontante"].fundo

        return None

    def setData(self, index: QModelIndex, value, role: int = Qt.ItemDataRole.EditRole) -> bool:
        if not index.isValid():
            return False
        campo = self._campo(index)

        # uma célula por vez (colar em bloco desfaz célula por célula, não
        # o bloco inteiro numa tacada só) — mais simples e sempre correto,
        # mesmo não sendo o Ctrl+Z "perfeito" de um Excel de verdade.
        if campo == "renumerar" and role == Qt.ItemDataRole.CheckStateRole:
            self._guardar_para_desfazer()
            self._df.iat[index.row(), index.column()] = value in _MARCADO
            self.dataChanged.emit(index, index, [role])
            return True

        if role == Qt.ItemDataRole.EditRole:
            self._guardar_para_desfazer()
            self._df.iat[index.row(), index.column()] = value
            self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole, role])
            return True

        return False

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        base = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if self._campo(index) == "renumerar":
            return base | Qt.ItemFlag.ItemIsUserCheckable
        return base | Qt.ItemFlag.ItemIsEditable

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return _ROTULOS[COLUNAS_VERTICE[section]]
        return str(section + 1)


class _ComboDelegate(QStyledItemDelegate):
    def __init__(self, opcoes: list[str], parent=None) -> None:
        super().__init__(parent)
        self._opcoes = opcoes

    def createEditor(self, parent, option, index):
        combo = QComboBox(parent)
        combo.addItems(self._opcoes)
        combo.setMaxVisibleItems(MAX_ITENS_VISIVEIS_COMBO)
        # abre o popup já na hora de entrar na célula — sem isto, dava
        # duplo clique (que abre o editor) e ainda precisava clicar de
        # novo só pra ver as opções.
        QTimer.singleShot(0, combo.showPopup)
        return combo

    def setEditorData(self, editor: QComboBox, index) -> None:
        valor = index.data(Qt.ItemDataRole.EditRole) or ""
        posicao = editor.findText(valor)
        editor.setCurrentIndex(posicao if posicao >= 0 else 0)

    def setModelData(self, editor: QComboBox, model, index) -> None:
        model.setData(index, editor.currentText(), Qt.ItemDataRole.EditRole)


class TabelaVerticesView(QTableView):
    """Colar em bloco (Ctrl+V), copiar (Ctrl+C) e preencher pra baixo
    (Ctrl+D) implementados aqui direto — sem depender de recurso pago de
    componente nenhum (motivo pelo qual ficamos no st.data_editor tanto
    tempo antes: colagem em bloco de verdade era recurso Enterprise do
    AG-Grid)."""

    def __init__(self, modelo: TabelaVerticesModel, parent=None) -> None:
        super().__init__(parent)
        self.setModel(modelo)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ContiguousSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
            | QAbstractItemView.EditTrigger.AnyKeyPressed
        )
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        # Sem esticar a última coluna: "descritivo" precisa de largura
        # própria (3x maior) e continuar redimensionável à mão — a barra de
        # rolagem horizontal (padrão do QTableView) cobre o resto.
        self.horizontalHeader().setStretchLastSection(False)
        self.setColumnWidth(COLUNAS_VERTICE.index("descritivo"), 270)
        self.setColumnWidth(COLUNAS_VERTICE.index("pt_original"), 90)

        self._colunas_combo = {COLUNAS_VERTICE.index(c) for c in _COLUNAS_COMBO}
        # sem largura própria, "Tipo" (coluna estreita, cabeçalho curto)
        # ficava com o combo/seta espremidos contra a borda — "Met. Posic."
        # e "Tipo Limite" só pareciam bons por acaso, por já serem colunas
        # mais largas.
        for campo in _COLUNAS_COMBO:
            self.setColumnWidth(COLUNAS_VERTICE.index(campo), 110)

        self.setItemDelegateForColumn(COLUNAS_VERTICE.index("tipo_vertice"), _ComboDelegate(modelo.opcoes_tipo_vertice, self))
        self.setItemDelegateForColumn(
            COLUNAS_VERTICE.index("metodo_posicionamento"), _ComboDelegate(modelo.opcoes_metodo, self)
        )
        self.setItemDelegateForColumn(COLUNAS_VERTICE.index("tipo_limite"), _ComboDelegate(modelo.opcoes_limite, self))

    def mousePressEvent(self, event) -> None:
        # clicar na setinha (ver TabelaVerticesModel._COLUNAS_COMBO) abre o
        # combo de primeira, sem precisar de duplo clique — clicar no resto
        # da célula continua só selecionando, pra não atrapalhar
        # arrastar/selecionar bloco pra copiar/colar.
        if event.button() == Qt.MouseButton.LeftButton:
            indice = self.indexAt(event.position().toPoint())
            if indice.isValid() and indice.column() in self._colunas_combo:
                retangulo = self.visualRect(indice)
                if event.position().toPoint().x() >= retangulo.right() - _LARGURA_SETA:
                    self.setCurrentIndex(indice)
                    self.edit(indice)
                    return
        super().mousePressEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.matches(QKeySequence.StandardKey.Undo):
            self.model().desfazer()
            return
        if event.matches(QKeySequence.StandardKey.Copy):
            self._copiar()
            return
        if event.matches(QKeySequence.StandardKey.Paste):
            self._colar()
            return
        if event.key() == Qt.Key.Key_D and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self._preencher_para_baixo()
            return
        super().keyPressEvent(event)

    def _selecao_por_linha(self) -> dict[int, dict[int, str]]:
        # EditRole (valor cru), não DisplayRole (formatado em GMS/casas
        # decimais) — copiar/colar/preencher pra baixo precisam do valor
        # editável de verdade, senão o texto formatado (ex. "48 32 52,8 W")
        # ia parar dentro da célula como se fosse o que a pessoa digitou.
        indices = self.selectionModel().selectedIndexes()
        linhas: dict[int, dict[int, str]] = {}
        for indice in indices:
            linhas.setdefault(indice.row(), {})[indice.column()] = indice.data(Qt.ItemDataRole.EditRole) or ""
        return linhas

    def _copiar(self) -> None:
        linhas = self._selecao_por_linha()
        if not linhas:
            return
        colunas = sorted({coluna for valores in linhas.values() for coluna in valores})
        texto = "\n".join(
            "\t".join(linhas.get(linha, {}).get(coluna, "") for coluna in colunas)
            for linha in sorted(linhas)
        )
        QGuiApplication.clipboard().setText(texto)

    def _colar(self) -> None:
        texto = QGuiApplication.clipboard().text()
        if not texto:
            return
        modelo = self.model()
        linhas_texto = texto.replace("\r\n", "\n").rstrip("\n").split("\n")
        bloco = [linha.split("\t") for linha in linhas_texto]

        indices_selecionados = self.selectionModel().selectedIndexes()
        if not indices_selecionados:
            atual = self.currentIndex()
            if not atual.isValid():
                return
            indices_selecionados = [atual]

        # âncora = topo-esquerda da SELEÇÃO, não currentIndex(): depois de
        # selecionar um bloco com o mouse, currentIndex() é a ÚLTIMA célula
        # clicada (normalmente o canto oposto ao início), não a primeira —
        # colar a partir dela fazia o bloco colado "vazar" pra fora da
        # seleção, dando a impressão de que só a última célula recebia o
        # valor.
        linha_topo = min(indice.row() for indice in indices_selecionados)
        coluna_esquerda = min(indice.column() for indice in indices_selecionados)

        if len(bloco) == 1 and len(bloco[0]) == 1 and len(indices_selecionados) > 1:
            # um valor só copiado, colado numa seleção de várias células:
            # preenche a seleção inteira (igual Excel/Sheets) em vez de
            # escrever numa célula só.
            valor = bloco[0][0]
            for indice in indices_selecionados:
                if modelo.flags(indice) & Qt.ItemFlag.ItemIsEditable:
                    modelo.setData(indice, valor, Qt.ItemDataRole.EditRole)
            return

        for deslocamento_linha, linha_valores in enumerate(bloco):
            for deslocamento_coluna, valor in enumerate(linha_valores):
                linha = linha_topo + deslocamento_linha
                coluna = coluna_esquerda + deslocamento_coluna
                if linha >= modelo.rowCount() or coluna >= modelo.columnCount():
                    continue
                indice = modelo.index(linha, coluna)
                if modelo.flags(indice) & Qt.ItemFlag.ItemIsEditable:
                    modelo.setData(indice, valor, Qt.ItemDataRole.EditRole)

    def _preencher_para_baixo(self) -> None:
        linhas = self._selecao_por_linha()
        if len(linhas) < 2:
            return
        modelo = self.model()
        colunas = sorted({coluna for valores in linhas.values() for coluna in valores})
        primeira_linha = min(linhas)
        for coluna in colunas:
            valor = linhas[primeira_linha].get(coluna)
            if valor is None:
                continue
            for linha in sorted(linhas):
                if linha == primeira_linha:
                    continue
                indice = modelo.index(linha, coluna)
                if modelo.flags(indice) & Qt.ItemFlag.ItemIsEditable:
                    modelo.setData(indice, valor, Qt.ItemDataRole.EditRole)
