"""Modelo de dados do formulário SIGEF. Sem streamlit, sem regra de negócio
ainda (Etapa 3) — só a forma dos dados que a UI coleta e o ods_writer grava.
"""
from __future__ import annotations

from pydantic import BaseModel


class Identificacao(BaseModel):
    natureza_servico: str = ""
    tipo_pessoa: str = ""
    nome: str = ""
    cpf_cnpj: str = ""
    denominacao_area: str = ""
    situacao: str = ""
    natureza_area: str = ""
    codigo_imovel_sncr: str = ""
    codigo_cartorio_cns: str = ""
    matricula: str = ""
    municipio_1: str = ""


class Vertice(BaseModel):
    codigo: str = ""
    # tipo do vértice (M/P/V, config/dominios.json) — não tem célula própria
    # no modelo ODS (só existe o "codigo" final), mas fica aqui porque é
    # dado de domínio, não detalhe de UI: a ferramenta de renumeração usa
    # este campo pra compor o codigo, e a validação futura do padrão
    # CCCC-T-NNN também vai precisar dele.
    tipo_vertice: str = ""
    e_long: float = 0.0
    sigma_long: float = 0.0
    n_lat: float = 0.0
    sigma_lat: float = 0.0
    h: float = 0.0
    sigma_h: float = 0.0
    metodo_posicionamento: str = ""
    # tipo de limite do segmento de vante (para o próximo vértice) — a
    # convenção do vértice de ré descrever o limite de vante é do SIGEF,
    # não uma escolha deste código (ver CLAUDE.md)
    tipo_limite: str = ""
    cns: str = ""
    matricula: str = ""
    descritivo: str = ""


class Perimetro(BaseModel):
    denominacao: str = ""
    parcela_numero: str = ""
    lado: str = "Externo"
    tipo_coordenada: str = "Geográfica"
    meridiano_central: float | None = None
    hemisferio: str = "Norte"
    vertices: list[Vertice] = []
