"""Preferências do app fora do projeto (.sigefproj) — a lista de projetos
recentes, pra tela de abertura (ui_qt/boas_vindas_dialog.py), e o tema
(Claro/Escuro/Automático).

`QSettings`, não um arquivo em config/: aquela pasta é domínio normativo
(cell_map, dominios, tema), não estado de uso do programa. E não entra em
core/ (que não importa PySide6).

Caminho de arquivo não é dado pessoal (CPF/nome/matrícula — regra 6 do
CLAUDE.md): guardar os últimos .sigefproj abertos é preferência de app, do
mesmo tipo que "lembrar a última aba aberta" (ui_qt/projeto_qt.py).
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings

_ORGANIZACAO = "IFSC"
_APLICATIVO = "PlanSIGEF"
_CHAVE_RECENTES = "projetos_recentes"
_MAXIMO_RECENTES = 5


def _settings() -> QSettings:
    # ponto único de acesso ao QSettings: tests/conftest.py o redireciona pra
    # um .ini temporário (o construtor (organização, aplicativo) ignora
    # QSettings.setDefaultFormat, então os testes vazavam no registro real)
    return QSettings(_ORGANIZACAO, _APLICATIVO)


def obter_recentes() -> list[str]:
    settings = _settings()
    valores = settings.value(_CHAVE_RECENTES, [])
    if isinstance(valores, str):
        valores = [valores]
    return [caminho for caminho in valores if Path(caminho).exists()]


_CHAVE_TEMA = "tema"
_TEMAS_VALIDOS = ("automatico", "claro", "escuro")


def obter_tema() -> str:
    # valor desconhecido (chave corrompida/versão futura) cai no Automático
    valor = _settings().value(_CHAVE_TEMA, "automatico")
    return valor if valor in _TEMAS_VALIDOS else "automatico"


def salvar_tema(tema: str) -> None:
    if tema in _TEMAS_VALIDOS:
        _settings().setValue(_CHAVE_TEMA, tema)


def registrar_recente(caminho: str) -> None:
    settings = _settings()
    recentes = [caminho] + [c for c in obter_recentes() if c != caminho]
    settings.setValue(_CHAVE_RECENTES, recentes[:_MAXIMO_RECENTES])
