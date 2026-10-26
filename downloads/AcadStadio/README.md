# AcadStadio 1.22.0 — 入力表の別窓・プレビュー表示チェック（試用版12）

**[試用版12 ZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_v1.22.0_DetachedTablesTrial12.zip)** ／ [SHA256](AcadStadio_v1.22.0_DetachedTablesTrial12.zip.sha256)

Excel / CSVの行からAutoCAD用SCRを生成するローカルアプリです。この配布はソース版です。

- 入力表は右上の「入力表を編集…」から別ウィンドウへ。メインと同時操作できます。
- メインの作図／入力表タブを廃止し、プレビューを上へ拡張。
- ブロック一覧を左から「順」「ブロック / フォルダ」「表示」に整理。実行条件・件数の列を削除。
- 表示チェックはメインプレビューだけに適用。SCR・作図対象・実行条件は変わりません。
- 「表示 ▾」で全体／選択項目を一括切替。フォルダのチェックは子孫も対象。複数選択後のSpaceも利用できます。
- 非表示のブロックは灰色表示。▣はフォルダ内の表示と非表示の混在です。
- チェックは改名・並べ替え後も追従。別窓の位置・開閉とともに、端末の作業状態として次回起動時に復元します。
- 作図設定の行番号スピン・タイトル表示・行チェックリスト・ブロックの累積プレビューを継続。
- ハッチングなしのフランジ平断面サンプル、CAD初期設定、システム設定の復元、ユーザーコマンド登録を同梱。

## 起動

Python 3.11以降（tkinter含む）で、ZIPを展開したフォルダから実行します。

```powershell
py -3 -m pip install -r requirements.txt
py -3 src/main.py
```

`AcadStadio.pyw`からも起動できます。DWG読込はWindows版AutoCADを起動して利用します。

## onedirでEXE化

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt pyinstaller
.\.venv\Scripts\python.exe -m PyInstaller --clean --noconfirm AcadStadio.spec
```

出力は`dist/AcadStadio/AcadStadio.exe`。フォルダ全体を配布します。詳細はZIP内のEXE_BUILD_ONEDIR.mdにあります。EXE本体は含みません。

## 検証

通常218件・実Tk GUI189件、計407件合格。全非表示でもSCRファイルの内容が元と一致することを確認しました。LinuxのTkで検証し、Windows EXE・AutoCAD実機は未検証です。ログと詳細はZIP内のdocs/VALIDATION.mdを参照してください。

既知の問題: 入力表1が作図用の表より短い場合、行チェックリストの適用で表示されない行が外れます。全角行番号のスピン操作が1へ戻る場合があります。行数をそろえ、半角数字を使用してください。今回のUI変更ではこの2件を修正していません。

画面キャプチャはZIP・この公開フォルダに含めません。既存の必須アプリアイコンを同梱しています。
