"""Painel de numeração de vértices: código do credenciado + próximo número
livre de cada tipo (M/P/V) + botão que renumera as linhas marcadas em
TODAS as parcelas, na ordem parcela_1..N — a numeração corre entre
parcelas (mesmo levantamento de campo), não reinicia por aba, então o
painel fica fora de qualquer aba específica (barra lateral), sempre
visível, em vez de dentro de `ui/aba_perimetro.py`.
"""
from __future__ import annotations

import streamlit as st

from core.numeracao import atualizar_tipos_parcelas, renumerar_parcelas
from ui.aba_perimetro import _linha_para_vertice, _preenchido

# do sem zero (1, 2, 3...) até 5 dígitos (00001) — a largura é o
# comprimento do próprio rótulo, então "001" já significa 3.
_FORMATOS_NUMERO = ["1", "01", "001", "0001", "00001"]


def _largura_selecionada() -> int:
    return len(st.session_state.get("numeracao_formato", "001"))


def _numero_de(chave: str) -> int:
    """Lê um campo de número-com-zero-à-esquerda de forma tolerante: texto
    vazio ou não numérico vira 1, nunca menos que 1."""
    bruto = st.session_state[chave].strip()
    try:
        return max(1, int(bruto))
    except ValueError:
        return 1


def _normaliza_numero(chave: str) -> None:
    """on_change do campo de número: reformata no formato escolhido
    (001, 0001...) assim que o profissional sai do campo — é só
    cosmético, o parsing pra número de verdade é tolerante (_numero_de)
    mesmo se isto não rodar."""
    st.session_state[chave] = f"{_numero_de(chave):0{_largura_selecionada()}d}"


def _reformata_campos_numero(tipos: list[dict]) -> None:
    """on_change do dropdown de formato: reaplica a largura nova em cima
    dos números já digitados. Callback roda antes de qualquer text_input
    ser instanciado nesta execução, então mexer neles aqui não esbarra na
    trava do Streamlit (não dá pra reatribuir st.session_state de um
    widget já instanciado na mesma execução)."""
    largura = _largura_selecionada()
    for tipo in tipos:
        chave = f"renum_inicio_{tipo['codigo']}"
        if chave in st.session_state:
            st.session_state[chave] = f"{_numero_de(chave):0{largura}d}"


def _aplicar_tabelas_atualizadas(tabelas: list, num_parcelas: int) -> None:
    """Escreve as tabelas de volta em session_state depois de renumerar ou
    atualizar tipo, e refaz o `perimetro_i` em cache (usado ao gerar o
    .ods) — sem isso, uma parcela que não é a aba aberta no momento
    gravaria o `codigo` antigo no arquivo final. Também troca a "geração"
    da grade daquela parcela: mudar `vertices_df_i` por fora do
    st.data_editor pode ficar misturado com edição antiga que o widget
    ainda lembra (mesmo motivo do botão Reorganizar/Marcar todos em
    ui/aba_perimetro.py)."""
    for i, tabela in enumerate(tabelas, start=1):
        st.session_state[f"vertices_df_{i}"] = tabela
        st.session_state[f"grade_geracao_{i}"] = st.session_state.get(f"grade_geracao_{i}", 0) + 1
        perimetro_existente = st.session_state.get(f"perimetro_{i}")
        if perimetro_existente is not None:
            vertices = [
                _linha_para_vertice(linha)
                for _, linha in tabela.iterrows()
                if _preenchido(linha["codigo"])
            ]
            st.session_state[f"perimetro_{i}"] = perimetro_existente.model_copy(
                update={"vertices": vertices}
            )


