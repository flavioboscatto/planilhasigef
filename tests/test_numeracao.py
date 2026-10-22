"""Testes de core/numeracao.py: faixa de números por tipo, ordem crescente/
decrescente (só inverte qual linha recebe qual número), linhas sem seleção
intactas (vértices de confrontante) e aviso de código repetido."""
from __future__ import annotations

from core.numeracao import atualizar_tipos_parcelas, renumerar_parcelas
from core.tabela_vertices import tabela_vazia


def _tabela(selecionadas: list[bool], tipos: list[str] | None = None, codigos: list[str] | None = None):
    df = tabela_vazia(len(selecionadas))
    for i, selecionada in enumerate(selecionadas):
        df.at[i, "renumerar"] = selecionada
        df.at[i, "tipo_vertice"] = (tipos[i] if tipos else "M")
        if codigos:
            df.at[i, "codigo"] = codigos[i]
    return df


def test_crescente_a_primeira_linha_recebe_o_menor():
    tabelas, proximos, avisos, total = renumerar_parcelas(
        [_tabela([True, True, True])], "AJQ", {"M": 1}, 3
    )

    assert list(tabelas[0]["codigo"]) == ["AJQ-M-001", "AJQ-M-002", "AJQ-M-003"]
    assert proximos["M"] == 4
    assert avisos == []
    assert total == 3


def test_decrescente_a_primeira_linha_recebe_o_maior_da_mesma_faixa():
    tabelas, proximos, avisos, total = renumerar_parcelas(
        [_tabela([True, True, True])], "AJQ", {"M": 1}, 3, decrescente=True
    )

    # mesma faixa (1 a 3) da ordem crescente, só invertida entre as linhas
    assert list(tabelas[0]["codigo"]) == ["AJQ-M-003", "AJQ-M-002", "AJQ-M-001"]
    assert proximos["M"] == 4
    assert avisos == []
    assert total == 3


def test_decrescente_o_proximo_numero_comeca_a_faixa_nao_o_topo():
    tabelas, proximos, _, _ = renumerar_parcelas(
        [_tabela([True, True, True])], "AJQ", {"M": 8}, 3, decrescente=True
    )

    assert list(tabelas[0]["codigo"]) == ["AJQ-M-010", "AJQ-M-009", "AJQ-M-008"]
    assert proximos["M"] == 11


def test_decrescente_com_oito_vertices_a_partir_do_um_cenario_relatado():
    # relato da turma-teste: 8 linhas selecionadas (9 a 16), Próximo nº = 001,
    # ordem decrescente — esperado 008 ... 001, não "abaixo de 1"
    tabelas, proximos, avisos, total = renumerar_parcelas(
        [_tabela([True] * 8)], "ABCD", {"M": 1}, 3, decrescente=True
    )

    assert list(tabelas[0]["codigo"]) == [f"ABCD-M-{n:03d}" for n in range(8, 0, -1)]
    assert proximos["M"] == 9
    assert avisos == []
    assert total == 8


def test_decrescente_dez_vertices_do_dez_ao_um():
    tabelas, proximos, _, _ = renumerar_parcelas(
        [_tabela([True] * 10)], "AJQ", {"M": 1}, 2, decrescente=True
    )

    assert tabelas[0]["codigo"].iloc[0] == "AJQ-M-10"
    assert tabelas[0]["codigo"].iloc[-1] == "AJQ-M-01"
    assert proximos["M"] == 11


def test_linhas_sem_selecao_nao_sao_tocadas_nem_gastam_numero():
    # linhas 3 e 4 são do confrontante: mantêm o código e não consomem número
    tabela = _tabela(
        [True, True, False, False, True],
        codigos=["", "", "XYZ-M-005", "XYZ-M-004", ""],
    )

    tabelas, _, avisos, total = renumerar_parcelas([tabela], "AJQ", {"M": 6}, 3, decrescente=True)

    assert list(tabelas[0]["codigo"]) == ["AJQ-M-008", "AJQ-M-007", "XYZ-M-005", "XYZ-M-004", "AJQ-M-006"]
    assert avisos == []
    assert total == 3


