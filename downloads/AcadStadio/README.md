# AcadStadio 1.23.0 — 順番に作図する・試用版14

**[試用版14 ZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_v1.23.0_SequentialBlocksTrial14.zip)** ／ [SHA256](AcadStadio_v1.23.0_SequentialBlocksTrial14.zip.sha256)

Excel / CSVの行からAutoCAD用SCRを生成するローカルアプリです。このZIPはソース版です。

## 今回の整理

ブロックを追加し、その中へコマンドを直接並べる操作に統一しました。ブロックは一覧の「順」の番号順、中のコマンドは上から順に実行します。

- 「作図対象／呼び出し専用」の区分と、四角が4つの切替ボタンを削除。
- ブロック編集の作図対象チェック、構成ツリーの切替、BLOCKコマンドの選択を削除。
- ブロック名の●／◇を削除。新規ブロックのJSONにdraw属性を持たせません。
- IF / ELSE、REPEAT、実行条件、コマンドの複製・並べ替えは利用できます。
- 表示チェックと全体・選択・フォルダの一括切替はメインプレビューだけに適用し、SCRに影響しません。

## 継続する操作

入力表は左上「入力表を編集…」から別窓に開きます。表で選択した行をプレビューへ表示し、SCRの行指定は作図設定を維持します。行番号スピン・行タイトル・行チェックリスト・ブロックの累積プレビューにも対応します。
表示切替・再生成でプレビューの倍率とパン位置を維持し、行選択の切替では同じ倍率で中央へ移します。
CADのレイヤー・色・印刷・線種・文字スタイル・寸法スタイルの初期設定、JSONによるユーザーコマンド登録、作図後のシステム設定復元を同梱。フランジの平断面図はハッチングなしです。

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

出力は`dist/AcadStadio/AcadStadio.exe`。フォルダ全体を配布します。詳細はZIP内のEXE_BUILD_ONEDIR.mdを参照してください。EXE本体は含みません。

## 検証

通常223件・実Tk GUI197件、計420件合格。廃止した操作のGUI試験を順次実行の仕様へ更新しました。フランジの1行102図形・全3行312図形について、前版とSCR全文・図形情報が一致しています。
LinuxのTkで検証し、Windows EXE・AutoCAD実機は未検証です。詳細とログはZIP内のdocs/VALIDATION.mdにあります。

既知の問題: 入力表1が作図用の表より短い場合、行チェックリストの適用で表示されない行が外れます。全角行番号のスピン操作が1へ戻る場合があります。行数をそろえ、半角数字を使用してください。この2件は今回の修正範囲に含みません。

画面キャプチャはZIP・この公開フォルダに含めません。既存の必須アプリアイコンを同梱しています。
