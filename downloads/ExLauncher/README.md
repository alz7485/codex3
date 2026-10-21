# ExLauncher v1.0.6

[VS Code対応・修正版ソースZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/ExLauncher/ExLauncher_Codex_Handoff_v1.0.6_VSCode_Build.zip)

`No module named PyInstaller` に対応し、プロジェクト内の `.venv` にPySide6とPyInstallerを準備します。ランチャー本体はv1.0.5と同じです。

1. ZIPをすべて展開し、main.pyと.vscodeがあるフォルダをVS Codeで開きます。Microsoftの「Python」「Python Debugger」拡張を使用します。
2. VS Codeのターミナルで初回の準備を実行します。

```powershell
python scripts/build_onedir.py --setup-only
```

3. Pythonインタープリターに `.venv\\Scripts\\python.exe` を選びます。**F5で起動・デバッグ**、**Ctrl+Shift+BでEXE作成**です。

[詳しい手順](VSCODE_GUIDE.md)。Windows用EXEの出力先は `dist\\ExLauncher\\ExLauncher.exe` です。

67テスト成功。日本語・空白を含むパスでPyInstallerの実ビルドとQt起動をLinux上で確認しました。Windows上のVS Code/F5/BAT/EXEは未検証です。ソースZIPであり、ビルド済みEXEは含みません。

SHA-256: `e2a4bb15d59bb8254abde263f7cc4e7810e96a5fc3c671ebc429e43f53a418fa`

[前版 v1.0.5（通常監査の不具合修正版）](ExLauncher_Codex_Handoff_v1.0.5_Audit_Fixes.zip)
