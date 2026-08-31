"""Gate de projeto (.sigefproj) + salvar/abrir — única forma de
persistência do app (Etapa 4 adiantada a pedido do usuário). Único módulo,
além de ui/aba_perimetro.py e ui/renumeracao.py, que conhece o nome das
chaves de session_state de cada campo; reaproveita esse conhecimento pra
montar/aplicar o projeto inteiro de uma vez.

Grava a Identificação (nome, CPF/CNPJ, matrícula) no arquivo — exceção
deliberada à regra 6 do CLAUDE.md, só porque é o próprio profissional quem
decide salvar/abrir, nunca automático (ver core/projeto.py).

Salvar = st.download_button (o navegador grava no Downloads da pessoa) e
Abrir = st.file_uploader (a pessoa escolhe o arquivo pelo seletor do
próprio navegador) — nunca um caminho de disco do servidor. Chegamos a usar
diálogo nativo do Windows via subprocess (funcionava só rodando localmente,
na máquina do profissional); trocamos ao publicar em hospedagem remota
(Render), onde não existe tela nem acesso ao disco de quem está usando.
Efeito colateral aceito: não existe mais "Salvar" (sobrescrever o mesmo
arquivo) — todo Salvar é um novo download; o navegador decide se sobrescreve
ou cria "(1)", "(2)" etc.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from core.models import Identificacao, Perimetro
from core.projeto import ProjetoInvalidoError, desserializar, serializar
from ui.aba_perimetro import _COLUNAS_VERTICE, _linha_para_vertice, _preenchido, _tabela_vazia

_CAMPOS_IDENTIFICACAO = list(Identificacao.model_fields)
_CHAVE_IDENT = {campo: f"ident_{campo}" for campo in _CAMPOS_IDENTIFICACAO}

# nome do campo do projeto -> modelo da chave de session_state do widget
# (formatado com o índice da parcela), e o padrão de Perimetro (core/models.py)
# pra quando a parcela existe (num_parcelas já conta com ela) mas o
# profissional nunca abriu a aba nesta sessão — os widgets daquele índice
# nunca chegaram a nascer, então a chave nem existe em session_state ainda.
_CHAVE_PARCELA = {
    "denominacao": ("perim_denominacao_{i}", ""),
    "parcela_numero": ("perim_numero_{i}", ""),
    "lado": ("perim_lado_{i}", "Externo"),
    "tipo_coordenada": ("perim_tipocoord_{i}", "Geográfica"),
    "meridiano_central": ("perim_meridiano_{i}", None),
    "hemisferio": ("perim_hemisferio_{i}", "Norte"),
}


def _identificacao_atual() -> dict:
    """Lê a chave do widget quando existe (aba aberta nesta mesma sessão
    desde a última visita) e cai pro cache `identificacao` (app.py) quando
    não existe mais — o Streamlit apaga a chave de um widget de
    session_state assim que ele deixa de ser desenhado numa execução (sair
    da aba), então ler só a chave bruta perdia todo o formulário se o
    profissional não estivesse na aba Identificação no instante de
    Salvar."""
    cache = st.session_state.get("identificacao")
    base = cache.model_dump() if cache is not None else dict.fromkeys(_CAMPOS_IDENTIFICACAO, "")
    return {campo: st.session_state.get(chave, base[campo]) for campo, chave in _CHAVE_IDENT.items()}


def _parcela_atual(indice: int) -> dict:
    """Mesmo raciocínio de `_identificacao_atual`, para os campos de
    cabeçalho de uma parcela (Denominação, Lado, Meridiano...) — os
    vértices já não sofriam disso porque `vertices_df_i` é variável nossa,
    não chave de widget."""
    cache = st.session_state.get(f"perimetro_{indice}")
    base = cache.model_dump() if cache is not None else {}
    return {
        campo: st.session_state.get(modelo.format(i=indice), base.get(campo, padrao))
        for campo, (modelo, padrao) in _CHAVE_PARCELA.items()
    }


def _montar_projeto(dominios: dict) -> dict:
    identificacao = _identificacao_atual()

    num_parcelas = st.session_state["num_parcelas"]
    parcelas = []
    for i in range(1, num_parcelas + 1):
        campos = _parcela_atual(i)
        tabela = st.session_state.get(f"vertices_df_{i}", _tabela_vazia())
        campos["vertices"] = tabela.to_dict(orient="records")
        parcelas.append(campos)

    inicio_por_tipo = {
        tipo["codigo"]: st.session_state.get(f"renum_inicio_{tipo['codigo']}", "001")
        for tipo in dominios["tipos_vertice"]
    }
    numeracao = {
        "codigo_credenciado": st.session_state.get("codigo_credenciado", ""),
        "formato": st.session_state.get("numeracao_formato", "001"),
        "inicio_por_tipo": inicio_por_tipo,
    }

    return {
        "nome_projeto": st.session_state.get("projeto_nome", ""),
        "identificacao": identificacao,
        "num_parcelas": num_parcelas,
        "parcelas": parcelas,
        "numeracao": numeracao,
    }


def _aplicar_projeto(dados: dict) -> None:
    """Escreve tudo em session_state ANTES de qualquer widget da tela
    normal ser criado nesta execução (o gate só libera via st.rerun() logo
    depois) — por isso pode atribuir livremente, sem esbarrar na trava do
    Streamlit contra reatribuir chave de widget já instanciado.

    Também recalcula e já deixa em cache `identificacao`/`perimetro_i`
    (não só as chaves cruas dos widgets): sem isso, "Gerar planilha SIGEF"
    usaria dado em branco pra qualquer parcela que o profissional não
    visitasse de novo nesta sessão — o cache só nasce de verdade quando
    aquela aba é renderizada (ver app.py).
    """
    identificacao_dict = dados.get("identificacao", {})
    for campo, chave in _CHAVE_IDENT.items():
        st.session_state[chave] = identificacao_dict.get(campo, "")
    st.session_state["identificacao"] = Identificacao(**identificacao_dict)

    num_parcelas = max(1, dados.get("num_parcelas", 1))
    st.session_state["num_parcelas"] = num_parcelas
    for i, parcela in enumerate(dados.get("parcelas", []), start=1):
        # meridiano_central pode ser None de propósito (campo opcional); os
        # demais não são string no modelo, então um None solto (arquivo de
        # versão anterior, editado à mão etc.) vira o padrão do Perimetro.
        valores_parcela = {
            campo: parcela[campo] if parcela.get(campo) is not None else padrao
            for campo, (_, padrao) in _CHAVE_PARCELA.items()
        }
        for campo, (modelo, _) in _CHAVE_PARCELA.items():
            valor = valores_parcela[campo]
            if campo == "meridiano_central" and valor is not None:
                # Perimetro.meridiano_central é float, mas o dropdown
                # (meridianos_centrais_brasil, dominios.json) só tem
                # inteiros — sem isto o valor salvo (-51.0) não bate com
                # nenhuma opção e o Streamlit troca pra primeira da lista
                # sem avisar (mesma conversão em ui/aba_perimetro.py).
                valor = int(valor)
            st.session_state[modelo.format(i=i)] = valor

        tabela = pd.DataFrame(parcela.get("vertices", []), columns=_COLUNAS_VERTICE)
        st.session_state[f"vertices_df_{i}"] = tabela
        vertices = [
            _linha_para_vertice(linha)
            for _, linha in tabela.iterrows()
            if _preenchido(linha["codigo"])
        ]
        st.session_state[f"perimetro_{i}"] = Perimetro(vertices=vertices, **valores_parcela)

    numeracao = dados.get("numeracao", {})
    st.session_state["codigo_credenciado"] = numeracao.get("codigo_credenciado", "")
    st.session_state["numeracao_formato"] = numeracao.get("formato", "001")
    for codigo_tipo, valor in numeracao.get("inicio_por_tipo", {}).items():
        st.session_state[f"renum_inicio_{codigo_tipo}"] = valor

    st.session_state["projeto_nome"] = dados.get("nome_projeto", "")


def _processar_upload(arquivo, chave_marca: str) -> None:
    """Aplica um .sigefproj vindo de st.file_uploader uma única vez por
    arquivo — o widget mantém o arquivo "selecionado" entre execuções, então
    sem marcar o que já foi processado (file_id, único por upload) o projeto
    seria reaplicado a cada rerun, atropelando qualquer edição feita depois
    de abrir."""
    if arquivo is None or st.session_state.get(chave_marca) == arquivo.file_id:
        return
    st.session_state[chave_marca] = arquivo.file_id
    try:
        dados = desserializar(arquivo.getvalue())
    except ProjetoInvalidoError as exc:
        st.error(f"Não consegui abrir o arquivo: {exc}")
        return
    _aplicar_projeto(dados)
    st.session_state["projeto_aberto"] = True
    st.rerun()


def render_gate() -> bool:
    """Tela obrigatória antes de liberar Identificação/Perímetro. Devolve
    True só quando um projeto (novo ou aberto de arquivo) está pronto."""
    if st.session_state.get("projeto_aberto"):
        return True

    st.subheader("Comece um projeto")
    st.caption(
        "Tudo o que você preencher fica só nesta sessão até você baixar o "
        "projeto — o arquivo .sigefproj é a única forma de continuar "
        "depois, inclusive a Identificação. Guarde-o com o mesmo cuidado "
        "que um documento do serviço."
    )
    aba_novo, aba_abrir = st.tabs(["Novo projeto", "Abrir projeto (.sigefproj)"])

    with aba_novo:
        nome = st.text_input("Nome do projeto", key="gate_nome_novo")
        st.caption(
            "Cria o projeto nesta sessão — use \"Baixar projeto\" na barra "
            "lateral sempre que quiser salvar um ponto pra continuar depois."
        )
        if st.button("Criar projeto", type="primary"):
            st.session_state["projeto_nome"] = nome.strip() or "projeto_sigef"
            st.session_state["projeto_aberto"] = True
            st.rerun()

    with aba_abrir:
        st.caption("Escolha o arquivo .sigefproj salvo anteriormente.")
        arquivo = st.file_uploader(
            "Arquivo .sigefproj", type=["sigefproj"], key="gate_upload_abrir"
        )
        _processar_upload(arquivo, "_gate_upload_processado")

    return False


def render_barra_lateral(dominios: dict) -> None:
    """Salvar/abrir projeto — sempre visível na barra lateral depois que o
    gate libera o app. Salvar baixa o .sigefproj pelo navegador (não existe
    caminho de disco do servidor pra reescrever); Abrir troca o projeto
    atual por outro arquivo escolhido pelo seletor do navegador."""
    st.divider()
    nome_projeto = st.session_state.get("projeto_nome") or "projeto_sigef"
    conteudo = serializar(_montar_projeto(dominios))
    st.download_button(
        "⬇️ Baixar projeto (.sigefproj)",
        data=conteudo,
        file_name=f"{nome_projeto}.sigefproj",
        mime="application/octet-stream",
        use_container_width=True,
    )
    st.caption(
        "O navegador salva na pasta de Downloads — configure-o para "
        "perguntar onde salvar se quiser escolher a pasta toda vez."
    )

    with st.expander("📂 Abrir outro projeto (.sigefproj)"):
        arquivo = st.file_uploader(
            "Arquivo .sigefproj", type=["sigefproj"], key="barra_upload_abrir"
        )
        st.caption("Substitui tudo o que está preenchido agora nesta sessão.")
        _processar_upload(arquivo, "_barra_upload_processado")
