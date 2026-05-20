# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:\\Users\\rodin\\OneDrive - PEREZ DE REZENDE ADVOCACIA\\Documentos\\Python Scripts\\automação\\assistent-meet\\main.py'],
    pathex=[],
    binaries=[],
    datas=[('C:\\Users\\rodin\\OneDrive - PEREZ DE REZENDE ADVOCACIA\\Documentos\\Python Scripts\\automação\\assistent-meet\\ui', 'ui')],
    hiddenimports=['PySide6.QtSvg'],
    hookspath=['C:\\Users\\rodin\\OneDrive - PEREZ DE REZENDE ADVOCACIA\\Documentos\\Python Scripts\\automação\\assistent-meet\\hooks'],
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
    name='Assistente Meet',
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
    icon=['C:\\Users\\rodin\\OneDrive - PEREZ DE REZENDE ADVOCACIA\\Documentos\\Python Scripts\\automação\\assistent-meet\\build\\assets\\assistente-meet.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Assistente Meet',
)
