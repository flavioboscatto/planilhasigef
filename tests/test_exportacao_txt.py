"""Testes de core/exportacao_txt.py — pedido explícito do usuário:
"exatamente igual a planilha que é exportada para o SIGEF", tabulação
como separador."""
from __future__ import annotations

from core.exportacao_txt import gerar_txt
from core.models import Perimetro, Vertice

_CASAS = {"segundos_gms_casas_decimais": 3, "sigma_casas_decimais": 2, "h_casas_decimais": 3}


def test_gera_cabecalho_de_colunas_separado_por_tabulacao():
    perimetro = Perimetro(denominacao="Parte 1", vertices=[Vertice(codigo="AJ4-M-001", e_long=-48.0, n_lat=-9.0)])

    saida = gerar_txt([perimetro], _CASAS)

    linhas = saida.splitlines()
    assert linhas[0] == "Parcela 1 — Parte 1"
    assert linhas[1].split("\t")[0] == "Vértice"
    assert "\t" in linhas[2]
    assert linhas[2].split("\t")[0] == "AJ4-M-001"


def test_uma_parcela_sem_vertices_ainda_gera_bloco_com_cabecalho():
    perimetro = Perimetro(vertices=[])

    saida = gerar_txt([perimetro], _CASAS)

    linhas = saida.splitlines()
    assert linhas[0] == "Parcela 1"  # sem denominação, sem travessão sobrando
    assert len(linhas) == 2  # só título + cabeçalho de colunas


def test_multiplas_parcelas_viram_blocos_separados():
    p1 = Perimetro(denominacao="Parte 1", vertices=[Vertice(codigo="A", e_long=-48.0, n_lat=-9.0)])
    p2 = Perimetro(denominacao="Parte 2", vertices=[Vertice(codigo="B", e_long=-47.0, n_lat=-8.0)])

    saida = gerar_txt([p1, p2], _CASAS)

    assert "Parcela 1 — Parte 1" in saida
    assert "Parcela 2 — Parte 2" in saida
    assert saida.index("Parcela 1") < saida.index("Parcela 2")
