# ExLauncher v1.0.9

[通常監査9件への修正版ソースZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/ExLauncher/ExLauncher_Codex_Handoff_v1.0.9_Audit_Fixes.zip)

保存失敗後に表示と操作対象がずれる問題を修正しました。変更は仮データへ適用し、保存成功後に画面と内部データを更新します。プリセットの追加・名前変更・削除と設定更新も一括で確定・復旧します。

高DPIの設定スライド、設定保存失敗時の入力保持、狭い設定フォーム、履歴資料の案内と日本語名も修正しています。

200項目を超えるカテゴリは可視行だけを描画します。合成2,000項目・各3回の中央値で、初回展開1,336.424ms→22.177ms、編集開始3,703.792ms→19.718msでした（Linux/Qt offscreen、アニメーションなし）。Windows実測やFPSではありません。

101テスト成功。100/150/200%と左右配置、保存失敗後の再試行、末尾項目の実行・編集・ドラッグ、大量一覧の設定/バー往復を確認しました。Windows実機とWindows EXEは未検証です。今回の修正・回帰確認は独立した修正後監査ではありません。

編集開始時の開閉状態維持と、設定の「カテゴリ収納 → バー高さ変更 → スライド表示」は維持しています。ClassicのUI、登録JSON形式、VS Code・ビルド設定も引き継いでいます。

1. ZIPをすべて展開し、main.pyと.vscodeがあるフォルダをVS Codeで開きます。Microsoftの「Python」「Python Debugger」拡張を使用します。
2. VS Codeのターミナルで初回の準備を実行します。

```powershell
python scripts/build_onedir.py --setup-only
```

3. Pythonインタープリターに `.venv\Scripts\python.exe` を選びます。**F5で起動・デバッグ**、**Ctrl+Shift+BでEXE作成**です。

[詳しい手順](VSCODE_GUIDE.md)。Windows用EXEの出力先は `dist\ExLauncher\ExLauncher.exe` です。ソースZIPであり、ビルド済みEXEは含みません。共通復旧層は削除を扱う記録version 2と従来version 1に対応します。旧版へ戻す前に未確定の復旧記録を解決し、記録を手動削除しないでください。

SHA-256: `66f6154649608ec1a8e8f75649a5e03e03fe9abb37f42b8785105a0f30db42a9`

[前版 v1.0.8（設定UIスライド）](ExLauncher_Codex_Handoff_v1.0.8_Settings_Slide.zip)
