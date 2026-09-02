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


def test_remover_parcelas_preserva_identificacao_e_as_nao_selecionadas(qtbot):
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)
    janela._adicionar_aba_parcela()
    janela._adicionar_aba_parcela()
    assert janela.abas.count() == 4

    janela._remover_parcelas([janela.abas.count() - 1])  # remove só a última

    assert janela.abas.count() == 3
    assert janela.abas.tabText(0) == "Identificação"
    assert janela.abas.tabText(1) == "Parcela 1"
    assert janela.abas.tabText(2) == "Parcela 2"


def test_remover_parcelas_aceita_mais_de_um_indice_de_uma_vez(qtbot):
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)
    janela._adicionar_aba_parcela()  # Parcela 2
    janela._adicionar_aba_parcela()  # Parcela 3
    assert janela.abas.count() == 4

    janela._remover_parcelas([1, 3])  # Parcela 1 e Parcela 3, mantém Parcela 2

    assert janela.abas.count() == 2
    assert janela.abas.tabText(0) == "Identificação"
    assert janela.abas.tabText(1) == "Parcela 2"


def test_nao_remove_a_ultima_parcela_restante(qtbot):
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)
    assert janela.abas.count() == 2

    janela._remover_parcelas([1])

    assert janela.abas.count() == 2
    assert janela.abas.tabText(1) == "Parcela 1"


def test_adicionar_aba_parcela_aceita_nome_customizado(qtbot):
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)

    janela._adicionar_aba_parcela("Fazenda Boa Vista")

    assert janela.abas.tabText(2) == "Fazenda Boa Vista"


def test_adicionar_com_prompt_usa_o_nome_digitado(qtbot, monkeypatch):
    from PySide6.QtWidgets import QInputDialog

    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("Gleba Norte", True)))
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)

    janela._adicionar_aba_parcela_com_prompt()

    assert janela.abas.tabText(2) == "Gleba Norte"


def test_adicionar_com_prompt_cancelado_nao_cria_aba(qtbot, monkeypatch):
    from PySide6.QtWidgets import QInputDialog

    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("", False)))
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)

    janela._adicionar_aba_parcela_com_prompt()

    assert janela.abas.count() == 2


def test_dialogo_remover_parcela_com_selecao_remove_as_marcadas(qtbot, monkeypatch):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QDialog

    janela = JanelaPrincipal()
    qtbot.addWidget(janela)
    janela._adicionar_aba_parcela()  # Parcela 2

    def _exec_falso(self):
        self.lista.item(0).setCheckState(Qt.CheckState.Checked)
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr("ui_qt.remover_parcela_dialog.RemoverParcelaDialog.exec", _exec_falso)

    janela._abrir_dialogo_remover_parcela()

    assert janela.abas.count() == 2
    assert janela.abas.tabText(1) == "Parcela 2"


def test_renomear_parcela_cancelado_nao_muda_o_rotulo(qtbot, monkeypatch):
    from PySide6.QtWidgets import QInputDialog

    # QInputDialog.getText abre um diálogo modal de verdade — sem stub, o
    # teste travaria esperando um clique que nunca vem (mesmo motivo de
    # QMessageBox.warning em outros testes deste arquivo).
    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("", False)))
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)

    janela._renomear_parcela(1)

    assert janela.abas.tabText(1) == "Parcela 1"


def test_renomear_parcela_com_dialogo_confirmado(qtbot, monkeypatch):
    from PySide6.QtWidgets import QInputDialog

    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("Gleba 7", True)))
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)

    janela._renomear_parcela(1)

    assert janela.abas.tabText(1) == "Gleba 7"


def test_identificacao_nao_sai_do_indice_0_ao_arrastar(qtbot):
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)
    janela._adicionar_aba_parcela()  # Parcela 2, agora 3 abas

    janela.abas.tabBar().moveTab(0, 2)  # tenta arrastar Identificação pro fim

    assert janela.abas.tabText(0) == "Identificação"


def test_parcelas_podem_ser_reordenadas_entre_si(qtbot):
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)
    janela._adicionar_aba_parcela()  # Parcela 2

    janela.abas.tabBar().moveTab(1, 2)  # troca Parcela 1 <-> Parcela 2, sem envolver o índice 0

    assert janela.abas.tabText(0) == "Identificação"
    assert janela.abas.tabText(1) == "Parcela 2"
    assert janela.abas.tabText(2) == "Parcela 1"


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
