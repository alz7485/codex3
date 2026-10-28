# AcadStadio 1.30.1 — 別窓UIを統一・試用版29

**[試用版29 ZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_v1.30.1_UnifiedDialogsTrial29.zip)** ／ [SHA256](AcadStadio_v1.30.1_UnifiedDialogsTrial29.zip.sha256)

Excel / CSVと作図コマンドからAutoCAD用SCRを生成するローカルアプリです。ソース版です。

## 今回の変更

- メインUIを維持し、別窓のボタンの高さ・余白・アイコン表現を統一。
- プリセット、ユーザーコマンド、プロジェクト一覧、構成ツリーの操作を一覧上のツールバーへ整理。
- CAD設定とコマンド引数の追加/削除、検査の再実行、SCRのコピー/再生成を一覧上へ配置。
- 保存・確定・取消は下へ配置。確定操作は文字を残し、編集ツールは操作名のツールチップで確認できます。
- 入力表の作図チェック、実色表示、16種類の分類別コマンドなどは継続しています。

## 起動とonedir EXE化

Python 3.11以降（tkinterを含む）で、展開したフォルダから実行します。

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

非GUI260件・実Tk GUI252件、計512件合格。Ruff・スモーク・ZIP CRC/全ファイルSHA256も確認済み。Windows EXE・AutoCAD実機は未検証。

SHA256: `863d152a6d868b98d9d215e34291c39df706bf45cb663b947113a468ee0f858f`

[前版Trial28](AcadStadio_v1.30.0_TableChecksTrial28.zip)
