# ExLauncher v1.0.7

[現在の開閉状態を維持する修正版ソースZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/ExLauncher/ExLauncher_Codex_Handoff_v1.0.7_Selective_Edit.zip)

Modernで、現在のカテゴリ開閉状態を維持したまま編集モードへ入ります。開いている項目は再利用し、閉じたカテゴリはユーザーが開くまで項目を生成しません。編集中も必要なカテゴリだけ開閉できます。編集終了時は従来どおり、編集前の開閉状態へ戻します。

76テスト成功。1,000項目・全カテゴリ収納の合成データでは、編集開始処理の中央値が836.786msから7.707msへ短縮しました（各5回、Linux/Qt offscreen、アニメーションなし）。Windowsの実測値やFPSではありません。

Classic、保存形式、VS Code設定、ビルド環境はv1.0.6を引き継いでいます。

1. ZIPをすべて展開し、main.pyと.vscodeがあるフォルダをVS Codeで開きます。Microsoftの「Python」「Python Debugger」拡張を使用します。
2. VS Codeのターミナルで初回の準備を実行します。

```powershell
python scripts/build_onedir.py --setup-only
```

3. Pythonインタープリターに `.venv\Scripts\python.exe` を選びます。**F5で起動・デバッグ**、**Ctrl+Shift+BでEXE作成**です。

[詳しい手順](VSCODE_GUIDE.md)。Windows用EXEの出力先は `dist\ExLauncher\ExLauncher.exe` です。Windows上のVS Code/F5/BAT/EXEは未検証です。ソースZIPであり、ビルド済みEXEは含みません。

SHA-256: `bd569f3b357cdab118bc2e56d81fe1ee778880712bd2ff2c08ee2e0eb0af5da0`

[前版 v1.0.6（VS Code・ビルド環境対応）](ExLauncher_Codex_Handoff_v1.0.6_VSCode_Build.zip)
