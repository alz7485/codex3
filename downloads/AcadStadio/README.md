# AcadStadio 1.22.1 — 行選択とプレビュー連動（試用版13）

**[試用版13 ZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_v1.22.1_LinkedPreviewTrial13.zip)** ／ [SHA256](AcadStadio_v1.22.1_LinkedPreviewTrial13.zip.sha256)

Excel / CSVの行からAutoCAD用SCRを生成するローカルアプリです。このZIPはソース版です。

- 入力表の別窓で行を選択すると、その行をメインプレビューへ表示。クリック・上下キー・複数選択に対応します。
- 表の選択は確認用で、SCRの出力行は作図設定を維持。選択解除や作図設定の行指定変更で、作図対象のプレビューへ戻ります。
- 入力表の選択・編集とCAD初期設定ボタンを左側へ集約。プレビューを上端まで広げました。
- 表示チェック・全非表示からの再表示・F5・SCR表示などで、倍率とパン位置を維持します。
- 行選択の変更時は倍率を保って中央へ移動。倍率はホイール・全体表示・ダブルクリックで調整できます。
- ブロック一覧は左から「順」「ブロック / フォルダ」「表示」。表示チェックはメインプレビューのみで、SCRへ影響しません。
- 全体／選択項目／フォルダ配下の表示を一括切替できます。
- 入力表は閉じても再表示でき、ウィンドウ位置・開閉とブロック表示状態はこの端末の作業状態に保存します。
- 行番号スピン・行タイトル・行チェックリスト・ブロックの累積プレビュー、ハッチングなしフランジ平断面サンプルを継続。
- CAD初期設定、作図後のシステム設定復元、ユーザーコマンド登録を同梱。

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

通常218件・実Tk GUI196件、計414件合格。表の行選択でSCRファイルが変わらないこと、表示切替で実倍率・パン・同じ線の画面座標が変わらないことを確認しました。LinuxのTkで検証し、Windows EXE・AutoCAD実機は未検証です。ログと詳細はZIP内のdocs/VALIDATION.mdを参照してください。

既知の問題: 入力表1が作図用の表より短い場合、行チェックリストの適用で表示されない行が外れます。全角行番号のスピン操作が1へ戻る場合があります。行数をそろえ、半角数字を使用してください。この2件は今回の修正範囲に含みません。

画面キャプチャはZIP・この公開フォルダに含めません。既存の必須アプリアイコンを同梱しています。
