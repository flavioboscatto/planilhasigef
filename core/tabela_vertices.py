"""Conversão entre a tabela de vértices (DataFrame, uma linha por vértice)
e Vertice (core/models.py) — compartilhado por qualquer camada de UI que
precise ler/escrever a grade (Streamlit em ui/aba_perimetro.py tem uma
cópia própria destas mesmas funções, feita antes deste módulo existir;
ui_qt usa esta versão). Sem framework nenhum aqui (CLAUDE.md).
"""
from __future__ import annotations

import pandas as pd

from core.models import Vertice
from core.parsing import ValorInvalidoError, normaliza_decimal, parse_coordenada, parse_numero

COLUNAS_VERTICE = [
    "renumerar",
    "tipo_vertice",
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


def tabela_vazia(n_linhas: int = 3) -> pd.DataFrame:
    # "renumerar" nasce marcado: uma parcela nova é presumidamente toda do
    # profissional que está preenchendo agora.
    linha_padrao = {c: "" for c in COLUNAS_VERTICE}
    linha_padrao["renumerar"] = True
    return pd.DataFrame([dict(linha_padrao) for _ in range(n_linhas)])


def preenchido(valor) -> bool:
    """False pra None/NaN/"" — uma linha nova em branco chega como NaN,
    não string vazia; str(nan) daria 'nan', que não é vazio pro Python."""
    if valor is None:
        return False
    texto = str(valor).strip()
    return bool(texto) and texto.lower() != "nan"


def _txt(valor) -> str:
    return str(valor).strip() if preenchido(valor) else ""


def linha_para_vertice(linha) -> Vertice:
    def num(campo: str) -> float:
        try:
            return parse_numero(_txt(linha[campo]))
        except ValorInvalidoError:
            return 0.0

    def coord(campo: str) -> float:
        try:
            return parse_coordenada(_txt(linha[campo]))
        except ValorInvalidoError:
            return 0.0

    return Vertice(
        codigo=_txt(linha["codigo"]),
        tipo_vertice=_txt(linha["tipo_vertice"]),
        e_long=coord("e_long"),
        sigma_long=num("sigma_long"),
        n_lat=coord("n_lat"),
        sigma_lat=num("sigma_lat"),
        h=num("h"),
        sigma_h=num("sigma_h"),
        metodo_posicionamento=_txt(linha["metodo_posicionamento"]),
        tipo_limite=_txt(linha["tipo_limite"]),
        cns=_txt(linha["cns"]),
        matricula=_txt(linha["matricula"]),
        descritivo=_txt(linha["descritivo"]),
    )


def vertice_para_linha(v: Vertice) -> dict:
    # texto com vírgula (normaliza_decimal), não o float cru: a grade
    # inteira assume que toda célula é texto (é assim que preenchido()/
    # parse_* funcionam) — devolver float aqui deixava a coluna com tipo
    # misto depois de operações como Reorganizar, e uma edição posterior
    # naquela célula podia se perder.
    def num_txt(valor: float) -> str:
        return normaliza_decimal(str(valor))

    return {
        "codigo": v.codigo,
        "tipo_vertice": v.tipo_vertice,
        "e_long": num_txt(v.e_long),
        "sigma_long": num_txt(v.sigma_long),
        "n_lat": num_txt(v.n_lat),
        "sigma_lat": num_txt(v.sigma_lat),
        "h": num_txt(v.h),
        "sigma_h": num_txt(v.sigma_h),
        "metodo_posicionamento": v.metodo_posicionamento,
        "tipo_limite": v.tipo_limite,
        "cns": v.cns,
        "matricula": v.matricula,
        "descritivo": v.descritivo,
    }
