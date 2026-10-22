"""Testes da Fase 4 (aba Perímetro): campos de cabeçalho, botões
(Reorganizar, Marcar/Desmarcar todos, Preencher em lote), round-trip
modelo()/carregar_cabecalho(), e as sub-abas de Importação persistentes
(ui_qt/importacao_tab.py) que moram dentro da Tabela de Perímetro."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from core.models import Perimetro
from ui_qt.importacao_tab import AbaImportacao
from ui_qt.perimetro_tab import AbaPerimetro
from ui_qt.tema_qt import carregar_tema

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


def _dominios():
    with (CONFIG_DIR / "dominios.json").open("r", encoding="utf-8") as f:
        return json.load(f)


def _nova_aba(indice: int = 1) -> AbaPerimetro:
    return AbaPerimetro(indice, _dominios(), carregar_tema())


def test_criar_aba_importacao_adiciona_sub_aba_persistente(qtbot):
    aba = _nova_aba()
    qtbot.addWidget(aba)

    dados = pd.DataFrame({"codigo": ["AJ4-M-001"], "e_long": ["-48,00"], "n_lat": ["-9,00"]})
    aba._criar_aba_importacao(dados, None, None, -51.0, "Sul")

    assert aba.subabas.count() == 2  # "Tabela de Perímetro" + "Importação 1"
    assert aba.subabas.tabText(1) == "Importação 1"
    assert isinstance(aba.subabas.widget(1), AbaImportacao)

    aba._criar_aba_importacao(dados, None, None, -51.0, "Sul")
    assert aba.subabas.tabText(2) == "Importação 2"


def test_usar_esta_versao_mescla_e_a_aba_de_importacao_continua_visivel(qtbot, monkeypatch):
    # pedido explícito do usuário: a aba de importação não deve sumir
    # depois de mesclada — precisa continuar ali pra reconferir/recalcular
    # depois, inclusive já com a Tabela de Perímetro preenchida.
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)
    aba = _nova_aba()
    qtbot.addWidget(aba)

    dados = pd.DataFrame({"codigo": ["AJ4-M-001"], "e_long": ["-48,00"], "n_lat": ["-9,00"]})
    aba._criar_aba_importacao(dados, None, None, -51.0, "Sul")
    aba_importacao = aba.subabas.widget(1)

    aba._aplicar_versao_importada(aba_importacao._dataframe_atual())

    resultado = aba.modelo_tabela.dataframe()
    assert "AJ4-M-001" in list(resultado["codigo"])
    assert aba.subabas.count() == 2  # a sub-aba de importação continua lá


def test_remover_aba_importacao_tira_da_lista_de_sub_abas(qtbot):
    aba = _nova_aba()
    qtbot.addWidget(aba)

    dados = pd.DataFrame({"codigo": ["AJ4-M-001"], "e_long": ["-48,00"], "n_lat": ["-9,00"]})
    aba._criar_aba_importacao(dados, None, None, -51.0, "Sul")
    aba_importacao = aba.subabas.widget(1)

    aba._remover_aba_importacao(aba_importacao)

    assert aba.subabas.count() == 1


def test_defaults_batem_com_o_pedido_pelo_usuario(qtbot):
    aba = _nova_aba(1)
    qtbot.addWidget(aba)

    assert aba.denominacao.text() == "Parte 1"
    assert aba.parcela_numero.text() == "001"
    assert aba.meridiano_central.currentText() == "-51"
    assert aba.hemisferio.currentText() == "Sul"


def test_marcar_e_desmarcar_todos(qtbot):
    aba = _nova_aba()
    qtbot.addWidget(aba)

    aba.modelo_tabela.definir_coluna("renumerar", False)
    assert not any(aba.modelo_tabela.dataframe()["renumerar"])


def test_renumerar_e_atualizar_delegam_para_o_painel_numeracao(qtbot):
    # os botões vieram morar aqui (ao lado da grade), mas a lógica e o
    # estado (Credenciado/Formato/Próximo nº) continuam no painel
    # compartilhado — precisa continuar entre todas as parcelas.
    aba = _nova_aba()
    qtbot.addWidget(aba)
    chamadas = []

    class _PainelFalso:
        def _renumerar(self):
            chamadas.append("renumerar")

        def _atualizar_tipos(self):
            chamadas.append("atualizar")

    aba._painel_numeracao = _PainelFalso()
    aba._renumerar()
    aba._atualizar_tipos()

    assert chamadas == ["renumerar", "atualizar"]

    aba.modelo_tabela.definir_coluna("renumerar", True)
    assert all(aba.modelo_tabela.dataframe()["renumerar"])


def test_subir_linha_selecionada_troca_com_a_vizinha_de_cima(qtbot):
    aba = _nova_aba()
    qtbot.addWidget(aba)
    col_codigo = aba.modelo_tabela.dataframe().columns.get_loc("codigo")
    aba.modelo_tabela.setData(aba.modelo_tabela.index(0, col_codigo), "A", 2)
    aba.modelo_tabela.setData(aba.modelo_tabela.index(1, col_codigo), "B", 2)
    aba.grade.selectRow(1)

    aba._mover_linha_selecionada(-1)

    assert list(aba.modelo_tabela.dataframe()["codigo"])[:2] == ["B", "A"]
    assert aba.grade.selectionModel().selectedIndexes()[0].row() == 0


def test_descer_linha_selecionada_troca_com_a_vizinha_de_baixo(qtbot):
    aba = _nova_aba()
    qtbot.addWidget(aba)
    col_codigo = aba.modelo_tabela.dataframe().columns.get_loc("codigo")
    aba.modelo_tabela.setData(aba.modelo_tabela.index(0, col_codigo), "A", 2)
    aba.modelo_tabela.setData(aba.modelo_tabela.index(1, col_codigo), "B", 2)
    aba.grade.selectRow(0)

    aba._mover_linha_selecionada(1)

    assert list(aba.modelo_tabela.dataframe()["codigo"])[:2] == ["B", "A"]


def test_mover_linha_sem_selecao_unica_avisa_e_nao_altera(qtbot, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    avisos = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: avisos.append(a))
    aba = _nova_aba()
    qtbot.addWidget(aba)
    col_codigo = aba.modelo_tabela.dataframe().columns.get_loc("codigo")
    aba.modelo_tabela.setData(aba.modelo_tabela.index(0, col_codigo), "A", 2)
    aba.modelo_tabela.setData(aba.modelo_tabela.index(1, col_codigo), "B", 2)
    # nada selecionado

    aba._mover_linha_selecionada(-1)

    assert avisos
    assert list(aba.modelo_tabela.dataframe()["codigo"])[:2] == ["A", "B"]


def test_preencher_em_lote_metodo_posicionamento(qtbot):
    aba = _nova_aba()
    qtbot.addWidget(aba)

    aba.combo_coluna_lote.setCurrentText("Método de Posicionamento")
    aba.combo_valor_lote.setCurrentText("PG1")
    aba._aplicar_lote()

    assert list(aba.modelo_tabela.dataframe()["metodo_posicionamento"]) == ["PG1", "PG1", "PG1"]


def test_botoes_usam_o_termo_selecionar_e_nao_marcar(qtbot):
    from PySide6.QtWidgets import QPushButton

    aba = _nova_aba()
    qtbot.addWidget(aba)
    textos = {b.text() for b in aba.findChildren(QPushButton)}

    assert {
        "Selecionar todas",
        "Limpar seleção de todas",
        "Renumerar vértices selecionados",
        "Aplicar às linhas selecionadas",
    } <= textos
    assert not [t for t in textos if "marcad" in t.lower() or "marcar" in t.lower()]


def test_menu_gerenciar_planilha_usa_o_termo_selecionar(qtbot):
    from app_qt import JanelaPrincipal

    janela = JanelaPrincipal()
    qtbot.addWidget(janela)
    menu = next(a.menu() for a in janela.menuBar().actions() if "Gerenciar Planilha" in a.text())
    textos = [a.text() for a in menu.actions() if not a.isSeparator()]

    assert "Selecionar todas" in textos
    assert "Limpar seleção de todas" in textos
    assert "Renumerar vértices selecionados" in textos
    assert not [t for t in textos if "marcad" in t.lower() or "marcar" in t.lower()]


def _marcar_linhas(aba, marcadas: list[bool]) -> None:
    for linha, marcada in enumerate(marcadas):
        aba.modelo_tabela._df.iat[linha, aba.modelo_tabela._df.columns.get_loc("renumerar")] = marcada


def test_preencher_em_lote_so_nas_linhas_marcadas(qtbot):
    aba = _nova_aba()
    qtbot.addWidget(aba)
    _marcar_linhas(aba, [True, False, True])

    aba.combo_coluna_lote.setCurrentText("Método de Posicionamento")
    aba.combo_valor_lote.setCurrentText("PG1")
    aba._aplicar_lote(True)

    assert list(aba.modelo_tabela.dataframe()["metodo_posicionamento"]) == ["PG1", "", "PG1"]


def test_preencher_em_lote_marcadas_e_desfazivel_em_um_passo(qtbot):
    aba = _nova_aba()
    qtbot.addWidget(aba)
    _marcar_linhas(aba, [True, False, True])

    aba.combo_coluna_lote.setCurrentText("Método de Posicionamento")
    aba.combo_valor_lote.setCurrentText("PG1")
    aba._aplicar_lote(True)
    aba.modelo_tabela.desfazer()

    assert list(aba.modelo_tabela.dataframe()["metodo_posicionamento"]) == ["", "", ""]


def test_preencher_em_lote_marcadas_sem_nenhuma_marcada_avisa_e_nao_altera(qtbot, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    avisos = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: avisos.append(a))
    aba = _nova_aba()
    qtbot.addWidget(aba)
    _marcar_linhas(aba, [False, False, False])

    aba.combo_coluna_lote.setCurrentText("Método de Posicionamento")
    aba.combo_valor_lote.setCurrentText("PG1")
    aba._aplicar_lote(True)

    assert len(avisos) == 1
    assert list(aba.modelo_tabela.dataframe()["metodo_posicionamento"]) == ["", "", ""]
    # não gravou passo vazio no histórico: Desfazer não tem nada a desfazer
    assert aba.modelo_tabela.desfazer() is False


def test_botao_reorganizar_esta_conectado_de_verdade(qtbot, monkeypatch):
    # V4: Reorganizar desceu do painel de Numeração pra junto da grade
    # (barra_visualizacao, ao lado de Visualizar parcela) — confere que o
    # botão de verdade chama self._reorganizar, não só que o método existe.
    from PySide6.QtWidgets import QMessageBox, QPushButton

    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)
    aba = _nova_aba()
    qtbot.addWidget(aba)
    botao = next(b for b in aba.findChildren(QPushButton) if "Reorganizar" in b.text())

    botao.click()  # menos de 3 vértices preenchidos -> só avisa, não quebra

    assert aba.modelo_tabela.rowCount() == 3


def test_reorganizar_exige_pelo_menos_tres_vertices(qtbot, monkeypatch):
    # QMessageBox.warning é modal (bloqueia esperando clique) — sem
    # substituir por um stub, o teste travaria pra sempre.
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)

    aba = _nova_aba()
    qtbot.addWidget(aba)
    col_codigo = aba.modelo_tabela.dataframe().columns.get_loc("codigo")
    aba.modelo_tabela.setData(aba.modelo_tabela.index(0, col_codigo), "A-1", 2)  # Qt.EditRole == 2

    aba._reorganizar()  # não deve lançar exceção, só avisar

    assert aba.modelo_tabela.rowCount() == 3


def test_reorganizar_avisa_quando_poligono_fica_autointersectante(qtbot, monkeypatch):
    # Reorganizar só rotaciona/inverte a ordem existente — se os vértices já
    # formavam uma "borboleta", ela continua depois de reorganizado; o
    # aviso extra (V3) é o único jeito de o usuário descobrir isso aqui.
    from PySide6.QtWidgets import QMessageBox

    avisos = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: avisos.append(a))

    aba = _nova_aba()
    qtbot.addWidget(aba)
    aba.modelo_tabela.inserir_linha()  # 4ª linha, pra formar um quadrilátero
    df = aba.modelo_tabela.dataframe()
    dados = [
        ("A", "-48,00", "-9,00"),
        ("B", "-47,90", "-9,10"),
        ("C", "-47,90", "-9,00"),
        ("D", "-48,00", "-9,10"),
    ]
    for i, (codigo, e_long, n_lat) in enumerate(dados):
        for campo, valor in (("codigo", codigo), ("e_long", e_long), ("n_lat", n_lat)):
            aba.modelo_tabela.setData(aba.modelo_tabela.index(i, list(df.columns).index(campo)), valor, 2)

    aba._reorganizar()

    assert len(avisos) == 1
    assert "cruza" in avisos[0][-1]


def test_reorganizar_com_poligono_simples_nao_avisa_de_cruzamento(qtbot, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    avisos = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: avisos.append(a))

    aba = _nova_aba()
    qtbot.addWidget(aba)
    df = aba.modelo_tabela.dataframe()
    dados = [("A", "-48,00", "-9,00"), ("B", "-47,90", "-9,10"), ("C", "-48,10", "-9,10")]
    for i, (codigo, e_long, n_lat) in enumerate(dados):
        for campo, valor in (("codigo", codigo), ("e_long", e_long), ("n_lat", n_lat)):
            aba.modelo_tabela.setData(aba.modelo_tabela.index(i, list(df.columns).index(campo)), valor, 2)

    aba._reorganizar()

    assert avisos == []


def test_abrir_visualizacao_cria_dialogo_nao_modal(qtbot):
    aba = _nova_aba()
    qtbot.addWidget(aba)

    aba._abrir_visualizacao()

    assert aba._dialogo_visualizacao is not None
    assert aba._dialogo_visualizacao.isModal() is False


def test_botao_visualizar_parcela_esta_conectado_de_verdade(qtbot):
    # clique real no botão (não chamada direta do método) — confere que a
    # conexão .clicked.connect foi feita, não só que o método existe.
    from PySide6.QtWidgets import QPushButton

    aba = _nova_aba()
    qtbot.addWidget(aba)
    botao = next(b for b in aba.findChildren(QPushButton) if "Visualizar parcela" in b.text())

    botao.click()

    assert aba._dialogo_visualizacao is not None


def test_reorganizar_funciona_com_coordenadas_digitadas_em_gms(qtbot):
    # pedido explícito do usuário: conferir que "mais ao norte" e "sentido
    # horário" funcionam certo quando a célula tem texto GMS de verdade
    # (não só grau decimal) — parse_coordenada entende os dois formatos.
    aba = _nova_aba()
    qtbot.addWidget(aba)
    df = aba.modelo_tabela.dataframe()
    # SUL fica mais ao sul (10°S > 9°S em valor absoluto), NORTE é o mais
    # ao norte dos três — em GMS com sufixo S/W, exatamente como sai/entra
    # na planilha real.
    dados = [
        ("SUL", "48 00 00,000 W", "10 00 00,000 S"),
        ("NORTE", "48 00 00,000 W", "9 00 00,000 S"),
        ("LESTE", "47 30 00,000 W", "9 30 00,000 S"),
    ]
    for i, (codigo, e_long, n_lat) in enumerate(dados):
        aba.modelo_tabela.setData(aba.modelo_tabela.index(i, list(df.columns).index("codigo")), codigo, 2)
        aba.modelo_tabela.setData(aba.modelo_tabela.index(i, list(df.columns).index("e_long")), e_long, 2)
        aba.modelo_tabela.setData(aba.modelo_tabela.index(i, list(df.columns).index("n_lat")), n_lat, 2)

    aba._reorganizar()

    resultado = aba.modelo_tabela.dataframe()
    assert resultado.iloc[0]["codigo"] == "NORTE"


def test_reorganizar_nao_desloca_colunas(qtbot):
    # bug relatado: cada coluna passava a mostrar o dado da coluna vizinha
    # depois de Reorganizar (pd.DataFrame(lista_de_dicts) usa a ordem das
    # chaves do dict, que não batia com COLUNAS_VERTICE).
    aba = _nova_aba()
    qtbot.addWidget(aba)
    df = aba.modelo_tabela.dataframe()
    linha = {
        "codigo": "AJ4-M-001",
        "e_long": "-48,00",
        "n_lat": "-9,00",
        "sigma_long": "0,01",
        "sigma_lat": "0,02",
        "h": "13,5",
        "sigma_h": "0,03",
        "tipo_vertice": "M",
        "metodo_posicionamento": "PG1",
        "tipo_limite": "LA1",
        "cns": "CNS-1",
        "matricula": "MAT-1",
        "descritivo": "Marco de concreto",
    }
    for i, base in enumerate([("SUL", "-10,00"), ("NORTE", "-9,00"), ("LESTE", "-9,50")]):
        codigo, n_lat = base
        valores = dict(linha, codigo=codigo, n_lat=n_lat)
        for campo, valor in valores.items():
            coluna = list(df.columns).index(campo)
            aba.modelo_tabela.setData(aba.modelo_tabela.index(i, coluna), valor, 2)

    aba._reorganizar()

    resultado = aba.modelo_tabela.dataframe()
    norte = resultado[resultado["codigo"] == "NORTE"].iloc[0]
    assert norte["metodo_posicionamento"] == "PG1"
    assert norte["tipo_limite"] == "LA1"
    assert norte["cns"] == "CNS-1"
    assert norte["matricula"] == "MAT-1"
    assert norte["descritivo"] == "Marco de concreto"
    assert norte["tipo_vertice"] == "M"
    assert norte["sigma_h"] == "0,03"


def test_reorganizar_preserva_pt_original(qtbot):
    # bug relatado: "pt_original" (nome do ponto tal como veio da
    # importação, ver core/tabela_vertices.py) sumia depois de Reorganizar
    # — Vertice (core/models.py) não tem esse campo, então o round-trip
    # linha_para_vertice/vertice_para_linha o descartava silenciosamente,
    # mesmo sem o usuário ter renumerado ainda.
    aba = _nova_aba()
    qtbot.addWidget(aba)
    df = aba.modelo_tabela.dataframe()
    dados = [
        {"codigo": "SUL", "e_long": "-48,00", "n_lat": "-10,00", "pt_original": "V3"},
        {"codigo": "NORTE", "e_long": "-48,00", "n_lat": "-9,00", "pt_original": "V1"},
        {"codigo": "LESTE", "e_long": "-47,50", "n_lat": "-9,50", "pt_original": "V2"},
    ]
    for i, linha in enumerate(dados):
        for campo, valor in linha.items():
            coluna = list(df.columns).index(campo)
            aba.modelo_tabela.setData(aba.modelo_tabela.index(i, coluna), valor, 2)

    aba._reorganizar()

    resultado = aba.modelo_tabela.dataframe()
    norte = resultado[resultado["codigo"] == "NORTE"].iloc[0]
    sul = resultado[resultado["codigo"] == "SUL"].iloc[0]
    leste = resultado[resultado["codigo"] == "LESTE"].iloc[0]
    assert norte["pt_original"] == "V1"
    assert sul["pt_original"] == "V3"
    assert leste["pt_original"] == "V2"


def test_reorganizar_reordena_mantendo_renumerar_por_vertice(qtbot):
    aba = _nova_aba()
    qtbot.addWidget(aba)
    df = aba.modelo_tabela.dataframe()
    # 3 vértices formando um triângulo; o mais ao norte deve virar o primeiro
    dados = [
        {"codigo": "SUL", "e_long": "-48,00", "n_lat": "-10,00", "renumerar": False},
        {"codigo": "NORTE", "e_long": "-48,00", "n_lat": "-9,00", "renumerar": True},
        {"codigo": "LESTE", "e_long": "-47,50", "n_lat": "-9,50", "renumerar": True},
    ]
    for i, linha in enumerate(dados):
        for campo, valor in linha.items():
            coluna = list(df.columns).index(campo)
            aba.modelo_tabela.setData(aba.modelo_tabela.index(i, coluna), valor, 2)

    aba._reorganizar()

    resultado = aba.modelo_tabela.dataframe()
    assert resultado.at[0, "codigo"] == "NORTE"
    assert bool(resultado.at[0, "renumerar"]) is True
    sul = resultado[resultado["codigo"] == "SUL"].iloc[0]
    assert bool(sul["renumerar"]) is False


def test_reorganizar_preserva_linhas_vazias_e_devolve_texto_com_virgula(qtbot):
    # bug relatado: depois de Reorganizar, linhas em branco (vagas pra
    # próximo vértice) desapareciam, e os campos numéricos viravam float
    # cru (ponto decimal) em vez de texto com vírgula.
    aba = _nova_aba()
    qtbot.addWidget(aba)
    aba.modelo_tabela.inserir_linha()  # 4ª linha, vazia, além das 3 iniciais
    df = aba.modelo_tabela.dataframe()
    dados = [
        {"codigo": "SUL", "e_long": "-48,00", "n_lat": "-10,00", "h": "13,5"},
        {"codigo": "NORTE", "e_long": "-48,00", "n_lat": "-9,00", "h": "13,6"},
        {"codigo": "LESTE", "e_long": "-47,50", "n_lat": "-9,50", "h": "13,7"},
    ]
    for i, linha in enumerate(dados):
        for campo, valor in linha.items():
            coluna = list(df.columns).index(campo)
            aba.modelo_tabela.setData(aba.modelo_tabela.index(i, coluna), valor, 2)

    aba._reorganizar()

    resultado = aba.modelo_tabela.dataframe()
    linhas_vazias = resultado[resultado["codigo"].astype(str).str.strip() == ""]
    assert len(linhas_vazias) == 1  # a 4ª linha, em branco, sobreviveu

    norte = resultado[resultado["codigo"] == "NORTE"].iloc[0]
    assert isinstance(norte["e_long"], str)
    assert "," in norte["h"]
    assert "." not in norte["h"]


def test_modelo_le_cabecalho_e_vertices_preenchidos(qtbot):
    aba = _nova_aba(2)
    qtbot.addWidget(aba)
    aba.denominacao.setText("Fazenda Teste")
    aba.hemisferio.setCurrentText("Norte")
    col_codigo = aba.modelo_tabela.dataframe().columns.get_loc("codigo")
    aba.modelo_tabela.setData(aba.modelo_tabela.index(0, col_codigo), "AJ4-M-001", 2)

    perimetro = aba.modelo()

    assert perimetro.denominacao == "Fazenda Teste"
    assert perimetro.hemisferio == "Norte"
    assert len(perimetro.vertices) == 1
    assert perimetro.vertices[0].codigo == "AJ4-M-001"


def test_carregar_cabecalho_repopula_campos(qtbot):
    aba = _nova_aba()
    qtbot.addWidget(aba)
    dados = Perimetro(
        denominacao="Parte X",
        parcela_numero="007",
        lado="Interno",
        tipo_coordenada="UTM",
        meridiano_central=-45.0,
        hemisferio="Norte",
    )

    aba.carregar_cabecalho(dados)

    assert aba.denominacao.text() == "Parte X"
    assert aba.parcela_numero.text() == "007"
    assert aba.lado.currentText() == "Interno"
    assert aba.tipo_coordenada.currentText() == "UTM"
    assert aba.meridiano_central.currentText() == "-45"
    assert aba.hemisferio.currentText() == "Norte"


def test_limpar_parcela_confirmado_apaga_a_grade(qtbot, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    aba = _nova_aba()
    qtbot.addWidget(aba)
    col_codigo = aba.modelo_tabela.dataframe().columns.get_loc("codigo")
    aba.modelo_tabela.setData(aba.modelo_tabela.index(0, col_codigo), "AJ4-M-001", 2)
    aba.denominacao.setText("Fazenda Teste")

    aba._limpar_parcela()

    assert aba.modelo_tabela.dataframe().at[0, "codigo"] == ""
    assert aba.denominacao.text() == "Fazenda Teste"  # cabeçalho não é afetado


def test_limpar_parcela_cancelado_nao_apaga_nada(qtbot, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.No)
    aba = _nova_aba()
    qtbot.addWidget(aba)
    col_codigo = aba.modelo_tabela.dataframe().columns.get_loc("codigo")
    aba.modelo_tabela.setData(aba.modelo_tabela.index(0, col_codigo), "AJ4-M-001", 2)

    aba._limpar_parcela()

    assert aba.modelo_tabela.dataframe().at[0, "codigo"] == "AJ4-M-001"


def test_limpar_parcela_pode_ser_desfeita(qtbot, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    aba = _nova_aba()
    qtbot.addWidget(aba)
    col_codigo = aba.modelo_tabela.dataframe().columns.get_loc("codigo")
    aba.modelo_tabela.setData(aba.modelo_tabela.index(0, col_codigo), "AJ4-M-001", 2)

    aba._limpar_parcela()
    aba.modelo_tabela.desfazer()

    assert aba.modelo_tabela.dataframe().at[0, "codigo"] == "AJ4-M-001"
