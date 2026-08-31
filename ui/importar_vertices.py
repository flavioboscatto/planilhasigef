"""Upload + separador + prévia + correlação de colunas antes de virar uma
versão de importação — e as versões em si, empilhadas, cada uma com botão
pra levar pra planilha definitiva da parcela. Único arquivo que conhece
importers/delimitado.py e core/importacao.py do lado da UI.

Cada arquivo importado vira uma tabela própria (não mexe direto na
planilha definitiva): o profissional pode importar só coordenadas agora e
só precisões depois, revisar cada uma na hora, e decidir quando (e se)
aquilo entra na parcela de verdade. "Renumerar?"/"Tipo" não aparecem
aqui — são só da planilha definitiva (ui/aba_perimetro.py).

Cada versão tem um id próprio, não o índice na lista: removendo uma versão
do meio, as outras não podem "herdar" a chave (e o estado do editor) de
quem foi removida.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from core.geo import utm_para_geodesica
from core.importacao import mesclar_por_codigo
from core.parsing import (
    ValorInvalidoError,
    normaliza_decimal,
    parse_coordenada,
    parse_geodesica_compacta,
    parse_numero,
)
from importers.delimitado import SEPARADORES, ler_arquivo
from ui.grid import render_vertices_grid

# e_long/n_lat saem desta função já em geodésica decimal (ver
# _converte_coordenadas) — o resto do app nunca lida com UTM nem com os
# formatos de texto de campo, só o já convertido.
_CAMPOS_NUMERICOS = {"sigma_long", "sigma_lat", "h", "sigma_h"}

_PARSERS_GEODESICA = {
    "Decimal (grau decimal, ex.: -27,508333)": parse_numero,
    "GMS — símbolos ou espaços (ex.: 27 30 30 S)": parse_coordenada,
    "Compactado GG,MMSS (ex.: -27,3030)": parse_geodesica_compacta,
}

_CAMPOS_VERTICE = {
    "(ignorar)": None,
    "Código do vértice": "codigo",
    "E / Longitude": "e_long",
    "Sigma Long": "sigma_long",
    "N / Latitude": "n_lat",
    "Sigma Lat": "sigma_lat",
    "h (altitude elipsoidal)": "h",
    "Sigma h": "sigma_h",
    "Método de Posicionamento": "metodo_posicionamento",
    "Tipo de Limite": "tipo_limite",
    "CNS": "cns",
    "Matrícula": "matricula",
    "Descritivo": "descritivo",
}


def render_importar_vertices(
    chave_df: str,
    indice: int,
    opcoes_metodo: list[str],
    opcoes_limite: list[str],
) -> None:
    chave_versoes = f"importacoes_{indice}"
    st.session_state.setdefault(chave_versoes, {})
    st.session_state.setdefault(f"importacoes_contador_{indice}", 0)

    with st.expander("Importar vértices de um arquivo (TXT/CSV)"):
        _render_upload(chave_versoes, indice)

    # fora do expander e da função de upload de propósito: um "return"
    # antecipado ali dentro (arquivo não escolhido, mapeamento incompleto
    # etc.) não pode impedir a lista de versões de aparecer — por isso o
    # upload em si vive isolado em _render_upload().
    _render_versoes(chave_versoes, chave_df, indice, opcoes_metodo, opcoes_limite)


def _converte_coordenadas(
    dados_importados: pd.DataFrame, sistema: str, formato_geo: str | None, indice: int
) -> None:
    """Deixa e_long/n_lat prontos em geodésica decimal (vírgula), na
    própria `dados_importados` — UTM convertido via core/geo.py com o
    Meridiano Central/Hemisfério já escolhidos na aba desta parcela;
    geodésica só reinterpreta o texto no formato indicado.
    """
    if sistema == "UTM":
        if not {"e_long", "n_lat"} <= set(dados_importados.columns):
            raise ValueError("importação em UTM precisa das colunas de E/Long e N/Lat juntas")
        meridiano = st.session_state.get(f"perim_meridiano_{indice}")
        hemisferio = st.session_state.get(f"perim_hemisferio_{indice}")
        if meridiano is None or not hemisferio:
            raise ValueError(
                "defina Meridiano Central e Hemisfério da parcela (acima) antes de "
                "importar em UTM"
            )
        longitudes, latitudes = [], []
        for easting_txt, northing_txt in zip(dados_importados["e_long"], dados_importados["n_lat"]):
            longitude, latitude = utm_para_geodesica(
                parse_numero(easting_txt), parse_numero(northing_txt), meridiano, hemisferio
            )
            longitudes.append(longitude)
            latitudes.append(latitude)
        dados_importados["e_long"] = [normaliza_decimal(str(v)) for v in longitudes]
        dados_importados["n_lat"] = [normaliza_decimal(str(v)) for v in latitudes]
        return

    parser = _PARSERS_GEODESICA[formato_geo]
    if "e_long" in dados_importados.columns:
        # Brasil só tem longitude Oeste: força negativo mesmo se o arquivo
        # não trouxer sinal nem sufixo (comum em exportação de campo).
        dados_importados["e_long"] = [
            normaliza_decimal(str(-abs(parser(v)))) for v in dados_importados["e_long"]
        ]
    if "n_lat" in dados_importados.columns:
        dados_importados["n_lat"] = [
            normaliza_decimal(str(parser(v))) for v in dados_importados["n_lat"]
        ]


def _render_upload(chave_versoes: str, indice: int) -> None:
    st.caption(
        "Cada arquivo vira uma versão nova, abaixo — dá pra importar "
        "quantos precisar, um de cada vez (por exemplo, primeiro as "
        "coordenadas, depois só as precisões), conferir cada um e só "
        "então levar pra planilha definitiva da parcela."
    )
    geracao = st.session_state.get(f"import_upload_gen_{indice}", 0)
    arquivo = st.file_uploader(
        "Arquivo", type=["txt", "csv"], key=f"import_arquivo_{indice}_{geracao}"
    )
    if arquivo is None:
        return

    col1, col2 = st.columns(2)
    with col1:
        opcao_sep = st.selectbox(
            "Separador de coluna",
            list(SEPARADORES) + ["Outro"],
            key=f"import_sep_{indice}",
        )
        if opcao_sep == "Outro":
            separador = st.text_input(
                "Digite o separador", key=f"import_sep_custom_{indice}"
            )
        else:
            separador = SEPARADORES[opcao_sep]
    with col2:
        tem_cabecalho = st.checkbox(
            "Arquivo tem linha de cabeçalho", value=True, key=f"import_cab_{indice}"
        )

    if not separador:
        st.info("Informe um separador para continuar.")
        return

    try:
        df_bruto = ler_arquivo(arquivo.getvalue(), separador, tem_cabecalho)
    except Exception as exc:
        st.error(f"Não consegui ler o arquivo com esse separador: {exc}")
        return

    st.caption("Prévia (5 primeiras linhas):")
    st.dataframe(df_bruto.head())

    st.caption("Diga o que cada coluna do arquivo significa:")
    mapeamento: dict[str, str] = {}
    for coluna in df_bruto.columns:
        escolha = st.selectbox(
            str(coluna), list(_CAMPOS_VERTICE), key=f"import_map_{indice}_{coluna}"
        )
        campo = _CAMPOS_VERTICE[escolha]
        if campo:
            mapeamento[coluna] = campo

    if len(set(mapeamento.values())) != len(mapeamento.values()):
        st.error("Duas colunas do arquivo não podem apontar para o mesmo campo.")
        return

    if "codigo" not in mapeamento.values():
        st.warning("Escolha qual coluna é o código do vértice — é a chave da importação.")
        return

    tem_coordenada = {"e_long", "n_lat"} & set(mapeamento.values())
    sistema = "Geodésica"
    formato_geo = None
    if tem_coordenada:
        sistema = st.selectbox(
            "Sistema de coordenadas no arquivo",
            ["Geodésica", "UTM"],
            key=f"import_sistema_{indice}",
        )
        if sistema == "Geodésica":
            formato_geo = st.selectbox(
                "Formato da coordenada geodésica no arquivo",
                list(_PARSERS_GEODESICA),
                key=f"import_formato_geo_{indice}",
                help="Como E/Long e N/Lat estão escritos no arquivo — todas "
                "as linhas precisam estar no mesmo formato.",
            )
        else:
            meridiano = st.session_state.get(f"perim_meridiano_{indice}")
            hemisferio = st.session_state.get(f"perim_hemisferio_{indice}")
            st.warning(
                f"Confira **antes de criar a versão**: Meridiano Central = "
                f"**{meridiano}°** e Hemisfério = **{hemisferio}** (campos no "
                "topo desta aba, acima da grade) — é isso que a conversão "
                "UTM → geodésica vai usar. Zona errada aqui sai sem aviso: "
                "o número parece válido, só que aponta pro lugar errado."
            )

    if st.button("Criar versão a partir deste arquivo", key=f"import_aplicar_{indice}"):
        dados_importados = df_bruto.rename(columns=mapeamento)[list(mapeamento.values())]
        if tem_coordenada:
            try:
                _converte_coordenadas(dados_importados, sistema, formato_geo, indice)
            except (ValorInvalidoError, ValueError) as exc:
                st.error(f"Não consegui interpretar as coordenadas: {exc}")
                return
        # ponto decimal do arquivo vira vírgula (regra do SIGEF é vírgula
        # sempre) antes de guardar a versão — sigma/h só, e_long/n_lat já
        # saíram prontos de _converte_coordenadas
        for campo in dados_importados.columns:
            if campo in _CAMPOS_NUMERICOS:
                dados_importados[campo] = dados_importados[campo].map(normaliza_decimal)
        novo_id = st.session_state[f"importacoes_contador_{indice}"]
        st.session_state[chave_versoes][novo_id] = dados_importados
        st.session_state[f"importacoes_contador_{indice}"] = novo_id + 1
        st.session_state[f"import_upload_gen_{indice}"] = geracao + 1
        st.success(f"Versão criada com {len(dados_importados)} linha(s) — revise abaixo.")
        st.rerun()


def _render_versoes(
    chave_versoes: str,
    chave_df: str,
    indice: int,
    opcoes_metodo: list[str],
    opcoes_limite: list[str],
) -> None:
    versoes: dict[int, pd.DataFrame] = st.session_state.get(chave_versoes, {})
    for posicao, versao_id in enumerate(sorted(versoes), start=1):
        st.markdown(f"**Importação {posicao}**")
        tabela_editada = render_vertices_grid(
            versoes[versao_id],
            opcoes_metodo,
            opcoes_limite,
            key=f"versao_grid_{indice}_{versao_id}",
        )
        st.session_state[chave_versoes][versao_id] = tabela_editada

        col1, col2 = st.columns(2)
        with col1:
            if st.button(
                "Usar esta versão na planilha definitiva",
                key=f"versao_usar_{indice}_{versao_id}",
            ):
                tabela_mesclada, avisos = mesclar_por_codigo(
                    st.session_state[chave_df], tabela_editada
                )
                st.session_state[chave_df] = tabela_mesclada
                for aviso in avisos:
                    st.warning(aviso)
                st.success("Versão levada para a planilha definitiva.")
                st.rerun()
        with col2:
            if st.button("Remover esta versão", key=f"versao_remover_{indice}_{versao_id}"):
                del st.session_state[chave_versoes][versao_id]
                st.rerun()
