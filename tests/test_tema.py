"""Tema Claro/Escuro/Automático (ui_qt/estilo_qt.py, ui_qt/preferencias_qt.py,
menu Exibir em app_qt.py) e as cores que não podem depender da paleta."""
from __future__ import annotations

import re

import pytest
from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import QApplication, QPushButton

from app_qt import JanelaPrincipal
from ui_qt import preferencias_qt
from ui_qt.estilo_qt import (
    TEMA_AUTOMATICO,
    TEMA_CLARO,
    TEMA_ESCURO,
    aplicar_tema,
    esta_escuro,
    gerar_folha_de_estilo,
)
from ui_qt.perimetro_tab import AbaPerimetro
from ui_qt.tema_qt import botao_azul, botao_marrom, botao_perigo, botao_verde, botao_verde_destaque, carregar_tema, cor_icone_neutra


@pytest.fixture(autouse=True)
def _restaurar_tema_global(qtbot):
    # preferências já isoladas em tests/conftest.py; aqui só devolvemos o
    # esquema de cores/folha de estilo globais, já que o QApplication é
    # compartilhado entre todos os testes
    app = QApplication.instance()
    # janelas de testes anteriores ficam aguardando deleteLater (não há loop
    # de eventos rodando nos testes) e cada troca de folha de estilo
    # reestiliza TODAS elas — ~20 s por troca com a suíte inteira. Descarta
    # antes de testar o tema.
    app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    folha_antes = app.styleSheet()
    yield
    app.styleHints().setColorScheme(Qt.ColorScheme.Unknown)
    app.setStyleSheet(folha_antes)


def test_folha_de_estilo_define_cor_de_texto_junto_com_cada_fundo_nos_dois_temas():
    # o bug original: fundo claro fixo SEM cor de texto -> texto herdado da
    # paleta (branco no modo escuro) ficava invisível
    for escuro in (False, True):
        folha = gerar_folha_de_estilo(escuro)
        for seletor in ("QLineEdit, QComboBox, QTextEdit", "QPushButton", "QTableView", "QHeaderView::section", "QTabBar::tab"):
            bloco = re.search(re.escape(seletor) + r" \{(.*?)\}", folha, re.S).group(1)
            assert "background" in bloco and re.search(r"(?<![-\w])color:", bloco), f"{seletor} (escuro={escuro})"


def test_caixa_de_selecao_da_grade_e_branca_com_visto_nos_dois_temas():
    # pedido: no tema escuro a caixa da coluna "Selecionar" aparecia cinza;
    # agora é branca (com visto escuro quando selecionada), igual nos dois
    for escuro in (False, True):
        folha = gerar_folha_de_estilo(escuro)
        regra = re.search(r"QCheckBox::indicator, QTableView::indicator \{(.*?)\}", folha, re.S).group(1)
        assert "background: #ffffff" in regra
        marcada = re.search(r"QCheckBox::indicator:checked, QTableView::indicator:checked \{(.*?)\}", folha, re.S).group(1)
        assert "background: #ffffff" in marcada and "image: url(" in marcada


def test_imagem_do_visto_e_gerada(qtbot):
    from ui_qt.estilo_qt import _IMAGEM_CHECK, _garantir_imagem_check

    assert _garantir_imagem_check() is True
    assert _IMAGEM_CHECK.exists() and _IMAGEM_CHECK.stat().st_size > 0


def test_folhas_claro_e_escuro_sao_diferentes():
    assert gerar_folha_de_estilo(False) != gerar_folha_de_estilo(True)


def test_aplicar_tema_escuro_e_claro_trocam_esquema_e_folha():
    app = QApplication.instance()

    aplicar_tema(app, TEMA_ESCURO)
    assert esta_escuro(app)
    assert app.styleSheet() == gerar_folha_de_estilo(True)

    aplicar_tema(app, TEMA_CLARO)
    assert not esta_escuro(app)
    assert app.styleSheet() == gerar_folha_de_estilo(False)


