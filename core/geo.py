"""Conversão UTM -> Geodésica para importação de arquivo de campo (Etapa 6).

A planilha do SIGEF sempre grava em geodésica (CLAUDE.md); quando o arquivo
importado vem em UTM, converte-se uma vez aqui, na entrada, e o resto do
app (grade, gravador) nunca lida com UTM. Sem streamlit (regra de fronteira
de core/).

pyproj (já em requirements.txt / arquitetura do CLAUDE.md) em vez de
reimplementar as fórmulas de Gauss-Krüger: zona UTM derivada do Meridiano
Central já escolhido na aba Perímetro, mesma convenção do INCRA
(zona = (meridiano_central + 183) / 6). Datum SIRGAS2000 (EPSG:4674),
padrão brasileiro para georreferenciamento.
"""
from __future__ import annotations

import pyproj

_GEODESICA = pyproj.CRS.from_epsg(4674)  # SIRGAS2000 geográfico


def _crs_utm(meridiano_central: float, hemisferio: str) -> pyproj.CRS:
    zona = round((meridiano_central + 183) / 6)
    sul = " +south" if hemisferio == "Sul" else ""
    return pyproj.CRS.from_proj4(f"+proj=utm +zone={zona}{sul} +ellps=GRS80 +units=m +no_defs")


def utm_para_geodesica(
    easting: float, northing: float, meridiano_central: float, hemisferio: str
) -> tuple[float, float]:
    """Devolve (longitude, latitude) em grau decimal, SIRGAS2000."""
    transformador = pyproj.Transformer.from_crs(
        _crs_utm(meridiano_central, hemisferio), _GEODESICA, always_xy=True
    )
    longitude, latitude = transformador.transform(easting, northing)
    return longitude, latitude
