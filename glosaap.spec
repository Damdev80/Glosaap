# -*- mode: python ; coding: utf-8 -*-
import os

# Obtener rutas absolutas
project_dir = os.path.abspath('.')
assets_dir = os.path.join(project_dir, 'assets')

# Configurar variable de entorno para Playwright
# Esto hace que Playwright use navegadores del sistema en AppData
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = os.path.join(
    os.getenv('APPDATA'), 'Glosaap', 'browsers'
)

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        (assets_dir, 'assets'),  # Incluir carpeta assets
    ],
    hiddenimports=[
        'playwright',
        'playwright.sync_api',
        'playwright._impl._driver',
        'openpyxl',
        'pandas',
        'flet',
        'app',
        'app.service',
        'app.service.web_scraper',
        'app.service.web_scraper.fomag_scraper',
        'app.service.web_scraper.base_scraper',
        'app.service.credential_manager',
        'app.service.attachment_service',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Glosaap',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
