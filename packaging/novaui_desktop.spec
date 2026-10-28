"""PyInstaller sample spec for a user-provided app.py; build on each target OS."""

from pathlib import Path

from PyInstaller.utils.hooks import collect_all

project_root = Path(SPECPATH).resolve().parent.parent
webview_datas, webview_binaries, webview_hiddenimports = collect_all("webview")
frontend = project_root / "novaui" / "frontend"

analysis = Analysis(
    [str(project_root / "app.py")],
    pathex=[str(project_root)],
    binaries=webview_binaries,
    datas=[*webview_datas, (str(frontend), "novaui/frontend")],
    hiddenimports=webview_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(analysis.pure)
executable = EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    [],
    name="NovaUIApplication",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)
