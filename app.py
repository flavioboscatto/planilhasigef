"""Entrypoint Streamlit do gerador de planilha SIGEF.

Protótipo desta rodada: N parcelas (perimetro_1..N, clonadas no gravador),
sem validação ainda. Ver PLANO_SIGEF_WEB.md para o que falta.

Página única (Identificação + todas as parcelas em rolagem contínua), sem
abas: já tivemos abas (primeiro st.tabs, depois st.segmented_control), mas
o Streamlit apaga a chave de session_state de um widget assim que ele
deixa de ser desenhado numa execução — trocar de aba apagava Denominação,
Meridiano, Identificação etc., exigindo reforço com cache pra não perder
dado. Com tudo desenhado sempre, essa classe de bug não existe mais: cada
seção só precisa ficar em dia consigo mesma. (A razão original de evitar
st.tabs — o AgGrid, escondido por CSS, media largura zero — também não se
aplica mais: trocamos AgGrid por st.data_editor faz tempo.)
"""
from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from core import ods_writer
from core.template_loader import load_template
from ui.aba_identificacao import render_identificacao
from ui.aba_perimetro import _tabela_vazia, render_perimetro
from ui.projeto import render_barra_lateral, render_gate
from ui.renumeracao import render_renumeracao

CONFIG_DIR = Path(__file__).resolve().parent / "config"


@st.cache_data
def _carregar_json(nome_arquivo: str):
    with (CONFIG_DIR / nome_arquivo).open("r", encoding="utf-8") as f:
        return json.load(f)


st.set_page_config(
    page_title="Gerador de Planilha SIGEF",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Streamlit não tem opção nativa de largura padrão da barra lateral (só o
# usuário arrastando); [data-testid="stSidebar"] já nasce com width:300px
# em style inline, então só um !important em CSS injetado sobrepõe. A
# barra lateral só tem o painel de numeração — 230px sobra espaço de
# verdade pra grade das parcelas sem cortar os campos.
st.markdown(
    '<style>[data-testid="stSidebar"] { width: 230px !important; }</style>',
    unsafe_allow_html=True,
)

st.title("Gerador de Planilha SIGEF")

dominios = _carregar_json("dominios.json")
municipios = _carregar_json("municipios.json")
tema = _carregar_json("theme_tokens.json")

if not render_gate():
    st.stop()

st.session_state.setdefault("num_parcelas", 1)

# a tabela de vértices de cada parcela precisa existir mesmo antes de a
# seção correspondente desenhar seus próprios widgets nesta execução: a
# renumeração (barra lateral, abaixo) é contínua entre parcelas e olha pra
# todas de uma vez
for _indice_parcela in range(1, st.session_state["num_parcelas"] + 1):
    st.session_state.setdefault(f"vertices_df_{_indice_parcela}", _tabela_vazia())

with st.sidebar:
    render_barra_lateral(dominios)
    render_renumeracao(dominios, st.session_state["num_parcelas"])

col_add, col_remove = st.columns(2)
with col_add:
    if st.button("+ Adicionar parcela", use_container_width=True):
        st.session_state["num_parcelas"] += 1
        st.rerun()
with col_remove:
    if st.session_state["num_parcelas"] > 1 and st.button(
        "- Remover última parcela", use_container_width=True
    ):
        ultima = st.session_state["num_parcelas"]
        st.session_state.pop(f"perimetro_{ultima}", None)
        st.session_state.pop(f"vertices_df_{ultima}", None)
        st.session_state["num_parcelas"] -= 1
        st.rerun()

st.divider()
identificacao = render_identificacao(dominios, municipios, tema)
st.session_state["identificacao"] = identificacao

perimetros = []
for _indice_parcela in range(1, st.session_state["num_parcelas"] + 1):
    st.divider()
    perimetro = render_perimetro(dominios, _indice_parcela, tema)
    st.session_state[f"perimetro_{_indice_parcela}"] = perimetro
    perimetros.append(perimetro)

st.divider()

if st.button("Gerar planilha SIGEF (.ods)", type="primary"):
    template_bytes = load_template()
    saida = ods_writer.write(identificacao, perimetros, template_bytes)
    st.success(f"Planilha gerada ({len(saida)} bytes). Confira no LibreOffice com F3.")
    st.download_button(
        "Baixar .ods",
        data=saida,
        file_name="sigef_gerado.ods",
        mime="application/vnd.oasis.opendocument.spreadsheet",
    )
