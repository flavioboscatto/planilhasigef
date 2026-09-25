"""Testes da Fase 5 (importação de vértices). QFileDialog.getOpenFileName
é um método estático fácil de simular — diferente do diálogo por
subprocess do Streamlit local, não precisa de clique manual nem de
processo à parte pra testar o fluxo inteiro.

Este diálogo só cuida de arquivo/separador/mapeamento/conversão; o que
acontece com o resultado (virar uma aba "Importação N" persistente) é
responsabilidade de quem chama, testada em test_importacao_tab.py e em
test_perimetro_tab.py."""
from __future__ import annotations

import io
import json
from pathlib import Path

import pandas as pd
from PySide6.QtWidgets import QFileDialog

from ui_qt.importar_vertices_dialog import _CAMPOS_VERTICE, ImportarVerticesDialog
from ui_qt.tema_qt import carregar_tema

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


def _dominios():
    with (CONFIG_DIR / "dominios.json").open("r", encoding="utf-8") as f:
        return json.load(f)


def _novo_dialogo(criar_aba_importacao, meridiano=-51.0, hemisferio="Sul", formato="texto"):
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
        formato=formato,
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


def test_rotulos_de_mapeamento_avisam_sobre_utm(qtbot):
    # pedido do usuário (turma-teste): na hora de mapear coluna, deixar
    # claro que Sigma Long/Sigma Lat podem ser na verdade Sigma de E/N,
    # caso o arquivo esteja em UTM — mesmo padrão que "E / Longitude" e
    # "N / Latitude" já usam ao lado.
    assert "Sigma Long/E" in _CAMPOS_VERTICE
    assert "Sigma Lat/N" in _CAMPOS_VERTICE
    assert _CAMPOS_VERTICE["Sigma Long/E"] == "sigma_long"
    assert _CAMPOS_VERTICE["Sigma Lat/N"] == "sigma_lat"


def test_rotulo_matricula_de_mapeamento_bate_com_o_da_grade(qtbot):
    assert "Matrícula/Reg.Imóveis" in _CAMPOS_VERTICE
    assert _CAMPOS_VERTICE["Matrícula/Reg.Imóveis"] == "matricula"


def test_formato_planilha_esconde_separador_e_mostra_combo_de_aba(qtbot):
    dialogo = _novo_dialogo(lambda *a: None, formato="planilha")
    qtbot.addWidget(dialogo)
    dialogo.show()  # isVisible() de um filho só reflete estado próprio com o pai mostrado

    assert not dialogo.rotulo_separador.isVisible()
    assert not dialogo.combo_separador.isVisible()
    assert dialogo.rotulo_aba_planilha.isVisible()
    assert dialogo.combo_aba_planilha.isVisible()


def test_formato_texto_continua_com_separador_e_sem_combo_de_aba(qtbot):
    dialogo = _novo_dialogo(lambda *a: None, formato="texto")
    qtbot.addWidget(dialogo)
    dialogo.show()

    assert dialogo.rotulo_separador.isVisible()
    assert dialogo.combo_separador.isVisible()
    assert not dialogo.rotulo_aba_planilha.isVisible()
    assert not dialogo.combo_aba_planilha.isVisible()


def _bytes_xlsx(dados: dict, aba: str = "Sheet1") -> bytes:
    buffer = io.BytesIO()
    pd.DataFrame(dados).to_excel(buffer, sheet_name=aba, index=False, engine="openpyxl")
    return buffer.getvalue()


def test_escolher_planilha_preenche_abas_previa_e_mapeamento(qtbot, tmp_path, monkeypatch):
    arquivo = tmp_path / "vertices.xlsx"
    arquivo.write_bytes(_bytes_xlsx({"codigo": ["AJ4-M-001", "AJ4-M-002"], "lat": ["-27,50", "-27,51"]}))
    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(arquivo), "")))

    dialogo = _novo_dialogo(lambda *a: None, formato="planilha")
    qtbot.addWidget(dialogo)

    dialogo._escolher_arquivo()

    assert dialogo.combo_aba_planilha.count() == 1
    assert dialogo.combo_aba_planilha.currentText() == "Sheet1"
    assert dialogo.tabela_previa.rowCount() == 2
    assert set(dialogo._combos_mapeamento) == {"codigo", "lat"}


def test_criar_versao_a_partir_de_planilha_com_varias_abas(qtbot, tmp_path, monkeypatch):
    arquivo = tmp_path / "vertices.xlsx"
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        pd.DataFrame({"codigo": ["ERRADO"]}).to_excel(writer, sheet_name="Rascunho", index=False)
        pd.DataFrame({"codigo": ["AJ4-M-001"], "lat": ["-27,50"], "long": ["-48,50"]}).to_excel(
            writer, sheet_name="Vertices", index=False
        )
    arquivo.write_bytes(buffer.getvalue())
    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(arquivo), "")))

    chamadas = []
    dialogo = _novo_dialogo(lambda dados, utm, mer, hem: chamadas.append(dados), formato="planilha")
    qtbot.addWidget(dialogo)
    dialogo._escolher_arquivo()
    dialogo.combo_aba_planilha.setCurrentText("Vertices")
    dialogo._combos_mapeamento["codigo"].setCurrentText("Código do vértice")
    dialogo._combos_mapeamento["lat"].setCurrentText("N / Latitude")
    dialogo._combos_mapeamento["long"].setCurrentText("E / Longitude")
    dialogo.combo_sistema.setCurrentText("Geodésica")
    dialogo.combo_formato_geo.setCurrentText("Decimal (grau decimal, ex.: -27,508333)")

    dialogo._criar_versao()

    assert len(chamadas) == 1
    assert chamadas[0].iloc[0]["codigo"] == "AJ4-M-001"
