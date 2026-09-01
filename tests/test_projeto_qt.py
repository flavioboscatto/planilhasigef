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
    col_codigo = abas[0].modelo_tabela.dataframe().columns.get_loc("codigo")
    abas[0].modelo_tabela.setData(abas[0].modelo_tabela.index(0, col_codigo), "AJ4-M-001", Qt.ItemDataRole.EditRole)
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


def test_round_trip_preserva_pt_original(qtbot):
    # Pt.Original precisa sobreviver a fechar/reabrir o projeto, senão a
    # renumeração perde a referência pro nome do ponto importado assim que
    # o profissional salva e volta a trabalhar noutro dia.
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)
    aba = janela._abas_perimetro()[0]
    col_pt_original = aba.modelo_tabela.dataframe().columns.get_loc("pt_original")
    col_codigo = aba.modelo_tabela.dataframe().columns.get_loc("codigo")
    aba.modelo_tabela.setData(aba.modelo_tabela.index(0, col_pt_original), "V1", Qt.ItemDataRole.EditRole)
    aba.modelo_tabela.setData(aba.modelo_tabela.index(0, col_codigo), "AJ4-M-001", Qt.ItemDataRole.EditRole)

    dados = desserializar(serializar(montar_projeto(janela)))

    nova = JanelaPrincipal()
    qtbot.addWidget(nova)
    aplicar_projeto(nova, dados)

    nova_aba = nova._abas_perimetro()[0]
    assert nova_aba.modelo_tabela.dataframe().at[0, "pt_original"] == "V1"
    assert nova_aba.modelo_tabela.dataframe().at[0, "codigo"] == "AJ4-M-001"


def test_reabrir_projeto_volta_para_a_subaba_que_estava_aberta_ao_salvar(qtbot):
    # bug relatado: criar uma importação deixa "Importação N" em foco
    # (efeito colateral de _criar_aba_importacao) — reabrir o projeto
    # sempre pousava lá, mesmo quando o usuário tinha voltado pra Tabela
    # de Perímetro antes de salvar.
    import pandas as pd

    janela = JanelaPrincipal()
    qtbot.addWidget(janela)
    aba = janela._abas_perimetro()[0]
    dados_importados = pd.DataFrame({"codigo": ["A"], "e_long": ["-48,00"], "n_lat": ["-9,00"]})
    aba._criar_aba_importacao(dados_importados, None, -51.0, "Sul")
    assert aba.subabas.currentIndex() == 1  # foco foi pra Importação 1 (comportamento normal)

    aba.subabas.setCurrentIndex(0)  # usuário volta pra Tabela de Perímetro antes de salvar

    dados = desserializar(serializar(montar_projeto(janela)))

    nova = JanelaPrincipal()
    qtbot.addWidget(nova)
    aplicar_projeto(nova, dados)

    nova_aba = nova._abas_perimetro()[0]
    assert nova_aba.subabas.currentIndex() == 0


def test_reabrir_projeto_com_varias_parcelas_volta_para_a_parcela_aberta_ao_salvar(qtbot):
    # mesmo bug, um nível acima: _adicionar_aba_parcela deixa a última
    # parcela recriada em foco — reabrir sempre pousava nela, mesmo tendo
    # sido a Parcela 1 a aba aberta quando o usuário salvou.
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)
    janela._adicionar_aba_parcela()  # Parcela 2 fica em foco (comportamento normal)
    assert janela.abas.currentIndex() == 2

    janela.abas.setCurrentIndex(1)  # usuário volta pra Parcela 1 antes de salvar

    dados = desserializar(serializar(montar_projeto(janela)))

    nova = JanelaPrincipal()
    qtbot.addWidget(nova)
    aplicar_projeto(nova, dados)

    assert nova.abas.currentIndex() == 1


def test_abrir_projeto_de_versao_antiga_sem_parcela_atual_usa_parcela_1_tabela_perimetro(qtbot):
    # arquivo salvo antes deste campo existir (sem "parcela_atual" nem
    # "subaba_atual") não pode quebrar nem sobrar em índice inválido — cai
    # no default (Parcela 1, Tabela de Perímetro), que é o que o usuário
    # pediu como comportamento padrão.
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)
    dados = desserializar(serializar(montar_projeto(janela)))
    del dados["parcela_atual"]
    del dados["parcelas"][0]["subaba_atual"]

    aplicar_projeto(janela, dados)

    assert janela.abas.currentIndex() == 1
    assert janela._abas_perimetro()[0].subabas.currentIndex() == 0


