# -*- mode: python ; coding: utf-8 -*-
# Empacotamento da versão desktop nativo (PySide6) do Gerador de Planilha
# SIGEF. Build: pyinstaller sigef_qt.spec --noconfirm
#
# Mais simples que sigef.spec (Streamlit): app_qt.py é o próprio entrypoint
# analisado pelo PyInstaller, então core/ e ui_qt/ são rastreados e
# compilados automaticamente pelo grafo de import — não precisam entrar
# como `datas` cru feito no sigef.spec antigo (aquele existia porque
# Streamlit roda app.py como arquivo externo via `streamlit run`, não como
# entrypoint direto). Só os arquivos NÃO-Python lidos em tempo de execução
# (config/, templates/) precisam ser adicionados como dados.
from PyInstaller.utils.hooks import collect_all

datas = [
    ("config", "config"),
    ("templates", "templates"),
]
binaries = []
hiddenimports = []

# pyproj precisa do banco proj.db; shapely/lxml/pydantic têm extensão
# compilada. PySide6 fica de fora desta lista de propósito: o hook nativo
# do PyInstaller pra PySide6 já detecta e empacota só os módulos Qt
# realmente importados (widgets/core/gui) — um collect_all aqui traria
# WebEngine, Multimedia, 3D etc. que este app nunca usa.
for pacote in ("pyproj", "shapely", "lxml", "pydantic"):
    d, b, h = collect_all(pacote)
    datas += d
    binaries += b
    hiddenimports += h

# nunca usados por este app — mesmo motivo do sigef.spec antigo: sem isto
# o hook de pandas puxa esse backend de gráfico opcional à toa.
excludes = [
    "matplotlib",
    "PyQt5",
    "PyQt6",
    "PySide2",
    "scipy",
    "IPython",
    "pandas.tests",
    "pytest",
    "pytestqt",
    "notebook",
    "jupyter",
    "streamlit",
]

a = Analysis(
    ["app_qt.py"],
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
    name="SigefWebQt",
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
    name="SigefWebQt",
)