def test_aplicar_tema_automatico_segue_o_sistema():
    app = QApplication.instance()
    aplicar_tema(app, TEMA_ESCURO)

    aplicar_tema(app, TEMA_AUTOMATICO)

    # não é mais forçado: o esquema efetivo volta a ser o do sistema
    assert app.styleSheet() == gerar_folha_de_estilo(esta_escuro(app))


def test_janela_nova_sem_preferencia_salva_abre_em_automatico(qtbot):
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)

    assert preferencias_qt.obter_tema() == "automatico"
    assert janela._acoes_tema[TEMA_AUTOMATICO].isChecked()


def test_preferencia_de_tema_padrao_e_automatico_e_faz_round_trip():
    assert preferencias_qt.obter_tema() == "automatico"

    preferencias_qt.salvar_tema("escuro")

    assert preferencias_qt.obter_tema() == "escuro"


def test_preferencia_de_tema_invalida_cai_no_automatico():
    preferencias_qt._settings().setValue("tema", "roxo")

    assert preferencias_qt.obter_tema() == "automatico"
    preferencias_qt.salvar_tema("roxo")  # ignorado
    assert preferencias_qt.obter_tema() == "automatico"


def test_menu_exibir_tema_escolher_escuro_aplica_e_salva(qtbot):
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)
    assert janela._acoes_tema[TEMA_AUTOMATICO].isChecked()

    janela._acoes_tema[TEMA_ESCURO].trigger()

    assert esta_escuro(QApplication.instance())
    assert preferencias_qt.obter_tema() == "escuro"
    assert janela._acoes_tema[TEMA_ESCURO].isChecked()


def test_trocar_tema_com_a_janela_aberta_atualiza_menu_barra_e_rotulos(qtbot):
    # bug relatado: com a janela já aberta, escolher Escuro deixava o menu e a
    # barra de ferramentas na paleta clara (folha de estilo congela a paleta
    # dos widgets existentes) e ícones claros sumiam sobre o fundo claro
    from PySide6.QtGui import QPalette
    from PySide6.QtWidgets import QLabel

    janela = JanelaPrincipal()
    qtbot.addWidget(janela)
    janela.show()
    qtbot.waitExposed(janela)
    janela._acoes_tema[TEMA_CLARO].trigger()
    rotulo = next(r for r in janela.findChildren(QLabel) if r.text() == "Tipo pessoa")

    fundo_menu = lambda: janela.menuBar().palette().color(QPalette.ColorRole.Window).lightness()
    texto_rotulo = lambda: rotulo.palette().color(QPalette.ColorRole.WindowText).lightness()

    janela._acoes_tema[TEMA_ESCURO].trigger()
    assert fundo_menu() < 100
    assert texto_rotulo() > 200

    janela._acoes_tema[TEMA_CLARO].trigger()
    assert fundo_menu() > 200
    assert texto_rotulo() < 100


def test_painel_congelado_fica_alinhado_com_a_grade_principal_com_a_folha_de_estilo(qtbot):
    # bug relatado: a borda `QTableView { border: 1px }` do app valia também
    # pro painel congelado, deixando cabeçalho e linhas 1px abaixo/à direita
    # da grade principal (desalinho na fronteira Vértice | E/Long)
    from PySide6.QtCore import QPoint

    app = QApplication.instance()
    for tema in (TEMA_CLARO, TEMA_ESCURO):
        aplicar_tema(app, tema)
        aba = AbaPerimetro(1, _dominios(), carregar_tema())
        qtbot.addWidget(aba)
        aba.show()
        qtbot.waitExposed(aba)
        grade, congelada = aba.grade, aba.grade.painel_congelado
        modelo = aba.modelo_tabela

        cab_congelada = congelada.horizontalHeader().mapTo(grade, QPoint(0, 0)).y()
        cab_principal = grade.horizontalHeader().mapTo(grade, QPoint(0, 0)).y()
        linha_congelada = congelada.viewport().mapTo(grade, congelada.visualRect(modelo.index(1, 3)).topLeft())
        linha_principal = grade.viewport().mapTo(grade, grade.visualRect(modelo.index(1, 5)).topLeft())
        borda_congelada = congelada.viewport().mapTo(
            grade, QPoint(congelada.columnViewportPosition(3) + congelada.columnWidth(3), 0)
        ).x()
        coluna_seguinte = grade.viewport().mapTo(grade, QPoint(grade.columnViewportPosition(4), 0)).x()

        assert cab_congelada == cab_principal, tema
        assert linha_congelada.y() == linha_principal.y(), tema
        assert borda_congelada == coluna_seguinte, tema


