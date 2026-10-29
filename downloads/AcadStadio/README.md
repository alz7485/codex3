# AcadStadio 1.35.0 — 連続点入力・試用版36

**[試用版36 ZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_v1.35.0_ContinuousPointsTrial36.zip)** ／ [SHA256](AcadStadio_v1.35.0_ContinuousPointsTrial36.zip.sha256)

Excel / CSVの行と作図コマンドから、AutoCAD用SCRを生成するローカルアプリのソース版です。

## 線分・ポリラインの連続点入力

- 始点/終点の下の＋アイコンで新しい終点を追加。以前の終点は中間点1、中間点2…へ変わります。
- 各点はX/Y横並び。表・変数・先行コマンドの点参照も使えます。新しい終点は空欄です。
- 各点の削除・自動番号更新、JSON保存、再編集、全区間プレビューとガイド化に対応。
- 線分はLINEで区間ごとに連続作図。ポリラインは1つのPLINEで作図し、閉じる設定も保持。
- 1コマンド2〜1000点。点参照の始点/中点/終点は全経路が対象で、中点は経路長の半分です。中間点の個別参照はありません。
- examples/continuous_points_project.json と docs/CONTINUOUS_POINTS.md を同梱。

## 引き続き使える機能

ガイド化で最上位のガイドへ独立コピーし、薄いプレビューと点参照だけに使用。SCRにガイドの図形は出力しません。参照元が後ろに来る並べ替えでは、ガイドへコピーして参照切替／リンク保持で警告／取消を選べます。

コマンドの座標は同じリストの先行コマンドや前のブロックから参照でき、視覚的な点選択、X/Y個別のずらし量、入力行ごとの計算に対応します。点参照は座標を解決する機能です。CADオブジェクト選択には対象が先に実際に作図されている必要があります。

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

非GUI286件・実Tk GUI273件、計559件合格。要約表示調整後も関連GUI3件/非GUI6件合格。Ruff・フランジスモーク・ZIP CRC/全ファイルSHA256・展開ソースのGUI起動を確認。Windows EXE・AutoCAD実機は未検証。

SHA256: `b56e8aba6050d4980d8482511e47d42ec11c95be3f2923fff6327deb111e547d`

[前版Trial35](AcadStadio_v1.34.0_GuideBlocksTrial35.zip)
