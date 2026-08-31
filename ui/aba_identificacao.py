"""Formulário da aba Identificação. Sem validação ainda (Etapa 3)."""
from __future__ import annotations

import streamlit as st

from core.models import Identificacao
from ui.tema import titulo_secao


def render_identificacao(dominios: dict, municipios: list[str], tema: dict) -> Identificacao:
    # key= em cada campo (não havia antes): é o que permite ui/projeto.py
    # pré-preencher a aba ao abrir um projeto salvo — sem key não tem como
    # escrever um valor em st.session_state antes do widget nascer.
    #
    # O Streamlit apaga a chave de um widget de session_state assim que ele
    # deixa de ser desenhado numa execução (trocar de aba) — sem resemear a
    # partir do cache "identificacao" (guardado pelo app.py a cada visita
    # desta aba), voltar aqui mostraria tudo em branco e o próximo Salvar
    # sobrescreveria o projeto com os campos vazios.
    cache = st.session_state.get("identificacao")
    if cache is not None:
        for campo in Identificacao.model_fields:
            st.session_state.setdefault(f"ident_{campo}", getattr(cache, campo))

    titulo_secao("Identificação do Serviço de Georreferenciamento", tema["servico_titulo"])
    natureza_servico = st.selectbox(
        "Natureza do serviço", dominios["natureza_servico"], key="ident_natureza_servico"
    )

    titulo_secao("Identificação do Detentor", tema["detentor_titulo"])
    col1, col2 = st.columns(2)
    with col1:
        tipo_pessoa = st.selectbox("Tipo pessoa", dominios["tipo_pessoa"], key="ident_tipo_pessoa")
    with col2:
        cpf_cnpj = st.text_input("CPF/CNPJ", key="ident_cpf_cnpj")
    nome = st.text_input("Nome", key="ident_nome")

    titulo_secao("Identificação da Área", tema["area_titulo"])
    col1, col2 = st.columns(2)
    with col1:
        denominacao_area = st.text_input("Denominação", key="ident_denominacao_area")
    with col2:
        situacao = st.selectbox("Situação", dominios["situacao"], key="ident_situacao")

    col1, col2 = st.columns(2)
    with col1:
        natureza_area = st.selectbox(
            "Natureza da área", dominios["natureza_area"], key="ident_natureza_area"
        )
    with col2:
        codigo_imovel_sncr = st.text_input(
            "Código do Imóvel (SNCR/INCRA)", key="ident_codigo_imovel_sncr"
        )

    col1, col2 = st.columns(2)
    with col1:
        codigo_cartorio_cns = st.text_input(
            "Código do cartório (CNS)", key="ident_codigo_cartorio_cns"
        )
    with col2:
        matricula = st.text_input("Matrícula", key="ident_matricula")

    col1, col2 = st.columns(2)
    with col1:
        municipio_1 = st.selectbox("Município 1", [""] + municipios, key="ident_municipio_1")
    with col2:
        # segunda linha de município do modelo — leitura ainda não
        # confirmada no LibreOffice, ver nota em config/cell_map.yaml
        municipio_2 = st.selectbox(
            "Município 2 (opcional)", [""] + municipios, key="ident_municipio_2"
        )

    return Identificacao(
        natureza_servico=natureza_servico,
        tipo_pessoa=tipo_pessoa,
        nome=nome,
        cpf_cnpj=cpf_cnpj,
        denominacao_area=denominacao_area,
        situacao=situacao,
        natureza_area=natureza_area,
        codigo_imovel_sncr=codigo_imovel_sncr,
        codigo_cartorio_cns=codigo_cartorio_cns,
        matricula=matricula,
        municipio_1=municipio_1,
        municipio_2=municipio_2,
    )
