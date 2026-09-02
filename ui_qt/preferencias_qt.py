"""Preferências do app fora do projeto (.sigefproj) — hoje só a lista de
projetos recentes, pra tela de abertura (ui_qt/boas_vindas_dialog.py).

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


def obter_recentes() -> list[str]:
    settings = QSettings(_ORGANIZACAO, _APLICATIVO)
    valores = settings.value(_CHAVE_RECENTES, [])
    if isinstance(valores, str):
        valores = [valores]
    return [caminho for caminho in valores if Path(caminho).exists()]


def registrar_recente(caminho: str) -> None:
    settings = QSettings(_ORGANIZACAO, _APLICATIVO)
    recentes = [caminho] + [c for c in obter_recentes() if c != caminho]
    settings.setValue(_CHAVE_RECENTES, recentes[:_MAXIMO_RECENTES])
