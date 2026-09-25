"""Testes da Fase 3 (grade de vértices) — cobrem exatamente os bugs que
motivaram a migração do Streamlit: checkbox que não marcava de primeira,
colar em bloco que engolia a primeira tentativa, célula que se perdia.
Aqui tudo é síncrono (sem rerun), então cada operação testada precisa
funcionar sempre, não "às vezes"."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QWidget

from core.tabela_vertices import tabela_vazia
from ui_qt.tema_qt import carregar_tema
from ui_qt.vertices_table import TabelaVerticesModel, TabelaVerticesView, _ComboDelegate

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


def _dominios():
    with (CONFIG_DIR / "dominios.json").open("r", encoding="utf-8") as f:
        return json.load(f)


def _nova_view(df: pd.DataFrame | None = None) -> TabelaVerticesView:
    dominios = _dominios()
    tema = carregar_tema()
    modelo = TabelaVerticesModel(
        tema=tema,
        opcoes_tipo_vertice=[t["codigo"] for t in dominios["tipos_vertice"]],
        opcoes_metodo=[m["codigo"] for m in dominios["metodos_posicionamento"]],
        opcoes_limite=[t["codigo"] for t in dominios["tipos_limite"]],
        casas=dominios["limites_coordenadas"],
        df=df,
    )
    return TabelaVerticesView(modelo)


def test_grade_comeca_com_tres_linhas_e_renumerar_marcado(qtbot):
    view = _nova_view()
    qtbot.addWidget(view)
    modelo = view.model()

    assert modelo.rowCount() == 3
    col_renumerar = modelo.dataframe().columns.get_loc("renumerar")
    for linha in range(3):
        indice = modelo.index(linha, col_renumerar)
        assert modelo.data(indice, Qt.ItemDataRole.CheckStateRole) == Qt.CheckState.Checked


def test_desmarcar_checkbox_renumerar_sempre_pega(qtbot):
    view = _nova_view()
    qtbot.addWidget(view)
    modelo = view.model()
    indice = modelo.index(0, modelo.dataframe().columns.get_loc("renumerar"))

    modelo.setData(indice, Qt.CheckState.Unchecked, Qt.ItemDataRole.CheckStateRole)

    assert modelo.data(indice, Qt.ItemDataRole.CheckStateRole) == Qt.CheckState.Unchecked
    assert bool(modelo.dataframe().at[0, "renumerar"]) is False


def test_digitar_codigo_reflete_no_dataframe(qtbot):
    view = _nova_view()
    qtbot.addWidget(view)
    modelo = view.model()
    coluna_codigo = modelo.dataframe().columns.get_loc("codigo")

    modelo.setData(modelo.index(0, coluna_codigo), "AJ4-M-9121", Qt.ItemDataRole.EditRole)

    assert modelo.dataframe().at[0, "codigo"] == "AJ4-M-9121"


def test_colar_bloco_preenche_varias_celulas_de_uma_vez(qtbot):
    view = _nova_view()
    qtbot.addWidget(view)
    modelo = view.model()
    col_codigo = modelo.dataframe().columns.get_loc("codigo")
    col_elong = modelo.dataframe().columns.get_loc("e_long")

    bloco = "AJ4-M-001\t-48,50\nAJ4-M-002\t-48,51\nAJ4-M-003\t-48,52"
    QGuiApplication.clipboard().setText(bloco)
    view.setCurrentIndex(modelo.index(0, col_codigo))

    view._colar()

    df = modelo.dataframe()
    assert list(df["codigo"]) == ["AJ4-M-001", "AJ4-M-002", "AJ4-M-003"]
    assert df.at[0, "e_long"] == "-48,50"
    assert df.at[2, "e_long"] == "-48,52"


def test_colar_valor_unico_preenche_selecao_inteira_nao_so_a_ultima_celula(qtbot):
    # bug relatado: selecionar várias células e colar um valor só (Ctrl+C
    # de UMA célula) só aplicava na última célula da seleção — currentIndex()
    # é a última clicada, não o topo-esquerda.
    view = _nova_view()
    qtbot.addWidget(view)
    modelo = view.model()
    col_tipo_limite = modelo.dataframe().columns.get_loc("tipo_limite")

    QGuiApplication.clipboard().setText("CO")
    selecao = view.selectionModel()
    # seleciona de baixo pra cima, do jeito que um arraste real do mouse de
    # baixo pra cima deixaria: várias células selecionadas, "atual" sendo a
    # ÚLTIMA marcada (a de cima), não o topo-esquerda da seleção.
    for linha in (2, 1, 0):
        selecao.select(modelo.index(linha, col_tipo_limite), selecao.SelectionFlag.Select)

    view._colar()

    assert list(modelo.dataframe()["tipo_limite"]) == ["CO", "CO", "CO"]


def test_colar_bloco_usa_topo_esquerda_da_selecao_nao_a_celula_atual(qtbot):
    view = _nova_view()
    qtbot.addWidget(view)
    modelo = view.model()
    col_codigo = modelo.dataframe().columns.get_loc("codigo")

    QGuiApplication.clipboard().setText("A-1\nA-2\nA-3")
    selecao = view.selectionModel()
    for linha in (2, 1, 0):  # seleciona de baixo pra cima, como um arraste real
        selecao.select(modelo.index(linha, col_codigo), selecao.SelectionFlag.Select)

    view._colar()

    assert list(modelo.dataframe()["codigo"]) == ["A-1", "A-2", "A-3"]


def test_copiar_usa_valor_editavel_nao_o_formatado(qtbot):
    view = _nova_view()
    qtbot.addWidget(view)
    modelo = view.model()
    col_elong = modelo.dataframe().columns.get_loc("e_long")
    modelo.setData(modelo.index(0, col_elong), "-48,548333", Qt.ItemDataRole.EditRole)

    selecao = view.selectionModel()
    selecao.select(modelo.index(0, col_elong), selecao.SelectionFlag.Select)
    view._copiar()

    assert QGuiApplication.clipboard().text() == "-48,548333"


def test_preencher_para_baixo_copia_valor_do_topo_da_selecao(qtbot):
    view = _nova_view()
    qtbot.addWidget(view)
    modelo = view.model()
    col_metodo = modelo.dataframe().columns.get_loc("metodo_posicionamento")
    modelo.setData(modelo.index(0, col_metodo), "GPS/GNSS", Qt.ItemDataRole.EditRole)

    selecao = view.selectionModel()
    for linha in range(3):
        selecao.select(
            modelo.index(linha, col_metodo),
            selecao.SelectionFlag.Select,
        )

    view._preencher_para_baixo()

    df = modelo.dataframe()
    assert list(df["metodo_posicionamento"]) == ["GPS/GNSS", "GPS/GNSS", "GPS/GNSS"]


def test_cores_por_grupo_de_coluna_batem_com_o_tema_oficial(qtbot):
    view = _nova_view()
    qtbot.addWidget(view)
    modelo = view.model()
    df = modelo.dataframe()
    tema = carregar_tema()

    col_codigo = df.columns.get_loc("codigo")
    col_cns = df.columns.get_loc("cns")

    cor_geral = modelo.data(modelo.index(0, col_codigo), Qt.ItemDataRole.BackgroundRole)
    cor_confrontante = modelo.data(modelo.index(0, col_cns), Qt.ItemDataRole.BackgroundRole)

    assert cor_geral.name() == tema["tabela_entrada_geral"].fundo.name()
    assert cor_confrontante.name() == tema["tabela_entrada_confrontante"].fundo.name()


def test_definir_coluna_preenche_todas_as_linhas(qtbot):
    view = _nova_view()
    qtbot.addWidget(view)
    modelo = view.model()

    modelo.definir_coluna("tipo_limite", "CO")

    assert list(modelo.dataframe()["tipo_limite"]) == ["CO", "CO", "CO"]


def test_inserir_e_remover_linha(qtbot):
    view = _nova_view()
    qtbot.addWidget(view)
    modelo = view.model()

    modelo.inserir_linha({"codigo": "NOVO-1"})
    assert modelo.rowCount() == 4
    assert modelo.dataframe().at[3, "codigo"] == "NOVO-1"

    modelo.remover_linhas([3])
    assert modelo.rowCount() == 3


def test_coluna_de_combo_mostra_setinha_indicativa_mas_edicao_fica_limpa(qtbot):
    view = _nova_view()
    qtbot.addWidget(view)
    modelo = view.model()
    col_tipo = modelo.dataframe().columns.get_loc("tipo_vertice")

    # célula vazia já mostra a seta (nada indicava que abria um combo antes
    # de digitar/clicar)
    assert modelo.data(modelo.index(0, col_tipo), Qt.ItemDataRole.DisplayRole) == "▾"

    modelo.setData(modelo.index(0, col_tipo), "M", Qt.ItemDataRole.EditRole)

    assert modelo.data(modelo.index(0, col_tipo), Qt.ItemDataRole.DisplayRole) == "M ▾"
    assert modelo.data(modelo.index(0, col_tipo), Qt.ItemDataRole.EditRole) == "M"


def _clicar(view, indice, x: float) -> list:
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QMouseEvent

    aberto = []
    view.edit = lambda i: aberto.append(i) or True  # substitui só pra este teste

    retangulo = view.visualRect(indice)
    local = QPointF(x, retangulo.center().y())
    evento = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        local,
        local,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    view.mousePressEvent(evento)
    return aberto


def test_combo_delegate_tem_opcao_em_branco_primeiro(qtbot, monkeypatch):
    # pedido do usuário: dá pra "limpar" a célula escolhendo o item em
    # branco, sem precisar apagar via teclado.
    #
    # Desliga o showPopup agendado (QTimer.singleShot(0, ...)) pra este
    # teste: monkeypatch.setattr direto em "QTimer.singleShot" NÃO funciona
    # (é um método C++/Shiboken — atribuir na classe não intercepta a
    # chamada real, mesmo motivo de QMenu.exec já visto neste projeto).
    # Sem isto, o showPopup agendado fica pendente na fila de eventos do Qt
    # e dispara mais tarde, em cima de um QComboBox já destruído pelo
    # término deste teste — access violation intermitente num teste
    # SEGUINTE, sem relação nenhuma com ele. Substituir o próprio nome
    # "QTimer" no módulo (objeto Python puro) evita o C++ por completo.
    from types import SimpleNamespace

    monkeypatch.setattr("ui_qt.vertices_table.QTimer", SimpleNamespace(singleShot=lambda *a, **k: None))
    janela = QWidget()
    qtbot.addWidget(janela)
    delegate = _ComboDelegate(["M", "P", "V"])

    editor = delegate.createEditor(janela, None, None)
    qtbot.addWidget(editor)

    assert editor.itemText(0) == ""
    assert [editor.itemText(i) for i in range(1, editor.count())] == ["M", "P", "V"]


def test_clicar_na_seta_da_coluna_combo_abre_o_editor(qtbot):
    view = _nova_view()
    qtbot.addWidget(view)
    modelo = view.model()
    col_tipo = modelo.dataframe().columns.get_loc("tipo_vertice")
    indice = modelo.index(0, col_tipo)

    retangulo = view.visualRect(indice)
    aberto = _clicar(view, indice, retangulo.right() - 2)

    assert aberto == [indice]


def test_clicar_em_qualquer_ponto_da_celula_combo_abre_o_editor(qtbot):
    # bug relatado pela turma-teste: só a "setinha" (últimos ~20px) abria de
    # primeira — o resto da célula (a maior parte, onde o texto aparece) só
    # selecionava, dando a impressão de precisar de 2-3 cliques.
    view = _nova_view()
    qtbot.addWidget(view)
    modelo = view.model()
    col_tipo = modelo.dataframe().columns.get_loc("tipo_vertice")
    indice = modelo.index(0, col_tipo)

    retangulo = view.visualRect(indice)
    aberto = _clicar(view, indice, retangulo.left() + 2)

    assert aberto == [indice]


def test_clicar_em_celula_de_texto_continua_so_selecionando(qtbot):
    # não pode virar "clica em qualquer coluna e já edita" — só as 3
    # colunas de combo (ver _COLUNAS_COMBO); o resto continua exigindo
    # duplo clique/tecla, pra não atrapalhar arrastar/selecionar bloco.
    #
    # qtbot.mouseClick (não um QMouseEvent construído à mão + chamada
    # direta de mousePressEvent, como no teste acima): pra colunas de texto
    # a chamada cai em super().mousePressEvent(), nunca exercitado antes
    # neste arquivo com evento sintético — fazer isso à mão travou o
    # processo (falha de acesso do Qt) numa rodada da suíte inteira.
    view = _nova_view()
    qtbot.addWidget(view)
    view.show()
    modelo = view.model()
    col_codigo = modelo.dataframe().columns.get_loc("codigo")
    indice = modelo.index(0, col_codigo)

    ponto = view.visualRect(indice).center()
    qtbot.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=ponto)

    assert view.state() != view.State.EditingState
    assert view.currentIndex() == indice


def test_mover_linha_para_cima_troca_com_a_vizinha_de_cima(qtbot):
    view = _nova_view()
    qtbot.addWidget(view)
    modelo = view.model()
    col_codigo = modelo.dataframe().columns.get_loc("codigo")
    modelo.setData(modelo.index(0, col_codigo), "A", 2)
    modelo.setData(modelo.index(1, col_codigo), "B", 2)
    modelo.setData(modelo.index(2, col_codigo), "C", 2)

    nova_pos = modelo.mover_linha(1, -1)

    assert nova_pos == 0
    assert list(modelo.dataframe()["codigo"]) == ["B", "A", "C"]


def test_mover_linha_para_baixo_troca_com_a_vizinha_de_baixo(qtbot):
    view = _nova_view()
    qtbot.addWidget(view)
    modelo = view.model()
    col_codigo = modelo.dataframe().columns.get_loc("codigo")
    modelo.setData(modelo.index(0, col_codigo), "A", 2)
    modelo.setData(modelo.index(1, col_codigo), "B", 2)
    modelo.setData(modelo.index(2, col_codigo), "C", 2)

    nova_pos = modelo.mover_linha(1, 1)

    assert nova_pos == 2
    assert list(modelo.dataframe()["codigo"]) == ["A", "C", "B"]


def test_mover_linha_na_ponta_nao_faz_nada(qtbot):
    view = _nova_view()
    qtbot.addWidget(view)
    modelo = view.model()
    modelo.setData(modelo.index(0, modelo.dataframe().columns.get_loc("codigo")), "A", 2)

    assert modelo.mover_linha(0, -1) is None
    assert modelo.mover_linha(2, 1) is None
    assert modelo.dataframe().at[0, "codigo"] == "A"


def test_exibicao_mostra_gms_e_casas_certas_mas_edicao_continua_decimal(qtbot):
    view = _nova_view()
    qtbot.addWidget(view)
    modelo = view.model()
    df = modelo.dataframe()
    col_elong = df.columns.get_loc("e_long")
    col_nlat = df.columns.get_loc("n_lat")
    col_h = df.columns.get_loc("h")
    col_sigma = df.columns.get_loc("sigma_h")

    modelo.setData(modelo.index(0, col_elong), "-48,548333", Qt.ItemDataRole.EditRole)
    modelo.setData(modelo.index(0, col_nlat), "-27,508333", Qt.ItemDataRole.EditRole)
    modelo.setData(modelo.index(0, col_h), "13,23", Qt.ItemDataRole.EditRole)
    modelo.setData(modelo.index(0, col_sigma), "0,1", Qt.ItemDataRole.EditRole)

    # exibição: formato final da planilha (GMS / casas decimais exigidas)
    texto_elong = modelo.data(modelo.index(0, col_elong), Qt.ItemDataRole.DisplayRole)
    texto_nlat = modelo.data(modelo.index(0, col_nlat), Qt.ItemDataRole.DisplayRole)
    texto_h = modelo.data(modelo.index(0, col_h), Qt.ItemDataRole.DisplayRole)
    texto_sigma = modelo.data(modelo.index(0, col_sigma), Qt.ItemDataRole.DisplayRole)
    assert texto_elong.endswith("W")
    assert texto_nlat.endswith("S")
    assert "," in texto_elong  # tem segundos com vírgula decimal
    assert texto_h == "13,230"  # 3 casas
    assert texto_sigma == "0,10"  # 2 casas

    # edição: continua decimal solto, do jeito que foi digitado
    assert modelo.data(modelo.index(0, col_elong), Qt.ItemDataRole.EditRole) == "-48,548333"
    assert modelo.data(modelo.index(0, col_h), Qt.ItemDataRole.EditRole) == "13,23"


def test_substituir_dataframe_inteiro():
    tema = carregar_tema()
    dominios = _dominios()
    modelo = TabelaVerticesModel(
        tema=tema,
        opcoes_tipo_vertice=[t["codigo"] for t in dominios["tipos_vertice"]],
        opcoes_metodo=[m["codigo"] for m in dominios["metodos_posicionamento"]],
        opcoes_limite=[t["codigo"] for t in dominios["tipos_limite"]],
        casas=dominios["limites_coordenadas"],
    )
    nova = tabela_vazia(5)
    nova.at[0, "codigo"] = "X-1"

    modelo.substituir(nova)

    assert modelo.rowCount() == 5
    assert modelo.dataframe().at[0, "codigo"] == "X-1"


def test_substituir_reordena_colunas_por_nome_mesmo_que_venham_fora_de_ordem(qtbot):
    # é exatamente isto que corrige o bug do Reorganizar: um DataFrame
    # construído a partir de uma lista de dicts pode vir com as colunas em
    # qualquer ordem — a grade sempre lê/escreve por posição, então
    # precisa normalizar antes de aceitar.
    view = _nova_view()
    qtbot.addWidget(view)
    modelo = view.model()

    fora_de_ordem = pd.DataFrame([
        {"descritivo": "obs", "codigo": "X-1", "renumerar": True, "tipo_vertice": "M",
         "e_long": "-48,00", "sigma_long": "0,01", "n_lat": "-9,00", "sigma_lat": "0,01",
         "h": "1,0", "sigma_h": "0,01", "metodo_posicionamento": "PG1", "tipo_limite": "LA1",
         "cns": "", "matricula": ""},
    ])

    modelo.substituir(fora_de_ordem)

    df = modelo.dataframe()
    assert df.at[0, "codigo"] == "X-1"
    assert df.at[0, "e_long"] == "-48,00"
    assert df.at[0, "descritivo"] == "obs"
    assert df.at[0, "metodo_posicionamento"] == "PG1"


def test_desfazer_volta_ao_estado_anterior(qtbot):
    view = _nova_view()
    qtbot.addWidget(view)
    modelo = view.model()
    col_codigo = modelo.dataframe().columns.get_loc("codigo")
    modelo.setData(modelo.index(0, col_codigo), "ORIGINAL", Qt.ItemDataRole.EditRole)
    modelo.setData(modelo.index(0, col_codigo), "MUDOU", Qt.ItemDataRole.EditRole)
    assert modelo.dataframe().at[0, "codigo"] == "MUDOU"

    resultado = modelo.desfazer()

    assert resultado is True
    assert modelo.dataframe().at[0, "codigo"] == "ORIGINAL"


def test_desfazer_sem_historico_nao_quebra(qtbot):
    view = _nova_view()
    qtbot.addWidget(view)
    modelo = view.model()

    assert modelo.desfazer() is False


def test_ctrl_z_na_view_chama_desfazer(qtbot):
    from PySide6.QtGui import QKeySequence

    view = _nova_view()
    qtbot.addWidget(view)
    modelo = view.model()
    col_codigo = modelo.dataframe().columns.get_loc("codigo")
    modelo.setData(modelo.index(0, col_codigo), "MUDOU", Qt.ItemDataRole.EditRole)
    view.setFocus()

    qtbot.keySequence(view, QKeySequence.StandardKey.Undo)

    assert modelo.dataframe().at[0, "codigo"] != "MUDOU"


def test_painel_congelado_mostra_so_as_4_primeiras_colunas(qtbot):
    # pedido do usuário: Pt.Original/Renum./Tipo/Código continuam visíveis
    # rolando a grade na horizontal — as outras 11 colunas ficam escondidas
    # no painel congelado (só aparecem na view principal, que rola).
    from core.tabela_vertices import COLUNAS_VERTICE

    view = _nova_view()
    qtbot.addWidget(view)

    congelado = view.painel_congelado
    for i, campo in enumerate(COLUNAS_VERTICE):
        assert congelado.isColumnHidden(i) == (i >= 4), campo


def test_painel_congelado_compartilha_selecao_com_a_view_principal(qtbot):
    view = _nova_view()
    qtbot.addWidget(view)

    assert view.painel_congelado.selectionModel() is view.selectionModel()


def test_redimensionar_coluna_congelada_na_view_principal_propaga_pro_painel(qtbot):
    view = _nova_view()
    qtbot.addWidget(view)

    view.setColumnWidth(0, 150)

    assert view.painel_congelado.columnWidth(0) == 150


def test_geometria_do_painel_congelado_bate_com_a_soma_das_4_colunas(qtbot):
    view = _nova_view()
    qtbot.addWidget(view)

    largura_esperada = sum(view.columnWidth(c) for c in range(4))

    assert view.painel_congelado.geometry().width() == largura_esperada


def test_painel_congelado_nao_recebe_foco_de_teclado(qtbot):
    # todo atalho de teclado (Ctrl+Z/C/V/D) precisa continuar passando só
    # pela view principal — duplicar isso no painel dispararia a ação duas
    # vezes se ele pudesse ganhar foco.
    view = _nova_view()
    qtbot.addWidget(view)

    assert view.painel_congelado.focusPolicy() == Qt.FocusPolicy.NoFocus
