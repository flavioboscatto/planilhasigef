"""Aplica as cores do modelo oficial (config/theme_tokens.json) na
interface Qt — equivalente a ui/tema.py (Streamlit), trocando HTML/CSS por
QColor/QFont de verdade. Só isso aqui, nenhuma regra de negócio.

Diferença real em relação à versão Streamlit: lá só dava pra colorir o que
o Streamlit desenha como HTML (rótulos de seção) — a grade de vértices
(canvas do st.data_editor) ficava fora do alcance, então a cor por coluna
só aparecia numa prévia à parte, só-leitura. Aqui, QTableView pinta célula
por célula de verdade (Qt.BackgroundRole) na MESMA grade editável — ver
ui_qt/vertices_table.py.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QLabel

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "theme_tokens.json"


@dataclass(frozen=True)
class Papel:
    fundo: QColor
    texto: QColor
    negrito: bool


def carregar_tema() -> dict[str, Papel]:
    """Lê config/theme_tokens.json (mesmo arquivo da versão Streamlit) —
    chamar uma vez na inicialização e repassar o dict adiante, igual
    `tema = _carregar_json("theme_tokens.json")` fazia em app.py."""
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        bruto = json.load(f)
    papeis: dict[str, Papel] = {}
    for nome, dados in bruto.items():
        fundo = QColor(dados["fundo"])
        texto = QColor(dados["texto"]) if dados.get("texto") else QColor("#000000")
        papeis[nome] = Papel(fundo=fundo, texto=texto, negrito=bool(dados.get("negrito")))
    return papeis


def titulo_secao(texto: str, papel: Papel) -> QLabel:
    """Rótulo de seção colorido, igual ao título de seção da planilha
    original (mesma cor de fundo/texto/negrito do estilo de célula real) —
    equivalente a ui/tema.py::titulo_secao."""
    rotulo = QLabel(texto)
    fonte = QFont()
    fonte.setBold(papel.negrito)
    fonte.setPointSize(12)
    rotulo.setFont(fonte)
    rotulo.setStyleSheet(
        f"background-color: {papel.fundo.name()}; color: {papel.texto.name()};"
        " padding: 6px 10px; border-radius: 4px;"
    )
    return rotulo
