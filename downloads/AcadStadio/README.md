# AcadStadio 1.27.3 — メイン画面の区画を明確化・試用版24

**[試用版24 ZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_v1.27.3_PanelBordersTrial24.zip)** ／ [SHA256](AcadStadio_v1.27.3_PanelBordersTrial24.zip.sha256)

Excel / CSVの行とコマンドから、AutoCAD用SCRを生成するローカルアプリです。このZIPはソース版です。

## 今回の変更

- メインの「設定」「入力表」「ブロック一覧」にグレーの枠線を追加し、境界を明確にしました。
- 3領域の内側に4pxの横余白を確保。右プレビューの領域は維持し、通常・最小画面・左幅300pxでも10個の操作ボタンが1行に収まります。

## 前版から継続する機能

- ブロック名を左のコマンド一覧の上、実行条件を一覧の下に移動。右プレビューを152px上へ広げ、条件を開いても高さを維持します。
- コマンド詳細に「色」「線種尺度」を追加。ACI番号・名前・色見本・ByLayer/ByBlock・列や式で指定できます。尺度は個別のCELTSCALEで、全体のLTSCALEは変えません。
- 作図設定に入力表のタブと全列表示を追加。クリック/Spaceで行をチェックし、全チェック/解除も利用できます。
- 「この表のチェック行を作図対象にする」で使用表と出力行を適用。タブやチェックだけではSCR対象は変わりません。適用は1回のUndoで戻せます。
- 計算列は結果と薄い式を表示。入力表の値は通常の編集画面で変更します。

色・線種尺度は空欄なら直前の設定を引き継ぎ、先頭ではCADの現在値を使用。終了時・エラー時は元へ戻します。
ACI 1〜255の指定色はプレビューにも反映。ByLayer/ByBlockは従来のレイヤー別色分けで、正確な破線間隔はCADで確認してください。

## 起動とonedir EXE化

Python 3.11以降（tkinterを含む）で展開したフォルダから実行します。

```powershell
py -3 -m pip install -r requirements.txt
py -3 src/main.py
```

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt pyinstaller
.\.venv\Scripts\python.exe -m PyInstaller --clean --noconfirm AcadStadio.spec
```

出力は `dist/AcadStadio/AcadStadio.exe`。フォルダ全体を配布します。EXE本体は含みません。詳しくはZIP内のEXE_BUILD_ONEDIR.mdをご覧ください。

## 検証

非GUI252件・実Tk GUI243件、計495件合格。色/尺度の式・範囲・継承・JSON・復元対象、表タブのチェック/適用/Undo・計算列・空表・外部変更を検証しました。
ブロック編集1160×780/850×640、作図設定1000×740/760×600の実画面を確認。フランジの既存SCRと図形情報はTrial23と一致し、1行102図形・全3行312図形を維持しています。ZIPのCRC・全ファイルSHA256と展開後の実Tk起動も確認済みです。
LinuxのTkで検証し、Windows EXE・AutoCAD実機は未検証です。詳細はZIP内のdocs/VALIDATION.mdとログをご覧ください。

既知の問題: 従来の「選択行…」チェックリストは入力表1が使用表より短いと表示されない選択行が外れます。今回の全列表示タブは使用表の全行から選べます。作図行指定の全角数字のスピン操作が1へ戻る場合があるため、行番号は半角数字を使用してください。

画面キャプチャはZIP・この公開フォルダに含めません。既存の必須アプリアイコン54点とonedir EXE化手順を同梱しています。
