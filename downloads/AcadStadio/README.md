# AcadStadio 1.27.1 — ブロック作図画面の左右配置・試用版22

**[試用版22 ZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_v1.27.1_RightPreviewTrial22.zip)** ／ [SHA256](AcadStadio_v1.27.1_RightPreviewTrial22.zip.sha256)

Excel / CSVの行と作図コマンドから、AutoCAD用SCRを生成するローカルアプリです。このZIPはソース版です。

## 今回の変更

- ブロック編集を左のコマンド一覧・右のプレビューへ変更しました。境界をドラッグして幅を調整できます。
- コマンド操作は一覧上部の1行です。順序は **＋（追加）→ 編集 → 複製 → 削除 → ↑ → ↓ → 元に戻す → やり直し**。
- 各操作はアイコンで表示し、マウスを重ねるかTabで移動すると操作名を確認できます。
- 「選択したコマンドまで表示」で、途中経過を右側の広いプレビューで確認できます。
- IF / ELSE・REPEATの内側の一覧も同じ1行の操作です。
- 通常1160×780・最小850×640で表示を確認しました。

主画面の目アイコン・10個のブロック操作・入力表の左一覧・式の2段表示・設定プリセット内のサイズ編集・プレビュー倍率保持・システム設定の復元・ユーザーコマンド登録も継続しています。
使い方はZIP内のREADME.md、docs/QUICK_START.txt、docs/BLOCKS.md、docs/USABILITY.mdをご覧ください。

## 起動

Python 3.11以降（tkinterを含む）で、ZIPをすべて展開したフォルダから実行します。

```powershell
py -3 -m pip install -r requirements.txt
py -3 src/main.py
```

## onedir EXE化

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt pyinstaller
.\.venv\Scripts\python.exe -m PyInstaller --clean --noconfirm AcadStadio.spec
```

出力は `dist/AcadStadio/AcadStadio.exe`。フォルダ全体を配布します。EXE本体は含みません。詳細はZIP内のEXE_BUILD_ONEDIR.mdにあります。

## 検証

非GUI247件・実Tk GUI237件、計484件合格。通常/最小画面の左右配置と1行の8操作、途中プレビュー、編集/保存/取消、Undo/Redoなどを確認しました。
フランジの1行102図形・全3行312図形はTrial21とSCR全文・図形情報が一致しています。ZIPのCRC・全ファイルSHA256と展開後の実Tk起動も確認済みです。
LinuxのTkで検証し、Windows EXE・AutoCAD実機は未検証です。詳しくはZIP内のdocs/VALIDATION.mdと検証ログをご覧ください。

既知の問題: 入力表1が作図用の表より短い場合、行チェックリストの適用で表示されない行が外れます。作図行指定で全角行番号のスピン操作が1へ戻る場合があります。行数をそろえ、作図行指定は半角数字を使用してください。

画面キャプチャはZIP・この公開フォルダに含めません。既存の必須アプリアイコン54点を同梱しています。
