# AcadStadio 1.29.0 — 実色表示・一覧操作の改善・試用版27

**[試用版27 ZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_v1.29.0_ActualColorsTrial27.zip)** ／ [SHA256](AcadStadio_v1.29.0_ActualColorsTrial27.zip.sha256)

Excel / CSVの行とコマンドからAutoCAD用SCRを生成するローカルアプリです。このZIPはソース版です。

## 実色表示・編集画面

- メインとブロック編集のプレビュー右下に、カラーパレットの「実色表示」トグルを追加。登録レイヤーとコマンドのACI色を使い、両画面で同期します。
- 色の切り替えで倍率・パン位置・作図対象・SCR・プロジェクトは変わりません。切替状態は端末に保存します。
- ブロック編集の初期サイズを1320×860へ拡大。小さい画面では画面内に収まるサイズへ調整します。
- 編集のボタンサイズ/間隔をメインと共通化し、コマンド行の先頭に追加分類と同じアイコンを表示します。
- 作図設定をチェックのアイコンに変更し、CAD設定の歯車と区別しました。

実色表示は登録ACIに基づきます。ByLayer/空欄の継承と単独作図のByBlock（ACI 7）を表示し、未知のレイヤー色は従来の色分けを使います。CADの未知の現在値や背景・印刷スタイルまでは取得しません。

## フォルダ・一覧

- ブロック一覧のセル罫線を明確にしました。
- フォルダ＋は最上位へ即時追加。名前は「新しいフォルダ(1)」から、同じ階層で空いている番号を使います。
- フォルダ名をダブルクリック/F2で一覧上編集し、Enterで確定、Escで取消。空欄/重複は確定できません。保存時も未確定の名前を確定します。
- 右クリックからフォルダ追加の項目を削除。子フォルダへの分類はドラッグまたは移動メニューを使います。

標準16コマンド、分類別の3追加アイコン、作図設定の入力表タブ、フランジのネイティブ一点鎖線も継続しています。使い方はZIP内のREADME.md、docs/USABILITY.md、docs/BLOCK_FOLDERS.md、docs/DRAWING_COMMANDS.mdをご覧ください。

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

出力は `dist/AcadStadio/AcadStadio.exe`。フォルダ全体を配布します。EXE本体は含みません。詳細はZIP内のEXE_BUILD_ONEDIR.mdを参照してください。

## 検証

非GUI260件・実Tk GUI256件、計516件合格。色/継承/凡例/カメラ維持/保存状態/trace解除、ボタンの同寸法、行頭画像、即時フォルダ追加、実際のダブルクリック・Enter/F2/Esc、保存、Undo/Redo、罫線を検証しました。
通常/最小画面を実Tkで確認。フランジの43/45/47・全135図形と生成SCRはTrial26から変更せず、プレビューに継承レイヤーの情報を追加しています。ZIPのCRC・全SHA256と展開後の起動も確認済みです。
LinuxのTkで検証し、Windows EXE・AutoCAD実機は未検証です。詳しくはZIP内のdocs/VALIDATION.mdとログをご覧ください。

既知の問題: 従来の「選択行…」リストは入力表1が使用表より短いと表示されない行が外れます。作図設定の表タブは全行から選べます。作図行指定で全角数字のスピン操作が1へ戻る場合があるため、行番号は半角数字を使用してください。

画面キャプチャはZIP・公開フォルダに含めず、既存の必須アプリアイコン54点とonedir EXE化手順を同梱しています。
