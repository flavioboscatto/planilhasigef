"""Serialização do projeto (.sigefproj) — salvar/reabrir o trabalho em
andamento entre sessões. Sem streamlit (CLAUDE.md, regra de fronteira de
core/); quem lê/grava em st.session_state é ui/projeto.py.

Exceção deliberada à regra 6 do CLAUDE.md ("dado pessoal nunca em disco"):
este arquivo inclui a Identificação (nome, CPF/CNPJ, matrícula), porque é
o profissional quem escolhe salvar/abrir, por conta própria, a qualquer
momento — nunca é gravação automática nem em segundo plano, e nunca sai
da máquina do profissional por este código.
"""
from __future__ import annotations

import json

VERSAO_ATUAL = 1


class ProjetoInvalidoError(ValueError):
    """Arquivo .sigefproj corrompido ou de versão incompatível."""


def serializar(dados: dict) -> bytes:
    """`dados` já no formato do projeto (ver ui/projeto.py); só carimba a
    versão e serializa. Indentado, UTF-8 — dá pra abrir num editor de texto
    comum se precisar depurar."""
    envelope = dict(dados, versao=VERSAO_ATUAL)
    return json.dumps(envelope, ensure_ascii=False, indent=2).encode("utf-8")


def desserializar(conteudo: bytes) -> dict:
    try:
        dados = json.loads(conteudo.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProjetoInvalidoError(f"arquivo de projeto corrompido: {exc}") from exc
    if dados.get("versao") != VERSAO_ATUAL:
        raise ProjetoInvalidoError(
            f"arquivo de projeto na versão {dados.get('versao')!r}, esperada "
            f"{VERSAO_ATUAL} — pode ter sido salvo por outra versão do app"
        )
    return dados
