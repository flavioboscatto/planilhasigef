"""Testes de core/formatacao_vertices.py — garante que a formatação usada
pela exportação TXT e pelo relatório DOCX bate com a da planilha oficial
(mesmas colunas de config/cell_map.yaml::perimetro.tabela_vertices.colunas,
sem "Tipo", que não tem célula própria no ODS)."""
from __future__ import annotations

from core.formatacao_vertices import COLUNAS_OFICIAIS, ROTULOS_OFICIAIS, linhas_formatadas
from core.models import Perimetro, Vertice


def test_colunas_oficiais_nao_incluem_ajuda_de_tela():
    # Pt.Original, Renum. e Tipo são ajuda de tela (core/tabela_vertices.py)
    # — nenhuma tem célula própria no modelo ODS.
    assert "pt_original" not in COLUNAS_OFICIAIS
    assert "renumerar" not in COLUNAS_OFICIAIS
    assert "tipo_vertice" not in COLUNAS_OFICIAIS
    assert set(COLUNAS_OFICIAIS) == set(ROTULOS_OFICIAIS)


def test_linhas_formatadas_usa_gms_e_casas_da_planilha():
    perimetro = Perimetro(
        vertices=[
            Vertice(codigo="AJ4-M-001", e_long=-48.548333, n_lat=-9.508333, sigma_long=0.01, h=13.23, sigma_h=0.1)
        ]
    )
    casas = {"segundos_gms_casas_decimais": 3, "sigma_casas_decimais": 2, "h_casas_decimais": 3}

    linhas = linhas_formatadas(perimetro, casas)

    assert len(linhas) == 1
    linha = linhas[0]
    assert linha["e_long"].endswith("W")
    assert linha["n_lat"].endswith("S")
    assert linha["sigma_long"] == "0,01"
    assert linha["h"] == "13,230"


def test_linhas_formatadas_so_traz_vertices_ja_filtrados_no_perimetro():
    perimetro = Perimetro(vertices=[])
    casas = {"segundos_gms_casas_decimais": 3, "sigma_casas_decimais": 2, "h_casas_decimais": 3}

    assert linhas_formatadas(perimetro, casas) == []
