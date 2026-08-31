"""Carrega o modelo oficial do ODS a partir da cópia local em templates/,
conferindo o hash contra manifest.json.

Único módulo de core/ que pode importar streamlit — os demais devem rodar em
teste puro, sem essa dependência (ver CLAUDE.md).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import streamlit as st

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
MANIFEST_PATH = TEMPLATES_DIR / "manifest.json"


class TemplateHashError(RuntimeError):
    """O sha256 do ODS obtido não bate com o registrado em manifest.json."""


def _read_manifest() -> dict:
    with MANIFEST_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def _sha256(dados: bytes) -> str:
    return hashlib.sha256(dados).hexdigest()


@st.cache_resource
def load_template() -> bytes:
    """Retorna os bytes do ODS oficial, validados contra o manifest.

    Só cópia local (sem tentativa de rede): o app agora roda localmente,
    inclusive em campo sem internet — uma tentativa de download que sempre
    falharia (ou demorasse pra falhar) só atrasaria a abertura à toa. O
    hash continua conferido contra manifest.json — rejeita divergência
    (TemplateHashError) porque indica modelo corrompido ou trocado sem
    atualizar o manifest (ver templates/manifest.json: url_origem tem o
    link oficial do INCRA pra rebaixar manualmente se precisar).
    """
    manifest = _read_manifest()
    nome_arquivo = manifest["nome_arquivo"]
    sha_esperado = manifest["sha256"]

    dados = (TEMPLATES_DIR / nome_arquivo).read_bytes()

    sha_obtido = _sha256(dados)
    if sha_obtido != sha_esperado:
        raise TemplateHashError(
            f"sha256 do modelo local não bate com manifest.json: "
            f"esperado {sha_esperado}, obtido {sha_obtido}"
        )

    return dados
