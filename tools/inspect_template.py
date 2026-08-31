#!/usr/bin/env python3
"""Dump de células do ODS oficial para CSV: aba, endereço A1, texto, tipo,
estilo e quantas colunas a célula mescla.

Uso:
    python tools/inspect_template.py [caminho_do_ods]

Sem argumento, usa o único .ods encontrado em templates/.

Tratamento de repetição (table:number-columns-repeated /
table:number-rows-repeated): o ODF usa esses atributos tanto para células
vazias que só preenchem a dimensão declarada da planilha (no LibreOffice,
até milhares ou centenas de milhares de linhas/colunas) quanto para blocos
pequenos de células realmente repetidas (ex.: várias linhas em branco
formatadas, ainda sem dado, aguardando preenchimento). Não dá para
distinguir os dois casos pelo atributo isoladamente — a diferença está na
magnitude.

Este script expande a repetição célula a célula / linha a linha para
calcular o endereço A1 correto. Quando encontra uma célula ou linha com
repetição >= REPEAT_THRESHOLD, para de processar o restante daquele nível
(célula final da linha, ou linha final da tabela) — mesmo que essas células
ainda carreguem table:style-name herdado de formatação de coluna, como
acontece nas linhas logo abaixo da tabela de vértices do modelo real: a
repetição de milhares indica preenchimento até a dimensão máxima da
planilha, nunca dado ou uma célula de entrada de fato. Isso é seguro porque,
nos exports do LibreOffice/OpenOffice, esse bloco de repetição gigante é
sempre o último filho do elemento (linha ou tabela). O limiar (500) foi
escolhido bem acima do número de linhas de vértice que uma tabela de
parcela chega a ter pré-formatadas (dezenas), e bem abaixo da escala de
milhares usada para preencher a planilha até sua dimensão máxima.

Já uma célula com repetição pequena (abaixo do limiar) é registrada mesmo
sem texto e sem office:value-type, desde que tenha table:style-name ou
table:content-validation-name — é uma célula de entrada pré-formatada,
ainda sem dado, e essa informação (estilo/validação) é o que a Etapa
seguinte (cell_map.yaml) precisa para saber que ali é onde um campo entra.
"""
from __future__ import annotations

import argparse
import csv
import sys
import zipfile
from pathlib import Path

from lxml import etree

TOOLS_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = TOOLS_DIR.parent / "templates"
OUTPUT_PATH = TOOLS_DIR / "out" / "dump_celulas.csv"

NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
}

REPEAT_THRESHOLD = 500

_TABLE_NAME = f"{{{NS['table']}}}name"
_TABLE_ROW = f"{{{NS['table']}}}table-row"
_TABLE_CELL = f"{{{NS['table']}}}table-cell"
_COVERED_CELL = f"{{{NS['table']}}}covered-table-cell"
_ROWS_REPEATED = f"{{{NS['table']}}}number-rows-repeated"
_COLS_REPEATED = f"{{{NS['table']}}}number-columns-repeated"
_VALUE_TYPE = f"{{{NS['office']}}}value-type"
_STYLE_NAME = f"{{{NS['table']}}}style-name"
_VALIDATION_NAME = f"{{{NS['table']}}}content-validation-name"
_COLS_SPANNED = f"{{{NS['table']}}}number-columns-spanned"
_TEXT_P = f"{{{NS['text']}}}p"


