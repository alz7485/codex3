# ACadPresetter RC42（Windows専用・ソース版）

[修正版ZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/ACadPresetter/ACadPresetter_RC42_Windows_Source.zip) / [SHA256](ACadPresetter_RC42_Windows_Source.zip.sha256)

[更新内容と使い方](UPDATE_RC42.md) / [検証結果](VALIDATION_RC42.md) / [役割別監査](ROLE_AUDIT_RC42.md)

PDF検出を壊す役、AutoCAD処理、保存・復旧、Windows配布・設定の4担当で監査し、担当を入れ替えて再レビューしたRC42です。書込み中のPDF検出、コピー中の更新、日時だけ変わった既存PDFの誤採用を修正しました。最終保存や生成直後のAutoCAD接続断が失敗しても新規PDFを保全し、表示・履歴へ実際の回収先を記録します。

基本の生成名は `図面A.dwg` → `図面A (1).pdf`。通常出力と複数Layout出力とも登録元のCAD名を使い、Unicode・空白・末尾表記を正規化して照合します。印刷開始時刻との日時比較は使用しません。RC39～RC41の修正も引き継いでいます。

結合後に変更された個別PDFの保持、印刷設定復元失敗時の停止、図面なし起動での環境取得、設定画面の現在入力による診断も修正しています。

Windows / Python 3.11または3.12（64bit）/ AutoCAD 2025または2026を対象とします。Adobe PDFを使用する場合はAdobe PDFプリンターとAcrobatが必要です。

ZIPを展開し、展開先の`ACadPresetter_RC42`で実行します。

```text
python -m pip install -r requirements.txt
python main.py
```

「設定」→「AutoCAD」→「Adobe PDF生成先」に、Adobeプリンター側と同じ自動保存先を指定してください。最終PDFの保存先・名前はプリセットで指定します。

既存の`data`フォルダは上書きせず引き継いでください。EXEは含みません。WindowsでのEXE作成手順はZIP内の`BUILD_onedir.txt`にあります。

クラウド検証では全403テスト（役割別の追加62件を含む）が成功しています。実AutoCAD＋Adobe PDFでの解消確認、Windows EXEのビルド・起動は未実施です。詳細は同梱の`VALIDATION_RC42.md`を参照してください。

[旧版RC41 ZIP](ACadPresetter_RC41_Windows_Source.zip) / [RC41更新記録](UPDATE_RC41.md)

[旧版RC40 ZIP](ACadPresetter_RC40_Windows_Source.zip) / [RC40更新記録](UPDATE_RC40.md)

[旧版RC39 ZIP](ACadPresetter_RC39_Windows_Source.zip) / [RC39更新記録](UPDATE_RC39.md)
