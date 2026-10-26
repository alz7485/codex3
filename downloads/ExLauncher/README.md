# ExLauncher v1.0.10

[長い名前のメニュー表示・修正版ソースZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/ExLauncher/ExLauncher_Codex_Handoff_v1.0.10_Long_Names.zip)

Modernの編集モードで、長いファイル名が右端の⋮メニューを画面外へ押し出す問題を修正しました。項目名とカテゴリ名を残り幅へ「…」で省略表示し、全文をツールチップに表示します。登録名とJSONの全文は維持します。

104テスト成功（Linux/Qt offscreen）。長い英数字・日本語名の実ファイル登録、最小幅での実メニューボタンクリックによる削除、201件の大量一覧から200件への切替を確認しました。追加3試験は100%と200%で成功しています。Windows実機・Windows EXEは未検証です。

v1.0.9の保存失敗対策・大量一覧の可視行描画、設定UIの段階表示、編集開始時の開閉状態維持、VS Code・ビルド環境を引き継いでいます。

1. ZIPをすべて展開し、main.pyと.vscodeがあるフォルダをVS Codeで開きます。Microsoftの「Python」「Python Debugger」拡張を使用します。
2. VS Codeのターミナルで初回の準備を実行します。

```powershell
python scripts/build_onedir.py --setup-only
```

3. Pythonインタープリターに `.venv\Scripts\python.exe` を選びます。**F5で起動・デバッグ**、**Ctrl+Shift+BでEXE作成**です。

[詳しい手順](VSCODE_GUIDE.md)。Windows用EXEの出力先は `dist\ExLauncher\ExLauncher.exe` です。ソースZIPであり、ビルド済みEXEは含みません。旧版へ戻す前に未確定の復旧記録を解決し、記録を手動削除しないでください。

SHA-256: `83354ef9fef28c384905243b03edbbdfb04f2167b033dbb7e9955270e07e8b9b`

[前版 v1.0.9（通常監査9件への修正）](ExLauncher_Codex_Handoff_v1.0.9_Audit_Fixes.zip)
