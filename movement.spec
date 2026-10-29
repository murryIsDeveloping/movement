# PyInstaller spec. Build with: python build.py
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

datas = [("models", "models"), ("static", "static")]
datas += collect_data_files("mediapipe")
binaries = collect_dynamic_libs("mediapipe")

a = Analysis(
    ["app.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=["pynput.keyboard._darwin", "pynput.mouse._darwin",
                   "pynput.keyboard._win32", "pynput.mouse._win32",
                   "ApplicationServices"],
    excludes=["tkinter", "PyQt5", "PySide2", "IPython", "pytest"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="Movement",
    debug=False,
    strip=False,
    upx=False,
    console=sys.platform == "win32",
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="Movement")

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="Movement.app",
        icon=None,
        bundle_identifier="com.mbrincat.movement",
        info_plist={
            "NSCameraUsageDescription": "Movement tracks your body with the camera to press keys.",
            "NSHighResolutionCapable": True,
            "LSUIElement": True,
            "LSMinimumSystemVersion": "12.0",
        },
    )
