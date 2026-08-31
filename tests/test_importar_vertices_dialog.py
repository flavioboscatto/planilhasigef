"""Testes da Fase 5 (importação de vértices). QFileDialog.getOpenFileName
é um método estático fácil de simular — diferente do diálogo por
subprocess do Streamlit local, não precisa de clique manual nem de
processo à parte pra testar o fluxo inteiro."""
from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtWidgets import QFileDialog

from ui_qt.importar_vertices_dialog import ImportarVerticesDialog
from ui_qt.tema_qt import carregar_tema
from ui_qt.vertices_table import TabelaVerticesView

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


def _dominios():
    with (CONFIG_DIR / "dominios.json").open("r", encoding="utf-8") as f:
        return json.load(f)


def _novo_dialogo(aplicar_versao, meridiano=-51.0, hemisferio="Sul"):
    dominios = _dominios()
    return ImportarVerticesDialog(
        opcoes_tipo_vertice=[t["codigo"] for t in dominios["tipos_vertice"]],
        opcoes_metodo=[m["codigo"] for m in dominios["metodos_posicionamento"]],
        opcoes_limite=[t["codigo"] for t in dominios["tipos_limite"]],
        meridiano_central=meridiano,
        hemisferio=hemisferio,
        tema=carregar_tema(),
        aplicar_versao=aplicar_versao,
    )


def _apontar_arquivo(monkeypatch, caminho: Path) -> None:
    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(caminho), "")))


def test_escolher_arquivo_preenche_previa_e_mapeamento(qtbot, tmp_path, monkeypatch):
    arquivo = tmp_path / "vertices.csv"
    arquivo.write_text("codigo;lat;long\nAJ4-M-001;-27,50;-48,50\nAJ4-M-002;-27,51;-48,51\n", encoding="utf-8")
    _apontar_arquivo(monkeypatch, arquivo)

    dialogo = _novo_dialogo(lambda df: None)
    qtbot.addWidget(dialogo)
    dialogo.combo_separador.setCurrentText("Ponto e vírgula (;)")

    dialogo._escolher_arquivo()

    assert dialogo.tabela_previa.rowCount() == 2
    assert set(dialogo._combos_mapeamento) == {"codigo", "lat", "long"}


def test_criar_versao_geodesica_cria_bloco_pendente_sem_aplicar_ainda(qtbot, tmp_path, monkeypatch):
    arquivo = tmp_path / "vertices.csv"
    arquivo.write_text("codigo;lat;long\nAJ4-M-001;27 30 30 S;48 30 30 W\n", encoding="utf-8")
    _apontar_arquivo(monkeypatch, arquivo)

    resultados = []
    dialogo = _novo_dialogo(resultados.append)
    qtbot.addWidget(dialogo)
    dialogo.combo_separador.setCurrentText("Ponto e vírgula (;)")
    dialogo._escolher_arquivo()
    dialogo._combos_mapeamento["codigo"].setCurrentText("Código do vértice")
    dialogo._combos_mapeamento["lat"].setCurrentText("N / Latitude")
    dialogo._combos_mapeamento["long"].setCurrentText("E / Longitude")
    dialogo.combo_sistema.setCurrentText("Geodésica")
    dialogo.combo_formato_geo.setCurrentText("GMS — símbolos ou espaços (ex.: 27 30 30 S)")

    dialogo._criar_versao()

    assert dialogo.layout_versoes.count() == 1
    assert resultados == []  # criar versão não aplica nada ainda, só fica pendente


def test_usar_versao_chama_callback_com_dados_convertidos_e_remove_bloco(qtbot, tmp_path, monkeypatch):
    arquivo = tmp_path / "vertices.csv"
    arquivo.write_text("codigo;lat;long\nAJ4-M-001;-27,50;-48,50\n", encoding="utf-8")
    _apontar_arquivo(monkeypatch, arquivo)

    resultados = []
    dialogo = _novo_dialogo(resultados.append)
    qtbot.addWidget(dialogo)
    dialogo.combo_separador.setCurrentText("Ponto e vírgula (;)")
    dialogo._escolher_arquivo()
    dialogo._combos_mapeamento["codigo"].setCurrentText("Código do vértice")
    dialogo._combos_mapeamento["lat"].setCurrentText("N / Latitude")
    dialogo._combos_mapeamento["long"].setCurrentText("E / Longitude")
    dialogo.combo_sistema.setCurrentText("Geodésica")
    dialogo.combo_formato_geo.setCurrentText("Decimal (grau decimal, ex.: -27,508333)")
    dialogo._criar_versao()

    bloco = dialogo.layout_versoes.itemAt(0).widget()
    vista = bloco.findChild(TabelaVerticesView)
    dialogo._usar_versao(vista.model(), bloco)

    assert len(resultados) == 1
    assert resultados[0].iloc[0]["codigo"] == "AJ4-M-001"
    assert dialogo.layout_versoes.count() == 0


def test_remover_versao_descarta_sem_chamar_callback(qtbot, tmp_path, monkeypatch):
    arquivo = tmp_path / "vertices.csv"
    arquivo.write_text("codigo;lat;long\nAJ4-M-001;-27,50;-48,50\n", encoding="utf-8")
    _apontar_arquivo(monkeypatch, arquivo)

    resultados = []
    dialogo = _novo_dialogo(resultados.append)
    qtbot.addWidget(dialogo)
    dialogo.combo_separador.setCurrentText("Ponto e vírgula (;)")
    dialogo._escolher_arquivo()
    dialogo._combos_mapeamento["codigo"].setCurrentText("Código do vértice")
    dialogo._combos_mapeamento["lat"].setCurrentText("N / Latitude")
    dialogo._combos_mapeamento["long"].setCurrentText("E / Longitude")
    dialogo.combo_formato_geo.setCurrentText("Decimal (grau decimal, ex.: -27,508333)")
    dialogo._criar_versao()

    bloco = dialogo.layout_versoes.itemAt(0).widget()
    dialogo._remover_versao(bloco)

    assert dialogo.layout_versoes.count() == 0
    assert resultados == []


def test_utm_sem_colunas_de_coordenada_nao_trava_so_avisa(qtbot, tmp_path, monkeypatch):
    arquivo = tmp_path / "vertices.csv"
    arquivo.write_text("codigo;obs\nAJ4-M-001;nota\n", encoding="utf-8")
    _apontar_arquivo(monkeypatch, arquivo)

    dialogo = _novo_dialogo(lambda df: None)
    qtbot.addWidget(dialogo)
    dialogo.combo_separador.setCurrentText("Ponto e vírgula (;)")
    dialogo._escolher_arquivo()
    dialogo._combos_mapeamento["codigo"].setCurrentText("Código do vértice")
    dialogo.combo_sistema.setCurrentText("UTM")

    dialogo._criar_versao()  # sem e_long/n_lat mapeados: cai no caminho "sem coordenada", não quebra

    assert dialogo.layout_versoes.count() == 1
