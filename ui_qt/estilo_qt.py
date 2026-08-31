"""Folha de estilo (QSS) global do app — resolve o problema real relatado:
o estilo nativo do Windows deixa campo de texto/combo quase sem borda em
repouso, e o foco vira só um traço fino, sem destacar o campo inteiro.
Aplicada uma vez, em app_qt.py::main().
"""
from __future__ import annotations

_AZUL_FOCO = "#2f6fed"
_AZUL_FOCO_FUNDO = "#eaf2ff"
_BORDA = "#8b95a1"
_BORDA_HOVER = "#5c6774"

FOLHA_DE_ESTILO = f"""
QWidget {{
    font-size: 10pt;
}}

QLineEdit, QComboBox, QTextEdit {{
    border: 1px solid {_BORDA};
    border-radius: 3px;
    padding: 4px 7px;
    background: #ffffff;
    selection-background-color: {_AZUL_FOCO};
    selection-color: white;
}}
QLineEdit:hover, QComboBox:hover, QTextEdit:hover {{
    border-color: {_BORDA_HOVER};
}}
QLineEdit:focus, QComboBox:focus, QTextEdit:focus {{
    border: 2px solid {_AZUL_FOCO};
    background: {_AZUL_FOCO_FUNDO};
    padding: 3px 6px;
}}
QLineEdit:disabled, QComboBox:disabled {{
    background: #eef0f3;
    color: #8b95a1;
}}
QComboBox::drop-down {{
    border-left: 1px solid {_BORDA};
    width: 22px;
}}

QPushButton {{
    border: 1px solid {_BORDA};
    border-radius: 4px;
    padding: 6px 14px;
    background: #f3f4f6;
}}
QPushButton:hover {{
    background: #e3e7ec;
    border-color: {_BORDA_HOVER};
}}
QPushButton:pressed {{
    background: #cfd6dd;
}}
QPushButton:focus {{
    border: 2px solid {_AZUL_FOCO};
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {_BORDA};
    border-radius: 2px;
    background: white;
}}
QCheckBox::indicator:checked {{
    background: {_AZUL_FOCO};
    border-color: {_AZUL_FOCO};
}}

QTableView {{
    gridline-color: #c7ced6;
    selection-background-color: {_AZUL_FOCO};
    selection-color: white;
    border: 1px solid {_BORDA};
}}
QHeaderView::section {{
    background: #eef0f3;
    border: 1px solid #c7ced6;
    padding: 5px;
    font-weight: 600;
}}

QTabWidget::pane {{
    border: 1px solid #c7ced6;
}}
QTabBar::tab {{
    padding: 8px 18px;
    border: 1px solid #c7ced6;
    border-bottom: none;
    background: #eef0f3;
    margin-right: 2px;
}}
QTabBar::tab:selected {{
    background: white;
    font-weight: 600;
    border-bottom: 3px solid {_AZUL_FOCO};
}}
QTabBar::tab:hover {{
    background: #e3e7ec;
}}
"""
