"""Testes da Fase 1 (esqueleto): janela abre, menu existe, abas
adicionam/removem sem perder as demais. pytest-qt (fixture `qtbot`) simula
clique sem abrir janela visível de verdade — equivalente ao AppTest do
Streamlit usado nas fases anteriores do projeto.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QContextMenuEvent
from PySide6.QtWidgets import QApplication, QMenu, QToolBar

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


def _menu_por_titulo(janela, titulo: str):
    acao = next(a for a in janela.menuBar().actions() if a.text().replace("&", "") == titulo)
    return acao.menu()


def test_menu_arquivo_tem_as_acoes_esperadas(qtbot):
    # Gerar/Exportar/Relatório saíram daqui pro menu Exportar (V6) — Arquivo
    # ficou só com ações de PROJETO (.sigefproj).
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)

    textos = [acao.text() for acao in _menu_por_titulo(janela, "Arquivo").actions() if acao.text()]

    assert "Novo projeto" in textos
    assert "Abrir..." in textos
    assert "Salvar" in textos
    assert "Salvar como..." in textos
    assert "Sair" in textos
    assert not any("Gerar planilha" in t for t in textos)


def test_menu_importar_tem_as_duas_opcoes(qtbot):
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)

    textos = [a.text() for a in _menu_por_titulo(janela, "Importar").actions()]

    assert any("TXT/CSV" in t for t in textos)
    assert any("planilha" in t for t in textos)


def test_menu_exportar_tem_as_quatro_opcoes(qtbot):
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)

    textos = [a.text() for a in _menu_por_titulo(janela, "Exportar").actions()]

    assert any(".ods" in t for t in textos)
    assert any("TXT" in t for t in textos)
    assert any("XLSX" in t for t in textos)
    assert any("DOCX" in t for t in textos)
    assert any("KML" in t for t in textos)
    assert any("Shapefile" in t for t in textos)


def test_menu_gerenciar_parcelas_tem_adicionar_e_remover_mas_nao_limpar(qtbot):
    # Limpar Parcela mexe no CONTEÚDO da parcela (apaga a grade), não na
    # aba em si — mora em Gerenciar Planilha (Parcela atual), pedido do
    # usuário depois de ver os dois menus na prática.
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)

    textos = [a.text() for a in _menu_por_titulo(janela, "Gerenciar Parcelas").actions() if a.text()]

    assert any("Adicionar" in t for t in textos)
    assert any("Remover" in t for t in textos)
    assert not any("Limpar" in t for t in textos)


def test_menu_gerenciar_planilha_tem_reorganizar_e_visualizar(qtbot):
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)

    textos = [a.text() for a in _menu_por_titulo(janela, "Gerenciar Planilha (Parcela atual)").actions()]

    assert any("Reorganizar" in t for t in textos)
    assert any("Visualizar" in t for t in textos)


def test_menu_gerenciar_planilha_chama_os_metodos_da_aba_atual(qtbot, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)
    aba = janela._abas_perimetro()[0]
    chamadas = []
    aba.modelo_tabela.definir_coluna = lambda campo, valor: chamadas.append(("definir_coluna", campo, valor))
    aba.modelo_tabela.inserir_linha = lambda: chamadas.append(("inserir_linha",))
    aba._remover_linhas_selecionadas = lambda: chamadas.append(("remover",))
    aba._mover_linha_selecionada = lambda d: chamadas.append(("mover", d))
    # Limpar Parcela abre um QMessageBox.question de verdade (modal) — sem
    # substituir o método, o teste travaria esperando um clique que nunca
    # vem (mesmo motivo de QMessageBox.warning acima); o comportamento real
    # dela já tem teste dedicado (test_menu_gerenciar_planilha_limpar_...).
    aba._limpar_parcela = lambda: chamadas.append(("limpar",))

    menu = _menu_por_titulo(janela, "Gerenciar Planilha (Parcela atual)")
    for acao in menu.actions():
        if acao.text():
            acao.trigger()

    assert ("definir_coluna", "renumerar", True) in chamadas
    assert ("definir_coluna", "renumerar", False) in chamadas
    assert ("inserir_linha",) in chamadas
    assert ("limpar",) in chamadas
    assert ("remover",) in chamadas
    assert ("mover", -1) in chamadas
    assert ("mover", 1) in chamadas


def test_menu_visualizar_parcela_abre_o_dialogo_da_aba_atual(qtbot):
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)
    aba = janela._abas_perimetro()[0]

    acao = next(a for a in _menu_por_titulo(janela, "Gerenciar Planilha (Parcela atual)").actions() if a.text() == "Visualizar parcela")
    acao.trigger()

    assert aba._dialogo_visualizacao is not None


def test_menu_reorganizar_vertices_chama_o_metodo_da_aba_atual(qtbot, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)
    aba = janela._abas_perimetro()[0]
    chamadas = []
    aba._reorganizar = lambda: chamadas.append(True)

    acao = next(a for a in _menu_por_titulo(janela, "Gerenciar Planilha (Parcela atual)").actions() if a.text() == "Reorganizar vértices")
    acao.trigger()

    assert chamadas == [True]


def test_menu_gerenciar_planilha_limpar_chama_limpar_parcela_da_aba_atual(qtbot, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)
    aba = janela._abas_perimetro()[0]
    col_codigo = aba.modelo_tabela.dataframe().columns.get_loc("codigo")
    aba.modelo_tabela.setData(aba.modelo_tabela.index(0, col_codigo), "AJ4-M-001", Qt.ItemDataRole.EditRole)

    acao = next(
        a for a in _menu_por_titulo(janela, "Gerenciar Planilha (Parcela atual)").actions() if a.text() == "Limpar Parcela"
    )
    acao.trigger()

    assert aba.modelo_tabela.dataframe().at[0, "codigo"] == ""


def test_menu_gerenciar_parcelas_adicionar_e_remover_chamam_os_metodos_certos(qtbot, monkeypatch):
    from PySide6.QtWidgets import QInputDialog

    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("Gleba Nova", True)))
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)

    acao_add = next(a for a in _menu_por_titulo(janela, "Gerenciar Parcelas").actions() if a.text() == "Adicionar Parcela")
    acao_add.trigger()

    assert janela.abas.tabText(janela.abas.count() - 1) == "Gleba Nova"


def test_menu_gerenciar_planilha_sem_aba_avisa_em_vez_de_quebrar(qtbot, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    avisos = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: avisos.append(a))
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)
    janela.abas.setCurrentIndex(0)  # foco na Identificação, não é AbaPerimetro

    janela._adicionar_vertice_atual()

    assert avisos


def test_barra_de_ferramentas_tem_abrir_salvar_salvar_como_e_desfazer(qtbot):
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)

    barras = janela.findChildren(QToolBar)
    assert len(barras) == 1
    textos = [a.text() for a in barras[0].actions() if a.text()]
    assert textos == ["Novo Projeto", "Abrir Projeto", "Salvar", "Salvar Como", "Desfazer"]


def test_botao_desfazer_da_barra_desfaz_a_grade_da_aba_atual(qtbot):
    # não dá pra substituir painel_numeracao._desfazer_atual DEPOIS de
    # construída a janela e esperar que o sinal já conectado chame a
    # versão nova — Qt captura o método vinculado no connect(). Por isso
    # este teste confere o EFEITO real (desfazer de verdade), não uma
    # chamada espionada.
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)
    aba = janela._abas_perimetro()[0]
    col_codigo = aba.modelo_tabela.dataframe().columns.get_loc("codigo")
    aba.modelo_tabela.setData(aba.modelo_tabela.index(0, col_codigo), "ORIGINAL", Qt.ItemDataRole.EditRole)
    aba.modelo_tabela.setData(aba.modelo_tabela.index(0, col_codigo), "MUDOU", Qt.ItemDataRole.EditRole)

    barra = janela.findChildren(QToolBar)[0]
    acao_desfazer = next(a for a in barra.actions() if a.text() == "Desfazer")
    acao_desfazer.trigger()

    assert aba.modelo_tabela.dataframe().at[0, "codigo"] == "ORIGINAL"
