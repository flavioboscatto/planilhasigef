"""Formata a tabela de vértices de uma parcela exatamente como sai na
planilha SIGEF final: mesmas colunas, na mesma ordem, com o mesmo GMS/
casas decimais de core/ods_writer.py::_escreve_perimetro (inclusive a
ausência de uma coluna própria para "Tipo" — o tipo do vértice não tem
célula no modelo ODS, só entra composto dentro do código CCCC-T-NNN).

Compartilhado por core/exportacao_txt.py e core/relatorio_docx.py, pra
nunca ficarem descolados um do outro nem da planilha de verdade. Sem
streamlit, sem PySide6 (CLAUDE.md, regra de fronteira de core/).
"""
from __future__ import annotations

from core.models import Perimetro
from core.ods_writer import _fmt_decimal, _fmt_geografica

COLUNAS_OFICIAIS = [
    "codigo",
    "e_long",
    "sigma_long",
    "n_lat",
    "sigma_lat",
    "h",
    "sigma_h",
    "metodo_posicionamento",
    "tipo_limite",
    "cns",
    "matricula",
    "descritivo",
]

ROTULOS_OFICIAIS = {
    "codigo": "Vértice",
    "e_long": "E/Long",
    "sigma_long": "Sigma Long",
    "n_lat": "N/Lat",
    "sigma_lat": "Sigma Lat",
    "h": "h",
    "sigma_h": "Sigma h",
    "metodo_posicionamento": "Met. Posic.",
    "tipo_limite": "Tipo Limite",
    "cns": "CNS",
    "matricula": "Matrícula/Reg.Imóveis",
    "descritivo": "Descritivo",
}


def linhas_formatadas(perimetro: Perimetro, casas: dict) -> list[dict[str, str]]:
    """Uma linha por vértice já preenchido (Perimetro.vertices já vem
    filtrado assim — ver ui_qt/perimetro_tab.py::modelo()), pronta pra
    virar linha de TXT ou de tabela do relatório."""
    casas_seg = casas["segundos_gms_casas_decimais"]
    casas_sigma = casas["sigma_casas_decimais"]
    casas_h = casas["h_casas_decimais"]

    linhas = []
    for vertice in perimetro.vertices:
        linhas.append(
            {
                "codigo": vertice.codigo,
                "e_long": _fmt_geografica(vertice.e_long, "E", "W", casas_seg),
                "sigma_long": _fmt_decimal(vertice.sigma_long, casas_sigma),
                "n_lat": _fmt_geografica(vertice.n_lat, "N", "S", casas_seg),
                "sigma_lat": _fmt_decimal(vertice.sigma_lat, casas_sigma),
                "h": _fmt_decimal(vertice.h, casas_h),
                "sigma_h": _fmt_decimal(vertice.sigma_h, casas_sigma),
                "metodo_posicionamento": vertice.metodo_posicionamento,
                "tipo_limite": vertice.tipo_limite,
                "cns": vertice.cns,
                "matricula": vertice.matricula,
                "descritivo": vertice.descritivo,
            }
        )
    return linhas
