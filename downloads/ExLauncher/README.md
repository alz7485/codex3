# ExLauncher v1.0.11

[カテゴリ展開の待ち時間・改善版ソースZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/ExLauncher/ExLauncher_Codex_Handoff_v1.0.11_Faster_Expand.zip)

Modernの初回展開で、登録件数分の個別ファイル/フォルダアイコンの取得を待っていた処理を改善しました。まず汎用またはキャッシュ済みアイコンで開き、展開後に個別アイコンへ順次切り替えます。同じパスの取得と再展開はキャッシュで再利用します。アニメーションの時間と既存の速度設定は維持します。

113テスト成功（Linux/Qt offscreen）。追加9件は100%と200%で成功しています。OS取得1件20msの遅延を入れた模擬条件では、10件の展開完了が456→254ms、50件が1293→269msでした（各3回の中央値）。遅延を入れないLinuxの10件は252→251msです。Windows実機の測定値ではありません。個別取得は展開後に1件ずつ行いますが、単一の遅いOS取得中の入力待ちが残る場合があります。

長い名前のメニュー表示修正、保存失敗対策・大量一覧の可視行描画、設定UIの段階表示、編集開始時の開閉状態維持、VS Code・ビルド環境を引き継いでいます。Windows実機・Windows EXE・独立した正式な修正後監査は未検証です。

1. ZIPをすべて展開し、main.pyと.vscodeがあるフォルダをVS Codeで開きます。Microsoftの「Python」「Python Debugger」拡張を使用します。
2. VS Codeのターミナルで初回の準備を実行します。

```powershell
python scripts/build_onedir.py --setup-only
```

3. Pythonインタープリターに `.venv\Scripts\python.exe` を選びます。**F5で起動・デバッグ**、**Ctrl+Shift+BでEXE作成**です。

[詳しい手順](VSCODE_GUIDE.md)。Windows用EXEの出力先は `dist\ExLauncher\ExLauncher.exe` です。ソースZIPであり、ビルド済みEXEは含みません。旧版へ戻す前に未確定の復旧記録を解決し、記録を手動削除しないでください。

SHA-256: `85936f886bb33b230bdb9408fcf4ea44414c096ad5fd8885c2f57f142f53844a`

[前版 v1.0.10（長い名前のメニュー表示修正）](ExLauncher_Codex_Handoff_v1.0.10_Long_Names.zip)
