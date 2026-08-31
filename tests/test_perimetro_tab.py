"""Testes da Fase 4 (aba Perímetro): campos de cabeçalho, botões
(Reorganizar, Marcar/Desmarcar todos, Preencher em lote), round-trip
modelo()/carregar_cabecalho()."""
from __future__ import annotations

import json
from pathlib import Path

from core.models import Perimetro
from ui_qt.perimetro_tab import AbaPerimetro
from ui_qt.tema_qt import carregar_tema

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


def _dominios():
    with (CONFIG_DIR / "dominios.json").open("r", encoding="utf-8") as f:
        return json.load(f)


def _nova_aba(indice: int = 1) -> AbaPerimetro:
    return AbaPerimetro(indice, _dominios(), carregar_tema())


def test_recalcular_utm_sem_vertice_importado_avisa_e_nao_quebra(qtbot, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    avisos = []
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: avisos.append(a))
    aba = _nova_aba()
    qtbot.addWidget(aba)

    aba._recalcular_utm()

    assert avisos


def test_recalcular_utm_apos_importacao_usa_meridiano_hemisferio_atuais(qtbot, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    aba = _nova_aba()
    qtbot.addWidget(aba)

    # simula o que ImportarVerticesDialog faria ao "Usar esta versão"
    # vinda de uma importação UTM (mesmo mecanismo, sem abrir diálogo)
    import pandas as pd
    dados_importados = pd.DataFrame([{"codigo": "AJ4-M-001", "e_long": "0", "n_lat": "0", "tipo_vertice": "", "sigma_long": "", "sigma_lat": "", "h": "", "sigma_h": "", "metodo_posicionamento": "", "tipo_limite": "", "cns": "", "matricula": "", "descritivo": ""}])
    aba._aplicar_versao_importada(dados_importados, {"AJ4-M-001": ("500000", "7000000")})

    aba.hemisferio.setCurrentText("Sul")
    aba._recalcular_utm()

    resultado = aba.modelo_tabela.dataframe()
    linha = resultado[resultado["codigo"] == "AJ4-M-001"].iloc[0]
    from core.parsing import parse_numero
    assert parse_numero(linha["n_lat"]) < 0  # Hemisfério Sul -> latitude negativa


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

    aba.modelo_tabela.definir_coluna("renumerar", True)
    assert all(aba.modelo_tabela.dataframe()["renumerar"])


def test_preencher_em_lote_metodo_posicionamento(qtbot):
    aba = _nova_aba()
    qtbot.addWidget(aba)

    aba.combo_coluna_lote.setCurrentText("Método de Posicionamento")
    aba.combo_valor_lote.setCurrentText("PG1")
    aba._aplicar_lote()

    assert list(aba.modelo_tabela.dataframe()["metodo_posicionamento"]) == ["PG1", "PG1", "PG1"]


def test_reorganizar_exige_pelo_menos_tres_vertices(qtbot, monkeypatch):
    # QMessageBox.warning é modal (bloqueia esperando clique) — sem
    # substituir por um stub, o teste travaria pra sempre.
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)

    aba = _nova_aba()
    qtbot.addWidget(aba)
    aba.modelo_tabela.setData(aba.modelo_tabela.index(0, 2), "A-1", 2)  # Qt.EditRole == 2

    aba._reorganizar()  # não deve lançar exceção, só avisar

    assert aba.modelo_tabela.rowCount() == 3


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
    aba.modelo_tabela.setData(aba.modelo_tabela.index(0, 2), "AJ4-M-001", 2)

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
