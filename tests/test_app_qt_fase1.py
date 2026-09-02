"""Testes da Fase 1 (esqueleto): janela abre, menu existe, abas
adicionam/removem sem perder as demais. pytest-qt (fixture `qtbot`) simula
clique sem abrir janela visível de verdade — equivalente ao AppTest do
Streamlit usado nas fases anteriores do projeto.
"""
from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtGui import QContextMenuEvent
from PySide6.QtWidgets import QApplication, QMenu

from app_qt import JanelaPrincipal


def _evento_contexto(bar, indice: int) -> QContextMenuEvent:
    pos = bar.tabRect(indice).center()
    return QContextMenuEvent(QContextMenuEvent.Reason.Mouse, pos, bar.mapToGlobal(pos))


def _clique_direito_e_escolhe(bar, indice: int, texto_acao: str) -> None:
    """Dispara um QContextMenuEvent de verdade na aba `indice` e clica na
    ação `texto_acao` do menu que abrir — não um QTest.mouseClick: QTest não
    sintetiza WM_CONTEXTMENU/QEvent::ContextMenu, então simular só o clique
    do mouse nunca chegaria no menu de contexto de verdade (confirmado
    manualmente: um QTest.mouseClick com botão direito não dispara
    customContextMenuRequested nenhum). O clique na ação precisa ser
    agendado num QTimer pra rodar DEPOIS que o laço modal do QMenu abrir —
    sem isso, `menu.exec()` trava esperando uma interação que nunca chega.
    `QAction.trigger()` não fecha o menu sozinho (só emite o sinal), daí o
    `menu.close()` explícito no fim.
    """

    def _interagir() -> None:
        menu = QApplication.activePopupWidget()
        assert isinstance(menu, QMenu), "menu de contexto não abriu"
        acao = next(a for a in menu.actions() if texto_acao in a.text())
        acao.trigger()
        menu.close()

    QTimer.singleShot(0, _interagir)
    QApplication.sendEvent(bar, _evento_contexto(bar, indice))


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


def test_clique_direito_e_remover_esta_parcela_remove_a_aba_certa(qtbot):
    # bug relatado: "clique com botão direito para excluir parcela não
    # funcionou, só no botão" — este teste dispara um QContextMenuEvent de
    # verdade (não chama _menu_contexto_aba/_remover_parcelas direto), pra
    # cobrir o caminho real que estava faltando teste nenhum.
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)
    janela._adicionar_aba_parcela()  # Parcela 2, agora 3 abas

    _clique_direito_e_escolhe(janela.abas.tabBar(), 1, "Remover esta parcela...")

    assert janela.abas.count() == 2
    assert janela.abas.tabText(1) == "Parcela 2"


def test_clique_direito_e_remover_com_uma_so_parcela_avisa_em_vez_de_remover(qtbot, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    avisos = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: avisos.append(a))
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)

    _clique_direito_e_escolhe(janela.abas.tabBar(), 1, "Remover esta parcela...")

    assert avisos
    assert janela.abas.count() == 2
    assert janela.abas.tabText(1) == "Parcela 1"


def test_clique_direito_e_renomear_parcela_funciona_pelo_menu(qtbot, monkeypatch):
    from PySide6.QtWidgets import QInputDialog

    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("Gleba 7", True)))
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)

    _clique_direito_e_escolhe(janela.abas.tabBar(), 1, "Renomear parcela...")

    assert janela.abas.tabText(1) == "Gleba 7"


def test_clique_direito_na_aba_identificacao_nao_abre_menu(qtbot):
    # índice 0 (Identificação) não ganha menu de contexto — sendEvent tem
    # que voltar sem entrar em laço modal nenhum (sem QTimer agendado: se
    # _menu_contexto_aba chamasse exec() aqui, o teste travaria).
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)

    QApplication.sendEvent(janela.abas.tabBar(), _evento_contexto(janela.abas.tabBar(), 0))

    assert janela.abas.tabText(0) == "Identificação"
    assert janela.abas.count() == 2


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
