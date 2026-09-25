"""Testes de importers/planilha.py (V5): leitura de planilha (XLS/XLSX/ODS)
pra importação de vértices — mesma sistemática de importers/delimitado.py
(devolve DataFrame cru, texto; a correlação de coluna fica na UI)."""
from __future__ import annotations

import io

import pandas as pd

from importers.planilha import ler_planilha, nomes_das_abas


def _bytes_xlsx(dados: dict) -> bytes:
    buffer = io.BytesIO()
    pd.DataFrame(dados).to_excel(buffer, sheet_name="Sheet1", index=False, engine="openpyxl")
    return buffer.getvalue()


def _bytes_ods(dados: dict) -> bytes:
    buffer = io.BytesIO()
    pd.DataFrame(dados).to_excel(buffer, sheet_name="Sheet1", index=False, engine="odf")
    return buffer.getvalue()


def test_ler_xlsx_com_cabecalho():
    conteudo = _bytes_xlsx({"Codigo": ["A", "B"], "E": ["-48,5", "-48,6"]})

    df = ler_planilha(conteudo, ".xlsx", "Sheet1", tem_cabecalho=True)

    assert list(df.columns) == ["Codigo", "E"]
    assert list(df["Codigo"]) == ["A", "B"]


def test_ler_xlsx_sem_cabecalho_usa_coluna_n():
    conteudo = _bytes_xlsx({"col1": ["A"], "col2": ["B"]})

    df = ler_planilha(conteudo, ".xlsx", "Sheet1", tem_cabecalho=False)

    assert list(df.columns) == ["Coluna 1", "Coluna 2"]
    # a própria linha de "cabeçalho" do arquivo (que não é cabeçalho de
    # verdade aqui) vira a primeira linha de dado
    assert list(df["Coluna 1"]) == ["col1", "A"]


def test_ler_ods_com_cabecalho():
    conteudo = _bytes_ods({"Codigo": ["X"], "N": ["-9,5"]})

    df = ler_planilha(conteudo, ".ods", "Sheet1", tem_cabecalho=True)

    assert list(df.columns) == ["Codigo", "N"]
    assert df.at[0, "Codigo"] == "X"


def test_extensao_maiuscula_tambem_funciona():
    conteudo = _bytes_xlsx({"a": ["1"]})

    df = ler_planilha(conteudo, ".XLSX", "Sheet1", tem_cabecalho=True)

    assert list(df.columns) == ["a"]


def test_valor_vazio_vira_string_vazia_nao_nan():
    conteudo = _bytes_xlsx({"a": [1, None], "b": ["x", "y"]})

    df = ler_planilha(conteudo, ".xlsx", "Sheet1", tem_cabecalho=True)

    assert df.at[1, "a"] == ""
    assert all(isinstance(v, str) for v in df["a"])


def test_nomes_das_abas_lista_todas_na_ordem():
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        pd.DataFrame({"a": [1]}).to_excel(writer, sheet_name="Vertices", index=False)
        pd.DataFrame({"b": [2]}).to_excel(writer, sheet_name="Precisoes", index=False)

    abas = nomes_das_abas(buffer.getvalue(), ".xlsx")

    assert abas == ["Vertices", "Precisoes"]


def test_ler_planilha_le_a_aba_escolhida_nao_so_a_primeira():
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        pd.DataFrame({"codigo": ["um"]}).to_excel(writer, sheet_name="Primeira", index=False)
        pd.DataFrame({"codigo": ["dois"]}).to_excel(writer, sheet_name="Segunda", index=False)

    df = ler_planilha(buffer.getvalue(), ".xlsx", "Segunda", tem_cabecalho=True)

    assert df.at[0, "codigo"] == "dois"
