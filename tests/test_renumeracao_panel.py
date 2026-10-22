"""Testes da Fase 6 (painel de numeração): renumerar entre parcelas,
respeitar "Renumerar?", e o método Atualizar (só o Tipo) — a lógica mora
aqui (_renumerar/_atualizar_tipos), mas os botões que a disparam moraram
pra ui_qt/perimetro_tab.py (que só delega de volta pra estes métodos).
Desfazer/Importar continuam com botão neste painel e agem só na aba de
Parcela ATUAL; Adicionar/Remover parcela (V4) o painel só expõe — quem
conecta o clique é app_qt.py::JanelaPrincipal."""
from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox

from ui_qt.perimetro_tab import AbaPerimetro
from ui_qt.renumeracao_panel import PainelNumeracao
from ui_qt.tema_qt import carregar_tema

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


def _dominios():
    with (CONFIG_DIR / "dominios.json").open("r", encoding="utf-8") as f:
        return json.load(f)


def _nova_aba(indice: int, qtbot) -> AbaPerimetro:
    aba = AbaPerimetro(indice, _dominios(), carregar_tema())
    qtbot.addWidget(aba)
    return aba


def _novo_painel(obter_abas, obter_atual=None, qtbot=None, decrescente: bool | None = False) -> PainelNumeracao:
    painel = PainelNumeracao(_dominios(), obter_abas, obter_atual or (lambda: None), carregar_tema())
    if qtbot is not None:
        qtbot.addWidget(painel)
    if decrescente is not None:
        # a pergunta de ordem é um QMessageBox modal: sem isto, qualquer teste
        # que chame _renumerar() travaria esperando clique. decrescente=None
        # mantém a pergunta real (testes do próprio diálogo).
        painel._perguntar_ordem = lambda crescente, decresc: decrescente
    return painel


def _col(aba: AbaPerimetro, nome: str) -> int:
    return aba.modelo_tabela.dataframe().columns.get_loc(nome)


def _silenciar_message_box(monkeypatch) -> None:
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)


def test_renumerar_atribui_codigo_e_avanca_contador_entre_parcelas(qtbot, monkeypatch):
    _silenciar_message_box(monkeypatch)
    aba1 = _nova_aba(1, qtbot)
    aba2 = _nova_aba(2, qtbot)

    aba1.modelo_tabela.setData(aba1.modelo_tabela.index(0, _col(aba1, "codigo")), "X", 2)
    aba1.modelo_tabela.setData(aba1.modelo_tabela.index(0, _col(aba1, "tipo_vertice")), "M", 2)
    aba2.modelo_tabela.setData(aba2.modelo_tabela.index(0, _col(aba2, "codigo")), "Y", 2)
    aba2.modelo_tabela.setData(aba2.modelo_tabela.index(0, _col(aba2, "tipo_vertice")), "M", 2)

    painel = _novo_painel(lambda: [aba1, aba2], qtbot=qtbot)
    painel.campo_credenciado.setText("ajq")

    painel._renumerar()

    assert aba1.modelo_tabela.dataframe().at[0, "codigo"] == "AJQ-M-001"
    assert aba2.modelo_tabela.dataframe().at[0, "codigo"] == "AJQ-M-002"
    assert painel._campos_numero["M"].text() == "003"


def test_renumerar_sem_credenciado_avisa_e_nao_altera(qtbot, monkeypatch):
    avisos = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: avisos.append(a))
    aba = _nova_aba(1, qtbot)
    aba.modelo_tabela.setData(aba.modelo_tabela.index(0, _col(aba, "codigo")), "X", 2)

    painel = _novo_painel(lambda: [aba], qtbot=qtbot)

    painel._renumerar()

    assert avisos
    assert aba.modelo_tabela.dataframe().at[0, "codigo"] == "X"


