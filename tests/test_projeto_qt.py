"""Testes da Fase 7 (projeto .sigefproj): round-trip completo
montar_projeto -> serializar -> desserializar -> aplicar_projeto, e os
menus Salvar/Abrir/Novo com QFileDialog nativo simulado (método estático,
sem precisar de clique manual nem subprocess)."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog, QMessageBox

from app_qt import JanelaPrincipal
from core.projeto import desserializar, serializar
from ui_qt.projeto_qt import aplicar_projeto, montar_projeto


def test_round_trip_identificacao_e_parcelas(qtbot):
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)

    janela.aba_identificacao.nome.setText("Fulano de Tal")
    janela.aba_identificacao.cpf_cnpj.setText("123.456.789-00")
    janela._adicionar_aba_parcela()
    abas = janela._abas_perimetro()
    abas[0].denominacao.setText("Parte Um")
    abas[0].modelo_tabela.setData(abas[0].modelo_tabela.index(0, 2), "AJ4-M-001", Qt.ItemDataRole.EditRole)
    abas[1].denominacao.setText("Parte Dois")
    abas[1].meridiano_central.setCurrentText("-45")

    conteudo = serializar(montar_projeto(janela))
    dados = desserializar(conteudo)

    nova_janela = JanelaPrincipal()
    qtbot.addWidget(nova_janela)
    aplicar_projeto(nova_janela, dados)

    assert nova_janela.aba_identificacao.modelo().nome == "Fulano de Tal"
    novas_abas = nova_janela._abas_perimetro()
    assert len(novas_abas) == 2
    assert novas_abas[0].denominacao.text() == "Parte Um"
    assert novas_abas[0].modelo_tabela.dataframe().at[0, "codigo"] == "AJ4-M-001"
    assert novas_abas[1].denominacao.text() == "Parte Dois"
    assert novas_abas[1].meridiano_central.currentText() == "-45"


def test_round_trip_preserva_numeracao(qtbot):
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)
    janela.painel_numeracao.campo_credenciado.setText("AJQ")
    janela.painel_numeracao.combo_formato.setCurrentText("0001")
    janela.painel_numeracao._campos_numero["M"].setText("0007")

    dados = desserializar(serializar(montar_projeto(janela)))

    nova = JanelaPrincipal()
    qtbot.addWidget(nova)
    aplicar_projeto(nova, dados)

    assert nova.painel_numeracao.campo_credenciado.text() == "AJQ"
    assert nova.painel_numeracao.combo_formato.currentText() == "0001"
    assert nova.painel_numeracao._campos_numero["M"].text() == "0007"


def test_salvar_como_grava_arquivo_e_salvar_reescreve_no_mesmo(qtbot, tmp_path, monkeypatch):
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)
    janela.aba_identificacao.nome.setText("Primeira versão")

    caminho = str(tmp_path / "meu_projeto.sigefproj")
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (caminho, "")))

    janela._salvar_projeto_como()

    assert janela.caminho_projeto == caminho
    dados = desserializar(open(caminho, "rb").read())
    assert dados["identificacao"]["nome"] == "Primeira versão"

    janela.aba_identificacao.nome.setText("Segunda versão")
    janela._salvar_projeto()  # já tem caminho — não deve abrir diálogo de novo

    dados2 = desserializar(open(caminho, "rb").read())
    assert dados2["identificacao"]["nome"] == "Segunda versão"


def test_abrir_projeto_carrega_arquivo_escolhido(qtbot, tmp_path, monkeypatch):
    caminho = tmp_path / "projeto.sigefproj"
    conteudo = serializar({
        "identificacao": {"nome": "Ciclano"},
        "num_parcelas": 1,
        "parcelas": [{"denominacao": "Parte Aberta", "vertices": []}],
        "numeracao": {},
    })
    caminho.write_bytes(conteudo)
    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(caminho), "")))

    janela = JanelaPrincipal()
    qtbot.addWidget(janela)

    janela._abrir_projeto()

    assert janela.aba_identificacao.modelo().nome == "Ciclano"
    assert janela._abas_perimetro()[0].denominacao.text() == "Parte Aberta"
    assert janela.caminho_projeto == str(caminho)


def test_novo_projeto_reseta_apos_confirmacao(qtbot, monkeypatch):
    monkeypatch.setattr(
        QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes
    )
    # Novo projeto já abre "Salvar como" em seguida (pedido do usuário);
    # simula cancelar esse diálogo pra não travar esperando um real.
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: ("", "")))
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)
    janela.aba_identificacao.nome.setText("Algo preenchido")
    janela._adicionar_aba_parcela()
    janela.caminho_projeto = "/algum/caminho.sigefproj"

    janela._novo_projeto()

    assert janela.aba_identificacao.modelo().nome == ""
    assert len(janela._abas_perimetro()) == 1
    assert janela.caminho_projeto is None
