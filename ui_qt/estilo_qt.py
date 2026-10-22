"""Folha de estilo (QSS) global do app — resolve o problema real relatado:
o estilo nativo do Windows deixa campo de texto/combo quase sem borda em
repouso, e o foco vira só um traço fino, sem destacar o campo inteiro.

Tema Claro/Escuro/Automático (pedido da turma-teste): o app roda com o
estilo Fusion, que acompanha o esquema de cores do Windows. A folha de
estilo antiga fixava fundos CLAROS sem definir a cor do texto — no Windows
em modo escuro o texto herdava a cor clara da paleta e sumia sobre o fundo
claro (botões e abas "invisíveis"). Agora toda regra que define fundo
também define a cor do texto, a partir de uma paleta por tema.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPen
from PySide6.QtWidgets import QApplication

TEMA_AUTOMATICO = "automatico"
TEMA_CLARO = "claro"
TEMA_ESCURO = "escuro"
TEMAS = (TEMA_AUTOMATICO, TEMA_CLARO, TEMA_ESCURO)

_ESQUEMA_QT = {
    TEMA_AUTOMATICO: Qt.ColorScheme.Unknown,  # Unknown = volta a seguir o Windows
    TEMA_CLARO: Qt.ColorScheme.Light,
    TEMA_ESCURO: Qt.ColorScheme.Dark,
}

_IMAGEM_CHECK = Path(tempfile.gettempdir()) / "PlanSIGEF_tema" / "check_v1.png"
_IMAGEM_CHECK_QSS = f'image: url("{_IMAGEM_CHECK.as_posix()}");'

_PALETA_CLARA = {
    "texto": "#1f2933",
    "texto_suave": "#55606b",
    "campo_fundo": "#ffffff",
    "borda": "#6f7a86",
    "borda_hover": "#4a5560",
    "foco": "#2f6fed",
    "foco_fundo": "#eaf2ff",
    "desab_fundo": "#eef0f3",
    "desab_texto": "#8b95a1",
    "botao_fundo": "#eceff3",
    "botao_hover": "#dfe4ea",
    "botao_pressed": "#cbd3dc",
    "botao_relevo": "#8f9ba7",
    "grade": "#b4bcc6",
    "cabecalho_fundo": "#e4e8ed",
    "aba_fundo": "#e4e8ed",
    "aba_texto": "#3b4652",
    "aba_hover": "#d6dce4",
    "aba_selecionada": "#ffffff",
    "tabela_fundo": "#ffffff",
}

_PALETA_ESCURA = {
    "texto": "#e6e9ee",
    "texto_suave": "#a7b0bb",
    "campo_fundo": "#2a2e35",
    "borda": "#78838f",
    "borda_hover": "#a0abb7",
    "foco": "#5b94ff",
    "foco_fundo": "#26334d",
    "desab_fundo": "#24272c",
    "desab_texto": "#7c8691",
    "botao_fundo": "#3b414a",
    "botao_hover": "#474e58",
    "botao_pressed": "#2f343b",
    "botao_relevo": "#1b1e22",
    "grade": "#4a525c",
    "cabecalho_fundo": "#343a42",
    "aba_fundo": "#2c3037",
    "aba_texto": "#b8c0ca",
    "aba_hover": "#383e46",
    "aba_selecionada": "#1e1e1e",
    "tabela_fundo": "#23262b",
}


def _garantir_imagem_check() -> bool:
    """Gera (uma vez) o PNG do visto das caixas de seleção. O QSS só desenha
    o visto de um indicador estilizado via `image: url(...)` — sem isto a
    caixa marcada ficava um bloco liso, sem indicar o estado. Pasta
    temporária do sistema (o .exe onefile já extrai ali mesmo)."""
    if _IMAGEM_CHECK.exists():
        return True
    try:
        _IMAGEM_CHECK.parent.mkdir(parents=True, exist_ok=True)
        imagem = QImage(16, 16, QImage.Format.Format_ARGB32)
        imagem.fill(Qt.GlobalColor.transparent)
        pintor = QPainter(imagem)
        pintor.setRenderHint(QPainter.RenderHint.Antialiasing)
        pintor.setPen(QPen(QColor("#1f2933"), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        pintor.drawPolyline([QPointF(3.5, 8.5), QPointF(6.8, 11.8), QPointF(12.5, 4.8)])
        pintor.end()
        return imagem.save(str(_IMAGEM_CHECK))
    except OSError:
        return False


def gerar_folha_de_estilo(escuro: bool = False) -> str:
    p = _PALETA_ESCURA if escuro else _PALETA_CLARA
    return f"""