def test_linha_desmarcada_nao_e_renumerada(qtbot, monkeypatch):
    _silenciar_message_box(monkeypatch)
    aba = _nova_aba(1, qtbot)
    aba.modelo_tabela.setData(aba.modelo_tabela.index(0, _col(aba, "codigo")), "X", 2)
    aba.modelo_tabela.setData(aba.modelo_tabela.index(0, _col(aba, "tipo_vertice")), "M", 2)
    aba.modelo_tabela.setData(
        aba.modelo_tabela.index(0, _col(aba, "renumerar")),
        Qt.CheckState.Unchecked, Qt.ItemDataRole.CheckStateRole,
    )

    painel = _novo_painel(lambda: [aba], qtbot=qtbot)
    painel.campo_credenciado.setText("AJQ")

    painel._renumerar()

    assert aba.modelo_tabela.dataframe().at[0, "codigo"] == "X"


def test_atualizar_tipos_reescreve_so_o_segmento_de_tipo(qtbot, monkeypatch):
    _silenciar_message_box(monkeypatch)
    aba = _nova_aba(1, qtbot)
    aba.modelo_tabela.setData(aba.modelo_tabela.index(0, _col(aba, "codigo")), "AJQ-M-001", 2)
    aba.modelo_tabela.setData(aba.modelo_tabela.index(0, _col(aba, "tipo_vertice")), "P", 2)

    painel = _novo_painel(lambda: [aba], qtbot=qtbot)

    painel._atualizar_tipos()

    assert aba.modelo_tabela.dataframe().at[0, "codigo"] == "AJQ-P-001"


def test_formato_do_numero_afeta_largura_do_zero_a_esquerda(qtbot, monkeypatch):
    _silenciar_message_box(monkeypatch)
    aba = _nova_aba(1, qtbot)
    aba.modelo_tabela.setData(aba.modelo_tabela.index(0, _col(aba, "codigo")), "X", 2)
    aba.modelo_tabela.setData(aba.modelo_tabela.index(0, _col(aba, "tipo_vertice")), "M", 2)

    painel = _novo_painel(lambda: [aba], qtbot=qtbot)
    painel.campo_credenciado.setText("AJQ")
    painel.combo_formato.setCurrentText("00001")
    painel._campos_numero["M"].setText("1")

    painel._renumerar()

    assert aba.modelo_tabela.dataframe().at[0, "codigo"] == "AJQ-M-00001"


def _preparar_aba_para_renumerar(aba, n_linhas: int) -> None:
    for linha in range(n_linhas):
        aba.modelo_tabela.setData(aba.modelo_tabela.index(linha, _col(aba, "tipo_vertice")), "M", 2)


def test_renumerar_decrescente_usa_a_faixa_a_partir_do_numero_informado(qtbot, monkeypatch):
    _silenciar_message_box(monkeypatch)
    aba = _nova_aba(1, qtbot)
    _preparar_aba_para_renumerar(aba, 3)

    painel = _novo_painel(lambda: [aba], qtbot=qtbot, decrescente=True)
    painel.campo_credenciado.setText("AJQ")
    painel._campos_numero["M"].setText("008")
    painel._renumerar()

    assert list(aba.modelo_tabela.dataframe()["codigo"]) == ["AJQ-M-010", "AJQ-M-009", "AJQ-M-008"]
    assert painel._campos_numero["M"].text() == "011"


def test_ordem_nao_e_mais_um_combo_do_painel_e_sim_uma_pergunta(qtbot):
    painel = _novo_painel(lambda: [], qtbot=qtbot)

    assert not hasattr(painel, "combo_ordem")


def test_mensagem_final_mostra_a_faixa_de_codigos(qtbot, monkeypatch):
    infos = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: infos.append(a[2]))
    aba = _nova_aba(1, qtbot)
    _preparar_aba_para_renumerar(aba, 3)

    painel = _novo_painel(lambda: [aba], qtbot=qtbot, decrescente=True)
    painel.campo_credenciado.setText("AJQ")
    painel._campos_numero["M"].setText("1")
    painel._renumerar()

    assert "AJQ-M-003 a AJQ-M-001" in infos[0]


