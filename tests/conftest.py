"""Fixtures compartilhadas da suíte."""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _preferencias_isoladas(tmp_path, monkeypatch):
    # os testes de janela salvam tema/recentes: sem isto escreviam no
    # registro REAL do Windows do usuário (um teste que escolhe o tema Claro
    # forçaria o app de verdade a abrir Claro). Importa o módulo só aqui
    # dentro pra não puxar PySide6 em testes de core/.
    from PySide6.QtCore import QSettings

    from ui_qt import preferencias_qt

    caminho = str(tmp_path / "preferencias.ini")
    monkeypatch.setattr(
        preferencias_qt, "_settings", lambda: QSettings(caminho, QSettings.Format.IniFormat)
    )
