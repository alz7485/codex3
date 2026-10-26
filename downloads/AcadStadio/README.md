# AcadStadio 1.24.0 — 入力表の計算列・試用版15

**[試用版15 ZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_v1.24.0_ColumnFormulasTrial15.zip)** ／ [SHA256](AcadStadio_v1.24.0_ColumnFormulasTrial15.zip.sha256)

Excel / CSVの行からAutoCAD用SCRを生成するローカルアプリです。このZIPはソース版です。

## 入力表の計算

同じ表の見出し名を、その表だけの変数として使えます。高さ列の1行目に `幅 * 2` と入れると、幅10の行は20、幅15の行は30になります。登録変数は `変数.半径` のように指定します。

- 式・変数の設定は1行目だけ。計算列の2行目以降を自動計算・編集不可にします。通常列は各行で編集できます。
- 計算結果の下に、小さく薄い色で式を表示します。列の指定は見出し名で表示します。
- 「式・変数」から参照を選択でき、1行目のダブルクリックで式を編集できます。
- JSON保存・再読込、Undo/Redo、別表参照、依存関係と循環参照の検査に対応します。
- サンプルは `examples/formula_columns_project.json`、説明は `docs/CALCULATED_COLUMNS.md` です。

ブロックは一覧順・コマンドは上から順に実行します。入力表の別窓、行選択とプレビューの連動、表示チェック、倍率保持、CAD初期設定、JSONユーザーコマンド、作図後のシステム設定復元は引き続き利用できます。

## 起動とonedir EXE化

Python 3.11以降（tkinterを含む）で、ZIPを展開したフォルダから実行します。

```powershell
py -3 -m pip install -r requirements.txt
py -3 src/main.py
```

EXE化:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt pyinstaller
.\.venv\Scripts\python.exe -m PyInstaller --clean --noconfirm AcadStadio.spec
```

出力は `dist/AcadStadio/AcadStadio.exe`。フォルダ全体を配布します。詳細はZIP内のEXE_BUILD_ONEDIR.mdを参照してください。EXE本体は含みません。

## 検証

非GUI243件・実Tk GUI213件、計456件合格。計算列の新規試験36件を含みます。フランジの1行102図形・全3行312図形は前版とSCR全文・図形情報が一致しています。ZIPのCRC・全ファイルのSHA256と展開後の実Tk起動も確認しました。
LinuxのTkで検証し、Windows EXE・AutoCAD実機は未検証です。詳細とログはZIP内のdocs/VALIDATION.mdにあります。

既知の問題: 入力表1が作図用の表より短い場合、行チェックリストの適用で表示されない行が外れます。全角行番号のスピン操作が1へ戻る場合があります。行数をそろえ、半角数字を使用してください。この2件は今回の修正範囲に含みません。

画面キャプチャはZIP・この公開フォルダに含めません。既存の必須アプリアイコンを同梱しています。
