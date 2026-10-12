# ACadPresetter RC39（Windows専用・ソース版）

[修正版ZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/ACadPresetter/ACadPresetter_RC39_Windows_Source.zip) / [SHA256](ACadPresetter_RC39_Windows_Source.zip.sha256)

[更新内容と使い方](UPDATE_RC39.md)

AutoCADへ渡す座標・尺度の2値変換、Adobe PDFの生成名照合・待機・取り込み、設定画面・診断ログ、PDF結合を改善したRC39です。元のRC38を基準にしています。

Windows / Python 3.11または3.12（64bit）/ AutoCAD 2025または2026を対象とします。Adobe PDFを使用する場合はAdobe PDFプリンターとAcrobatが必要です。

ZIPを展開し、展開先の`ACadPresetter_RC39`で実行します。

```text
python -m pip install -r requirements.txt
python main.py
```

「設定」→「AutoCAD」→「Adobe PDF生成先」に、Adobeプリンター側と同じ自動保存先を指定してください。最終PDFの保存先・名前はプリセットで指定します。

既存の`data`フォルダは上書きせず引き継いでください。EXEは含みません。WindowsでのEXE作成手順はZIP内の`BUILD_onedir.txt`にあります。

クラウド検証では全317テストが成功しています。実AutoCAD＋Adobe PDFでの解消確認、Windows EXEのビルド・起動は未実施です。詳細は同梱の`VALIDATION_RC39.md`を参照してください。
