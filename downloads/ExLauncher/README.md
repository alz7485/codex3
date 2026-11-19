# ExLauncher v1.0.13

[右クリック編集・中央クリックで保存先表示版ソースZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/ExLauncher/ExLauncher_Codex_Handoff_v1.0.13_Mouse_Actions.zip)

ClassicとModernの通常画面で、アプリを含むファイル項目も右クリックで編集UIを開くようにしました。Explorerの保存先表示（対象ファイルを選択）はホイールクリックへ移動しました。左クリックの起動、他の種類の右クリック編集は維持します。Modernの大量一覧でも同じ操作に対応します。

120テスト成功（Linux/Qt offscreen）。追加4件は100%と200%で成功しています。Windows実機のExplorer実行・マウス/DPI・Windows EXEは未検証です。検証中の外部起動はモックへ置き換えています。両UIの展開待ち改善、保存復旧、設定スライド、長い名前のメニュー修正などは引き継ぎます。

ZIPをすべて展開し、main.pyと.vscodeがあるフォルダをVS Codeで開いてください。初回は `python scripts/build_onedir.py --setup-only` で準備し、`.venv\Scripts\python.exe` を選択します。MicrosoftのPython/Python Debugger拡張を使い、F5で起動、Ctrl+Shift+BでEXE作成です。

[詳しい手順](VSCODE_GUIDE.md)。Windows用EXEの出力先は `dist\ExLauncher\ExLauncher.exe` です。ソースZIPであり、ビルド済みEXEは含みません。旧版へ戻す前に未確定の復旧記録を解決し、手動削除しないでください。

SHA-256: `84bc91ccc7481e2ba1d196992de01f5157a3f7b8bd00e082403863abbd1321f0`

[前版 v1.0.12（Classic展開待ち改善）](ExLauncher_Codex_Handoff_v1.0.12_Classic_Expand.zip)
