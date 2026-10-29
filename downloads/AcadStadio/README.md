# AcadStadio 1.31.0 — コマンドの点参照・試用版30

**[試用版30 ZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_v1.31.0_CommandPointsTrial30.zip)** ／ [SHA256](AcadStadio_v1.31.0_CommandPointsTrial30.zip.sha256)

Excel / CSVと作図コマンドからAutoCAD用SCRを生成するローカルアプリのソース版です。

## 点参照

座標欄の「表・変数 ▾」→「別コマンドの始点・中点・終点から選ぶ…」を使います。

- 同じリストの先行コマンドを指定し、始点・中点・終点などのX/Yを個別に取得。
- Xだけ取得した場合、Yは変更しません。ずらし量 -10 や表の列/変数の式にも対応。
- 寸法の測定点を線へ合わせ、入力値の変更に追従。登録コマンドの引数にも使用可能。
- 表示はコマンド番号、保存は内部ID。削除・後続へ移動・未作図の参照先はエラーとして検出。
- docs/COMMAND_POINTS.mdと、線＋寸法の examples/line_dimension_points_project.json を同梱。

座標によるCADオブジェクト選択に使えますが、図形が同じ選択点に重なる場合は一意に区別できません。X−10で元の線から外れる場合もあります。SCR生成時に解決する点参照です。

## 起動とonedir EXE化

Python 3.11以降（tkinterを含む）で展開フォルダから実行します。

```powershell
py -3 -m pip install -r requirements.txt
py -3 src/main.py
```

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt pyinstaller
.\.venv\Scripts\python.exe -m PyInstaller --clean --noconfirm AcadStadio.spec
```

出力は `dist/AcadStadio/AcadStadio.exe`。フォルダ全体を配布します。EXE本体は含みません。

## 検証

非GUI268件・実Tk GUI255件、計523件合格。Ruff・スモーク・ZIP CRC/全ファイルSHA256確認。Windows EXE・AutoCAD実機は未検証。

SHA256: `7b3d42493a787ca681e1476916f135b488d16e853c3b9c9191ac4f519819c90d`

[前版Trial29](AcadStadio_v1.30.1_UnifiedDialogsTrial29.zip)
