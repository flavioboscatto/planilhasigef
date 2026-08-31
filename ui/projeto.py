"""Gate de projeto (.sigefproj) + salvar/abrir — única forma de
persistência do app (Etapa 4 adiantada a pedido do usuário). Único módulo,
além de ui/aba_perimetro.py e ui/renumeracao.py, que conhece o nome das
chaves de session_state de cada campo; reaproveita esse conhecimento pra
montar/aplicar o projeto inteiro de uma vez.

Grava a Identificação (nome, CPF/CNPJ, matrícula) no arquivo — exceção
deliberada à regra 6 do CLAUDE.md, só porque é o próprio profissional quem
decide salvar/abrir, nunca automático (ver core/projeto.py).

Diálogo nativo do SO via subprocess, não st.download_button/file_uploader:
chegamos a usar download/upload pelo navegador pra publicar numa hospedagem
remota (Render), mas o projeto voltou a ser 100% local (distribuído como
.exe — ver PLANO_SIGEF_WEB.md) e diálogo nativo dá de volta o "Salvar"
de verdade (regrava o mesmo arquivo), sem a limitação de download sempre
criar um arquivo novo.

tkinter não é thread-safe e o Streamlit roda o script de cada sessão numa
thread própria (não a principal) — chamar tk.Tk() direto dali dá diálogo
que às vezes nem aparece. Rodar num processo Python à parte (dialogo_arquivo.py,
na raiz do projeto) elimina isso: cada chamada nasce com sua própria thread
principal, que é onde o Tcl/Tk exige rodar.

No .exe empacotado (PyInstaller) não existe um "python.exe" à parte pra
rodar dialogo_arquivo.py — main_exe.py reconhece a flag --dialogo-arquivo e
reinvoca o próprio executável nesse modo (ver comentário em _rodar_dialogo).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

from core.models import Identificacao, Perimetro
from core.projeto import ProjetoInvalidoError, desserializar, serializar
from ui.aba_perimetro import _COLUNAS_VERTICE, _linha_para_vertice, _preenchido, _tabela_vazia

_RAIZ_PROJETO = Path(__file__).resolve().parent.parent


def _rodar_dialogo(*args: str) -> str | None:
    if getattr(sys, "frozen", False):
        comando = [sys.executable, "--dialogo-arquivo", *args]
    else:
        comando = [sys.executable, str(_RAIZ_PROJETO / "dialogo_arquivo.py"), *args]
    resultado = subprocess.run(
        comando,
        capture_output=True,
        text=True,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    caminho = resultado.stdout.strip()
    return caminho or None


def _dialogo_salvar_como(nome_sugerido: str) -> str | None:
    return _rodar_dialogo("salvar-como", nome_sugerido)


def _dialogo_abrir() -> str | None:
    return _rodar_dialogo("abrir")


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


def _salvar(dominios: dict, caminho: str | None) -> None:
    """Grava direto no `caminho` já escolhido antes (Salvar Como/Abrir) —
    sem diálogo, é o que faz o botão Salvar ir atualizando o mesmo arquivo
    a cada clique. Sem caminho ainda, cai pra Salvar Como."""
    if not caminho:
        _salvar_como(dominios)
        return
    conteudo = serializar(_montar_projeto(dominios))
    try:
        Path(caminho).write_bytes(conteudo)
    except OSError as exc:
        st.error(f"Não consegui salvar em {caminho}: {exc}")
    else:
        st.session_state["projeto_caminho"] = caminho
        st.toast(f"Projeto salvo em {caminho}")


def _salvar_como(dominios: dict) -> None:
    nome_sugerido = st.session_state.get("projeto_nome") or "projeto_sigef"
    caminho = _dialogo_salvar_como(nome_sugerido)
    if not caminho:
        return
    st.session_state["projeto_nome"] = Path(caminho).stem
    _salvar(dominios, caminho)


def _abrir() -> None:
    caminho = _dialogo_abrir()
    if not caminho:
        return
    try:
        dados = desserializar(Path(caminho).read_bytes())
        _aplicar_projeto(dados)
    except (ProjetoInvalidoError, OSError) as exc:
        st.error(f"Não consegui abrir {caminho}: {exc}")
        return
    st.session_state["projeto_caminho"] = caminho
    st.session_state["projeto_aberto"] = True
    st.rerun()


def render_gate() -> bool:
    """Tela obrigatória antes de liberar Identificação/Perímetro. Devolve
    True só quando um projeto (novo ou aberto de arquivo) está pronto."""
    if st.session_state.get("projeto_aberto"):
        return True

    st.subheader("Comece um projeto")
    st.caption(
        "Tudo o que você preencher fica só nesta sessão até você salvar — "
        "o arquivo .sigefproj é a única forma de continuar depois, "
        "inclusive a Identificação. Guarde-o com o mesmo cuidado que um "
        "documento do serviço."
    )
    aba_novo, aba_abrir = st.tabs(["Novo projeto", "Abrir projeto (.sigefproj)"])

    with aba_novo:
        nome = st.text_input("Nome do projeto", key="gate_nome_novo")
        st.caption(
            "Ao criar, abre o diálogo do Windows pra você escolher a pasta "
            "de uma vez — se cancelar, o projeto continua, só sem lugar "
            "salvo ainda (dá pra usar Salvar Como depois, na barra lateral)."
        )
        if st.button("Criar projeto", type="primary"):
            nome_final = nome.strip() or "projeto_sigef"
            st.session_state["projeto_nome"] = nome_final
            caminho = _dialogo_salvar_como(nome_final)
            if caminho:
                dados_iniciais = {
                    "nome_projeto": Path(caminho).stem,
                    "identificacao": {},
                    "num_parcelas": 1,
                    "parcelas": [{"vertices": []}],
                    "numeracao": {},
                }
                try:
                    Path(caminho).write_bytes(serializar(dados_iniciais))
                except OSError as exc:
                    st.error(f"Não consegui salvar em {caminho}: {exc}")
                else:
                    st.session_state["projeto_nome"] = Path(caminho).stem
                    st.session_state["projeto_caminho"] = caminho
            st.session_state["projeto_aberto"] = True
            st.rerun()

    with aba_abrir:
        st.caption("Abre o diálogo do Windows para escolher o arquivo .sigefproj.")
        if st.button("Abrir projeto...", type="primary"):
            caminho = _dialogo_abrir()
            if caminho:
                try:
                    dados = desserializar(Path(caminho).read_bytes())
                    _aplicar_projeto(dados)
                except (ProjetoInvalidoError, OSError) as exc:
                    st.error(f"Não consegui abrir {caminho}: {exc}")
                else:
                    st.session_state["projeto_caminho"] = caminho
                    st.session_state["projeto_aberto"] = True
                    st.rerun()

    return False


def render_barra_lateral(dominios: dict) -> None:
    """Salvar/abrir projeto — sempre visível na barra lateral depois que o
    gate libera o app. Diálogos nativos do SO (ver _dialogo_*): Salvar
    regrava direto no arquivo já escolhido, sem perguntar de novo."""
    st.divider()
    caminho_atual = st.session_state.get("projeto_caminho")
    if caminho_atual:
        st.caption(f"📄 {Path(caminho_atual).name}")
    else:
        st.caption("Projeto ainda sem arquivo salvo.")

    if st.button("💾 Salvar", use_container_width=True):
        _salvar(dominios, caminho_atual)
    if st.button("🗂️ Salvar como...", use_container_width=True):
        _salvar_como(dominios)
    if st.button("📂 Abrir...", use_container_width=True):
        _abrir()
