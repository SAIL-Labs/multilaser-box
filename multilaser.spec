# PyInstaller spec for the Windows build (one-folder mode).
#
#   pyinstaller multilaser.spec --noconfirm
#
# Output: dist/MultiLaserController/ with MultiLaserController.exe inside.
# Velopack (vpk pack) packs that folder into the installer, the Portable zip
# and the update packages. One-folder (not one-file) starts faster and keeps
# updates small.

NAME = "MultiLaserController"

from PyInstaller.utils.hooks import copy_metadata

# Package metadata so pyvisa/pyvisa-py can report their versions in the
# diagnostics report (they read it via importlib.metadata)
_metadata = []
for _dist in ("pyvisa", "pyvisa-py"):
    try:
        _metadata += copy_metadata(_dist)
    except Exception:
        pass

a = Analysis(
    ["multilaser/laser_controller_gui.py"],
    pathex=["."],
    binaries=[],
    datas=[("figures/icon.ico", "figures")] + _metadata,
    # Imported lazily, so PyInstaller can't see them
    hiddenimports=[
        "velopack",
        "multilaser._update_token",  # only exists if CI writes it (private repo)
        "pyvisa",
        "pyvisa_py",
        "openpyxl",
    ],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=NAME,
    icon="figures/icon.ico",
    console=False,
    upx=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name=NAME,
    upx=False,
)