def test_menu_exibir_abre_marcado_com_o_tema_salvo(qtbot):
    preferencias_qt.salvar_tema("claro")

    janela = JanelaPrincipal()
    qtbot.addWidget(janela)

    assert janela._acoes_tema[TEMA_CLARO].isChecked()
    assert not janela._acoes_tema[TEMA_AUTOMATICO].isChecked()


def _cor_do_icone(acao) -> str:
    # cor de um pixel bem opaco do ícone (o traço do ícone vetorial)
    imagem = acao.icon().pixmap(32, 32).toImage()
    for y in range(imagem.height()):
        for x in range(imagem.width()):
            cor = imagem.pixelColor(x, y)
            if cor.alpha() > 240:
                return cor.name()
    raise AssertionError("ícone sem pixel opaco")


def test_icones_da_barra_acompanham_o_tema(qtbot):
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)
    acao = janela._icones_barra[0][0]

    janela._acoes_tema[TEMA_ESCURO].trigger()
    assert cor_icone_neutra() == "#e6e9ee"
    assert _cor_do_icone(acao) == "#e6e9ee"

    janela._acoes_tema[TEMA_CLARO].trigger()
    assert cor_icone_neutra() == "#2f2f2f"
    assert _cor_do_icone(acao) == "#2f2f2f"


def test_botoes_coloridos_tem_texto_escuro_fixo_e_marrom_branco():
    tema = carregar_tema()
    for fabrica in (botao_verde, botao_verde_destaque, botao_azul, botao_perigo):
        folha = fabrica("x", tema).styleSheet()
        assert "color: #1f2933" in folha, fabrica.__name__
    assert "color: white" in botao_marrom("x", tema).styleSheet()


def test_celulas_coloridas_da_grade_tem_texto_fixo_em_qualquer_tema(qtbot):
    from core.tabela_vertices import COLUNAS_VERTICE

    # o modelo devolve sempre a mesma cor de texto (não consulta o esquema
    # do sistema): é isso que garante o texto escuro sobre o pastel no escuro
    aba = AbaPerimetro(1, _dominios(), carregar_tema())
    qtbot.addWidget(aba)
    modelo = aba.modelo_tabela

    texto_geral = modelo.data(modelo.index(0, COLUNAS_VERTICE.index("codigo")), Qt.ItemDataRole.ForegroundRole)
    texto_confrontante = modelo.data(modelo.index(0, COLUNAS_VERTICE.index("tipo_limite")), Qt.ItemDataRole.ForegroundRole)
    assert texto_geral.name() == "#000000"
    assert texto_confrontante.name() == "#000000"
    # colunas sem fundo próprio seguem a paleta do tema
    assert modelo.data(modelo.index(0, COLUNAS_VERTICE.index("pt_original")), Qt.ItemDataRole.ForegroundRole) is None


def _dominios():
    import json
    from pathlib import Path

    with (Path(__file__).resolve().parent.parent / "config" / "dominios.json").open("r", encoding="utf-8") as f:
        return json.load(f)


def test_rotulos_pequenos_do_painel_usam_propriedade_tematizavel(qtbot):
    from ui_qt.renumeracao_panel import PainelNumeracao

    painel = PainelNumeracao(_dominios(), lambda: [], lambda: None, carregar_tema())
    qtbot.addWidget(painel)

    from PySide6.QtWidgets import QLabel

    pequenos = [r for r in painel.findChildren(QLabel) if r.property("rotuloPequeno")]
    assert {r.text() for r in pequenos} >= {"Credenciado", "Formato"}
    assert not [b for b in painel.findChildren(QPushButton) if "#55606b" in b.styleSheet()]
