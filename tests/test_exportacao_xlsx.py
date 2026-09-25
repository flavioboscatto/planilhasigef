"""Testes de core/exportacao_xlsx.py — mesmas colunas oficiais de
core/exportacao_txt.py, só que em Excel: uma aba por parcela, cabeçalho em
negrito."""
from __future__ import annotations

import io

import pandas as pd

from core.exportacao_xlsx import gerar_xlsx
from core.models import Perimetro, Vertice

_CASAS = {"segundos_gms_casas_decimais": 3, "sigma_casas_decimais": 2, "h_casas_decimais": 3}


def test_gera_uma_aba_por_parcela_com_cabecalho_oficial():
    p1 = Perimetro(denominacao="Parte 1", vertices=[Vertice(codigo="AJ4-M-001", e_long=-48.0, n_lat=-9.0)])
    p2 = Perimetro(denominacao="Parte 2", vertices=[Vertice(codigo="AJ4-M-002", e_long=-47.0, n_lat=-8.0)])

    saida = gerar_xlsx([p1, p2], _CASAS)

    livro = pd.ExcelFile(io.BytesIO(saida), engine="openpyxl")
    assert livro.sheet_names == ["Parcela 1", "Parcela 2"]

    df1 = livro.parse("Parcela 1")
    assert list(df1.columns)[0] == "Vértice"
    assert df1.at[0, "Vértice"] == "AJ4-M-001"

    df2 = livro.parse("Parcela 2")
    assert df2.at[0, "Vértice"] == "AJ4-M-002"


def test_cabecalho_fica_em_negrito():
    from openpyxl import load_workbook

    perimetro = Perimetro(vertices=[Vertice(codigo="A", e_long=-48.0, n_lat=-9.0)])

    saida = gerar_xlsx([perimetro], _CASAS)

    planilha = load_workbook(io.BytesIO(saida))["Parcela 1"]
    assert all(celula.font.bold for celula in planilha[1])
    assert not planilha[2][0].font.bold


def test_uma_parcela_sem_vertices_ainda_gera_aba_so_com_cabecalho():
    perimetro = Perimetro(vertices=[])

    saida = gerar_xlsx([perimetro], _CASAS)

    df = pd.ExcelFile(io.BytesIO(saida), engine="openpyxl").parse("Parcela 1")
    assert len(df) == 0
    assert list(df.columns)[0] == "Vértice"
