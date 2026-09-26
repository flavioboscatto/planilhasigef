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

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox

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


def _novo_painel(obter_abas, obter_atual=None, qtbot=None) -> PainelNumeracao:
    painel = PainelNumeracao(_dominios(), obter_abas, obter_atual or (lambda: None), carregar_tema())
    if qtbot is not None:
        qtbot.addWidget(painel)
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
