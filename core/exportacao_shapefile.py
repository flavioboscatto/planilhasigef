"""Exportação do projeto em Shapefile — duas feições, já que um Shapefile
só aceita um tipo de geometria por arquivo: pontos (um por vértice, com
todas as colunas da grade como atributo, mais a área SGL da parcela) e
polígonos (um por parcela). Os dois pares de arquivo (.shp/.shx/.dbf/.prj)
saem zipados num arquivo só.

Coordenadas em SIRGAS2000 geográfico (EPSG:4674) — mesmo datum usado no
resto do app (core/sgl.py, GRS80). Usa pyshp (puro Python, sem GDAL/Fiona)
só pra LER/ESCREVER um arquivo à parte que o usuário pediu — não é o .ods
oficial do SIGEF, então a regra 2 do CLAUDE.md (nunca usar essas libs pra
escrever o modelo oficial) não se aplica aqui.
"""
from __future__ import annotations

import io
import warnings
import zipfile

import shapefile
from pyproj import CRS

from core.models import Perimetro, Vertice
from core.sgl import area_sgl

_PRJ_WKT = CRS.from_epsg(4674).to_wkt("WKT1_ESRI")

# nomes de campo DBF: limite clássico de 10 caracteres
_CAMPOS_PONTOS = [
    ("parcela", "N", 5, 0),
    ("codigo", "C", 20, 0),
    ("tipo", "C", 4, 0),
    ("e_long", "F", 18, 8),
    ("n_lat", "F", 18, 8),
    ("sigma_lon", "F", 12, 3),
    ("sigma_lat", "F", 12, 3),
    ("h", "F", 12, 3),
    ("sigma_h", "F", 12, 3),
    ("metodo", "C", 10, 0),
    ("tipo_lim", "C", 10, 0),
    ("cns", "C", 20, 0),
    ("matricula", "C", 30, 0),
    ("descrit", "C", 254, 0),
    ("area_ha", "F", 18, 4),
]


def _area_ha_segura(vertices: list[Vertice]) -> float | None:
    if len(vertices) < 3:
        return None
    pontos = [(v.n_lat, v.e_long, v.h) for v in vertices]
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # aviso de extensão >50km não importa aqui
            return area_sgl(pontos)["area_ha"]
    except ValueError:
        return None


def _escrever_pontos(perimetros: list[Perimetro]) -> tuple[bytes, bytes, bytes]:
    shp, shx, dbf = io.BytesIO(), io.BytesIO(), io.BytesIO()
    escritor = shapefile.Writer(shp=shp, shx=shx, dbf=dbf, shapeType=shapefile.POINT)
    for nome, tipo, tamanho, decimais in _CAMPOS_PONTOS:
        escritor.field(nome, tipo, tamanho, decimais)

    for indice, perimetro in enumerate(perimetros, start=1):
        vertices = [v for v in perimetro.vertices if v.codigo]
        area_ha = _area_ha_segura(vertices)
        for v in vertices:
            escritor.point(v.e_long, v.n_lat)
            escritor.record(
                parcela=indice,
                codigo=v.codigo,
                tipo=v.tipo_vertice,
                e_long=v.e_long,
                n_lat=v.n_lat,
                sigma_lon=v.sigma_long,
                sigma_lat=v.sigma_lat,
                h=v.h,
                sigma_h=v.sigma_h,
                metodo=v.metodo_posicionamento,
                tipo_lim=v.tipo_limite,
                cns=v.cns,
                matricula=v.matricula,
                descrit=v.descritivo,
                area_ha=area_ha,
            )
    escritor.close()
    return shp.getvalue(), shx.getvalue(), dbf.getvalue()


def _escrever_poligonos(perimetros: list[Perimetro]) -> tuple[bytes, bytes, bytes]:
    shp, shx, dbf = io.BytesIO(), io.BytesIO(), io.BytesIO()
    escritor = shapefile.Writer(shp=shp, shx=shx, dbf=dbf, shapeType=shapefile.POLYGON)
    escritor.field("parcela", "N", 5, 0)
    escritor.field("denominac", "C", 60, 0)
    escritor.field("area_ha", "F", 18, 4)

    for indice, perimetro in enumerate(perimetros, start=1):
        vertices = [v for v in perimetro.vertices if v.codigo]
        if len(vertices) < 3:
            continue
        anel = [[v.e_long, v.n_lat] for v in vertices]
        anel.append(anel[0])
        escritor.poly([anel])
        escritor.record(parcela=indice, denominac=perimetro.denominacao, area_ha=_area_ha_segura(vertices))
    escritor.close()
    return shp.getvalue(), shx.getvalue(), dbf.getvalue()


def gerar_shapefile_zip(perimetros: list[Perimetro]) -> bytes:
    shp_p, shx_p, dbf_p = _escrever_pontos(perimetros)
    shp_g, shx_g, dbf_g = _escrever_poligonos(perimetros)

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("vertices.shp", shp_p)
        zf.writestr("vertices.shx", shx_p)
        zf.writestr("vertices.dbf", dbf_p)
        zf.writestr("vertices.prj", _PRJ_WKT)
        zf.writestr("perimetros.shp", shp_g)
        zf.writestr("perimetros.shx", shx_g)
        zf.writestr("perimetros.dbf", dbf_g)
        zf.writestr("perimetros.prj", _PRJ_WKT)
    return buffer.getvalue()
