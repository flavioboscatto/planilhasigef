"""Conversão tolerante de texto digitado/colado/importado para número.

Usado pela grade de vértices (Etapa 4) e vai ser reaproveitado pelos
importadores (Etapa 6) — o mesmo texto solto que um profissional digita ou
cola de uma planilha pode vir com vírgula ou ponto decimal, e coordenada
geográfica pode vir em graus decimais ou em GMS com espaço.
"""
from __future__ import annotations

import re

_GMS_RE = re.compile(
    r"^\s*(-?\d+)[°\s]+(\d+)['\s]+(\d+(?:[.,]\d+)?)\"?\s*([NSEWnsew])?\s*$"
)


class ValorInvalidoError(ValueError):
    """Texto não reconhecido como número nem como GMS."""


def parse_numero(texto: str) -> float:
    """Aceita vírgula ou ponto decimal, espaços e separador de milhar."""
    texto = str(texto).strip()
    if not texto:
        return 0.0
    limpo = texto.replace(" ", "")
    if "," in limpo and "." in limpo:
        # padrão brasileiro com separador de milhar: 1.234,56
        limpo = limpo.replace(".", "").replace(",", ".")
    else:
        limpo = limpo.replace(",", ".")
    try:
        return float(limpo)
    except ValueError as exc:
        raise ValorInvalidoError(f"'{texto}' não é um número válido") from exc


def normaliza_decimal(texto: str) -> str:
    """Ponto decimal vira vírgula — regra do SIGEF é vírgula sempre, na
    grade e no arquivo final. Só troca ponto entre dígitos (evita mexer em
    outras coisas, tipo o próprio sufixo de hemisfério ou texto livre).
    Usado logo depois de digitar/colar/importar, antes mesmo de gerar o
    arquivo — assim a grade já mostra vírgula, não só o .ods final.
    """
    return re.sub(r"(?<=\d)\.(?=\d)", ",", str(texto))


def parse_geodesica_compacta(texto: str) -> float:
    """Formato compactado GG,MMSS[frac] de outros programas de campo (ex.:
    '-27,3030' = -27°30'30"). A vírgula aqui separa graus do bloco
    minutos+segundos — não é separador decimal. Sinal por '-' à esquerda ou
    sufixo de hemisfério (S/W nega, N/E não muda).
    """
    texto = str(texto).strip()
    if not texto:
        return 0.0
    bruto = texto.upper()
    negativo = bruto.startswith("-")
    if bruto[-1:] in ("S", "W"):
        negativo = True
    corpo = bruto.strip("+-").rstrip("NSEW").strip()
    if "," not in corpo:
        raise ValorInvalidoError(
            f"'{texto}' não está no formato compactado GG,MMSS (ex.: -27,3030)"
        )
    graus_str, bloco = (parte.strip() for parte in corpo.split(",", 1))
    if not graus_str.isdigit() or not bloco.isdigit():
        raise ValorInvalidoError(
            f"'{texto}' não está no formato compactado GG,MMSS (ex.: -27,3030)"
        )
    minutos = float(bloco[:2]) if bloco[:2] else 0.0
    resto = bloco[2:]
    if not resto:
        segundos = 0.0
    elif len(resto) <= 2:
        segundos = float(resto)
    else:
        segundos = float(f"{resto[:2]}.{resto[2:]}")
    valor = float(graus_str) + minutos / 60.0 + segundos / 3600.0
    return -valor if negativo else valor


def formatar_cpf_cnpj(bruto: str) -> str:
    """Máscara progressiva: só dígitos entram, pontuação é reconstruída —
    até 11 dígitos vira CPF (000.000.000-00), 12 a 14 vira CNPJ
    (00.000.000/0000-00). Cola de fora com pontuação e o número (com
    excesso de dígito) funciona igual: os dígitos são extraídos primeiro.
    """
    digitos = "".join(c for c in str(bruto) if c.isdigit())[:14]
    if len(digitos) <= 11:
        saida = digitos[:3]
        if len(digitos) > 3:
            saida += "." + digitos[3:6]
        if len(digitos) > 6:
            saida += "." + digitos[6:9]
        if len(digitos) > 9:
            saida += "-" + digitos[9:11]
        return saida
    saida = digitos[:2]
    saida += "." + digitos[2:5]
    if len(digitos) > 5:
        saida += "." + digitos[5:8]
    if len(digitos) > 8:
        saida += "/" + digitos[8:12]
    if len(digitos) > 12:
        saida += "-" + digitos[12:14]
    return saida


def parse_coordenada(texto: str) -> float:
    """Aceita grau decimal ('-48,548') ou GMS ('48 32 52,8 W').

    Sufixo S ou W torna o resultado negativo; N ou E, positivo. Sem
    sufixo, o sinal já digitado no valor é respeitado.
    """
    texto = str(texto).strip()
    if not texto:
        return 0.0
    m = _GMS_RE.match(texto)
    if not m:
        return parse_numero(texto)
    graus, minutos, segundos, sufixo = m.groups()
    valor = abs(int(graus)) + int(minutos) / 60 + parse_numero(segundos) / 3600
    negativo = int(graus) < 0 or (sufixo or "").upper() in ("S", "W")
    return -valor if negativo else valor
