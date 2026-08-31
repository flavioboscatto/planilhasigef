"""Carrega o modelo oficial do ODS: baixa do GitHub, confere o hash e cacheia.

Único módulo de core/ que pode importar streamlit — os demais devem rodar em
teste puro, sem essa dependência (ver CLAUDE.md).
"""
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

import requests
import streamlit as st

# TODO: preencher com o owner/repo reais do GitHub onde o modelo está publicado.
GITHUB_RAW_URL = (
    "https://raw.githubusercontent.com/OWNER/REPO/main/templates/{nome_arquivo}"
)

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
MANIFEST_PATH = TEMPLATES_DIR / "manifest.json"

logger = logging.getLogger(__name__)


class TemplateHashError(RuntimeError):
    """O sha256 do ODS obtido não bate com o registrado em manifest.json."""


def _read_manifest() -> dict:
    with MANIFEST_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def _sha256(dados: bytes) -> str:
    return hashlib.sha256(dados).hexdigest()


def _baixar_do_github(nome_arquivo: str) -> bytes:
    url = GITHUB_RAW_URL.format(nome_arquivo=nome_arquivo)
    resposta = requests.get(url, timeout=10)
    resposta.raise_for_status()
    return resposta.content


def _ler_copia_local(nome_arquivo: str) -> bytes:
    return (TEMPLATES_DIR / nome_arquivo).read_bytes()


@st.cache_resource
def load_template() -> bytes:
    """Retorna os bytes do ODS oficial, validados contra o manifest.

    Tenta baixar do GitHub primeiro; se a rede falhar, usa a cópia local em
    templates/. Em ambos os casos confere o sha256 contra manifest.json e
    rejeita divergência (TemplateHashError), pois indica modelo corrompido
    ou trocado sem atualizar o manifest.
    """
    manifest = _read_manifest()
    nome_arquivo = manifest["nome_arquivo"]
    sha_esperado = manifest["sha256"]

    try:
        dados = _baixar_do_github(nome_arquivo)
        origem = "github"
    except requests.RequestException as exc:
        logger.warning("Falha ao baixar modelo do GitHub (%s); usando cópia local.", exc)
        dados = _ler_copia_local(nome_arquivo)
        origem = "local"

    sha_obtido = _sha256(dados)
    if sha_obtido != sha_esperado:
        raise TemplateHashError(
            f"sha256 do modelo ({origem}) não bate com manifest.json: "
            f"esperado {sha_esperado}, obtido {sha_obtido}"
        )

    logger.info("Modelo do SIGEF carregado a partir de: %s (%s)", origem, nome_arquivo)
    return dados
