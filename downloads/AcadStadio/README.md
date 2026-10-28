# AcadStadio 1.30.0 — 入力表の作図チェック・試用版28

**[試用版28 ZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_v1.30.0_TableChecksTrial28.zip)** ／ [SHA256](AcadStadio_v1.30.0_TableChecksTrial28.zip.sha256)

Excel / CSVの行とコマンドからAutoCAD用SCRを生成するローカルアプリです。ソース版ZIPです。

## 今回の変更

- 作図対象を入力表左端の「作図」チェックへ統合。チェックを即時反映し、表ごとにJSON保存・Undo/Redoに対応。
- 全チェック・全解除、見出しクリックによる一括切替、選択行のSpace操作に対応。
- 独立した作図設定画面・行番号指定・対象行の別窓・適用ボタンを削除。チェックをすべて外した場合はSCRの出力を停止します。
- 行ハイライトとメインの表示行はプレビュー確認用。作図チェックとは独立しています。
- 表管理と行編集のボタンを表の上に移動し、アイコン・サイズ・間隔をメイン画面と統一しました。

実色表示、拡大したブロック編集、16種類の分類別コマンド、フォルダ管理も継続しています。

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

出力は `dist/AcadStadio/AcadStadio.exe`。フォルダ全体を配布します。EXE本体は含みません。詳細は同梱のEXE_BUILD_ONEDIR.mdをご覧ください。

## 検証

非GUI260件・実Tk GUI250件、合計510件合格。Ruff、スモーク、ZIP CRC/全ファイルSHA256も確認済みです。Windows EXE・AutoCAD実機は未検証。

SHA256: `5bdd26aead6d569bcf467fc1cf17c0019b29a465a8808fd49187249ba9c4b97a`

[前版Trial27](AcadStadio_v1.29.0_ActualColorsTrial27.zip)