def render_renumeracao(dominios: dict, num_parcelas: int) -> None:
    tipos = dominios["tipos_vertice"]

    # Streamlit não deixa reatribuir st.session_state[key] de um widget já
    # instanciado nesta mesma execução — por isso o autoavanço do "próximo
    # número" (depois de renumerar) fica pendente num rerun: aqui, ANTES de
    # criar os text_input de baixo, aplicamos o que ficou pendente da
    # rodada anterior.
    pendente = st.session_state.pop("numeracao_proximos_pendente", None)
    if pendente:
        largura = _largura_selecionada()
        for codigo_tipo, valor in pendente.items():
            st.session_state[f"renum_inicio_{codigo_tipo}"] = f"{valor:0{largura}d}"

    # st.success/st.warning chamado logo antes de st.rerun() nunca dá tempo
    # de aparecer pro profissional (o rerun troca a tela na sequência) —
    # por isso o resultado do botão fica pendente igual ao bloco acima, e é
    # exibido aqui, na entrada seguinte, antes de qualquer widget novo.
    resultado = st.session_state.pop("renum_resultado_pendente", None)
    if resultado:
        for aviso in resultado["avisos"]:
            st.warning(aviso)
        if resultado["total"] > 0:
            st.success(
                f"{resultado['total']} vértice(s) renumerado(s). O próximo "
                "número de cada tipo já foi atualizado abaixo."
            )
        else:
            st.warning(
                "Nenhum vértice foi renumerado — confira se a caixa "
                "\"Renumerar?\" está marcada e se a coluna \"Tipo\" (M/P/V) "
                "está preenchida nas linhas que você queria mudar."
            )

    resultado_atualizar = st.session_state.pop("atualizar_resultado_pendente", None)
    if resultado_atualizar:
        for aviso in resultado_atualizar["avisos"]:
            st.warning(aviso)
        if resultado_atualizar["total"] > 0:
            st.success(f"{resultado_atualizar['total']} código(s) atualizado(s).")
        else:
            st.warning(
                "Nenhum código foi atualizado — confira se a caixa "
                "\"Renumerar?\" está marcada, se a coluna \"Tipo\" mudou de "
                "verdade, e se o código já está no formato "
                "CREDENCIADO-TIPO-NUMERO."
            )

    st.subheader("Numeração de vértices")
    st.text_input(
        "Código do credenciado",
        key="codigo_credenciado",
        help="Vai maiúsculo automaticamente ao compor o código do vértice.",
    )
    st.session_state.setdefault("numeracao_formato", "001")
    st.selectbox(
        "Formato do número",
        _FORMATOS_NUMERO,
        key="numeracao_formato",
        help="Quantos dígitos o número do vértice usa: 1 (sem zero), 01, "
        "001, 0001 ou 00001. Número maior que o formato não é cortado, só "
        "deixa de precisar do zero.",
        on_change=_reformata_campos_numero,
        args=(tipos,),
    )

    st.caption(
        "Próximo número livre de cada tipo — o mesmo contador da sua vida "
        "profissional, não reinicia por parcela nem por serviço."
    )
    inicio_por_tipo: dict[str, int] = {}
    for tipo in tipos:
        codigo_tipo = tipo["codigo"]
        chave = f"renum_inicio_{codigo_tipo}"
        st.session_state.setdefault(chave, "001")
        st.text_input(
            f"{codigo_tipo} — {tipo['descricao']}",
            key=chave,
            on_change=_normaliza_numero,
            args=(chave,),
        )
        inicio_por_tipo[codigo_tipo] = _numero_de(chave)

    if st.button("Renumerar vértices marcados", key="renum_botao"):
        credenciado = st.session_state["codigo_credenciado"].strip().upper()
        if not credenciado:
            st.warning("Informe o código do credenciado antes de renumerar.")
            return

        tabelas = [
            st.session_state[f"vertices_df_{i}"] for i in range(1, num_parcelas + 1)
        ]
        atualizadas, proximos, avisos, total_renumerado = renumerar_parcelas(
            tabelas, credenciado, inicio_por_tipo, _largura_selecionada()
        )
        _aplicar_tabelas_atualizadas(atualizadas, num_parcelas)
        st.session_state["numeracao_proximos_pendente"] = proximos
        st.session_state["renum_resultado_pendente"] = {
            "total": total_renumerado,
            "avisos": avisos,
        }
        st.rerun()

    st.caption(
        "Só as linhas com a caixa \"Renumerar?\" marcada, na tabela de cada "
        "parcela, recebem código novo — desmarque vértices que não são "
        "seus (ex.: de outro credenciado)."
    )

    if st.button(
        "🔄 Atualizar código (só o Tipo)",
        key="atualizar_botao",
        help="Já renumerou e corrigiu o Tipo (M/P/V) de algum vértice na "
        "grade? Isto reescreve só o pedaço do Tipo no código, mantendo "
        "credenciado e número — não reatribui número de novo.",
    ):
        tabelas = [
            st.session_state[f"vertices_df_{i}"] for i in range(1, num_parcelas + 1)
        ]
        atualizadas, avisos, total_atualizado = atualizar_tipos_parcelas(tabelas)
        _aplicar_tabelas_atualizadas(atualizadas, num_parcelas)
        st.session_state["atualizar_resultado_pendente"] = {
            "total": total_atualizado,
            "avisos": avisos,
        }
        st.rerun()

    st.caption(
        "Atualizar também só olha linha marcada com \"Renumerar?\" — e só "
        "muda o código se ele já estiver no formato CREDENCIADO-TIPO-NUMERO "
        "(ou seja, se já passou pela renumeração pelo menos uma vez)."
    )
