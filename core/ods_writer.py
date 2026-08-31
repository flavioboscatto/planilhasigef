"""Gravador do ODS: abre o modelo oficial, escreve os valores no content.xml
e regrava o restante do ZIP byte a byte. Sem streamlit (CLAUDE.md, regra 2).

Suporta N parcelas: clona perimetro_1 (deepcopy do table:table, sem macro
embutida no .ods para se preocupar — a Extensão SIGEF é um add-on separado
do LibreOffice) e renomeia para perimetro_2, perimetro_3... Cada aba de
vértices só tem 9 linhas pré-formatadas no modelo (12 a 20); mais que isso
por parcela exige inserir linha no bloco de preenchimento da planilha, não
implementado ainda.
"""
from __future__ import annotations

import copy
import io
import json
import zipfile
from pathlib import Path

import yaml
from lxml import etree

from core.models import Identificacao, Perimetro

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
CELL_MAP_PATH = CONFIG_DIR / "cell_map.yaml"
DOMINIOS_PATH = CONFIG_DIR / "dominios.json"

NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
}
_TABLE = f"{{{NS['table']}}}table"
_TABLE_NAME = f"{{{NS['table']}}}name"
_TABLE_ROW = f"{{{NS['table']}}}table-row"
_TABLE_CELL = f"{{{NS['table']}}}table-cell"
_COVERED_CELL = f"{{{NS['table']}}}covered-table-cell"
_ROWS_REPEATED = f"{{{NS['table']}}}number-rows-repeated"
_COLS_REPEATED = f"{{{NS['table']}}}number-columns-repeated"
_VALUE_TYPE = f"{{{NS['office']}}}value-type"
_TEXT_P = f"{{{NS['text']}}}p"
_XML_ID = "{http://www.w3.org/XML/1998/namespace}id"
_FORM_ID = "{urn:oasis:names:tc:opendocument:xmlns:form:1.0}id"


def _carregar_cell_map() -> dict:
    with CELL_MAP_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _carregar_dominios() -> dict:
    with DOMINIOS_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def _letras_para_col(letras: str) -> int:
    col = 0
    for c in letras:
        col = col * 26 + (ord(c.upper()) - ord("A") + 1)
    return col


def _fmt_decimal(valor: float, casas: int) -> str:
    """Vírgula decimal, sem separador de milhar (regra do manual/CLAUDE.md)."""
    return f"{valor:.{casas}f}".replace(".", ",")


def _fmt_livre(valor: float) -> str:
    texto = f"{valor:g}"
    return texto.replace(".", ",")


def _fmt_geografica(valor_decimal: float, sufixo_positivo: str, sufixo_negativo: str, casas_segundos: int) -> str:
    """Grau decimal -> "GG MM SS,sss <hemisfério>", como o manual exige."""
    sufixo = sufixo_positivo if valor_decimal >= 0 else sufixo_negativo
    valor_abs = abs(valor_decimal)
    graus = int(valor_abs)
    minutos_decimais = (valor_abs - graus) * 60
    minutos = int(minutos_decimais)
    segundos = (minutos_decimais - minutos) * 60
    return f"{graus:02d} {minutos:02d} {_fmt_decimal(segundos, casas_segundos)} {sufixo}"


def _find_table(root: etree._Element, nome_aba: str) -> etree._Element:
    for tabela in root.iter(_TABLE):
        if tabela.get(_TABLE_NAME) == nome_aba:
            return tabela
    raise KeyError(f"aba '{nome_aba}' não encontrada no content.xml do modelo")


def _split_repeated_row(table: etree._Element, row_num: int) -> etree._Element:
    """Garante que a linha `row_num` (1-based) seja um elemento individual,
    separando-a de um bloco table:number-rows-repeated se for o caso."""
    acumulado = 0
    for row in list(table.iter(_TABLE_ROW)):
        repeticoes = int(row.get(_ROWS_REPEATED, "1"))
        inicio = acumulado + 1
        fim = acumulado + repeticoes
        if inicio <= row_num <= fim:
            if repeticoes == 1:
                return row
            pai = row.getparent()
            indice = list(pai).index(row)
            pai.remove(row)
            copias = []
            for _ in range(repeticoes):
                copia = copy.deepcopy(row)
                if _ROWS_REPEATED in copia.attrib:
                    del copia.attrib[_ROWS_REPEATED]
                copias.append(copia)
            for offset, copia in enumerate(copias):
                pai.insert(indice + offset, copia)
            return copias[row_num - inicio]
        acumulado = fim
    raise KeyError(f"linha {row_num} não encontrada na aba (fim da tabela)")


