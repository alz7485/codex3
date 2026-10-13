# ACadPresetter RC41（Windows専用・ソース版）

[修正版ZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/ACadPresetter/ACadPresetter_RC41_Windows_Source.zip) / [SHA256](ACadPresetter_RC41_Windows_Source.zip.sha256)

[更新内容と使い方](UPDATE_RC41.md) / [検証結果](VALIDATION_RC41.md)

作成済みPDFが認識されない問題に対応したRC41です。印刷開始時刻との日時比較を除去し、印刷前後の情報・内容ハッシュで新規生成を確認します。更新日時・サイズが保持される場合やサーバーとの時計差に対応し、Unicode・空白・末尾(1)を正規化して照合します。検出できない場合は実際のファイル名と除外理由をログへ残します。

基本の生成名は `図面A.dwg` → `図面A (1).pdf`。通常出力と複数Layout出力とも登録元のCAD名を使います。RC39/RC40の修正も引き継いでいます。

Windows / Python 3.11または3.12（64bit）/ AutoCAD 2025または2026を対象とします。Adobe PDFを使用する場合はAdobe PDFプリンターとAcrobatが必要です。

ZIPを展開し、展開先の`ACadPresetter_RC41`で実行します。

```text
python -m pip install -r requirements.txt
python main.py
```

「設定」→「AutoCAD」→「Adobe PDF生成先」に、Adobeプリンター側と同じ自動保存先を指定してください。最終PDFの保存先・名前はプリセットで指定します。

既存の`data`フォルダは上書きせず引き継いでください。EXEは含みません。WindowsでのEXE作成手順はZIP内の`BUILD_onedir.txt`にあります。

クラウド検証では全341テストが成功しています。実AutoCAD＋Adobe PDFでの解消確認、Windows EXEのビルド・起動は未実施です。詳細は同梱の`VALIDATION_RC41.md`を参照してください。

[旧版RC40 ZIP](ACadPresetter_RC40_Windows_Source.zip) / [RC40更新記録](UPDATE_RC40.md)

[旧版RC39 ZIP](ACadPresetter_RC39_Windows_Source.zip) / [RC39更新記録](UPDATE_RC39.md)
