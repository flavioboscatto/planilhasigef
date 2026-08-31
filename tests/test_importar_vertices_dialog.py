"""Testes da Fase 5 (importação de vértices). QFileDialog.getOpenFileName
é um método estático fácil de simular — diferente do diálogo por
subprocess do Streamlit local, não precisa de clique manual nem de
processo à parte pra testar o fluxo inteiro.

Este diálogo só cuida de arquivo/separador/mapeamento/conversão; o que
acontece com o resultado (virar uma aba "Importação N" persistente) é
responsabilidade de quem chama, testada em test_importacao_tab.py e em
test_perimetro_tab.py."""
from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtWidgets import QFileDialog

from ui_qt.importar_vertices_dialog import ImportarVerticesDialog
from ui_qt.tema_qt import carregar_tema

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


def _dominios():
    with (CONFIG_DIR / "dominios.json").open("r", encoding="utf-8") as f:
        return json.load(f)


def _novo_dialogo(criar_aba_importacao, meridiano=-51.0, hemisferio="Sul"):
    dominios = _dominios()
    return ImportarVerticesDialog(
        opcoes_tipo_vertice=[t["codigo"] for t in dominios["tipos_vertice"]],
        opcoes_metodo=[m["codigo"] for m in dominios["metodos_posicionamento"]],
        opcoes_limite=[t["codigo"] for t in dominios["tipos_limite"]],
        meridianos_disponiveis=dominios["meridianos_centrais_brasil"],
        hemisferios_disponiveis=dominios["hemisferio"],
        meridiano_inicial=meridiano,
        hemisferio_inicial=hemisferio,
        tema=carregar_tema(),
        casas=dominios["limites_coordenadas"],
        criar_aba_importacao=criar_aba_importacao,
    )


def _apontar_arquivo(monkeypatch, caminho: Path) -> None:
    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(caminho), "")))


def test_escolher_arquivo_preenche_previa_e_mapeamento(qtbot, tmp_path, monkeypatch):
    arquivo = tmp_path / "vertices.csv"
    arquivo.write_text("codigo;lat;long\nAJ4-M-001;-27,50;-48,50\nAJ4-M-002;-27,51;-48,51\n", encoding="utf-8")
    _apontar_arquivo(monkeypatch, arquivo)

    dialogo = _novo_dialogo(lambda *a: None)
    qtbot.addWidget(dialogo)
    dialogo.combo_separador.setCurrentText("Ponto e vírgula (;)")

    dialogo._escolher_arquivo()

    assert dialogo.tabela_previa.rowCount() == 2
    assert set(dialogo._combos_mapeamento) == {"codigo", "lat", "long"}


def test_criar_versao_geodesica_chama_callback_com_dados_convertidos(qtbot, tmp_path, monkeypatch):
    arquivo = tmp_path / "vertices.csv"
    arquivo.write_text("codigo;lat;long\nAJ4-M-001;27 30 30 S;48 30 30 W\n", encoding="utf-8")
    _apontar_arquivo(monkeypatch, arquivo)

    chamadas = []
    dialogo = _novo_dialogo(lambda dados, utm, mer, hem: chamadas.append((dados, utm, mer, hem)))
    qtbot.addWidget(dialogo)
    dialogo.combo_separador.setCurrentText("Ponto e vírgula (;)")
    dialogo._escolher_arquivo()
    dialogo._combos_mapeamento["codigo"].setCurrentText("Código do vértice")
    dialogo._combos_mapeamento["lat"].setCurrentText("N / Latitude")
    dialogo._combos_mapeamento["long"].setCurrentText("E / Longitude")
    dialogo.combo_sistema.setCurrentText("Geodésica")
    dialogo.combo_formato_geo.setCurrentText("GMS — símbolos ou espaços (ex.: 27 30 30 S)")

    dialogo._criar_versao()

    assert len(chamadas) == 1
    dados, dados_utm_brutos, _meridiano, _hemisferio = chamadas[0]
    assert dados.iloc[0]["codigo"] == "AJ4-M-001"
    assert dados_utm_brutos is None  # não é UTM: não guarda easting/northing bruto