def test_round_trip_preserva_abas_de_importacao(qtbot):
    # reclamação do usuário: fechar e reabrir o projeto perdia as abas
    # "Importação N" (a Tabela de Perímetro já mesclada continuava, só a
    # sub-aba de conferência/recálculo sumia).
    import pandas as pd

    janela = JanelaPrincipal()
    qtbot.addWidget(janela)
    aba = janela._abas_perimetro()[0]

    dados_geo = pd.DataFrame({"codigo": ["AJ4-M-001"], "e_long": ["-48,50"], "n_lat": ["-27,50"]})
    aba._criar_aba_importacao(dados_geo, None, 0.0, "")

    dados_utm = pd.DataFrame({"codigo": ["AJ4-M-002"], "e_long": ["-48,60"], "n_lat": ["-27,60"]})
    dados_utm_brutos = pd.DataFrame({"e_long": ["500000"], "n_lat": ["7000000"]})
    aba._criar_aba_importacao(dados_utm, dados_utm_brutos, -51.0, "Sul")

    dados = desserializar(serializar(montar_projeto(janela)))

    nova = JanelaPrincipal()
    qtbot.addWidget(nova)
    aplicar_projeto(nova, dados)

    nova_aba = nova._abas_perimetro()[0]
    assert nova_aba.subabas.count() == 3  # Tabela de Perímetro + 2 importações

    sub_geo = nova_aba.subabas.widget(1)
    assert sub_geo._dataframe_atual().at[0, "codigo"] == "AJ4-M-001"
    assert sub_geo._dados_utm_brutos is None
    assert not hasattr(sub_geo, "combo_meridiano")

    sub_utm = nova_aba.subabas.widget(2)
    assert sub_utm._dataframe_atual().at[0, "codigo"] == "AJ4-M-002"
    assert sub_utm._dados_utm_brutos.at[0, "e_long"] == "500000"
    assert sub_utm.combo_meridiano.currentText() == "-51"
    assert sub_utm.combo_hemisferio.currentText() == "Sul"


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


def test_round_trip_preserva_numeracao_mesmo_com_importacao_na_parcela(qtbot):
    # bug relatado pelo usuário: o loop que recria as sub-abas de
    # importação reaproveitava o nome "dados" (parâmetro da função
    # inteira) pra cada DataFrame — como DataFrame também tem `.get()`,
    # `dados.get("numeracao", {})` mais adiante nunca dava erro, só
    # devolvia sempre vazio, e só quando existia importação em alguma
    # parcela (por isso o round trip "puro", sem importação, não pegava).
    import pandas as pd

    janela = JanelaPrincipal()
    qtbot.addWidget(janela)
    janela.painel_numeracao.campo_credenciado.setText("FBFB")
    janela.painel_numeracao._campos_numero["M"].setText("211")
    aba = janela._abas_perimetro()[0]
    dados_importados = pd.DataFrame({"codigo": ["6"], "e_long": ["-48,50"], "n_lat": ["-27,50"]})
    aba._criar_aba_importacao(dados_importados, None, -51.0, "Sul")

    dados = desserializar(serializar(montar_projeto(janela)))

    nova = JanelaPrincipal()
    qtbot.addWidget(nova)
    aplicar_projeto(nova, dados)

    assert nova.painel_numeracao.campo_credenciado.text() == "FBFB"
    assert nova.painel_numeracao._campos_numero["M"].text() == "211"


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


def test_novo_projeto_mantem_hemisferio_sul_como_padrao(qtbot, monkeypatch):
    # bug relatado: "Novo projeto" passa pelo default do Pydantic
    # (core/models.py::Perimetro), não pelo construtor da aba — se os dois
    # defaults divergirem, a parcela nova às vezes abre em Norte.
    monkeypatch.setattr(
        QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes
    )
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: ("", "")))
    janela = JanelaPrincipal()
    qtbot.addWidget(janela)

    janela._novo_projeto()

    assert janela._abas_perimetro()[0].hemisferio.currentText() == "Sul"


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
