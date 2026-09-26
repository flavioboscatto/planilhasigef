"""Exportação do projeto em KML — um <Folder> por parcela (funciona como
camada no Google Earth): um Placemark de polígono (perímetro fechado) e um
Placemark de ponto por vértice, rotulado com o código final da planilha.
Coordenadas geodésicas (Vertice.e_long/n_lat) já são a representação
interna do app, então não precisa converter nada aqui. Sem streamlit, sem
PySide6 (CLAUDE.md, regra de fronteira de core/).
"""
from __future__ import annotations

from xml.dom import minidom
from xml.etree.ElementTree import Element, SubElement, tostring

from core.models import Identificacao, Perimetro

_KML_XMLNS = "http://www.opengis.net/kml/2.2"


def _titulo_parcela(indice: int, perimetro: Perimetro) -> str:
    titulo = f"Parcela {indice}"
    if perimetro.denominacao:
        titulo += f" — {perimetro.denominacao}"
    return titulo


def _coordenadas(vertices: list) -> str:
    return " ".join(f"{v.e_long},{v.n_lat},0" for v in vertices)


def gerar_kml(identificacao: Identificacao, perimetros: list[Perimetro]) -> bytes:
    kml = Element("kml", {"xmlns": _KML_XMLNS})
    documento = SubElement(kml, "Document")
    SubElement(documento, "name").text = identificacao.denominacao_area or "Projeto SIGEF"

    for indice, perimetro in enumerate(perimetros, start=1):
        vertices = [v for v in perimetro.vertices if v.codigo]
        titulo = _titulo_parcela(indice, perimetro)

        pasta = SubElement(documento, "Folder")
        SubElement(pasta, "name").text = titulo

        if len(vertices) >= 3:
            marco_poligono = SubElement(pasta, "Placemark")
            SubElement(marco_poligono, "name").text = f"Perímetro — {titulo}"
            poligono = SubElement(marco_poligono, "Polygon")
            SubElement(poligono, "tessellate").text = "1"
            anel = SubElement(SubElement(poligono, "outerBoundaryIs"), "LinearRing")
            # anel fechado: o último ponto repete o primeiro, exigência do KML
            SubElement(anel, "coordinates").text = _coordenadas(vertices + [vertices[0]])

        for v in vertices:
            marco = SubElement(pasta, "Placemark")
            SubElement(marco, "name").text = v.codigo
            SubElement(SubElement(marco, "Point"), "coordinates").text = f"{v.e_long},{v.n_lat},0"

    bruto = tostring(kml, encoding="utf-8")
    return minidom.parseString(bruto).toprettyxml(indent="  ", encoding="utf-8")
