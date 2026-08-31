"""Testes da Fase 1 (esqueleto): janela abre, menu existe, abas
adicionam/removem sem perder as demais. pytest-qt (fixture `qtbot`) simula
clique sem abrir janela visível de verdade — equivalente ao AppTest do
Streamlit usado nas fases anteriores do projeto.
"""
from __future__ import annotations

from app_qt import JanelaPrincipal


def test_abre_com_identificacao_e_uma_parcela(qtbot):
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)

    assert janela.abas.count() == 2
    assert janela.abas.tabText(0) == "Identificação"
    assert janela.abas.tabText(1) == "Parcela 1"


def test_adicionar_parcela_cria_aba_nova(qtbot):
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)

    janela._adicionar_aba_parcela()

    assert janela.abas.count() == 3
    assert janela.abas.tabText(2) == "Parcela 2"


def test_remover_ultima_parcela_preserva_identificacao_e_primeira_parcela(qtbot):
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)
    janela._adicionar_aba_parcela()
    janela._adicionar_aba_parcela()
    assert janela.abas.count() == 4

    janela._remover_ultima_parcela()

    assert janela.abas.count() == 3
    assert janela.abas.tabText(0) == "Identificação"
    assert janela.abas.tabText(1) == "Parcela 1"
    assert janela.abas.tabText(2) == "Parcela 2"


def test_nao_remove_a_ultima_parcela_restante(qtbot):
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)
    assert janela.abas.count() == 2

    janela._remover_ultima_parcela()

    assert janela.abas.count() == 2
    assert janela.abas.tabText(1) == "Parcela 1"


def test_menu_arquivo_tem_as_acoes_esperadas(qtbot):
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)

    menu_arquivo = janela.menuBar().actions()[0].menu()
    textos = [acao.text() for acao in menu_arquivo.actions() if acao.text()]

    assert "Novo projeto" in textos
    assert "Abrir..." in textos
    assert "Salvar" in textos
    assert "Salvar como..." in textos
    assert "Gerar planilha SIGEF (.ods)..." in textos
    assert "Sair" in textos
