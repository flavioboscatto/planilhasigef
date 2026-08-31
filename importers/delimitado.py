"""Leitura de arquivo texto delimitado (TXT/CSV) — Etapa 6, adiantada a
pedido do usuário porque nem toda importação vem num único arquivo (às
vezes só coordenadas, às vezes só precisões).

Sem streamlit: devolve um DataFrame cru, com as colunas como vieram do
arquivo (ou "Coluna N" se não tiver cabeçalho). A correlação dessas
colunas para o schema de vértice é feita na UI (ui/importar_vertices.py),
não aqui — este módulo só sabe ler texto delimitado.
"""
from __future__ import annotations

import io

import pandas as pd

SEPARADORES = {
    "Vírgula (,)": ",",
    "Ponto e vírgula (;)": ";",
    "Tabulação": "\t",
    "Espaço": r"\s+",
    "Barra vertical (|)": "|",
}


def ler_arquivo(conteudo: bytes, separador: str, tem_cabecalho: bool) -> pd.DataFrame:
    texto = conteudo.decode("utf-8-sig", errors="replace")
    df = pd.read_csv(
        io.StringIO(texto),
        sep=separador,
        header=0 if tem_cabecalho else None,
        engine="python",
        dtype=str,
        skip_blank_lines=True,
    )
    if not tem_cabecalho:
        df.columns = [f"Coluna {i + 1}" for i in range(len(df.columns))]
    return df.fillna("").astype(str)