def _garantir_linhas_vertice(
    tabela: etree._Element, linha_final_maxima: int, necessario_ate: int
) -> None:
    """Clona a última linha pré-formatada da tabela de vértices (mesmo
    estilo, mesma validação de célula — nada de formatação nova) até
    existir linha real suficiente para `necessario_ate`. Não mexe no bloco
    de preenchimento do resto da planilha (linhas 21+, ver
    tools/inspect_template.py); só insere logo depois da última linha de
    vértice, então o total de linhas da aba cresce — ODF não exige
    contagem fixa de linha por aba, então isso não quebra a planilha.

    Risco não verificado por este código: a Extensão SIGEF (macro, fora
    deste repositório) pode presumir um número fixo de linhas na tabela de
    vértices. Só o teste manual com F3 (critério de aceite do CLAUDE.md)
    confirma se uma parcela com mais vértices do que os pré-formatados no
    modelo é lida corretamente pela extensão — testar antes de confiar.
    """
    if necessario_ate <= linha_final_maxima:
        return
    modelo = _split_repeated_row(tabela, linha_final_maxima)
    pai = modelo.getparent()
    indice_insercao = list(pai).index(modelo) + 1
    for offset in range(necessario_ate - linha_final_maxima):
        pai.insert(indice_insercao + offset, copy.deepcopy(modelo))


def _split_repeated_cell(row: etree._Element, col_num: int) -> etree._Element:
    """Garante que a coluna `col_num` (1-based) da linha seja um elemento
    individual, separando-a de um bloco table:number-columns-repeated."""
    acumulado = 0
    for cell in list(row):
        if cell.tag not in (_TABLE_CELL, _COVERED_CELL):
            continue
        repeticoes = int(cell.get(_COLS_REPEATED, "1"))
        inicio = acumulado + 1
        fim = acumulado + repeticoes
        if inicio <= col_num <= fim:
            if cell.tag == _COVERED_CELL:
                raise KeyError(
                    f"coluna {col_num} é uma célula mesclada (covered-table-cell); "
                    "o cell_map deve apontar para a célula-mestra do merge"
                )
            if repeticoes == 1:
                return cell
            pai = row
            indice = list(pai).index(cell)
            pai.remove(cell)
            copias = []
            for _ in range(repeticoes):
                copia = copy.deepcopy(cell)
                if _COLS_REPEATED in copia.attrib:
                    del copia.attrib[_COLS_REPEATED]
                copias.append(copia)
            for offset, copia in enumerate(copias):
                pai.insert(indice + offset, copia)
            return copias[col_num - inicio]
        acumulado = fim
    raise KeyError(f"coluna {col_num} não encontrada na linha (fim da linha)")


def _get_editable_cell(table: etree._Element, row_num: int, col_letras: str) -> etree._Element:
    row = _split_repeated_row(table, row_num)
    return _split_repeated_cell(row, _letras_para_col(col_letras))


def _set_texto(cell: etree._Element, texto: str) -> None:
    cell.set(_VALUE_TYPE, "string")
    for p in cell.findall(_TEXT_P):
        cell.remove(p)
    p = etree.SubElement(cell, _TEXT_P)
    p.text = texto


def _reescreve_zip(template_bytes: bytes, content_xml: bytes) -> bytes:
    saida = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(template_bytes)) as zin:
        with zipfile.ZipFile(saida, "w") as zout:
            for item in zin.infolist():
                dados = content_xml if item.filename == "content.xml" else zin.read(item.filename)
                compress_type = zipfile.ZIP_STORED if item.filename == "mimetype" else item.compress_type
                zout.writestr(item, dados, compress_type=compress_type)
    return saida.getvalue()


def _content_xml_de(template_bytes: bytes) -> bytes:
    with zipfile.ZipFile(io.BytesIO(template_bytes)) as zf:
        return zf.read("content.xml")


def _renomeia_ids_controles(elemento: etree._Element, sufixo: str) -> None:
    """Os controles de formulário sobrepostos às células (listbox do
    Hemisfério, Tipo de Coordenada etc. — achado real no modelo, não estão
    em content-validation) têm xml:id/form:id únicos no documento inteiro.
    Clonar a aba sem trocar esses ids quebra o XML (ID duplicado); o
    form:name pode repetir entre abas sem problema, pois o form:form pai
    já fica dentro de cada table:table."""
    for el in elemento.iter():
        xml_id = el.get(_XML_ID)
        if xml_id is None:
            continue
        novo_id = f"{xml_id}_{sufixo}"
        el.set(_XML_ID, novo_id)
        if el.get(_FORM_ID) == xml_id:
            el.set(_FORM_ID, novo_id)


def _clonar_abas_perimetro(root: etree._Element, prefixo: str, quantidade: int) -> list[etree._Element]:
    """Garante `quantidade` abas perimetro_N, clonando perimetro_1.

    Cada clone parte sempre do perimetro_1 original (pristino, sem valores
    gravados), não do clone anterior, e é inserido logo depois da última
    aba de perímetro já existente — mantém identificacao, perimetro_1..N,
    sobre, parametros_* na ordem certa.
    """
    tabela_base = _find_table(root, f"{prefixo}1")
    tabelas = [tabela_base]
    ultima = tabela_base
    for i in range(2, quantidade + 1):
        clone = copy.deepcopy(tabela_base)
        _renomeia_ids_controles(clone, f"p{i}")
        clone.set(_TABLE_NAME, f"{prefixo}{i}")
        pai = ultima.getparent()
        pai.insert(list(pai).index(ultima) + 1, clone)
        tabelas.append(clone)
        ultima = clone
    return tabelas


