"""Leitura de planilha (XLS/XLSX/ODS) para importação de vértices — mesma
sistemática de importers/delimitado.py: devolve um DataFrame cru, com as
colunas como vieram do arquivo (ou "Coluna N" se não tiver cabeçalho). A
correlação dessas colunas para o schema de vértice continua na UI
(ui_qt/importar_vertices_dialog.py), não aqui.

Cada extensão precisa de uma lib de leitura própria via pandas (motor
escolhido explicitamente porque a leitura parte de bytes em memória, não de
um caminho de arquivo — sem extensão no nome pra pandas inferir sozinho):
openpyxl (.xlsx), xlrd (.xls, formato antigo do Excel 97-2003) e odfpy
(.ods — nome do pacote instalável é "odfpy", mas o motor do pandas chama-se
"odf"). Só leitura de arquivo do usuário: não conflita com a regra 2 do
CLAUDE.md (nunca usar odfpy/pandas pra ESCREVER o .ods oficial do SIGEF).
"""
from __future__ import annotations

import io

import pandas as pd

_ENGINE_POR_EXTENSAO = {".xls": "xlrd", ".xlsx": "openpyxl", ".ods": "odf"}


def nomes_das_abas(conteudo: bytes, extensao: str) -> list[str]:
    engine = _ENGINE_POR_EXTENSAO[extensao.lower()]
    with pd.ExcelFile(io.BytesIO(conteudo), engine=engine) as arquivo:
        return list(arquivo.sheet_names)


def ler_planilha(conteudo: bytes, extensao: str, aba: str, tem_cabecalho: bool) -> pd.DataFrame:
    engine = _ENGINE_POR_EXTENSAO[extensao.lower()]
    df = pd.read_excel(
        io.BytesIO(conteudo),
        sheet_name=aba,
        engine=engine,
        header=0 if tem_cabecalho else None,
        dtype=str,
    )
    if not tem_cabecalho:
        df.columns = [f"Coluna {i + 1}" for i in range(len(df.columns))]
    return df.fillna("").astype(str)
