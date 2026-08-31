"""Grade de vértices (Qt) — o coração desta migração. Equivalente a
ui/grid.py (Streamlit), mas resolvendo o motivo real da migração: aqui
colar em bloco, preencher pra baixo e marcar checkbox são só estado local
de widget, sem round-trip nenhum — nunca "engolem" a primeira tentativa
nem perdem célula digitada, porque não existe "primeira tentativa que se
perde num rerun": o clique já é o estado final.

Também resolve de graça uma limitação que o Streamlit nunca teve como
resolver: a MESMA grade fica colorida (Qt.BackgroundRole) E editável ao
mesmo tempo — lá precisava de duas grades (editável sem cor + prévia
colorida só-leitura).
"""
from __future__ import annotations

import pandas as pd
from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QGuiApplication, QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHeaderView,
    QStyledItemDelegate,
    QTableView,
)

from core.tabela_vertices import COLUNAS_VERTICE, tabela_vazia
from ui_qt.tema_qt import Papel

_ROTULOS = {
    "renumerar": "Renumerar?",
    "tipo_vertice": "Tipo",
    "codigo": "Vértice",
    "e_long": "E/Long",
    "sigma_long": "Sigma long",
    "n_lat": "N/Lat",
    "sigma_lat": "Sigma lat",
    "h": "h",
    "sigma_h": "Sigma h",
    "metodo_posicionamento": "Método de Posicionamento",
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

_MARCADO = {Qt.CheckState.Checked, Qt.CheckState.Checked.value, 2}


class TabelaVerticesModel(QAbstractTableModel):
    def __init__(
        self,
        tema: dict[str, Papel],
        opcoes_tipo_vertice: list[str],
        opcoes_metodo: list[str],
        opcoes_limite: list[str],
        df: pd.DataFrame | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._tema = tema
        self.opcoes_tipo_vertice = opcoes_tipo_vertice
        self.opcoes_metodo = opcoes_metodo
        self.opcoes_limite = opcoes_limite
        self._df = (df if df is not None else tabela_vazia()).reset_index(drop=True)

    # --- leitura/escrita em bloco (usado por quem envolve a grade) ---

    def dataframe(self) -> pd.DataFrame:
        return self._df.copy()

    def substituir(self, df: pd.DataFrame) -> None:
        self.beginResetModel()
        self._df = df.reset_index(drop=True)
        self.endResetModel()

    def inserir_linha(self, valores: dict | None = None) -> None:
        nova = {c: "" for c in COLUNAS_VERTICE}
        nova["renumerar"] = True
        if valores:
            nova.update(valores)
        pos = len(self._df)
        self.beginInsertRows(QModelIndex(), pos, pos)
        self._df.loc[pos] = nova
        self.endInsertRows()

    def remover_linhas(self, posicoes: list[int]) -> None:
        for pos in sorted(set(posicoes), reverse=True):
            if 0 <= pos < len(self._df):
                self.beginRemoveRows(QModelIndex(), pos, pos)
                self._df = self._df.drop(self._df.index[pos]).reset_index(drop=True)
                self.endRemoveRows()

    def definir_coluna(self, campo: str, valor) -> None:
        """Preenche uma coluna inteira de uma vez (equivalente ao
        "Preencher em lote" do Streamlit) — uma emissão de dataChanged só,
        não uma por célula."""
        coluna = COLUNAS_VERTICE.index(campo)
        self._df[campo] = valor
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

        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            return "" if pd.isna(valor) else str(valor)

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

        if campo == "renumerar" and role == Qt.ItemDataRole.CheckStateRole:
            self._df.iat[index.row(), index.column()] = value in _MARCADO
            self.dataChanged.emit(index, index, [role])
            return True

        if role == Qt.ItemDataRole.EditRole:
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
        self.horizontalHeader().setStretchLastSection(True)

        self.setItemDelegateForColumn(COLUNAS_VERTICE.index("tipo_vertice"), _ComboDelegate(modelo.opcoes_tipo_vertice, self))
        self.setItemDelegateForColumn(
            COLUNAS_VERTICE.index("metodo_posicionamento"), _ComboDelegate(modelo.opcoes_metodo, self)
        )
        self.setItemDelegateForColumn(COLUNAS_VERTICE.index("tipo_limite"), _ComboDelegate(modelo.opcoes_limite, self))

    def keyPressEvent(self, event) -> None:
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
        indices = self.selectionModel().selectedIndexes()
        linhas: dict[int, dict[int, str]] = {}
        for indice in indices:
            linhas.setdefault(indice.row(), {})[indice.column()] = indice.data(Qt.ItemDataRole.DisplayRole) or ""
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
        atual = self.currentIndex()
        if not texto or not atual.isValid():
            return
        modelo = self.model()
        linhas_texto = texto.replace("\r\n", "\n").rstrip("\n").split("\n")
        for deslocamento_linha, linha_texto in enumerate(linhas_texto):
            for deslocamento_coluna, valor in enumerate(linha_texto.split("\t")):
                linha = atual.row() + deslocamento_linha
                coluna = atual.column() + deslocamento_coluna
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
