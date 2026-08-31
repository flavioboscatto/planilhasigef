"""Script auxiliar rodado como subprocesso à parte para abrir diálogos
nativos de arquivo — tkinter exige rodar na thread principal do processo, e
o Streamlit roda o script de cada sessão numa thread própria (não a
principal), então chamar tk.Tk() direto do app dava diálogo instável. Rodar
isto num processo separado elimina o problema: nasce com sua própria thread
principal.

Chamado por ui/projeto.py::_rodar_dialogo — nunca importado diretamente.
No .exe empacotado (PyInstaller), quem chama este código é main_exe.py,
reinvocando o próprio executável com --dialogo-arquivo (não existe um
"python.exe" à parte pra rodar; ver main_exe.py).

Uso: python dialogo_arquivo.py salvar-como <nome_sugerido>
     python dialogo_arquivo.py abrir
Imprime o caminho escolhido no stdout (vazio se cancelado).
"""
from __future__ import annotations

import sys
import tkinter as tk
from tkinter import filedialog


def escolher_caminho(argv: list[str]) -> str:
    modo = argv[0] if argv else ""
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    root.focus_force()

    if modo == "salvar-como":
        nome_sugerido = argv[1] if len(argv) > 1 else "projeto_sigef"
        caminho = filedialog.asksaveasfilename(
            title="Salvar projeto SIGEF como",
            defaultextension=".sigefproj",
            initialfile=nome_sugerido,
            filetypes=[("Projeto SIGEF", "*.sigefproj"), ("Todos os arquivos", "*.*")],
        )
    elif modo == "abrir":
        caminho = filedialog.askopenfilename(
            title="Abrir projeto SIGEF",
            filetypes=[("Projeto SIGEF", "*.sigefproj"), ("Todos os arquivos", "*.*")],
        )
    else:
        caminho = ""

    root.destroy()
    return caminho


if __name__ == "__main__":
    print(escolher_caminho(sys.argv[1:]))
