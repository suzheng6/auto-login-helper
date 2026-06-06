# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = ['tgcrypto', 'keyboard', 'bs4']

# telethon / tgcrypto 需要完整收集，确保运行时不缺子模块
for _pkg in ('telethon', 'tgcrypto'):
    _d, _b, _h = collect_all(_pkg)
    datas += _d
    binaries += _b
    hiddenimports += _h


a = Analysis(
    ['自动登录小帮手.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # 主程序不直接使用 opentele（tdata 转换交给 sync_tdata.exe 子进程），
    # 排除以减小体积；其余为无关大库。
    excludes=[
        'opentele', 'matplotlib', 'numpy', 'pandas', 'scipy',
        'tkinter', 'PyQt5.QtWebEngineWidgets', 'PyQt5.QtBluetooth',
        'PyQt5.QtMultimedia', 'PyQt5.QtQml', 'PyQt5.QtQuick',
    ],
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
    name='AutoLoginHelper',
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
