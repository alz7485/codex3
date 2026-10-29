# AcadStadio 1.32.0 — 視覚的な点選択・試用版31

**[試用版31 ZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_v1.32.0_VisualPointsTrial31.zip)** ／ [SHA256](AcadStadio_v1.32.0_VisualPointsTrial31.zip.sha256)

Excel / CSVと作図コマンドからAutoCAD用SCRを生成するローカルアプリのソース版です。

## 視覚的な点選択と座標入力

- 始点・終点・寸法位置などを行にまとめ、X/Yを横並びに配置。各欄の参照ボタンを共通アイコンに統一。
- 点選択画面にプレビューを追加し、白い点マーカーをクリックして選択。黄色が選択点、桃色の十字がずらし後です。
- 確認する入力表の行を変更可能。ホイール拡大縮小・ドラッグ移動にもマーカーが追従し、全体表示ではずらし後の点も収めます。

各座標欄右の参照アイコン→「別コマンドの始点・中点・終点から選ぶ…」を使います。

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

非GUI268件・実Tk GUI259件、計527件合格。Ruff・スモーク・ZIP CRC/全ファイルSHA256確認。Windows EXE・AutoCAD実機は未検証。

SHA256: `b85ed1ed77b67a5f73826f0469fd1de7158aab7e4be39eaa2bfa4f28a49e230d`

[前版Trial30](AcadStadio_v1.31.0_CommandPointsTrial30.zip)
