"""Aplica as cores do modelo oficial (config/theme_tokens.json) na
interface. Só isso — nenhuma regra de negócio aqui.

Limitação real, não escondida: só dá pra colorir elementos que o Streamlit
renderiza como HTML de verdade (títulos de seção, aqui). O `st.data_editor`
desenha a grade num canvas — não tem seletor CSS que alcance dentro dele.
O cabeçalho da grade pega cor pelo tema global (`.streamlit/config.toml`),
não célula a célula como na planilha original; a coluna Tipo
Limite/CNS/Matrícula/Descritivo não sai com a cor azul diferente do resto
como no modelo — isso ficaria fora do alcance do Streamlit sem trocar de
componente de novo.
"""
from __future__ import annotations

import html

import streamlit as st


def titulo_secao(texto: str, papel: dict) -> None:
    """Banner colorido igual ao título de seção da planilha original
    (mesma cor de fundo/texto/negrito do estilo de célula real)."""
    peso = "bold" if papel.get("negrito") else "normal"
    cor_texto = papel.get("texto") or "#ffffff"
    st.markdown(
        f'<div style="background-color:{papel["fundo"]}; color:{cor_texto}; '
        f'font-weight:{peso}; padding:0.5rem 0.75rem; border-radius:0.25rem; '
        f'font-size:1.15rem; margin:0.75rem 0 0.5rem 0;">{html.escape(texto)}</div>',
        unsafe_allow_html=True,
    )
