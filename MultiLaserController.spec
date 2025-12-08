# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['multilaser/laser_controller_gui.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('figures/icon.icns', 'figures'),
        ('laser_ttl_controller/*.ino', 'laser_ttl_controller'),
        ('README.md', '.'),
        ('POWER_METER_GUIDE.md', '.'),
    ],
    hiddenimports=[
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'serial',
        'pyvisa',
        'pyvisa_py',
        'multilaser.laser_controller',
        'multilaser.power_meter_controller',
        'multilaser.power_meter_tab',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'PIL',
        'tkinter',
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MultiLaserController',
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
    icon=['figures/icon.icns'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='MultiLaserController',
)
app = BUNDLE(
    coll,
    name='MultiLaserController.app',
    icon='figures/icon.icns',
    bundle_identifier='com.multilaser.controller',
    info_plist={
        'NSPrincipalClass': 'NSApplication',
        'NSHighResolutionCapable': 'True',
        'CFBundleShortVersionString': '1.1.0',
        'CFBundleVersion': '1.1.0',
    },
)
