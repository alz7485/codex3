# AcadStadio 1.24.2 — スペース付きCAD名の修正・試用版17

**[試用版17 ZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_v1.24.2_SpacedCadNamesTrial17.zip)** ／ [SHA256](AcadStadio_v1.24.2_SpacedCadNamesTrial17.zip.sha256)

Excel / CSVの行からAutoCAD用SCRを生成するローカルアプリです。このZIPはソース版です。

## 修正した問題

DWGから文字スタイル「MS明朝　縦」「SX_FONT 縦」を読むと、アプリ側の名前検証で除外される問題を修正しました。

- 半角・全角スペースを含むCAD名に対応。元の名前を保持し、変更する必要はありません。
- 取込候補・登録・コマンドの選択・JSON保存・再読込を通して同じ名前を使います。
- SCRではスペース付きの名前を引用符で囲み、一つの引数として出力します。
- レイヤー・線種・寸法スタイルも同じ名前の規則に統一。改行・タブ・制御文字・禁止記号は拒否します。
- CAD初期設定画面の「名前は空白なし」という説明も更新しました。

## 入力表を左の一覧で管理

入力表の別窓を、左の表一覧・右の編集領域に整理しました。表を選ぶプルダウンと「管理」メニューは削除しました。

- 左の一覧をクリック、または上下キーで表を切り替えます。
- 表を追加・名前変更（鉛筆 / F2）・複製・削除を一覧の下に配置しました。
- Excel / CSV読込・選択した表のファイル置換も同じ場所にあります。
- 切り替え時には未確定のセルを元の表へ確定し、表ごとの選択行を保持します。
- メインの「使用する入力表」と一覧の選択は連動します。JSON保存・再読込・Undo/Redoにも対応します。

## 計算列も利用できます

同じ表の見出し名を、その表だけの変数として使えます。高さ列の1行目に `幅 * 2` と入れると、幅10の行は20、幅15の行は30になります。登録変数は `変数.半径` のように指定します。
式・変数の設定は1行目だけ。計算列の2行目以降を自動計算・編集不可にし、結果の下に小さく薄い色で式を表示します。通常列は各行で編集できます。
サンプルは `examples/formula_columns_project.json`、説明は `docs/CALCULATED_COLUMNS.md` です。

ブロックの順次実行、行選択プレビュー、表示チェック、倍率保持、CAD初期設定、JSONユーザーコマンド、作図後のシステム設定復元は引き続き利用できます。

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

非GUI247件・実Tk GUI218件、計465件合格。両名のDWG抽出・チェック登録・設定の確定・コマンド選択・SCR出力と、JSON保存・再読込、マクロON/OFF、各リソースの引用と不正名の拒否を確認しました。DWGのCOM抽出はFakeDocumentで検証しています。
フランジの1行102図形・全3行312図形は前版とSCR全文・図形情報が一致しています。ZIPのCRC・全ファイルのSHA256と展開後の実Tk起動も確認しました。
LinuxのTkで検証し、Windows EXE・AutoCAD実機は未検証です。詳細とログはZIP内のdocs/VALIDATION.mdにあります。

既知の問題: 入力表1が作図用の表より短い場合、行チェックリストの適用で表示されない行が外れます。全角行番号のスピン操作が1へ戻る場合があります。行数をそろえ、半角数字を使用してください。この2件は今回の修正範囲に含みません。

画面キャプチャはZIP・この公開フォルダに含めません。既存の必須アプリアイコンを同梱しています。
