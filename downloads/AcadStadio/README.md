# AcadStadio 1.28.0 — 分類別コマンド追加・中心線の改善・試用版25

**[試用版25 ZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_v1.28.0_CommandGroupsTrial25.zip)** ／ [SHA256](AcadStadio_v1.28.0_CommandGroupsTrial25.zip.sha256)

Excel / CSVの行と作図コマンドからAutoCAD用SCRを生成するローカルアプリです。このZIPはソース版です。

## 分類別に追加

ブロック編集の上部に、分類ごとの3つの追加アイコンを配置しました。各▼でメニューを開き、マウスを重ねるかTabで操作名を表示します。編集・複製・削除・上下・Undo/Redoも同じ1行です。

- **線・形状（7種）**: 線分・ポリライン・円・円弧・楕円・長方形・点。
- **文字・寸法（5種）**: 文字・長さ寸法・平行寸法・半径寸法・直径寸法。
- **制御（4種）**: IF/ELSE・繰り返し・システム変数変更・ユーザー登録コマンド。

標準16種へ拡張。円弧・楕円・ポリライン・点・平行寸法・半径寸法・直径寸法の7種を追加しました。入力表の列・式、詳細の色/線種尺度、スタイル、条件、JSON保存、プレビューに対応します。
ポリラインの頂点は `@X,@Y; @X+100,@Y; @X+100,@Y+50` の形式です。半径/直径寸法は中心と半径から独立したネイティブ寸法を作成し、既存円の編集には自動追従しません。詳細はZIP内のdocs/DRAWING_COMMANDS.mdをご覧ください。

## フランジの一点鎖線

PCDは円1個、十字/断面の中心線は線分3本とし、CENTERの一点鎖線を指定しました。中心線のためのREPEATは削除し、ボルト穴の等配だけに繰り返しを使います。
初期設定ONなら、不足するCENTERを直接作成します。外部LINファイルは読み込まず、既存のCENTERは変更しません。OFFではCAD内にCENTERが必要です。
プレビューも線種パターンと個別尺度を反映し、ズーム時に更新します。正確な外観はCADのLTSCALEや印刷設定にも依存します。

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

出力は `dist/AcadStadio/AcadStadio.exe`。フォルダ全体を配布します。EXE本体は含みません。詳しくはZIP内のEXE_BUILD_ONEDIR.mdをご覧ください。

## 検証

非GUI259件・実Tk GUI247件、計506件合格。新コマンドの式/範囲/JSON/SCR/監査、分類メニューからの追加とUndo、プレビュー・ズーム・最小画面を確認しました。
フランジの外形・穴・寸法・文字の座標はTrial24と一致。中心線の分割63本を円1個/線3本へ変更し、1行43/45/47図形・全3行135図形になりました。ZIP CRC・全SHA256と展開後の起動も確認済みです。
LinuxのTkで検証しました。Windows EXE・AutoCAD実機は未検証です。詳しくはdocs/VALIDATION.mdとログをご覧ください。

既知の問題: 従来の「選択行…」リストは入力表1が使用表より短いと表示されない行が外れます。新しい作図設定の入力表タブは全行から選べます。作図行指定で全角数字のスピン操作が1へ戻る場合があるため、行番号は半角数字を使用してください。

画面キャプチャはZIP・公開フォルダに含めず、既存の必須アプリアイコン54点とonedir EXE化手順を同梱しています。