def test_decrescente_continua_entre_parcelas_na_ordem_das_abas():
    tabelas, proximos, _, total = renumerar_parcelas(
        [_tabela([True, True]), _tabela([True, True])], "AJQ", {"M": 1}, 3, decrescente=True
    )

    # a faixa 1..4 inteira é invertida, da 1ª linha da parcela 1 à última da parcela 2
    assert list(tabelas[0]["codigo"]) == ["AJQ-M-004", "AJQ-M-003"]
    assert list(tabelas[1]["codigo"]) == ["AJQ-M-002", "AJQ-M-001"]
    assert proximos["M"] == 5
    assert total == 4


def test_cada_tipo_tem_sua_propria_faixa_e_ordem():
    tabela = _tabela([True, True, True], tipos=["M", "P", "M"])

    tabelas, proximos, _, _ = renumerar_parcelas([tabela], "AJQ", {"M": 4, "P": 9}, 3, decrescente=True)

    assert list(tabelas[0]["codigo"]) == ["AJQ-M-005", "AJQ-P-009", "AJQ-M-004"]
    assert proximos == {"M": 6, "P": 10}


def test_avisa_quando_codigo_novo_repete_o_de_linha_sem_selecao():
    # um bloco só, passando por cima dos números 5 e 4 que o vizinho (mesmo
    # credenciado) já usa: a faixa 3..6 cobre as linhas 3 e 4 — as duas
    # repetições são avisadas
    tabela = _tabela(
        [True, True, False, False, True, True],
        codigos=["", "", "AJQ-M-005", "AJQ-M-004", "", ""],
    )

    tabelas, _, avisos, _ = renumerar_parcelas([tabela], "AJQ", {"M": 3}, 3, decrescente=True)

    assert list(tabelas[0]["codigo"]) == [
        "AJQ-M-006", "AJQ-M-005", "AJQ-M-005", "AJQ-M-004", "AJQ-M-004", "AJQ-M-003",
    ]
    assert len(avisos) == 2
    assert "linha 2" in avisos[0] and "AJQ-M-005" in avisos[0] and "linha 3" in avisos[0]
    assert "linha 5" in avisos[1] and "AJQ-M-004" in avisos[1] and "linha 4" in avisos[1]


def test_duas_rodadas_um_bloco_de_cada_vez_nao_repetem_codigo():
    # o fluxo recomendado com vértices de vizinho no meio: seleciona só o 1º
    # bloco (início 6, faixa 6..8); depois só o 2º (início 1, faixa 1..3)
    tabela = _tabela(
        [True, True, True, False, False, False, False, False],
        codigos=["", "", "", "AJQ-M-005", "AJQ-M-004", "", "", ""],
    )
    tabelas, _, avisos, _ = renumerar_parcelas([tabela], "AJQ", {"M": 6}, 3, decrescente=True)
    assert avisos == []

    tabela2 = tabelas[0].copy()
    tabela2["renumerar"] = [False, False, False, False, False, True, True, True]
    tabelas2, _, avisos2, _ = renumerar_parcelas([tabela2], "AJQ", {"M": 1}, 3, decrescente=True)

    assert avisos2 == []
    assert list(tabelas2[0]["codigo"]) == [
        "AJQ-M-008", "AJQ-M-007", "AJQ-M-006", "AJQ-M-005", "AJQ-M-004",
        "AJQ-M-003", "AJQ-M-002", "AJQ-M-001",
    ]


def test_sem_repeticao_nao_ha_aviso_de_duplicidade():
    tabela = _tabela([True, False], codigos=["", "XYZ-M-001"])

    _, _, avisos, _ = renumerar_parcelas([tabela], "AJQ", {"M": 1}, 3)

    assert avisos == []


def test_linha_selecionada_sem_tipo_e_ignorada_com_aviso_e_nao_gasta_numero():
    tabela = _tabela([True, True, True], tipos=["M", "", "M"])

    tabelas, proximos, avisos, total = renumerar_parcelas([tabela], "AJQ", {"M": 1}, 3, decrescente=True)

    assert list(tabelas[0]["codigo"]) == ["AJQ-M-002", "", "AJQ-M-001"]
    assert len(avisos) == 1 and "linha 2" in avisos[0]
    assert proximos["M"] == 3
    assert total == 2


def test_atualizar_tipos_continua_so_nas_linhas_selecionadas():
    tabela = _tabela([True, False], tipos=["P", "P"], codigos=["AJQ-M-001", "AJQ-M-002"])

    tabelas, _, total = atualizar_tipos_parcelas([tabela])

    assert list(tabelas[0]["codigo"]) == ["AJQ-P-001", "AJQ-M-002"]
    assert total == 1