def write(identificacao: Identificacao, perimetros: list[Perimetro], template_bytes: bytes) -> bytes:
    """Grava identificação + N parcelas (perimetro_1..N) no modelo oficial.

    Assinatura difere do `ods_writer.write(dados) -> bytes` do plano: aqui
    o template_loader (único módulo de core/ que pode importar streamlit)
    fica de fora deste arquivo, então quem chama write() precisa passar os
    bytes do template já carregados.
    """
    if not perimetros:
        raise ValueError("é preciso pelo menos 1 parcela (perimetro_1)")

    cell_map = _carregar_cell_map()
    dominios = _carregar_dominios()

    root = etree.fromstring(_content_xml_de(template_bytes))

    tabela_ident = _find_table(root, cell_map["identificacao"]["aba"])
    _escreve_identificacao(tabela_ident, identificacao, cell_map["identificacao"])

    tabelas_perimetro = _clonar_abas_perimetro(
        root, cell_map["perimetro"]["aba_prefixo"], len(perimetros)
    )
    for tabela, perimetro in zip(tabelas_perimetro, perimetros):
        _escreve_perimetro(tabela, perimetro, cell_map["perimetro"], dominios)

    content_xml = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
    return _reescreve_zip(template_bytes, content_xml)


def _escreve_identificacao(tabela: etree._Element, dados: Identificacao, mapa: dict) -> None:
    campos = mapa["campos"]
    valores = dados.model_dump()
    for campo, endereco in campos.items():
        col_letras = "".join(c for c in endereco if c.isalpha())
        linha = int("".join(c for c in endereco if c.isdigit()))
        cell = _get_editable_cell(tabela, linha, col_letras)
        _set_texto(cell, str(valores.get(campo, "")))


def _escreve_perimetro(tabela: etree._Element, dados: Perimetro, mapa: dict, dominios: dict) -> None:
    campos = mapa["campos"]
    casas = dominios["limites_coordenadas"]

    valores_simples = {
        "denominacao": dados.denominacao,
        "parcela_numero": dados.parcela_numero,
        "lado": dados.lado,
        "tipo_coordenada": dados.tipo_coordenada,
        "hemisferio": dados.hemisferio,
    }
    for campo, endereco in campos.items():
        if campo == "meridiano_central":
            continue
        col_letras = "".join(c for c in endereco if c.isalpha())
        linha = int("".join(c for c in endereco if c.isdigit()))
        cell = _get_editable_cell(tabela, linha, col_letras)
        _set_texto(cell, valores_simples.get(campo, ""))

    if dados.meridiano_central is not None:
        endereco = campos["meridiano_central"]
        col_letras = "".join(c for c in endereco if c.isalpha())
        linha = int("".join(c for c in endereco if c.isdigit()))
        cell = _get_editable_cell(tabela, linha, col_letras)
        _set_texto(cell, _fmt_livre(dados.meridiano_central))

    colunas = mapa["tabela_vertices"]["colunas"]
    linha_inicial = mapa["tabela_vertices"]["linha_inicial"]
    linha_final_maxima = mapa["tabela_vertices"]["linha_final_maxima"]

    if dados.vertices:
        _garantir_linhas_vertice(
            tabela, linha_final_maxima, linha_inicial + len(dados.vertices) - 1
        )

    for i, vertice in enumerate(dados.vertices):
        linha = linha_inicial + i

        # Vertice.e_long/n_lat são sempre grau decimal geodésico — digitado
        # à mão (core/parsing.parse_coordenada) ou já convertido de UTM na
        # importação (core/geo.py) — então a tabela de vértices sempre sai
        # em GMS, mesmo quando "Tipo de Coordenada" (metadado do serviço,
        # célula à parte) diz "UTM": esse campo não guarda coordenada, só
        # declara o sistema usado em campo.
        casas_seg = casas["segundos_gms_casas_decimais"]
        e_long_txt = _fmt_geografica(vertice.e_long, "E", "W", casas_seg)
        n_lat_txt = _fmt_geografica(vertice.n_lat, "N", "S", casas_seg)

        # h (altitude elipsoidal) tem 3 casas, diferente do sigma (2) —
        # confirmado numa planilha real preenchida, não só no manual.
        sigma_casas = casas["sigma_casas_decimais"]
        h_casas = casas["h_casas_decimais"]
        valores = {
            "codigo": vertice.codigo,
            "e_long": e_long_txt,
            "sigma_long": _fmt_decimal(vertice.sigma_long, sigma_casas),
            "n_lat": n_lat_txt,
            "sigma_lat": _fmt_decimal(vertice.sigma_lat, sigma_casas),
            "h": _fmt_decimal(vertice.h, h_casas),
            "sigma_h": _fmt_decimal(vertice.sigma_h, sigma_casas),
            "metodo_posicionamento": vertice.metodo_posicionamento,
            "tipo_limite": vertice.tipo_limite,
            "cns": vertice.cns,
            "matricula": vertice.matricula,
            "descritivo": vertice.descritivo,
        }
        for campo, col_letras in colunas.items():
            cell = _get_editable_cell(tabela, linha, col_letras)
            _set_texto(cell, valores[campo])