QWidget {{
    font-size: 10pt;
}}

QLabel[rotuloPequeno="true"] {{
    font-size: 8.5pt;
    color: {p['texto_suave']};
}}

QLineEdit, QComboBox, QTextEdit {{
    border: 1px solid {p['borda']};
    border-radius: 3px;
    padding: 4px 7px;
    background: {p['campo_fundo']};
    color: {p['texto']};
    selection-background-color: {p['foco']};
    selection-color: white;
}}
QLineEdit:hover, QComboBox:hover, QTextEdit:hover {{
    border-color: {p['borda_hover']};
}}
QLineEdit:focus, QComboBox:focus, QTextEdit:focus {{
    border: 2px solid {p['foco']};
    background: {p['foco_fundo']};
    padding: 3px 6px;
}}
QLineEdit:disabled, QComboBox:disabled {{
    background: {p['desab_fundo']};
    color: {p['desab_texto']};
}}
QComboBox::drop-down {{
    border-left: 1px solid {p['borda']};
    width: 22px;
}}
QComboBox QAbstractItemView {{
    background: {p['campo_fundo']};
    color: {p['texto']};
    selection-background-color: {p['foco']};
    selection-color: white;
}}

QPushButton {{
    border: 1px solid {p['borda']};
    border-bottom: 2px solid {p['botao_relevo']};
    border-radius: 4px;
    padding: 6px 14px;
    background: {p['botao_fundo']};
    color: {p['texto']};
}}
QPushButton:hover {{
    background: {p['botao_hover']};
    border-color: {p['borda_hover']};
}}
QPushButton:pressed {{
    background: {p['botao_pressed']};
}}
QPushButton:focus {{
    border: 2px solid {p['foco']};
}}
QPushButton:disabled {{
    color: {p['desab_texto']};
}}

QCheckBox::indicator, QTableView::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {p['borda']};
    border-radius: 2px;
    background: #ffffff;
}}
QCheckBox::indicator:checked, QTableView::indicator:checked {{
    background: #ffffff;
    {_IMAGEM_CHECK_QSS}
}}

QTableView {{
    gridline-color: {p['grade']};
    background: {p['tabela_fundo']};
    color: {p['texto']};
    selection-background-color: {p['foco']};
    selection-color: white;
    border: 1px solid {p['borda']};
}}
QHeaderView::section {{
    background: {p['cabecalho_fundo']};
    color: {p['texto']};
    border: 1px solid {p['grade']};
    padding: 5px;
    font-weight: 600;
}}

QTabWidget::pane {{
    border: 1px solid {p['grade']};
}}
QTabBar::tab {{
    padding: 8px 18px;
    border: 1px solid {p['borda']};
    border-bottom: none;
    background: {p['aba_fundo']};
    color: {p['aba_texto']};
    margin-right: 2px;
}}
QTabBar::tab:selected {{
    background: {p['aba_selecionada']};
    color: {p['texto']};
    font-weight: 600;
    border-bottom: 3px solid {p['foco']};
}}
QTabBar::tab:hover {{
    background: {p['aba_hover']};
}}
"""


def esta_escuro(app: QApplication) -> bool:
    """Esquema efetivo agora (já resolvido: no Automático é o do Windows)."""
    return app.styleHints().colorScheme() == Qt.ColorScheme.Dark


def reaplicar_folha(app: QApplication) -> None:
    # só mexe quando mudou: cada setStyleSheet reestiliza TODOS os widgets
    # abertos (~1 s com a janela cheia), e trocar o esquema já dispara
    # colorSchemeChanged -> esta função, antes de aplicar_tema chamá-la de novo
    _garantir_imagem_check()
    nova = gerar_folha_de_estilo(esta_escuro(app))
    if app.styleSheet() != nova:
        app.setStyleSheet(nova)


def aplicar_tema(app: QApplication, escolha: str) -> None:
    """Aplica Claro/Escuro/Automático: troca a paleta do Qt (menus, caixas
    de diálogo, barra de rolagem...) e regera a folha de estilo do app."""
    # com folha de estilo ativa o Qt "congela" a paleta de widgets já
    # criados (menu e barra de ferramentas ficavam claros depois de trocar
    # pra escuro com a janela aberta) — limpar antes de trocar o esquema e
    # aplicar de novo depois força cada widget a reler a paleta nova.
    app.setStyleSheet("")
    app.styleHints().setColorScheme(_ESQUEMA_QT.get(escolha, Qt.ColorScheme.Unknown))
    reaplicar_folha(app)