def test_cenario_relatado_oito_linhas_proximo_um_decrescente_numera_de_oito_a_um(qtbot, monkeypatch):
    avisos = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: avisos.append(a[2]))
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    aba = _nova_aba(1, qtbot)
    for _ in range(5):
        aba.modelo_tabela.inserir_linha()
    _preparar_aba_para_renumerar(aba, 8)

    painel = _novo_painel(lambda: [aba], qtbot=qtbot, decrescente=True)
    painel.campo_credenciado.setText("ABCD")
    painel._renumerar()

    assert list(aba.modelo_tabela.dataframe()["codigo"]) == [f"ABCD-M-{n:03d}" for n in range(8, 0, -1)]
    assert avisos == []
    assert painel._campos_numero["M"].text() == "009"


def test_varios_avisos_saem_numa_janela_so(qtbot, monkeypatch):
    janelas = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: janelas.append(a[2]))
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    aba = _nova_aba(1, qtbot)  # 3 linhas selecionadas, nenhuma com Tipo
    painel = _novo_painel(lambda: [aba], qtbot=qtbot)
    painel.campo_credenciado.setText("AJQ")

    painel._renumerar()

    assert len(janelas) == 1
    assert janelas[0].count("sem Tipo") == 3


def test_avisos_demais_sao_resumidos(qtbot, monkeypatch):
    janelas = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: janelas.append(a[2]))
    painel = _novo_painel(lambda: [], qtbot=qtbot)

    painel._mostrar_avisos([f"aviso {i}" for i in range(20)])

    assert len(janelas) == 1
    assert "aviso 11" in janelas[0] and "aviso 12" not in janelas[0]
    assert "e mais 8 aviso(s)" in janelas[0]


def test_cancelar_a_pergunta_de_ordem_nao_altera_nada(qtbot, monkeypatch):
    _silenciar_message_box(monkeypatch)
    aba = _nova_aba(1, qtbot)
    _preparar_aba_para_renumerar(aba, 3)

    painel = _novo_painel(lambda: [aba], qtbot=qtbot, decrescente=None)
    painel._perguntar_ordem = lambda crescente, decresc: None  # clicou "Cancelar"
    painel.campo_credenciado.setText("AJQ")
    painel._renumerar()

    assert list(aba.modelo_tabela.dataframe()["codigo"]) == ["", "", ""]
    assert painel._campos_numero["M"].text() == "001"


def test_sem_nada_selecionado_nao_pergunta_a_ordem_e_avisa(qtbot, monkeypatch):
    avisos = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: avisos.append(a[2]))
    aba = _nova_aba(1, qtbot)
    _preparar_aba_para_renumerar(aba, 3)
    aba.modelo_tabela.definir_coluna("renumerar", False)

    perguntas = []
    painel = _novo_painel(lambda: [aba], qtbot=qtbot)
    painel._perguntar_ordem = lambda c, d: perguntas.append((c, d)) or False
    painel.campo_credenciado.setText("AJQ")
    painel._renumerar()

    assert perguntas == []
    assert any("Nenhum vértice foi renumerado" in a for a in avisos)


def test_pergunta_de_ordem_recebe_a_previa_das_duas_ordens(qtbot, monkeypatch):
    _silenciar_message_box(monkeypatch)
    aba = _nova_aba(1, qtbot)
    _preparar_aba_para_renumerar(aba, 3)
    recebidas = []

    painel = _novo_painel(lambda: [aba], qtbot=qtbot)
    painel._perguntar_ordem = lambda c, d: recebidas.append((c, d)) or None
    painel.campo_credenciado.setText("AJQ")
    painel._campos_numero["M"].setText("3")
    painel._renumerar()

    crescente, decrescente = recebidas[0]
    assert crescente == (3, "AJQ-M-003 a AJQ-M-005", 0)
    assert decrescente == (3, "AJQ-M-005 a AJQ-M-003", 0)


