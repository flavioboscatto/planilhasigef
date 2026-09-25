"""Exportação da Tabela de Perímetro em XLSX — mesmas colunas oficiais e
mesma formatação (GMS, casas decimais) de core/formatacao_vertices.py,
compartilhada com core/exportacao_txt.py e core/relatorio_docx.py. Uma aba
por parcela ("Parcela N"), cabeçalho em negrito. Sem streamlit, sem PySide6
(CLAUDE.md, regra de fronteira de core/).

Não confundir com core/ods_writer.py: aquele grava no MODELO OFICIAL do
SIGEF (regras 1-4 do CLAUDE.md); este é um arquivo de conferência à parte,
formato Excel, pro profissional consultar/imprimir fora do SIGEF.
"""
from __future__ import annotations

import io

import pandas as pd
from openpyxl.styles import Font

from core.formatacao_vertices import COLUNAS_OFICIAIS, ROTULOS_OFICIAIS, linhas_formatadas
from core.models import Perimetro


def gerar_xlsx(perimetros: list[Perimetro], casas: dict) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for indice, perimetro in enumerate(perimetros, start=1):
            linhas = linhas_formatadas(perimetro, casas)
            df = pd.DataFrame(linhas, columns=COLUNAS_OFICIAIS).rename(columns=ROTULOS_OFICIAIS)
            aba = f"Parcela {indice}"
            df.to_excel(writer, sheet_name=aba, index=False)
            planilha = writer.sheets[aba]
            for celula in planilha[1]:
                celula.font = Font(bold=True)
            for coluna in planilha.columns:
                letra = coluna[0].column_letter
                maior = max((len(str(c.value)) for c in coluna if c.value is not None), default=8)
                planilha.column_dimensions[letra].width = min(maior + 2, 40)
    return buffer.getvalue()
