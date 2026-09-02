"""Testes de ui_qt/boas_vindas_dialog.py (V4): tela de abertura pedindo
Novo projeto ou Abrir (com atalho pros últimos projetos usados)."""
from __future__ import annotations

from PySide6.QtWidgets import QFileDialog

from ui_qt.boas_vindas_dialog import BoasVindasDialog


def test_lista_recentes_mostra_os_caminhos_recebidos(qtbot):
    dialogo = BoasVindasDialog(["C:/projeto_a.sigefproj", "C:/projeto_b.sigefproj"])
    qtbot.addWidget(dialogo)

    assert dialogo.lista_recentes.count() == 2
    assert dialogo.lista_recentes.isEnabled()


def test_sem_recentes_lista_fica_desabilitada(qtbot):
    dialogo = BoasVindasDialog([])
    qtbot.addWidget(dialogo)

    assert not dialogo.lista_recentes.isEnabled()


def test_escolher_novo_aceita_o_dialogo_com_acao_novo(qtbot):
    dialogo = BoasVindasDialog([])
    qtbot.addWidget(dialogo)

    dialogo._escolher_novo()

    assert dialogo.result()
    assert dialogo.resultado() == ("novo", None)


def test_escolher_abrir_com_arquivo_selecionado(qtbot, monkeypatch, tmp_path):
    caminho = tmp_path / "projeto.sigefproj"
    caminho.write_bytes(b"")
    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(caminho), "")))
    dialogo = BoasVindasDialog([])
    qtbot.addWidget(dialogo)

    dialogo._escolher_abrir()

    assert dialogo.result()
    assert dialogo.resultado() == ("abrir", str(caminho))


def test_escolher_abrir_cancelado_nao_aceita_o_dialogo(qtbot, monkeypatch):
    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: ("", "")))
    dialogo = BoasVindasDialog([])
    qtbot.addWidget(dialogo)

    dialogo._escolher_abrir()

    assert not dialogo.result()


def test_duplo_clique_num_recente_abre_direto(qtbot, tmp_path):
    caminho = tmp_path / "projeto.sigefproj"
    caminho.write_bytes(b"")
    dialogo = BoasVindasDialog([str(caminho)])
    qtbot.addWidget(dialogo)

    dialogo._abrir_recente(dialogo.lista_recentes.item(0))

    assert dialogo.result()
    assert dialogo.resultado() == ("abrir", str(caminho))


def test_duplo_clique_em_recente_que_nao_existe_mais_nao_aceita(qtbot):
    dialogo = BoasVindasDialog(["C:/nao_existe_mais.sigefproj"])
    qtbot.addWidget(dialogo)

    dialogo._abrir_recente(dialogo.lista_recentes.item(0))

    assert not dialogo.result()