def _responder_dialogo(texto_do_botao: str, capturado: list) -> None:
    # clica o botão do QMessageBox modal que está aberto (exec() bloqueia a
    # chamada do teste, então a resposta vem de um timer); o segundo timer é
    # só rede de segurança contra travar a suíte se o diálogo não aparecer
    def _clicar() -> None:
        caixa = QApplication.activeModalWidget()
        capturado.append(caixa.informativeText())
        next(b for b in caixa.buttons() if b.text() == texto_do_botao).click()

    def _desistir() -> None:
        caixa = QApplication.activeModalWidget()
        if caixa is not None:
            caixa.reject()

    QTimer.singleShot(150, _clicar)
    QTimer.singleShot(5000, _desistir)


def test_dialogo_de_ordem_devolve_a_escolha_do_botao_clicado(qtbot):
    painel = _novo_painel(lambda: [], qtbot=qtbot, decrescente=None)
    crescente = (3, "AJQ-M-001 a AJQ-M-003", 0)
    decrescente = (3, "AJQ-M-003 a AJQ-M-001", 0)

    for botao, esperado in (("Crescente", False), ("Decrescente", True), ("Cancelar", None)):
        textos: list = []
        _responder_dialogo(botao, textos)
        assert painel._perguntar_ordem(crescente, decrescente) is esperado, botao

    # a mensagem mostra o resultado de cada ordem pra decidir sem tentar e desfazer
    assert "AJQ-M-001 a AJQ-M-003" in textos[0]
    assert "AJQ-M-003 a AJQ-M-001" in textos[0]
    assert "confrontante" in textos[0]


def test_dialogo_de_ordem_avisa_quando_uma_ordem_tem_problema(qtbot):
    painel = _novo_painel(lambda: [], qtbot=qtbot, decrescente=None)
    textos: list = []
    _responder_dialogo("Cancelar", textos)

    painel._perguntar_ordem((8, "AJQ-M-001 a AJQ-M-008", 0), (1, "AJQ-M-001 a AJQ-M-001", 7))

    assert "7 aviso(s)" in textos[0]


def test_importar_atual_chama_o_metodo_da_aba_certa(qtbot, monkeypatch):
    _silenciar_message_box(monkeypatch)
    aba = _nova_aba(1, qtbot)
    chamadas = []
    aba._abrir_importador = lambda: chamadas.append(True)

    painel = _novo_painel(lambda: [aba], obter_atual=lambda: aba, qtbot=qtbot)
    painel._importar_atual()

    assert chamadas == [True]


def test_sem_aba_atual_avisa_em_vez_de_quebrar(qtbot, monkeypatch):
    avisos = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: avisos.append(a))

    painel = _novo_painel(lambda: [], obter_atual=lambda: None, qtbot=qtbot)
    painel._importar_atual()

    assert len(avisos) == 1


def test_painel_expoe_botoes_adicionar_e_remover_parcela(qtbot):
    # Reorganizar desceu pra junto da grade (ui_qt/perimetro_tab.py); quem
    # sabe adicionar/remover aba é a janela (app_qt.py), então o painel só
    # expõe os botões — quem conecta o clique é ela.
    painel = _novo_painel(lambda: [], qtbot=qtbot)

    # sem "+"/"-" no texto desde que ganharam ícone qtawesome (V8)
    assert painel.btn_adicionar_parcela.text() == "Adicionar parcela"
    assert painel.btn_remover_parcela.text() == "Remover parcela..."
    assert not painel.btn_adicionar_parcela.icon().isNull()
    assert not painel.btn_remover_parcela.icon().isNull()


def test_desfazer_atual_volta_estado_da_aba_certa(qtbot, monkeypatch):
    _silenciar_message_box(monkeypatch)
    aba = _nova_aba(1, qtbot)
    aba.modelo_tabela.setData(aba.modelo_tabela.index(0, _col(aba, "codigo")), "ORIGINAL", 2)
    aba.modelo_tabela.setData(aba.modelo_tabela.index(0, _col(aba, "codigo")), "MUDOU", 2)

    painel = _novo_painel(lambda: [aba], obter_atual=lambda: aba, qtbot=qtbot)
    painel._desfazer_atual()

    assert aba.modelo_tabela.dataframe().at[0, "codigo"] == "ORIGINAL"
