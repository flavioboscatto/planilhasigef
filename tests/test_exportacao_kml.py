"""Testes de core/exportacao_kml.py — um Folder por parcela (camada),
polígono fechado + um Placemark de ponto por vértice, rotulado pelo código
final."""
from __future__ import annotations

from xml.etree import ElementTree as ET

from core.exportacao_kml import gerar_kml
from core.models import Identificacao, Perimetro, Vertice

_NS = {"k": "http://www.opengis.net/kml/2.2"}


def _v(codigo: str, e_long: float, n_lat: float) -> Vertice:
    return Vertice(codigo=codigo, e_long=e_long, n_lat=n_lat)


def test_uma_parcela_gera_uma_pasta_com_poligono_e_pontos():
    perimetro = Perimetro(
        denominacao="Parte 1",
        vertices=[_v("A", -48.5, -27.5), _v("B", -48.4, -27.5), _v("C", -48.4, -27.4)],
    )

    saida = gerar_kml(Identificacao(), [perimetro])

    root = ET.fromstring(saida)
    pastas = root.findall(".//k:Folder", _NS)
    assert len(pastas) == 1
    pontos = pastas[0].findall(".//k:Point", _NS)
    assert len(pontos) == 3
    poligonos = pastas[0].findall(".//k:Polygon", _NS)
    assert len(poligonos) == 1


def test_nome_do_placemark_de_ponto_e_o_codigo_final():
    perimetro = Perimetro(vertices=[_v("AJ4-M-001", -48.5, -27.5), _v("AJ4-M-002", -48.4, -27.5), _v("AJ4-M-003", -48.4, -27.4)])

    saida = gerar_kml(Identificacao(), [perimetro])

    root = ET.fromstring(saida)
    nomes = [p.find("k:name", _NS).text for p in root.findall(".//k:Folder/k:Placemark", _NS)]
    assert "AJ4-M-001" in nomes
    assert "AJ4-M-002" in nomes
    assert "AJ4-M-003" in nomes


def test_poligono_fecha_repetindo_o_primeiro_ponto():
    perimetro = Perimetro(vertices=[_v("A", -48.5, -27.5), _v("B", -48.4, -27.5), _v("C", -48.4, -27.4)])

    saida = gerar_kml(Identificacao(), [perimetro])

    root = ET.fromstring(saida)
    coords = root.find(".//k:Polygon//k:coordinates", _NS).text.split()
    assert coords[0] == coords[-1]
    assert len(coords) == 4  # 3 vértices + fecho


def test_menos_de_3_vertices_nao_gera_poligono_mas_gera_pontos():
    perimetro = Perimetro(vertices=[_v("A", -48.5, -27.5), _v("B", -48.4, -27.5)])

    saida = gerar_kml(Identificacao(), [perimetro])

    root = ET.fromstring(saida)
    assert root.findall(".//k:Polygon", _NS) == []
    assert len(root.findall(".//k:Point", _NS)) == 2


def test_multiplas_parcelas_viram_pastas_separadas():
    p1 = Perimetro(denominacao="Parte 1", vertices=[_v("A", -48.5, -27.5), _v("B", -48.4, -27.5), _v("C", -48.4, -27.4)])
    p2 = Perimetro(denominacao="Parte 2", vertices=[_v("D", -47.5, -26.5), _v("E", -47.4, -26.5), _v("F", -47.4, -26.4)])

    saida = gerar_kml(Identificacao(), [p1, p2])

    root = ET.fromstring(saida)
    nomes_pasta = [f.find("k:name", _NS).text for f in root.findall(".//k:Folder", _NS)]
    assert any("Parte 1" in n for n in nomes_pasta)
    assert any("Parte 2" in n for n in nomes_pasta)


def test_nome_do_documento_usa_denominacao_da_area():
    saida = gerar_kml(Identificacao(denominacao_area="Fazenda Santa Rita"), [Perimetro(vertices=[])])

    root = ET.fromstring(saida)
    assert root.find("k:Document/k:name", _NS).text == "Fazenda Santa Rita"
