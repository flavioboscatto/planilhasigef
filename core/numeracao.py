"""Renumeração de códigos de vértice (ferramenta operacional da aba
Perímetro). Sem streamlit (CLAUDE.md, regra de fronteira de core/).

Cada tipo de vértice (M/P/V, config/dominios.json) tem sequência própria e
contínua entre parcelas: o profissional sabe, da própria vida profissional,
qual o próximo número livre de cada tipo (não há persistência entre
serviços ainda) e digita isso uma vez; a ferramenta só sobrescreve o
`codigo` das linhas marcadas com `renumerar = True` — uma linha
desmarcada pode ser um vértice de outro credenciado que não deve ser
tocado.
"""
from __future__ import annotations

import pandas as pd


def renumerar_parcelas(
    tabelas: list[pd.DataFrame],
    credenciado: str,
    inicio_por_tipo: dict[str, int],
    largura_numero: int = 3,
) -> tuple[list[pd.DataFrame], dict[str, int], list[str], int]:
    """Percorre as tabelas na ordem recebida (parcela_1, parcela_2, ...) e,
    linha a linha, atribui `codigo = CREDENCIADO-TIPO-NNN` às linhas
    marcadas para renumerar, com um contador por tipo que começa em
    `inicio_por_tipo` e só avança quando de fato usado.

    `largura_numero` é o mínimo de dígitos do número (com zero à esquerda,
    ex.: 3 -> "001"); número maior que a largura não é truncado, só deixa
    de precisar do zero — mesmo comportamento de `:03d` do Python, só que
    configurável (ver ui/renumeracao.py).

    Devolve: as tabelas atualizadas (cópias — não altera as originais), o
    próximo número livre de cada tipo depois da operação (pra mostrar ao
    profissional, já que ele digitou o de agora), avisos de linhas marcadas
    que foram puladas por falta de tipo válido, e quantas linhas foram
    realmente renumeradas — 0 sem nenhum aviso é sinal de que nenhuma
    linha estava com "Renumerar?" marcado, não de erro silencioso.
    """
    contadores = dict(inicio_por_tipo)
    avisos: list[str] = []
    atualizadas: list[pd.DataFrame] = []
    total_renumerado = 0

    for indice_parcela, tabela_original in enumerate(tabelas, start=1):
        tabela = tabela_original.copy()
        for posicao in tabela.index:
            if not bool(tabela.at[posicao, "renumerar"]):
                continue
            tipo = str(tabela.at[posicao, "tipo_vertice"]).strip().upper()
            if not tipo:
                avisos.append(
                    f"Parcela {indice_parcela}, linha {posicao + 1}: marcada "
                    "para renumerar mas sem Tipo (M/P/V) selecionado — linha "
                    "ignorada."
                )
                continue
            if tipo not in contadores:
                avisos.append(
                    f"Parcela {indice_parcela}, linha {posicao + 1}: tipo "
                    f"'{tipo}' não está em config/dominios.json — linha "
                    "ignorada."
                )
                continue
            numero = contadores[tipo]
            tabela.at[posicao, "codigo"] = f"{credenciado}-{tipo}-{numero:0{largura_numero}d}"
            contadores[tipo] = numero + 1
            total_renumerado += 1
        atualizadas.append(tabela)

    return atualizadas, contadores, avisos, total_renumerado


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
    Mesma regra de `renumerar_parcelas`: só toca linha marcada com
    "Renumerar?".
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
