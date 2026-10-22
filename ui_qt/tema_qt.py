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

import qtawesome as qta
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QIcon
from PySide6.QtWidgets import QLabel, QPushButton

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "theme_tokens.json"

# maior lista de domínio real hoje é Método de Posicionamento (26 itens,
# config/dominios.json) — um cap menor que isso obriga rolar pra ver o
# resto mesmo quando a tela tem espaço de sobra. Compartilhado entre
# ui_qt/perimetro_tab.py, ui_qt/identificacao_tab.py e
# ui_qt/vertices_table.py (delegate de combo da grade); município (5571
# itens) usa combo pesquisável à parte (ui_qt/identificacao_tab.py::
# _combo_pesquisavel), não este cap.
MAX_ITENS_VISIVEIS_COMBO = 30


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


# texto dos botões coloridos: fixo, nunca herda a cor da paleta — os fundos
# pastel (verde/azul/rosa) são os mesmos nos temas Claro e Escuro, então um
# texto herdado (branco no modo escuro) sumia sobre eles.
_TEXTO_ESCURO = "#1f2933"


def cor_icone_neutra() -> str:
    """Cor de ícone para superfícies que seguem o tema (barra de
    ferramentas): escuro no tema claro, claro no escuro."""
    escuro = QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
    return "#e6e9ee" if escuro else "#2f2f2f"


def icone(nome: str, cor: str = "#2f2f2f") -> QIcon:
    """Ícone vetorial (Font Awesome/Material Design) via qtawesome, pedido
    do usuário no lugar dos emojis usados até aqui — mais "profissional" e
    com cor consistente por botão (`nome` no formato "fa5s.xxx"/"mdi.xxx",
    ver https://pictogrammers.com/library/mdi/ e a lista do Font Awesome 5)."""
    return qta.icon(nome, color=cor)


def _aplicar_icone(botao: QPushButton, nome: str | None, cor: str) -> None:
    if nome is None:
        return
    botao.setIcon(icone(nome, cor))
    botao.setIconSize(QSize(14, 14))


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


def botao_verde(texto: str, tema: dict[str, Papel], icone_nome: str | None = None) -> QPushButton:
    """Botão de ação em verde claro (mesma cor de "perimetro_entrada" no
    modelo oficial) — pedido do usuário pra diferenciar visualmente as
    ações de aba/painel do resto do app. Compartilhado entre
    ui_qt/perimetro_tab.py, ui_qt/importacao_tab.py e
    ui_qt/renumeracao_panel.py, então mora aqui, não num arquivo só.
    `icone_nome`: ícone qtawesome opcional (ex.: "fa5s.check-square"),
    trocando o emoji que o texto do botão usava antes."""
    cor = tema["perimetro_entrada"].fundo
    botao = QPushButton(texto)
    _aplicar_icone(botao, icone_nome, "#2f2f2f")
    botao.setStyleSheet(_estilo_botao_pastel(cor))
    return botao


def _estilo_botao_pastel(cor: QColor, destaque: bool = False) -> str:
    """QSS dos botões coloridos claros (verde/azul/rosa): texto escuro
    explícito e borda um tom mais marcada que o fundo (contraste sutil, pedido
    da turma-teste); borda inferior um pouco mais grossa dá leve relevo. Em
    `destaque` (negrito + borda 2px) a borda já é grossa o bastante."""
    if destaque:
        borda = f"border: 2px solid {cor.darker(155).name()}; font-weight: bold;"
    else:
        borda = f"border: 1px solid {cor.darker(155).name()}; border-bottom: 2px solid {cor.darker(185).name()};"
    return (
        f"QPushButton {{ background: {cor.name()}; color: {_TEXTO_ESCURO}; {borda} }}"
        f"QPushButton:hover {{ background: {cor.darker(108).name()}; }}"
        f"QPushButton:pressed {{ background: {cor.darker(120).name()}; }}"
    )


def botao_verde_destaque(texto: str, tema: dict[str, Papel], icone_nome: str | None = None) -> QPushButton:
    """Mesma cor de botao_verde, mas em negrito e com borda mais grossa —
    pedido do usuário (turma-teste) pra destacar as ações mais importantes/
    usadas com frequência (Importar, Renumerar, Reorganizar, Visualizar
    parcela) das demais ações verdes comuns."""
    cor = tema["perimetro_entrada"].fundo
    botao = QPushButton(texto)
    _aplicar_icone(botao, icone_nome, "#2f2f2f")
    botao.setStyleSheet(_estilo_botao_pastel(cor, destaque=True))
    return botao


def botao_marrom(texto: str, tema: dict[str, Papel], icone_nome: str | None = None) -> QPushButton:
    """Botão de exportação (planilha/TXT/relatório) no mesmo marrom escuro
    de "servico_titulo" — a faixa "Identificação do Serviço de
    Georreferenciamento" na aba Identificação, pedido explícito do usuário
    como referência de cor — texto branco (fundo escuro), pra separar
    visualmente exportação (sai um arquivo) de ação normal (botao_verde,
    mexe só no que está na tela)."""
    cor = tema["servico_titulo"].fundo
    botao = QPushButton(texto)
    _aplicar_icone(botao, icone_nome, "white")
    botao.setStyleSheet(
        f"QPushButton {{ background: {cor.name()}; color: white; border: 1px solid {cor.darker(160).name()};"
        f" border-bottom: 2px solid {cor.darker(200).name()}; }}"
        f"QPushButton:hover {{ background: {cor.lighter(115).name()}; }}"
        f"QPushButton:pressed {{ background: {cor.darker(120).name()}; }}"
    )
    return botao


def botao_azul(texto: str, tema: dict[str, Papel], icone_nome: str | None = None) -> QPushButton:
    """Botão de exportação georreferenciada (KML/Shapefile), pedido do
    usuário em azul — mesmo azul-claro de "detentor_entrada" (campo de
    entrada da faixa "Identificação do Detentor"), texto escuro (fundo
    claro). Era o azul escuro de "detentor_titulo" antes; o usuário achou
    forte demais, trocado pro mesmo tom claro que botao_verde/botao_perigo
    já usam, só que azul."""
    cor = tema["detentor_entrada"].fundo
    botao = QPushButton(texto)
    _aplicar_icone(botao, icone_nome, "#2f2f2f")
    botao.setStyleSheet(_estilo_botao_pastel(cor))
    return botao


def botao_perigo(texto: str, tema: dict[str, Papel], icone_nome: str | None = None) -> QPushButton:
    """Botão de ação destrutiva (Limpar Parcela), pedido do usuário em
    rosa/vermelho claro — mesma cor de "servico_entrada", texto escuro
    (fundo claro)."""
    cor = tema["servico_entrada"].fundo
    botao = QPushButton(texto)
    _aplicar_icone(botao, icone_nome, "#2f2f2f")
    botao.setStyleSheet(_estilo_botao_pastel(cor))
    return botao
