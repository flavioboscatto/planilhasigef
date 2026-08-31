"""Formulário + grade de UMA aba Perímetro (uma parcela). Sem validação
ainda (Etapa 3, exceto a reorganização por geometria).

`indice` distingue os widgets de cada parcela no session_state do
Streamlit — sem isso, "Denominação" da Parcela 1 e da Parcela 2 dividiriam
a mesma chave e um sobrescreveria o outro ao trocar de parcela.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from core.models import Perimetro, Vertice
from core.parsing import ValorInvalidoError, normaliza_decimal, parse_coordenada, parse_numero
from core.validators.geometria import reordena_norte_horario
from ui.grid import render_vertices_grid, render_vertices_preview
from ui.importar_vertices import render_importar_vertices
from ui.tema import titulo_secao

_COLUNAS_VERTICE = [
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


_LINHAS_INICIAIS = 3  # mínimo pra fechar um polígono; dá pra adicionar/remover na própria grade

_COLUNAS_NUMERICAS = ["e_long", "sigma_long", "n_lat", "sigma_lat", "h", "sigma_h"]


def _tabela_vazia(n_linhas: int = _LINHAS_INICIAIS) -> pd.DataFrame:
    # "renumerar" nasce marcado: uma parcela nova é presumidamente toda do
    # profissional que está preenchendo agora. Vértice importado de
    # arquivo nasce desmarcado (ver core/importacao.py) — pode ser de
    # outro credenciado.
    linha_padrao = {c: "" for c in _COLUNAS_VERTICE}
    linha_padrao["renumerar"] = True
    return pd.DataFrame([dict(linha_padrao) for _ in range(n_linhas)])


def _normaliza_tabela(df: pd.DataFrame) -> pd.DataFrame:
    """Ponto vira vírgula assim que a grade é editada — regra do SIGEF é
    vírgula sempre, não só no .ods final."""
    df = df.copy()
    for coluna in _COLUNAS_NUMERICAS:
        df[coluna] = df[coluna].map(normaliza_decimal)
    return df


def _preenchido(valor) -> bool:
    """False pra None/NaN/"" — uma linha nova em branco (botão + da grade)
    chega como NaN, não string vazia; str(nan) daria 'nan', que não é
    vazio pro Python."""
    if valor is None:
        return False
    texto = str(valor).strip()
    return bool(texto) and texto.lower() != "nan"


def _txt(valor) -> str:
    return str(valor).strip() if _preenchido(valor) else ""


def _linha_para_vertice(linha: pd.Series) -> Vertice:
    def num(campo: str) -> float:
        try:
            return parse_numero(_txt(linha[campo]))
        except ValorInvalidoError:
            return 0.0

    def coord(campo: str) -> float:
        try:
            return parse_coordenada(_txt(linha[campo]))
        except ValorInvalidoError:
            return 0.0

    return Vertice(
        codigo=_txt(linha["codigo"]),
        tipo_vertice=_txt(linha["tipo_vertice"]),
        e_long=coord("e_long"),
        sigma_long=num("sigma_long"),
        n_lat=coord("n_lat"),
        sigma_lat=num("sigma_lat"),
        h=num("h"),
        sigma_h=num("sigma_h"),
        metodo_posicionamento=_txt(linha["metodo_posicionamento"]),
        tipo_limite=_txt(linha["tipo_limite"]),
        cns=_txt(linha["cns"]),
        matricula=_txt(linha["matricula"]),
        descritivo=_txt(linha["descritivo"]),
    )


def _vertice_para_linha(v: Vertice) -> dict:
    return {
        "codigo": v.codigo,
        "tipo_vertice": v.tipo_vertice,
        "e_long": v.e_long,
        "sigma_long": v.sigma_long,
        "n_lat": v.n_lat,
        "sigma_lat": v.sigma_lat,
        "h": v.h,
        "sigma_h": v.sigma_h,
        "metodo_posicionamento": v.metodo_posicionamento,
        "tipo_limite": v.tipo_limite,
        "cns": v.cns,
        "matricula": v.matricula,
        "descritivo": v.descritivo,
    }


def render_perimetro(dominios: dict, indice: int, tema: dict) -> Perimetro:
    titulo_secao(f"Tabela de Perímetro — Parcela {indice}", tema["perimetro_titulo"])

    # O Streamlit apaga a chave de um widget de session_state assim que ele
    # deixa de ser desenhado numa execução (trocar de aba) — sem resemear a
    # partir do cache perimetro_N (guardado pelo app.py a cada visita desta
    # aba), voltar aqui resetaria os campos pro padrão de parcela nova e o
    # próximo Salvar sobrescreveria o projeto com esses valores errados
    # (mesmo problema de ui/aba_identificacao.py). Passar value=/index= aqui
    # WHEN a chave já existe geraria o aviso do Streamlit de "index/value
    # em conflito com Session State" — por isso o padrão entra só via
    # setdefault, nunca no parâmetro do widget.
    cache = st.session_state.get(f"perimetro_{indice}")
    st.session_state.setdefault(
        f"perim_denominacao_{indice}", cache.denominacao if cache else f"Parte {indice}"
    )
    st.session_state.setdefault(
        f"perim_numero_{indice}", cache.parcela_numero if cache else f"{indice:03d}"
    )
    # int(...): Perimetro.meridiano_central é float (core/models.py), mas a
    # lista de opções do dropdown (meridianos_centrais_brasil, dominios.json)
    # é de inteiros — sem essa conversão, o valor guardado (-51.0) não bate
    # com nenhuma opção (-51) e o Streamlit cai pra primeira da lista sem
    # avisar. Foi isto que fazia o Meridiano parecer "trocar sozinho".
    st.session_state.setdefault(
        f"perim_meridiano_{indice}",
        int(cache.meridiano_central) if cache and cache.meridiano_central is not None else -51,
    )
    st.session_state.setdefault(
        f"perim_hemisferio_{indice}", cache.hemisferio if cache else "Sul"
    )
    if cache is not None:
        st.session_state.setdefault(f"perim_lado_{indice}", cache.lado)
        st.session_state.setdefault(f"perim_tipocoord_{indice}", cache.tipo_coordenada)

    col1, col2, col3 = st.columns(3)
    with col1:
        denominacao = st.text_input("Denominação", key=f"perim_denominacao_{indice}")
        parcela_numero = st.text_input("Parcela número", key=f"perim_numero_{indice}")
    with col2:
        lado = st.selectbox("Lado", dominios["lado"], key=f"perim_lado_{indice}")
        tipo_coordenada = st.selectbox(
            "Tipo de Coordenada", dominios["tipo_coordenada"], key=f"perim_tipocoord_{indice}"
        )
    with col3:
        meridianos = dominios["meridianos_centrais_brasil"]
        meridiano_central = st.selectbox(
            "Meridiano Central (°)", meridianos, key=f"perim_meridiano_{indice}"
        )
        hemisferios = dominios["hemisferio"]
        hemisferio = st.selectbox("Hemisfério", hemisferios, key=f"perim_hemisferio_{indice}")

    st.caption(
        "Use o + no fim da grade para adicionar vértice — sem limite fixo: "
        "além dos 9 pré-formatados, o gravador insere linha na planilha "
        "final conforme precisar (confira sempre no LibreOffice com F3 "
        "antes de certificar, é o único jeito de saber se a Extensão SIGEF "
        "leu direito). Linhas com código vazio são ignoradas ao gerar o "
        "arquivo. E/Long e N/Lat aceitam grau decimal (-48,548) ou GMS "
        "(48 32 52,8 W). Dá pra colar um bloco de células copiado do "
        "Excel/LibreOffice direto na grade."
    )

    chave_df = f"vertices_df_{indice}"
    if chave_df not in st.session_state:
        st.session_state[chave_df] = _tabela_vazia()

    # troca de código externo na tabela (reorganizar, marcar/desmarcar
    # todos, preencher em lote) sem passar pela própria grade: o
    # st.data_editor guarda um histórico de edição por "key" e reaplica
    # esse histórico por cima do novo valor a cada rerun, então uma
    # atualização em massa feita por fora pode ser ignorada/misturada com
    # edição antiga. Trocar a "geração" força a grade a nascer do zero
    # (sem histórico), então a atualização em massa vale de verdade.
    chave_geracao = f"grade_geracao_{indice}"
    geracao = st.session_state.get(chave_geracao, 0)

    opcoes_metodo = [m["codigo"] for m in dominios["metodos_posicionamento"]]
    opcoes_limite = [t["codigo"] for t in dominios["tipos_limite"]]
    opcoes_tipo_vertice = [t["codigo"] for t in dominios["tipos_vertice"]]

    render_importar_vertices(chave_df, indice, opcoes_metodo, opcoes_limite)

    col_reorganiza, col_marcar, col_desmarcar = st.columns(3)
    with col_reorganiza:
        if st.button(
            "↻ Reorganizar (mais ao norte, sentido horário)",
            key=f"perim_reorganiza_{indice}",
            use_container_width=True,
        ):
            linhas_preenchidas = [
                (linha, _linha_para_vertice(linha))
                for _, linha in st.session_state[chave_df].iterrows()
                if _preenchido(linha["codigo"])
            ]
            if len(linhas_preenchidas) >= 3:
                vertices_atuais = [v for _, v in linhas_preenchidas]
                # reordena_norte_horario só reordena/inverte a lista (não cria
                # Vertice novo), então id(v) ainda identifica a linha original —
                # é assim que "renumerar" (que não existe em Vertice, só na
                # grade) acompanha o vértice até a nova posição.
                renumerar_por_id = {
                    id(v): bool(linha["renumerar"]) for linha, v in linhas_preenchidas
                }
                reordenados = reordena_norte_horario(vertices_atuais)
                novas_linhas = []
                for v in reordenados:
                    nova_linha = _vertice_para_linha(v)
                    nova_linha["renumerar"] = renumerar_por_id[id(v)]
                    novas_linhas.append(nova_linha)
                st.session_state[chave_df] = _normaliza_tabela(pd.DataFrame(novas_linhas))
                st.session_state[chave_geracao] = geracao + 1
                st.rerun()
            else:
                st.warning("Precisa de pelo menos 3 vértices com código preenchido para reorganizar.")
    with col_marcar:
        if st.button("☑ Marcar todos p/ renumerar", key=f"perim_marcar_todos_{indice}", use_container_width=True):
            st.session_state[chave_df]["renumerar"] = True
            st.session_state[chave_geracao] = geracao + 1
            st.rerun()
    with col_desmarcar:
        if st.button("☐ Desmarcar todos", key=f"perim_desmarcar_todos_{indice}", use_container_width=True):
            st.session_state[chave_df]["renumerar"] = False
            st.session_state[chave_geracao] = geracao + 1
            st.rerun()

    with st.expander("Preencher uma coluna em todas as linhas de uma vez"):
        st.caption(
            "Alternativa a selecionar célula por célula na grade (dropdown "
            "de várias linhas pode ser lento) — aplica o mesmo valor em "
            "TODAS as linhas da tabela de uma vez, inclusive as vazias."
        )
        campos_lote = {
            "Tipo": ("tipo_vertice", opcoes_tipo_vertice),
            "Método de Posicionamento": ("metodo_posicionamento", opcoes_metodo),
            "Tipo de Limite": ("tipo_limite", opcoes_limite),
        }
        col_campo, col_valor, col_botao = st.columns([2, 2, 1])
        with col_campo:
            escolha_campo = st.selectbox(
                "Coluna", list(campos_lote), key=f"lote_coluna_{indice}"
            )
        campo_lote, opcoes_lote = campos_lote[escolha_campo]
        with col_valor:
            valor_lote = st.selectbox("Valor", opcoes_lote, key=f"lote_valor_{indice}_{escolha_campo}")
        with col_botao:
            st.write("")
            if st.button("Aplicar a todas", key=f"lote_aplicar_{indice}", use_container_width=True):
                st.session_state[chave_df][campo_lote] = valor_lote
                st.session_state[chave_geracao] = geracao + 1
                st.rerun()

    df_editado = _normaliza_tabela(
        render_vertices_grid(
            st.session_state[chave_df],
            opcoes_metodo,
            opcoes_limite,
            opcoes_tipo_vertice,
            key=f"grid_vertices_{indice}_{geracao}",
        )
    )
    # só reatribui se algo mudou de verdade: reatribuir sempre — mesmo
    # quando o rerun foi disparado por outro widget da página, sem
    # nenhuma edição real na grade — troca a identidade do DataFrame a
    # cada volta, e é isso que parece contribuir pro grid perder
    # seleção de dropdown/posição de rolagem com mais frequência.
    if not df_editado.equals(st.session_state[chave_df]):
        st.session_state[chave_df] = df_editado
    render_vertices_preview(df_editado, tema, dominios["limites_coordenadas"])

    vertices = [
        _linha_para_vertice(linha)
        for _, linha in df_editado.iterrows()
        if _preenchido(linha["codigo"])
    ]

    return Perimetro(
        denominacao=denominacao,
        parcela_numero=parcela_numero,
        lado=lado,
        tipo_coordenada=tipo_coordenada,
        meridiano_central=meridiano_central,
        hemisferio=hemisferio,
        vertices=vertices,
    )
