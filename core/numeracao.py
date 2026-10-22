"""Renumeração de códigos de vértice (ferramenta operacional da aba
Perímetro). Sem streamlit (CLAUDE.md, regra de fronteira de core/).

Cada tipo de vértice (M/P/V, config/dominios.json) tem sequência própria e
contínua entre parcelas: o profissional sabe, da própria vida profissional,
qual o próximo número livre de cada tipo (não há persistência entre
serviços ainda) e digita isso uma vez; a ferramenta só sobrescreve o
`codigo` das linhas selecionadas (`renumerar = True`, coluna "Selecionar") —
uma linha sem seleção pode ser um vértice de outro credenciado que não deve
ser tocado.
"""
from __future__ import annotations

import pandas as pd


def renumerar_parcelas(
    tabelas: list[pd.DataFrame],
    credenciado: str,
    inicio_por_tipo: dict[str, int],
    largura_numero: int = 3,
    decrescente: bool = False,
) -> tuple[list[pd.DataFrame], dict[str, int], list[str], int]:
    """Percorre as tabelas na ordem recebida (parcela_1, parcela_2, ...) e
    atribui `codigo = CREDENCIADO-TIPO-NNN` às linhas selecionadas
    ("Selecionar") para renumerar, com uma faixa de números por tipo que
    começa em `inicio_por_tipo` (o MENOR número da faixa) e tem um número por
    linha selecionada daquele tipo.

    A ordem só decide qual linha recebe qual número da faixa:
    `decrescente=False`: a primeira linha selecionada recebe o menor (1, 2,
    3...). `decrescente=True`: a primeira recebe o MAIOR e a última o menor
    (10, 9, 8...) — vértice compartilhado com confrontante já certificado
    aparece na ordem inversa da dele, e a faixa inteira (os mesmos números)
    continua a mesma. Linhas sem seleção (os vértices do confrontante)
    nunca são tocadas nem gastam número.

    `largura_numero` é o mínimo de dígitos do número (com zero à esquerda,
    ex.: 3 -> "001"); número maior que a largura não é truncado, só deixa
    de precisar do zero — mesmo comportamento de `:03d` do Python, só que
    configurável (ver ui/renumeracao.py).

    Devolve: as tabelas atualizadas (cópias — não altera as originais), o
    próximo número livre de cada tipo depois da operação (maior usado +1,
    igual nas duas ordens — pra mostrar ao profissional, já que ele digitou
    o de agora), avisos (linhas selecionadas puladas por falta de tipo
    válido, e código novo igual ao de uma linha sem seleção — o profissional
    escolhe o número inicial e a ferramenta não sabe que o vizinho já usa
    aquele), e quantas linhas foram realmente renumeradas — 0 sem nenhum
    aviso é sinal de que nenhuma linha estava com "Selecionar" selecionado,
    não de erro silencioso.
    """
    avisos: list[str] = []
    linhas_por_tipo: dict[str, list[tuple[int, int]]] = {}

    for indice_parcela, tabela in enumerate(tabelas, start=1):
        for posicao in tabela.index:
            if not bool(tabela.at[posicao, "renumerar"]):
                continue
            tipo = str(tabela.at[posicao, "tipo_vertice"]).strip().upper()
            if not tipo:
                avisos.append(
                    f"Parcela {indice_parcela}, linha {posicao + 1}: selecionada "
                    "para renumerar mas sem Tipo (M/P/V) escolhido — linha "
                    "ignorada."
                )
                continue
            if tipo not in inicio_por_tipo:
                avisos.append(
                    f"Parcela {indice_parcela}, linha {posicao + 1}: tipo "
                    f"'{tipo}' não está em config/dominios.json — linha "
                    "ignorada."
                )
                continue
            linhas_por_tipo.setdefault(tipo, []).append((indice_parcela, posicao))

    atualizadas = [tabela.copy() for tabela in tabelas]
    contadores = dict(inicio_por_tipo)
    renumeradas: set[tuple[int, int]] = set()

    for tipo, linhas in linhas_por_tipo.items():
        inicio = inicio_por_tipo[tipo]
        ultimo = inicio + len(linhas) - 1
        for ordem, (indice_parcela, posicao) in enumerate(linhas):
            numero = ultimo - ordem if decrescente else inicio + ordem
            atualizadas[indice_parcela - 1].at[posicao, "codigo"] = (
                f"{credenciado}-{tipo}-{numero:0{largura_numero}d}"
            )
            renumeradas.add((indice_parcela, posicao))
        contadores[tipo] = ultimo + 1

    avisos.extend(_avisar_codigos_repetidos(atualizadas, renumeradas))
    return atualizadas, contadores, avisos, len(renumeradas)


