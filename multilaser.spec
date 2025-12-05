# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Multi-Laser Controller
This provides more control over the build process than command-line options
"""

block_cipher = None

a = Analysis(
    ['laser_controller_gui.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('laser_ttl_controller/*.ino', 'laser_ttl_controller'),
        ('README.md', '.'),
        ('multilaser_manual.md', '.'),
        ('figures', 'figures'),
    ],
    hiddenimports=[
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'serial',
        'numpy',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'PIL',
        'tkinter',
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
    name='MultiLaserController',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to True for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='figures/icon.ico',  # Windows icon
)

# For macOS app bundle
app = BUNDLE(
    exe,
    name='MultiLaserController.app',
    icon='figures/icon.icns',  # macOS icon
    bundle_identifier='com.multilaser.controller',
    info_plist={
        'NSPrincipalClass': 'NSApplication',
        'NSHighResolutionCapable': 'True',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1.0.0',
    },
)
