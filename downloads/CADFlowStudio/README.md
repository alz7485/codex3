# CADFlow Studio 1.18.0

Excel / CSVの行と作図ブロックから、AutoCAD用のSCRを作成するWindows向けデスクトップアプリです。

**[最新版ZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/CADFlowStudio/CADFlow_Studio_v1.18.0.zip)** / [SHA256](CADFlow_Studio_v1.18.0.zip.sha256)

公開日: 2026-10-23（JST）。**Pythonソース版**です。EXEは含みません。
WindowsでonedirのEXEを作成するコマンドと`CADFlowStudio.spec`をZIP内に同梱しています。

![CADFlow Studio 1.18.0](Main_UI_v1.18.0.png)

## 構造を一つ減らしました

作図プリセットと共通ブロックの別管理を統合し、**プロジェクト → ブロック → コマンド**にしました。
通常はブロックを並べ、各ブロックの中にコマンドを直接追加します。
条件分岐・繰り返し・条件・ローカル変数もブロック内に設定します。

- **● 作図対象**: 一覧の上から順に直接実行します。
- **◇ 呼び出し専用**: 同じ一覧で管理し、BLOCKコマンドから呼び出して再利用します。
- 名前を変えても呼び出しは維持します。使用中の削除と循環参照を防止します。
- 文字高さ・寸法尺度などの**設定プリセット**は、作図の階層と別に維持しています。

旧JSONは開くと自動移行します。単に一度だけ呼び出していた中間層は取り込みます。
入力表、対象行、実行順、条件、変数、サイズ設定を引き継ぎ、読込だけでは元ファイルを書き換えません。
保存後はモデル版11のblocks配列だけを持ち、作図用presetsキーは保存しません。
旧版アプリで使うJSONが必要な場合は、別名保存やバックアップで残してください。

## 引き続き利用できる機能

- 複数の入力表、セル編集、Tab移動、Excel範囲貼り付け。
- 選択行・行番号・全行での作図指定、サイズ設定と設定プリセット。
- プレビュー・生成SCR、選択と呼び出し先の強調、数式試算、検査から該当箇所への移動。
- 標準11タイプ、初期15件の登録コマンド、ユーザー登録とJSON共有。
- レイヤー・色・線種・線の太さ・印刷・文字/寸法スタイル・線種読込。
- 不足定義を作成する冒頭マクロのON/OFF、通常作図完了後のシステム設定復元。
- アイコンとツールチップ、省スペースのツールバー、右ペイン上端から使うプレビュー。
- JSONプロジェクト一覧、ウィンドウ・タブ・倍率復元、15秒ごとの未保存データ退避。

## 起動

ZIPをすべて展開し、`CADFlow_Studio_v1.18.0`フォルダーでPowerShellを開きます。
Python 3.11以降（標準のTkinterを含む）が必要です。

```powershell
py -3 -m pip install -r requirements.txt
py -3 src/main.py
```

`CADFlow Studio.pyw`のダブルクリックでも起動できます。
ZIP内の`docs/BLOCKS.md`で新しい構造と移行、`docs/USABILITY.md`で操作、`EXE_BUILD_ONEDIR.md`でEXE化を確認できます。

## 検証

基本処理154件・実際のTk GUI操作122件の**計276件合格**。
旧形式とのSCR全文・図形座標の比較、旧版の最大深さ、条件・変数・once、改名・取消・Undo・参照保護を検証しています。
ZIPのCRC・各ファイルSHA256・展開後のスモーク検証も通過。詳細はZIP内の`docs/VALIDATION.md`です。
Windows EXEのビルド・実行とAutoCAD実機でのSCR実行は未検証です。

SHA256:

```text
713ea0538c21c857bb2116cb991e3460dfa661abc9c1b35e45245e4b31c9c347
```

[旧版1.17.0 ZIP](CADFlow_Studio_v1.17.0.zip) / [旧版SHA256](CADFlow_Studio_v1.17.0.zip.sha256)
