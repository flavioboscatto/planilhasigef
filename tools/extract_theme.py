#!/usr/bin/env python3
"""Lê os estilos de célula do modelo oficial e gera config/theme_tokens.json
com as cores reais do SIGEF, pra interface parecer com a planilha que os
profissionais já conhecem.

As cores de célula do ODS (table:style-name -> fo:background-color /
fo:color) ficam em office:automatic-styles do próprio content.xml, não em
styles.xml (isso é comum confundir: styles.xml só tem os estilos
"nomeados"/de página, os de célula usados no corpo do documento são
automáticos e vivem junto com os dados).

Uso:
    python tools/extract_theme.py
"""
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

from lxml import etree

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "config" / "theme_tokens.json"

NS = {
    "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
    "fo": "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0",
}

# Papel semântico -> nome do estilo no modelo 1.4_rc5 (conferido célula a
# célula no dump do tools/inspect_template.py). Se a versão do modelo
# mudar e os nomes de estilo mudarem junto, é só atualizar este dicionário
# — o resto do script não muda.
PAPEIS = {
    "servico_titulo": "ce1",
    "servico_label": "ce2",
    "servico_entrada": "ce14",
    "detentor_titulo": "ce4",
    "detentor_label": "ce5",
    "detentor_entrada": "ce15",
    "area_titulo": "ce7",
    "area_label": "ce8",
    "area_entrada": "ce19",
    "perimetro_titulo": "ce21",
    "perimetro_label": "ce22",
    "perimetro_entrada": "ce31",
    "perimetro_coord_label": "ce71",
    "perimetro_coord_sublabel": "ce39",
    "perimetro_coord_entrada": "ce33",
    "tabela_header_geral": "ce34",
    "tabela_entrada_geral": "ce43",
    "tabela_header_confrontante": "ce102",
    "tabela_entrada_confrontante": "ce122",
}

_TABLE_CELL_PROPS = f"{{{NS['style']}}}table-cell-properties"
_TEXT_PROPS = f"{{{NS['style']}}}text-properties"
_BG = f"{{{NS['fo']}}}background-color"
_COR = f"{{{NS['fo']}}}color"
_PESO = f"{{{NS['fo']}}}font-weight"


def _find_template_ods() -> Path:
    candidatos = sorted(TEMPLATES_DIR.glob("*.ods"))
    if not candidatos:
        sys.exit(f"Nenhum .ods encontrado em {TEMPLATES_DIR}")
    return candidatos[0]


def _extrai_estilos(root: etree._Element) -> dict[str, dict]:
    auto = root.find("office:automatic-styles", {"office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0"})
    estilos = {}
    for style in auto.findall("style:style", NS):
        nome = style.get(f"{{{NS['style']}}}name")
        tcp = style.find("style:table-cell-properties", NS)
        tp = style.find("style:text-properties", NS)
        estilos[nome] = {
            "fundo": tcp.get(_BG) if tcp is not None else None,
            "texto": tp.get(_COR) if tp is not None else None,
            "negrito": (tp.get(_PESO) == "bold") if tp is not None else False,
        }
    return estilos


def main() -> None:
    ods_path = _find_template_ods()
    print(f"Lendo: {ods_path}")
    with zipfile.ZipFile(ods_path) as zf:
        content = zf.read("content.xml")
    root = etree.fromstring(content)
    estilos = _extrai_estilos(root)

    tokens = {}
    faltando = []
    for papel, nome_estilo in PAPEIS.items():
        info = estilos.get(nome_estilo)
        if info is None:
            faltando.append(nome_estilo)
            continue
        tokens[papel] = info

    if faltando:
        print(f"Aviso: estilo(s) não encontrado(s) no modelo: {faltando}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(tokens, f, ensure_ascii=False, indent=2)
    print(f"Gravado em {OUTPUT_PATH} ({len(tokens)} papéis)")


if __name__ == "__main__":
    main()
