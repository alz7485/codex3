# AcadStadio 1.26.0 — 設定と表をまとめる・試用版19

**[試用版19 ZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_v1.26.0_GroupedSettingsTrial19.zip)** ／ [SHA256](AcadStadio_v1.26.0_GroupedSettingsTrial19.zip.sha256)

Excel / CSVの行と作図コマンドから、AutoCAD用SCRを生成するローカルアプリです。このZIPはソース版です。

## 今回の画面

- 「設定」にCAD設定・設定プリセット・作図設定を集約。
- 「表」に表一覧・使用表のプルダウン・表示行を集約。
- 表示行はプレビュー専用。入力表の選択と連動し、SCRの対象行は作図設定で独立して指定します。
- サイズ設定を設定プリセット画面に統合。現在値の変更、標準の複製、カスタムの編集・保存・適用を同じ画面で行えます。
- 「選択フロー」タブを削除。ブロック一覧は常時表示し、追加・フォルダ追加・編集・↑・↓・削除・表示を1行へ配置しました。
- ブロック追加は＋、フォルダ追加はフォルダ＋。操作名はマウスを重ねると表示します。
- 検査結果のコマンドは、既存の構成ツリーで該当箇所を選択します。

入力表の左一覧、計算結果と薄い式の2段表示、スペース付きCAD名、プレビュー倍率保持、システム設定の復元、ユーザーコマンド登録なども利用できます。
詳細な使い方はZIP内のREADME.md、docs/QUICK_START.txt、docs/USABILITY.mdをご覧ください。

## 起動とonedir EXE化

Python 3.11以降（tkinterを含む）で、展開したフォルダから実行します。

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

出力は `dist/AcadStadio/AcadStadio.exe`。フォルダ全体を配布します。EXE本体は含みません。詳細はZIP内のEXE_BUILD_ONEDIR.mdにあります。

## 検証

非GUI247件・実Tk GUI230件、計477件合格。設定と表の配置、表示行とSCRの独立、サイズの保存・取消・Undo、標準保護・カスタム・部分プリセット、計算式と空欄の検証を確認しました。通常・最小画面でも操作できます。
フランジの1行102図形・全3行312図形は前版とSCR全文・図形情報が一致しています。ZIPのCRC・全ファイルのSHA256と展開後の実Tk起動も確認済みです。
LinuxのTkで検証し、Windows EXE・AutoCAD実機は未検証です。詳細はZIP内のdocs/VALIDATION.mdと検証ログをご覧ください。

既知の問題: 入力表1が作図用の表より短い場合、行チェックリストの適用で表示されない行が外れます。作図行指定で全角行番号のスピン操作が1へ戻る場合があります。行数をそろえ、作図行指定は半角数字を使用してください。新しい表示行は別のUIです。

画面キャプチャはZIP・この公開フォルダに含めません。既存の必須アプリアイコンを同梱しています。
ZIP内の公開保留に関する記述は配布準備時点の記録です。その後、公開先alz7485/codex3へのユーザー承認を受けています。承認対象のZIPは変更していません。
