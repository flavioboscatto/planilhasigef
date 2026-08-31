"""Ponto de entrada do .exe empacotado (PyInstaller) — não é o app em si
(isso é app.py, rodado pelo Streamlit dentro deste mesmo processo). Dois
papéis, dependendo do argv:

1. Sem argumentos (clique duplo no .exe): sobe o servidor Streamlit
   apontando pra app.py e abre o navegador — é o "clique e usa".
2. Com --dialogo-arquivo <modo> [args]: não sobe o Streamlit, só roda o
   diálogo nativo de arquivo (dialogo_arquivo.py) e sai. ui/projeto.py
   reinvoca o próprio .exe nesse modo porque, dentro do pacote, não existe
   um "python.exe" separado pra rodar dialogo_arquivo.py como subprocesso
   igual acontece em modo desenvolvimento (ver ui/projeto.py::_rodar_dialogo)
   — dentro do .exe, ele mesmo assume esse papel quando chamado assim.
"""
from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
sys.path.insert(0, str(BASE_DIR))


def _rodar_dialogo_e_sair() -> None:
    from dialogo_arquivo import escolher_caminho

    print(escolher_caminho(sys.argv[2:]))
    sys.exit(0)


def _subir_app() -> None:
    from streamlit.web import cli as stcli

    sys.argv = [
        "streamlit",
        "run",
        str(BASE_DIR / "app.py"),
        "--server.headless=false",
        "--global.developmentMode=false",
    ]
    sys.exit(stcli.main())


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--dialogo-arquivo":
        _rodar_dialogo_e_sair()
    else:
        _subir_app()
