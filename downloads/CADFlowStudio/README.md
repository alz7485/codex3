# CADFlow Studio 1.17.0

Excel / CSVの行と作図プリセットから、AutoCAD用のSCRを作成するWindows向けデスクトップアプリです。

**[配布ZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/CADFlowStudio/CADFlow_Studio_v1.17.0.zip)** / [SHA256](CADFlow_Studio_v1.17.0.zip.sha256)

公開日: 2026-10-23（JST）。この配布は**Pythonソース版**です。EXEは含みません。
WindowsでonedirのEXEを作成するコマンドと`CADFlowStudio.spec`をZIP内に同梱しています。

![CADFlow Studioの画面](Main_UI_v1.17.0.png)

## 主な機能

- 複数の入力表、セル直接編集、Tab移動、Excel範囲貼り付け。
- 行番号・選択行・全行での作図対象指定、サイズ設定と設定プリセット。
- 作図プリセット、IF / ELSE、繰り返し、共通ブロック、展開できるフロー表示。
- プレビューと生成SCR、選択図形の強調、行を選べる数式試算、検査結果から該当箇所への移動。
- 標準11タイプ、初期15件の登録コマンド。ユーザーによるコマンド登録とJSON保存・共有。
- レイヤー・色・線種・線の太さ・印刷指定・文字/寸法スタイル・線種読込の設定。
- 不足定義を作成する冒頭マクロのON/OFF、作図後のシステム設定復元。
- アイコンと操作名ツールチップ、1段のツールバー、右ペイン上端から広く使うプレビュー。
- JSONプロジェクト一覧の別窓管理、ウィンドウ・タブ・倍率の復元、15秒ごとの未保存データ退避。

## 起動

1. 上のZIPをダウンロードし、すべて展開します。
2. `CADFlow_Studio_v1.17.0`フォルダーを開きます。
3. Python 3.11以降（標準のTkinterを含む）を用意します。
4. フォルダーでPowerShellを開いて実行します。

```powershell
py -3 -m pip install -r requirements.txt
py -3 src/main.py
```

`CADFlow Studio.pyw`のダブルクリックでも起動できます。
Excel読込にopenpyxlを使用します。CSV・GUIの基本動作は標準ライブラリで利用できます。

操作ガイドはZIP内の`docs/USABILITY.md`、EXE化は`EXE_BUILD_ONEDIR.md`を参照してください。

## 検証

基本処理123件・実際のTk GUI操作100件の**計223件合格**。詳細ログと検証環境はZIP内の`docs/VALIDATION.md`にあります。
ZIPのCRC・ファイル別SHA256と、展開後のスモーク検証も通過しています。
Windows EXEのビルド・実行とAutoCAD実機でのSCR実行は未検証です。

SHA256:

```text
a448342912e334bbd2a1f507cfafa1255682c2be5046add3b75be57ed03125cb
```
