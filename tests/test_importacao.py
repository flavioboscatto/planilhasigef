"""Testes de core/importacao.py::mesclar_por_codigo — cobre também o
casamento por "Pt.Original", que existe pra sobreviver à renumeração:
depois que "codigo" vira CREDENCIADO-TIPO-NNN, reimportar (recalcular
geodésica de novo, por exemplo) só continua encontrando a linha certa
porque "Pt.Original" nunca muda (core/tabela_vertices.py)."""
from __future__ import annotations

import pandas as pd

from core.importacao import mesclar_por_codigo
from core.tabela_vertices import tabela_vazia


def test_vertice_novo_recebe_pt_original_igual_ao_codigo_importado():
    tabela = tabela_vazia(1)
    importados = pd.DataFrame({"codigo": ["V1"], "e_long": ["-48,00"], "n_lat": ["-9,00"]})

    resultado, avisos = mesclar_por_codigo(tabela, importados)

    assert not avisos
    linha = resultado[resultado["codigo"] == "V1"].iloc[0]
    assert linha["pt_original"] == "V1"


def test_vertice_novo_sem_vaga_livre_tambem_recebe_pt_original():
    tabela = tabela_vazia(1)
    tabela.loc[0, "codigo"] = "JA-OCUPADO"  # sem vaga livre — força criar linha nova
    importados = pd.DataFrame({"codigo": ["V1"], "e_long": ["-48,00"], "n_lat": ["-9,00"]})

    resultado, _ = mesclar_por_codigo(tabela, importados)

    nova = resultado[resultado["codigo"] == "V1"].iloc[0]
    assert nova["pt_original"] == "V1"


def test_reimportar_depois_de_renumerado_casa_por_pt_original_nao_duplica():
    tabela = tabela_vazia(1)
    importados = pd.DataFrame({"codigo": ["V1"], "e_long": ["-48,00"], "n_lat": ["-9,00"]})
    tabela, _ = mesclar_por_codigo(tabela, importados)

    # simula a renumeração: "codigo" muda, "Pt.Original" não (core/numeracao.py)
    tabela.loc[tabela["pt_original"] == "V1", "codigo"] = "AJ4-M-001"

    reimportado = pd.DataFrame({"codigo": ["V1"], "e_long": ["-48,50"], "n_lat": ["-9,50"]})
    resultado, avisos = mesclar_por_codigo(tabela, reimportado)

    assert not avisos
    assert len(resultado) == 1  # não duplicou linha
    linha = resultado.iloc[0]
    assert linha["codigo"] == "AJ4-M-001"  # renumeração preservada
    assert linha["pt_original"] == "V1"  # Pt.Original nunca muda
    assert linha["e_long"] == "-48,50"  # dado novo do arquivo entrou


def test_atualizacao_de_vertice_existente_nao_mexe_no_pt_original():
    tabela = tabela_vazia(1)
    importados = pd.DataFrame({"codigo": ["V1"], "e_long": ["-48,00"], "n_lat": ["-9,00"]})
    tabela, _ = mesclar_por_codigo(tabela, importados)

    atualizacao = pd.DataFrame({"codigo": ["V1"], "sigma_long": ["0,02"]})
    resultado, _ = mesclar_por_codigo(tabela, atualizacao)

    linha = resultado.iloc[0]
    assert linha["pt_original"] == "V1"
    assert linha["sigma_long"] == "0,02"
    assert linha["e_long"] == "-48,00"  # coluna ausente no 2º arquivo não se apaga
