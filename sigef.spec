# -*- mode: python ; coding: utf-8 -*-
# Empacotamento do Gerador de Planilha SIGEF como app local (.exe).
# Build: pyinstaller sigef.spec --noconfirm
#
# Modo --onedir (pasta com o .exe + arquivos de apoio), não --onefile: mais
# fácil de depurar problema de arquivo faltando (onefile some tudo dentro de
# um zip que só se abre em tempo de execução, num diretório temporário).
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = []

# streamlit precisa dos próprios arquivos estáticos (HTML/JS/CSS) e de
# metadata de pacote instalado (importlib.metadata) pra funcionar; pyproj
# precisa do banco proj.db; shapely/lxml têm extensão compilada. collect_all
# cobre os três (código + dados + binário) de uma vez. pandas fica de fora
# desta lista de propósito: collect_all nele arrasta a suíte de testes
# inteira e, por tabela, o backend opcional de gráfico (matplotlib/PyQt6/
# scipy) que nunca usamos — a análise estática normal do PyInstaller já
# resolve o que realmente é importado por streamlit/nosso código.
for pacote in ("streamlit", "pyproj", "shapely", "lxml", "pydantic"):
    d, b, h = collect_all(pacote)
    datas += d
    binaries += b
    hiddenimports += h

# nunca usados por este app — sem isto, o hook de pandas puxa esse backend
# de gráfico opcional de qualquer jeito e o build fica gigante à toa.
excludes = [
    "matplotlib",
    "PyQt5",
    "PyQt6",
    "PySide2",
    "PySide6",
    "scipy",
    "IPython",
    "pandas.tests",
    "pytest",
    "notebook",
    "jupyter",
]

# nosso próprio código e dados, preservando a árvore de diretórios — são
# lidos como arquivo comum (não passam pela análise estática do
# PyInstaller), então main_exe.py bota a raiz do pacote em sys.path pra
# eles serem importados normalmente em tempo de execução.
datas += [
    ("app.py", "."),
    ("dialogo_arquivo.py", "."),
    ("core", "core"),
    ("ui", "ui"),
    ("importers", "importers"),
    ("config", "config"),
    ("templates", "templates"),
]

a = Analysis(
    ["main_exe.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SigefWeb",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,  # mantém o console aberto por enquanto para ver erro; tirar depois de validar
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="SigefWeb",
)