def col_to_letters(col: int) -> str:
    """Converte índice de coluna 1-based para letras estilo A1 (1 -> A, 27 -> AA)."""
    letters = ""
    while col > 0:
        col, rem = divmod(col - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


def cell_text(cell: etree._Element) -> str:
    paragrafos = cell.findall(_TEXT_P)
    return "\n".join("".join(p.itertext()) for p in paragrafos)


def find_template_ods() -> Path:
    candidatos = sorted(TEMPLATES_DIR.glob("*.ods"))
    if not candidatos:
        sys.exit(f"Nenhum .ods encontrado em {TEMPLATES_DIR}")
    if len(candidatos) > 1:
        sys.exit(
            f"Mais de um .ods em {TEMPLATES_DIR}: {[c.name for c in candidatos]}. "
            "Informe o caminho explicitamente."
        )
    return candidatos[0]


def dump_tabela(table: etree._Element) -> list[dict]:
    aba = table.get(_TABLE_NAME)
    registros: list[dict] = []
    row_num = 0

    for row in table.iter(_TABLE_ROW):
        row_repeat = int(row.get(_ROWS_REPEATED, "1"))
        if row_repeat >= REPEAT_THRESHOLD:
            # preenchimento até o fim da tabela: nada de real vem depois,
            # mesmo que as células ainda carreguem estilo de coluna
            break

        col_num = 0
        # (col_num, texto, value_type, style_name, col_span) — endereço
        # monta-se por linha repetida, na hora de emitir, não aqui.
        celulas_linha: list[tuple[int, str, str, str, int]] = []
        for cell in row:
            if cell.tag not in (_TABLE_CELL, _COVERED_CELL):
                continue
            col_repeat = int(cell.get(_COLS_REPEATED, "1"))
            if col_repeat >= REPEAT_THRESHOLD:
                # preenchimento até o fim da linha: nada de real vem depois
                break

            if cell.tag == _COVERED_CELL:
                # continuação de célula mesclada: mesmo que carregue texto ou
                # value-type residual (achado real no modelo: identificacao.B1
                # e perimetro_1.B1 têm conteúdo "fantasma" de antes da
                # mesclagem), nunca é uma célula visível ou gravável — quem
                # recebe o valor é sempre a célula-mestra do merge
                texto = ""
                value_type = ""
                style_name = ""
                col_span = 1
                vazio = True
            else:
                texto = cell_text(cell)
                value_type = cell.get(_VALUE_TYPE, "")
                style_name = cell.get(_STYLE_NAME, "")
                validation_name = cell.get(_VALIDATION_NAME, "")
                col_span = int(cell.get(_COLS_SPANNED, "1"))
                # uma célula sem texto/valor mas com estilo ou validação
                # próprios ainda é relevante: é uma célula de entrada
                # pré-formatada, aguardando dado (comum na tabela de vértices)
                vazio = not (texto or value_type or style_name or validation_name)

            for _ in range(col_repeat):
                col_num += 1
                if not vazio:
                    celulas_linha.append((col_num, texto, value_type, style_name, col_span))

        for _ in range(row_repeat):
            row_num += 1
            for col, texto, value_type, style_name, col_span in celulas_linha:
                registros.append(
                    {
                        "aba": aba,
                        "endereco": f"{col_to_letters(col)}{row_num}",
                        "texto": texto,
                        "value_type": value_type,
                        "style_name": style_name,
                        "col_span": col_span,
                    }
                )

    return registros


def dump(ods_path: Path) -> tuple[list[str], list[dict]]:
    with zipfile.ZipFile(ods_path) as zf:
        content_xml = zf.read("content.xml")
    root = etree.fromstring(content_xml)
    tabelas = root.findall(".//table:table", NS)

    abas = [t.get(_TABLE_NAME) for t in tabelas]
    linhas: list[dict] = []
    for tabela in tabelas:
        linhas.extend(dump_tabela(tabela))
    return abas, linhas


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ods_path", nargs="?", type=Path, default=None)
    args = parser.parse_args()

    ods_path = args.ods_path or find_template_ods()
    print(f"Lendo: {ods_path}")

    abas, linhas = dump(ods_path)
    print(f"Abas encontradas ({len(abas)}): {', '.join(abas)}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["aba", "endereco", "texto", "value_type", "style_name", "col_span"],
        )
        writer.writeheader()
        writer.writerows(linhas)

    print(f"CSV gravado em {OUTPUT_PATH} ({len(linhas)} linhas)")


if __name__ == "__main__":
    main()
