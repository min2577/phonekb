# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for PhoneKB desktop
# build: pyinstaller phonekb.spec --clean

import os
from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files

block_cipher = None

# Qt must be collected explicitly for the one-file build. In particular this
# keeps the Windows platform plugin (qwindows.dll) and shiboken runtime in the
# bundle even when PyInstaller cannot infer every import from the entry point.
qt_datas, qt_binaries, qt_hidden = [], [], []
for package in ('PySide6', 'shiboken6'):
    package_datas, package_binaries, package_hidden = collect_all(package)
    qt_datas += package_datas
    qt_binaries += package_binaries
    qt_hidden += package_hidden

# 收集 winrt 全部子模块（PyInstaller 默认会漏一些 .pyc / 元数据）
winrt_hidden = collect_submodules('winrt')

# 收集 winrt 包的元数据
winrt_datas = collect_data_files('winrt')

a = Analysis(
    ['main.py'],
    pathex=[os.getcwd()],
    binaries=qt_binaries,
    datas=[
        ('presets', 'presets'),  # 布局预设 json
        # 编辑器页面已重写为原生 Qt 控件，不再需要把 gamepad_editor/ 目录打包。
        # 若以后再次需要外部 HTTP 入口，再打开下行：
        # ('gamepad_editor', 'gamepad_editor'),  # 本机手柄布局编辑器
    ] + winrt_datas + qt_datas,
    hiddenimports=[
        'winrt.windows.devices.bluetooth',
        'winrt.windows.devices.bluetooth.advertisement',
        'winrt.windows.devices.bluetooth.genericattributeprofile',
        'winrt.windows.storage.streams',
        'winrt.windows.foundation',
        'winrt.windows.foundation.collections',
        'websockets.asyncio.server',
        'websockets.asyncio.client',
        'qrcode.image.pil',
        'serial',
        'serial.tools.list_ports',
        'serial.tools.list_ports_windows',
    ] + winrt_hidden + qt_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'numpy', 'pandas', 'scipy',
        'tkinter.test', 'unittest', 'pydoc', 'doctest',
        'pytest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='PhoneKB',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='phonekb.ico' if os.path.exists('phonekb.ico') else None,
)
