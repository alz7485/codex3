# Windows onedir build: python -m PyInstaller --noconfirm --clean Yohaku.spec
from pathlib import Path
from runpy import run_path

project = Path(SPECPATH)
run_path(str(project / "scripts" / "check_source.py"))["verify_source"](project)
assets = project / "companion" / "assets"
a = Analysis(
    [str(project / "main.py")],
    pathex=[str(project)],
    binaries=[],
    datas=[(str(assets), "companion/assets")],
    hiddenimports=["win32timezone", "pythoncom", "win32com.client", "win32com.shell.shell"],
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True,
    name="Yohaku", debug=False, bootloader_ignore_signals=False,
    strip=False, upx=False, console=False,
    icon=str(assets / "app" / "yohaku.ico"),
    version=str(project / "packaging" / "windows_version_info.txt"),
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="Yohaku")
