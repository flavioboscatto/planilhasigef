"""Único arquivo que conhece o componente de grade (CLAUDE.md) — trocar
de componente no futuro mexe só aqui.

st.data_editor, não streamlit-aggrid: colar bloco de células do
Excel/LibreOffice (várias de uma vez) é nativo aqui e só existe na versão
paga (Enterprise) da AG-Grid — decisão tomada depois de confirmar isso na
prática (o console do AG-Grid não avisa, só fica mudo).

Sem realce de erro/alerta por célula ainda: isso depende de
`Ocorrencia(severidade, aba, linha, campo, mensagem)`, que só existe a
partir da Etapa 3 (validadores).
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from core.ods_writer import _fmt_decimal, _fmt_geografica
from core.parsing import ValorInvalidoError, parse_coordenada, parse_numero

_ORDEM_COLUNAS = [
    "renumerar",
    "tipo_vertice",
    "codigo",
    "e_long",
    "sigma_long",
    "n_lat",
    "sigma_lat",
    "h",
    "sigma_h",
    "metodo_posicionamento",
    "tipo_limite",
    "cns",
    "matricula",
    "descritivo",
]


def render_vertices_grid(
    df: pd.DataFrame,
    opcoes_metodo: list[str],
    opcoes_limite: list[str],
    opcoes_tipo_vertice: list[str] | None = None,
    *,
    key: str,
) -> pd.DataFrame:
    # todas as colunas de coordenada/sigma como texto livre (não number):
    # permite digitar/colar GMS com espaço, vírgula decimal etc. A
    # conversão tolerante pra número (core/parsing.py) só acontece depois,
    # ao montar o Vertice.
    #
    # "renumerar"/"tipo_vertice" só entram se o df tiver essas colunas: a
    # numeração de vértice é recurso só da planilha definitiva de cada
    # parcela — as tabelas de versão de importação (ui/importar_vertices.py)
    # não têm essas colunas, então nem aparecem ali.
    # rótulo curto + width="small": st.column_config não aceita largura em
    # pixel nem cabeçalho em duas linhas (só "small"/"medium"/"large" —
    # confirmado na documentação atual do Streamlit), então isto é o único
    # jeito de sobrar mais coluna visível na tela sem mexer no dado.
    config = {
        "codigo": st.column_config.TextColumn("Vértice", width="small"),
        "e_long": st.column_config.TextColumn("E/Long", width="small"),
        "sigma_long": st.column_config.TextColumn("σ long", width="small"),
        "n_lat": st.column_config.TextColumn("N/Lat", width="small"),
        "sigma_lat": st.column_config.TextColumn("σ lat", width="small"),
        "h": st.column_config.TextColumn("h", width="small"),
        "sigma_h": st.column_config.TextColumn("σ h", width="small"),
        "metodo_posicionamento": st.column_config.SelectboxColumn(
            "Método Pos.", options=opcoes_metodo, width="small"
        ),
        "tipo_limite": st.column_config.SelectboxColumn(
            "Tipo Limite", options=opcoes_limite, width="small"
        ),
        "cns": st.column_config.TextColumn("CNS", width="small"),
        "matricula": st.column_config.TextColumn("Matrícula", width="small"),
        "descritivo": st.column_config.TextColumn("Descritivo"),
    }
    if "renumerar" in df.columns:
        config["renumerar"] = st.column_config.CheckboxColumn("Renumerar?", default=True)
    if "tipo_vertice" in df.columns:
        config["tipo_vertice"] = st.column_config.SelectboxColumn(
            "Tipo", options=opcoes_tipo_vertice or []
        )
    ordem = [c for c in _ORDEM_COLUNAS if c in df.columns]
    return st.data_editor(
        df,
        column_config=config,
        column_order=ordem,
        num_rows="dynamic",
        key=key,
    )


# grupos de coluna que levam cada cor no modelo original — ver
# tools/extract_theme.py / config/theme_tokens.json
_COLUNAS_GERAL = [
    "codigo", "e_long", "sigma_long", "n_lat", "sigma_lat", "h", "sigma_h",
    "metodo_posicionamento",
]
_COLUNAS_CONFRONTANTE = ["tipo_limite", "cns", "matricula", "descritivo"]


def _para_gms(texto: str, sufixo_positivo: str, sufixo_negativo: str, casas_segundos: int) -> str:
    """E/Long e N/Lat na grade ficam em grau decimal (editável); a
    planilha final sempre sai em GMS (core/ods_writer._fmt_geografica) —
    sem isto a prévia mostrava decimal, dando a entender que o arquivo
    final também sairia assim, o que não é verdade."""
    if not str(texto).strip():
        return ""
    try:
        valor = parse_coordenada(str(texto))
    except ValorInvalidoError:
        return str(texto)
    return _fmt_geografica(valor, sufixo_positivo, sufixo_negativo, casas_segundos)


def _para_decimal_arredondado(texto: str, casas: int) -> str:
    """Sigma e h na grade ficam com quantas casas o profissional digitou;
    a planilha final sempre arredonda pro nº de casas exigido (2 pro sigma,
    3 pro h — CLAUDE.md) — mesmo motivo do _para_gms: prévia tem que
    mostrar o valor que realmente vai sair no arquivo."""
    if not str(texto).strip():
        return ""
    try:
        valor = parse_numero(str(texto))
    except ValorInvalidoError:
        return str(texto)
    return _fmt_decimal(valor, casas)


def render_vertices_preview(df: pd.DataFrame, tema: dict, casas: dict) -> None:
    """Prévia só-leitura com as cores reais do SIGEF por grupo de coluna,
    e com E/Long, N/Lat, sigmas e h já no formato/arredondamento final.

    st.data_editor (editável, acima) não aceita Styler do pandas — só
    st.dataframe aceita. É por isso que a grade editável fica sem cor e
    esta prévia existe: dá pra ter os dois (colar em bloco na grade E ver
    a cara do modelo), só não simultaneamente no mesmo componente.

    `casas` é `dominios["limites_coordenadas"]` (mesma fonte que
    core/ods_writer.py usa pra gerar o .ods de verdade).
    """
    cor_geral = tema["tabela_entrada_geral"]["fundo"]
    cor_confrontante = tema["tabela_entrada_confrontante"]["fundo"]
    casas_segundos = casas["segundos_gms_casas_decimais"]
    casas_sigma = casas["sigma_casas_decimais"]
    casas_h = casas["h_casas_decimais"]

    df_exibicao = df.copy()
    if "e_long" in df_exibicao.columns:
        df_exibicao["e_long"] = df_exibicao["e_long"].map(
            lambda v: _para_gms(v, "E", "W", casas_segundos)
        )
    if "n_lat" in df_exibicao.columns:
        df_exibicao["n_lat"] = df_exibicao["n_lat"].map(
            lambda v: _para_gms(v, "N", "S", casas_segundos)
        )
    for coluna in ("sigma_long", "sigma_lat", "sigma_h"):
        if coluna in df_exibicao.columns:
            df_exibicao[coluna] = df_exibicao[coluna].map(
                lambda v: _para_decimal_arredondado(v, casas_sigma)
            )
    if "h" in df_exibicao.columns:
        df_exibicao["h"] = df_exibicao["h"].map(
            lambda v: _para_decimal_arredondado(v, casas_h)
        )

    def estiliza(_: pd.DataFrame) -> pd.DataFrame:
        estilos = pd.DataFrame("", index=df_exibicao.index, columns=df_exibicao.columns)
        for coluna in _COLUNAS_GERAL:
            if coluna in estilos.columns:
                estilos[coluna] = f"background-color: {cor_geral}"
        for coluna in _COLUNAS_CONFRONTANTE:
            if coluna in estilos.columns:
                estilos[coluna] = f"background-color: {cor_confrontante}"
        return estilos

    st.markdown("**Sua planilha será exportada assim:**")
    st.caption("Cores do modelo oficial — só leitura, edite na grade acima.")
    st.dataframe(df_exibicao.style.apply(estiliza, axis=None), hide_index=True)
