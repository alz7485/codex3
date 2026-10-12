# ACadPresetter RC40（Windows専用・ソース版）

[修正版ZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/ACadPresetter/ACadPresetter_RC40_Windows_Source.zip) / [SHA256](ACadPresetter_RC40_Windows_Source.zip.sha256)

[更新内容と使い方](UPDATE_RC40.md) / [検証結果](VALIDATION_RC40.md)

Adobe PDFの検出名を「登録元CADデータ名＋半角スペース(1).pdf」に固定したRC40です。例: `図面A.dwg` → `図面A (1).pdf`。AutoCADが変換後・一時図面の別名を返しても、通常出力・複数Layout出力とも登録元の名前で照合します。RC39の座標・尺度の2値変換、待機・取り込み、設定画面・ログ、PDF結合の改善も引き継いでいます。

Windows / Python 3.11または3.12（64bit）/ AutoCAD 2025または2026を対象とします。Adobe PDFを使用する場合はAdobe PDFプリンターとAcrobatが必要です。

ZIPを展開し、展開先の`ACadPresetter_RC40`で実行します。

```text
python -m pip install -r requirements.txt
python main.py
```

「設定」→「AutoCAD」→「Adobe PDF生成先」に、Adobeプリンター側と同じ自動保存先を指定してください。最終PDFの保存先・名前はプリセットで指定します。

既存の`data`フォルダは上書きせず引き継いでください。EXEは含みません。WindowsでのEXE作成手順はZIP内の`BUILD_onedir.txt`にあります。

クラウド検証では全325テストが成功しています。実AutoCAD＋Adobe PDFでの解消確認、Windows EXEのビルド・起動は未実施です。詳細は同梱の`VALIDATION_RC40.md`を参照してください。

[旧版RC39 ZIP](ACadPresetter_RC39_Windows_Source.zip) / [RC39更新記録](UPDATE_RC39.md)
