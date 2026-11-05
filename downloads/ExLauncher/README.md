# ExLauncher v1.0.12

[Classicの展開待ち・改善版ソースZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/ExLauncher/ExLauncher_Codex_Handoff_v1.0.12_Classic_Expand.zip)

Classicも個別ファイル/フォルダアイコンの取得を待たずに一覧を展開し、後から順次更新します。同じパスと再展開ではキャッシュを利用します。Modernのv1.0.11までの改善も含みます。

116テスト成功（Linux/Qt offscreen）。Windows実機・Windows EXEは未検証です。OSアイコン1件の取得が非常に遅い場合、展開後の取得中に入力待ちが残ることがあります。

ZIPをすべて展開し、main.pyと.vscodeがあるフォルダをVS Codeで開いてください。初回は `python scripts/build_onedir.py --setup-only` で準備し、`.venv\Scripts\python.exe` を選択します。MicrosoftのPython/Python Debugger拡張を使い、F5で起動、Ctrl+Shift+BでEXE作成です。

[詳しい手順](VSCODE_GUIDE.md)。Windows用EXEの出力先は `dist\ExLauncher\ExLauncher.exe` です。ソースZIPであり、ビルド済みEXEは含みません。旧版へ戻す前に未確定の復旧記録を解決し、手動削除しないでください。

SHA-256: `5a1d8edb875e48af92d8aa0c0004de09ea04877ce6f5075de9a293b84c0d39bd`

[前版 v1.0.11（Modern展開待ち改善）](ExLauncher_Codex_Handoff_v1.0.11_Faster_Expand.zip)