def test_criar_versao_grau_minuto_decimal_chama_callback_com_dados_convertidos(qtbot, tmp_path, monkeypatch):
    arquivo = tmp_path / "vertices.csv"
    arquivo.write_text("codigo;lat;long\nAJ4-M-001;27 30,500 S;48 30,500 W\n", encoding="utf-8")
    _apontar_arquivo(monkeypatch, arquivo)

    chamadas = []
    dialogo = _novo_dialogo(lambda dados, utm, mer, hem: chamadas.append((dados, utm, mer, hem)))
    qtbot.addWidget(dialogo)
    dialogo.combo_separador.setCurrentText("Ponto e vírgula (;)")
    dialogo._escolher_arquivo()
    dialogo._combos_mapeamento["codigo"].setCurrentText("Código do vértice")
    dialogo._combos_mapeamento["lat"].setCurrentText("N / Latitude")
    dialogo._combos_mapeamento["long"].setCurrentText("E / Longitude")
    dialogo.combo_sistema.setCurrentText("Geodésica")
    dialogo.combo_formato_geo.setCurrentText("Grau + minuto decimal, sem segundos (ex.: 27 30,500 S)")

    dialogo._criar_versao()

    assert len(chamadas) == 1
    dados, dados_utm_brutos, _meridiano, _hemisferio = chamadas[0]
    assert dados.iloc[0]["codigo"] == "AJ4-M-001"
    assert dados_utm_brutos is None
    assert dados.iloc[0]["n_lat"].startswith("-27,5")
    assert dados.iloc[0]["e_long"].startswith("-48,5")


def test_criar_versao_utm_repassa_easting_northing_bruto_e_meridiano_hemisferio_atuais(qtbot, tmp_path, monkeypatch):
    arquivo = tmp_path / "vertices.csv"
    arquivo.write_text("codigo;x;y\nAJ4-M-001;500000;7000000\n", encoding="utf-8")
    _apontar_arquivo(monkeypatch, arquivo)

    chamadas = []
    dialogo = _novo_dialogo(lambda dados, utm, mer, hem: chamadas.append((dados, utm, mer, hem)), meridiano=-51.0, hemisferio="Sul")
    qtbot.addWidget(dialogo)
    dialogo.combo_separador.setCurrentText("Ponto e vírgula (;)")
    dialogo._escolher_arquivo()
    dialogo._combos_mapeamento["codigo"].setCurrentText("Código do vértice")
    dialogo._combos_mapeamento["x"].setCurrentText("E / Longitude")
    dialogo._combos_mapeamento["y"].setCurrentText("N / Latitude")
    dialogo.combo_sistema.setCurrentText("UTM")

    dialogo._criar_versao()

    assert len(chamadas) == 1
    dados, dados_utm_brutos, meridiano, hemisferio = chamadas[0]
    assert dados_utm_brutos is not None
    assert dados_utm_brutos.iloc[0]["e_long"] == "500000"
    assert dados_utm_brutos.iloc[0]["n_lat"] == "7000000"
    assert meridiano == -51.0
    assert hemisferio == "Sul"


def test_utm_sem_colunas_de_coordenada_nao_trava_so_avisa(qtbot, tmp_path, monkeypatch):
    arquivo = tmp_path / "vertices.csv"
    arquivo.write_text("codigo;obs\nAJ4-M-001;nota\n", encoding="utf-8")
    _apontar_arquivo(monkeypatch, arquivo)

    chamadas = []
    dialogo = _novo_dialogo(lambda *a: chamadas.append(a))
    qtbot.addWidget(dialogo)
    dialogo.combo_separador.setCurrentText("Ponto e vírgula (;)")
    dialogo._escolher_arquivo()
    dialogo._combos_mapeamento["codigo"].setCurrentText("Código do vértice")
    dialogo.combo_sistema.setCurrentText("UTM")

    dialogo._criar_versao()  # sem e_long/n_lat mapeados: cai no caminho "sem coordenada", não quebra

    assert len(chamadas) == 1
