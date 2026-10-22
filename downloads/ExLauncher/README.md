# ExLauncher v1.0.8

[設定UIスライド対応・修正版ソースZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/ExLauncher/ExLauncher_Codex_Handoff_v1.0.8_Settings_Slide.zip)

Modernの設定ボタンは、**カテゴリ収納 → バーを設定UIの高さへ変更 → 設定UIをスライド表示**の順に動きます。バーの左右配置に合わせ、カテゴリ表示と同じ方向へ出ます。速度設定もカテゴリと共通です。

OK・キャンセル・Esc・バークリックでは逆順で戻し、設定前のカテゴリ開閉状態を復元します。設定中のバードラッグにも追従します。狭い画面では設定項目をスクロールでき、OK・キャンセルは表示を維持します。

85テスト成功（Linux/Qt offscreen）。Windows実機での滑らかさ・ちらつき・DPI/複数モニター・EXE実行は未検証です。ソースZIPであり、ビルド済みEXEは含みません。

v1.0.7の編集時の選択展開、Classic、保存形式、VS Code・ビルド環境は引き継いでいます。

1. ZIPをすべて展開し、main.pyと.vscodeがあるフォルダをVS Codeで開きます。Microsoftの「Python」「Python Debugger」拡張を使用します。
2. VS Codeのターミナルで初回の準備を実行します。

```powershell
python scripts/build_onedir.py --setup-only
```

3. Pythonインタープリターに `.venv\Scripts\python.exe` を選びます。**F5で起動・デバッグ**、**Ctrl+Shift+BでEXE作成**です。

[詳しい手順](VSCODE_GUIDE.md)。Windows用EXEの出力先は `dist\ExLauncher\ExLauncher.exe` です。

SHA-256: `409e948615b578e6035c108e32239a3cd489ceb92ea2c586bb76e766afa6f384`

[前版 v1.0.7（編集時の開閉状態維持）](ExLauncher_Codex_Handoff_v1.0.7_Selective_Edit.zip)
