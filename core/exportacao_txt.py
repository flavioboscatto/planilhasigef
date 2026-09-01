"""Exportação da Tabela de Perímetro em TXT — pedido explícito do
usuário: "exatamente igual a planilha que é exportada para o SIGEF",
mesmas colunas oficiais e mesma formatação (GMS, casas decimais) de
core/formatacao_vertices.py, separadas por tabulação. Um arquivo só,
com um bloco por parcela (cabeçalho "Parcela N — Denominação" + linha de
título das colunas + uma linha por vértice). Sem streamlit, sem PySide6
(CLAUDE.md, regra de fronteira de core/).
"""
from __future__ import annotations

from core.formatacao_vertices import COLUNAS_OFICIAIS, ROTULOS_OFICIAIS, linhas_formatadas
from core.models import Perimetro


def gerar_txt(perimetros: list[Perimetro], casas: dict) -> str:
    cabecalho_colunas = "\t".join(ROTULOS_OFICIAIS[c] for c in COLUNAS_OFICIAIS)
    blocos = []
    for indice, perimetro in enumerate(perimetros, start=1):
        titulo = f"Parcela {indice}"
        if perimetro.denominacao:
            titulo += f" — {perimetro.denominacao}"
        linhas = [titulo, cabecalho_colunas]
        for linha in linhas_formatadas(perimetro, casas):
            linhas.append("\t".join(linha[c] for c in COLUNAS_OFICIAIS))
        blocos.append("\n".join(linhas))
    return "\n\n".join(blocos) + "\n"
