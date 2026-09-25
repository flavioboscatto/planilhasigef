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
    ("assets", "assets"),
]
binaries = []
hiddenimports = []

# pyproj precisa do banco proj.db; shapely/lxml/pydantic têm extensão
# compilada; openpyxl/odf/xlrd (importers/planilha.py, V5) são os motores
# de leitura de XLSX/ODS/XLS do pandas — o hook padrão às vezes não pega
# tudo que pandas carrega dinamicamente por dentro, coleta explícita evita
# erro só na hora de abrir um arquivo desse formato no .exe empacotado.
# PySide6 fica de fora desta lista de propósito: o hook nativo do
# PyInstaller pra PySide6 já detecta e empacota só os módulos Qt realmente
# importados (widgets/core/gui) — um collect_all aqui traria WebEngine,
# Multimedia, 3D etc. que este app nunca usa.
for pacote in ("pyproj", "shapely", "lxml", "pydantic", "openpyxl", "odf", "xlrd"):
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

# onefile: tudo (binários e dados) entra direto no EXE, sem a pasta
# _internal ao lado — só isso muda de onedir (exclude_binaries=True +
# COLLECT); o Analysis acima é igual. Efeito colateral aceito: o exe
# demora um pouco mais pra abrir, porque se autoextrai numa pasta
# temporária a cada execução.
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="PlanSIGEF",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon="assets/icone_app.ico",
)
