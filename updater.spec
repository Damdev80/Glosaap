# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file para Glosaap Updater

Este archivo genera updater.exe, un ejecutable independiente
que se encarga de instalar las actualizaciones de Glosaap.

Uso:
    pyinstaller updater.spec

El ejecutable generado debe copiarse a la carpeta de distribución
junto con Glosaap.exe
"""

a = Analysis(
    ['updater.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Excluir módulos innecesarios para reducir tamaño
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'PIL',
        'scipy',
        'pytest',
        'unittest',
    ],
    noarchive=False,
    optimize=2,  # Optimización máxima
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='updater',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Comprimir con UPX
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Sin ventana de consola
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
