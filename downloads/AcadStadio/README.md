# AcadStadio 1.35.1 — 入力欄の案内整理・試用版37

**[試用版37 ZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_v1.35.1_FieldHintsTrial37.zip)** ／ [SHA256](AcadStadio_v1.35.1_FieldHintsTrial37.zip.sha256)

Excel / CSVの行と作図コマンドから、AutoCAD用SCRを生成するローカルアプリのソース版です。

## コマンド設定の表示整理

- コマンド編集の縦スクロールバーは内容が収まらない場合だけ表示し、収まると非表示。
- テキスト入力欄・プルダウン・スピンボックスの入力枠を同じ高さに統一。
- 詳細設定の下の説明文と試算メッセージを削除しました。
- レイヤー・線種・色・線種尺度・文字/寸法スタイルが空欄のとき、入力欄内に「現在の設定を引き継ぐ」と薄く表示。
- 入力すると案内が消え、消去すると再表示。任意の実行条件は「条件なし（常に実行）」と案内します。
- 案内は表示だけで、入力値・JSON・生成SCRには入りません。試算は右上の列・変数一覧から利用可能です。

線分/ポリラインの＋で連続点追加、視覚的な点参照、先行ブロック参照、ガイドブロック、フォルダ管理、入力表の計算式などは引き続き利用できます。

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

非GUI286件・実Tk GUI276件、計562件合格。Ruff・フランジスモーク・ZIP CRC/全ファイルSHA256・展開ソースのGUI起動を確認。Windows EXE・AutoCAD実機は未検証。

SHA256: `5e0af8935973f7ec228b2ddd54ea3cf6d3845ea263d316736f65a8719b0656c2`

[前版Trial36](AcadStadio_v1.35.0_ContinuousPointsTrial36.zip)
