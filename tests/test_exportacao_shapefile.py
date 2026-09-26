"""Testes de core/exportacao_shapefile.py — duas feições (pontos e
polígonos), zipadas junto. Pontos carregam todas as colunas da grade como
atributo mais a área SGL da parcela."""
from __future__ import annotations

import io
import zipfile

import shapefile

from core.exportacao_shapefile import gerar_shapefile_zip
from core.models import Perimetro, Vertice


def _v(codigo: str, e_long: float, n_lat: float, **kw) -> Vertice:
    return Vertice(codigo=codigo, e_long=e_long, n_lat=n_lat, **kw)


_TRIANGULO = [_v("A", -48.5, -27.5), _v("B", -48.4, -27.5), _v("C", -48.4, -27.4)]


def _abrir_zip(zbytes: bytes) -> zipfile.ZipFile:
    return zipfile.ZipFile(io.BytesIO(zbytes))


def test_zip_contem_os_8_arquivos_esperados():
    saida = gerar_shapefile_zip([Perimetro(vertices=_TRIANGULO)])

    nomes = set(_abrir_zip(saida).namelist())

    assert nomes == {
        "vertices.shp", "vertices.shx", "vertices.dbf", "vertices.prj",
        "perimetros.shp", "perimetros.shx", "perimetros.dbf", "perimetros.prj",
    }


def test_arquivo_de_pontos_tem_um_ponto_por_vertice_com_atributos():
    perimetro = Perimetro(
        vertices=[
            _v("AJ4-M-001", -48.5, -27.5, tipo_vertice="M", metodo_posicionamento="PG1",
               tipo_limite="LA1", matricula="123", descritivo="marco de concreto"),
            *_TRIANGULO[1:],
        ]
    )
    zf = _abrir_zip(gerar_shapefile_zip([perimetro]))

    leitor = shapefile.Reader(shp=io.BytesIO(zf.read("vertices.shp")), dbf=io.BytesIO(zf.read("vertices.dbf")))

    assert len(leitor.shapes()) == 3
    campos = [c[0] for c in leitor.fields[1:]]
    registro = dict(zip(campos, leitor.records()[0]))
    assert registro["codigo"] == "AJ4-M-001"
    assert registro["tipo"] == "M"
    assert registro["metodo"] == "PG1"
    assert registro["tipo_lim"] == "LA1"
    assert registro["matricula"] == "123"
    assert registro["descrit"] == "marco de concreto"
    assert leitor.shapes()[0].points[0] == (-48.5, -27.5)


def test_arquivo_de_pontos_tem_atributo_de_area_sgl():
    zf = _abrir_zip(gerar_shapefile_zip([Perimetro(vertices=_TRIANGULO)]))

    leitor = shapefile.Reader(shp=io.BytesIO(zf.read("vertices.shp")), dbf=io.BytesIO(zf.read("vertices.dbf")))
    campos = [c[0] for c in leitor.fields[1:]]
    registro = dict(zip(campos, leitor.records()[0]))

    assert registro["area_ha"] > 0


def test_menos_de_3_vertices_nao_gera_poligono_mas_gera_pontos():
    zf = _abrir_zip(gerar_shapefile_zip([Perimetro(vertices=_TRIANGULO[:2])]))

    pontos = shapefile.Reader(shp=io.BytesIO(zf.read("vertices.shp")), dbf=io.BytesIO(zf.read("vertices.dbf")))
    # .shx também, pra este caso de 0 feições — sem shx, o próprio leitor do
    # pyshp tromba (UnboundLocalError) tentando contar shapes até o fim do
    # arquivo quando não há shape nenhum.
    poligonos = shapefile.Reader(
        shp=io.BytesIO(zf.read("perimetros.shp")),
        shx=io.BytesIO(zf.read("perimetros.shx")),
        dbf=io.BytesIO(zf.read("perimetros.dbf")),
    )

    assert len(pontos.shapes()) == 2
    assert len(poligonos.shapes()) == 0


def test_multiplas_parcelas_geram_multiplos_poligonos_numerados():
    p1 = Perimetro(denominacao="Parte 1", vertices=_TRIANGULO)
    p2 = Perimetro(denominacao="Parte 2", vertices=_TRIANGULO)
    zf = _abrir_zip(gerar_shapefile_zip([p1, p2]))

    leitor = shapefile.Reader(shp=io.BytesIO(zf.read("perimetros.shp")), dbf=io.BytesIO(zf.read("perimetros.dbf")))
    campos = [c[0] for c in leitor.fields[1:]]
    registros = [dict(zip(campos, r)) for r in leitor.records()]

    assert len(leitor.shapes()) == 2
    assert {r["parcela"] for r in registros} == {1, 2}
    assert {r["denominac"] for r in registros} == {"Parte 1", "Parte 2"}


def test_prj_declara_sirgas2000():
    zf = _abrir_zip(gerar_shapefile_zip([Perimetro(vertices=_TRIANGULO)]))

    prj = zf.read("vertices.prj").decode("ascii")

    assert "SIRGAS" in prj
