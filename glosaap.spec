# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file para Glosaap

Este archivo genera Glosaap.exe y toda la distribución necesaria.
Para compilar: pyinstaller glosaap.spec

IMPORTANTE: Después de compilar Glosaap, también compilar el updater:
    pyinstaller updater.spec
    
Y copiar updater.exe a la carpeta dist/Glosaap/
"""
from PyInstaller.utils.hooks import collect_all

datas = [('assets', 'assets'), ('app', 'app')]
binaries = []
hiddenimports = ['flet', 'pandas', 'openpyxl', 'keyring', 'playwright']
tmp_ret = collect_all('flet')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    [],
    exclude_binaries=True,
    name='Glosaap',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icons/app_logo.ico',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Glosaap',
)