def _avisar_codigos_repetidos(
    tabelas: list[pd.DataFrame], renumeradas: set[tuple[int, int]]
) -> list[str]:
    """Código recém-atribuído que já existe numa linha NÃO renumerada (ex.:
    vértice do confrontante, ou um bloco meu que ficou de fora desta
    rodada). Só avisa — não bloqueia, e Desfazer volta o estado anterior."""
    fixos: dict[str, tuple[int, int]] = {}
    for indice_parcela, tabela in enumerate(tabelas, start=1):
        for posicao in tabela.index:
            if (indice_parcela, posicao) in renumeradas:
                continue
            codigo = str(tabela.at[posicao, "codigo"]).strip().upper()
            if codigo:
                fixos.setdefault(codigo, (indice_parcela, posicao))

    avisos: list[str] = []
    for indice_parcela, posicao in sorted(renumeradas):
        codigo = str(tabelas[indice_parcela - 1].at[posicao, "codigo"])
        onde = fixos.get(codigo.upper())
        if onde is not None:
            avisos.append(
                f"Parcela {indice_parcela}, linha {posicao + 1}: o código "
                f"'{codigo}' já existe na Parcela {onde[0]}, linha {onde[1] + 1} "
                "(linha sem seleção) — confira o número inicial."
            )
    return avisos


def atualizar_tipos_parcelas(
    tabelas: list[pd.DataFrame],
) -> tuple[list[pd.DataFrame], list[str], int]:
    """Recompõe só o segmento de Tipo do `codigo` (CREDENCIADO-TIPO-NNN)
    pelo valor atual da coluna "Tipo" — credenciado e número sequencial
    continuam vindo do próprio código já existente, sem contador e sem
    precisar do código do credenciado digitado na renumeração.

    Uso: já renumerou, percebeu que o Tipo de um vértice estava errado,
    corrigiu o dropdown — isto sincroniza o código com essa correção sem
    reatribuir número de novo (que é o que `renumerar_parcelas` faria).
    Mesma regra de `renumerar_parcelas`: só toca linha com a caixa
    "Selecionar" selecionada.
    """
    avisos: list[str] = []
    atualizadas: list[pd.DataFrame] = []
    total_atualizado = 0

    for indice_parcela, tabela_original in enumerate(tabelas, start=1):
        tabela = tabela_original.copy()
        for posicao in tabela.index:
            if not bool(tabela.at[posicao, "renumerar"]):
                continue
            codigo_atual = str(tabela.at[posicao, "codigo"]).strip()
            tipo = str(tabela.at[posicao, "tipo_vertice"]).strip().upper()
            if not codigo_atual or not tipo:
                continue
            partes = codigo_atual.split("-")
            if len(partes) != 3:
                avisos.append(
                    f"Parcela {indice_parcela}, linha {posicao + 1}: código "
                    f"'{codigo_atual}' não está no formato CREDENCIADO-TIPO-NUMERO "
                    "— atualize pela renumeração, não dá pra só trocar o Tipo."
                )
                continue
            credenciado, tipo_atual_no_codigo, numero = partes
            if tipo_atual_no_codigo == tipo:
                continue
            tabela.at[posicao, "codigo"] = f"{credenciado}-{tipo}-{numero}"
            total_atualizado += 1
        atualizadas.append(tabela)

    return atualizadas, avisos, total_atualizado
