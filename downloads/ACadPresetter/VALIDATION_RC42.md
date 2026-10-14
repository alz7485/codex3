# RC42 検証記録

- 全体テスト: `QT_QPA_PLATFORM=offscreen python -X faulthandler -m pytest -q -o faulthandler_timeout=20`
- 結果: **403 passed**。失敗・スキップ・xfailなし。
- 実行記録: `validation/pytest_RC42.txt`。
- Python 3.12.14 / PySide6 6.8.3 / pypdf 6.20.0 / pytest 9.1.1。
- `python -m compileall -q app main.py tests`成功。
- 標準`data`の内容はRC41と同じです。

## 回帰テスト

RC41の341件に4役の専用62件を追加しました。役割ごとの対象と担当を入れ替えたレビュー結果は`ROLE_AUDIT_RC42.md`に記録しています。

旧コードへの故障注入では、書込み中のPDFを採用すること、日時だけ更新された既存PDFを採用すること、同じ日時・サイズでコピー中に更新された生成元を削除することなどを実再現しました。修正後は内容の安定・コピー前後の照合・更新された生成元の保持を確認しています。

保存失敗時は実PDFと実ファイル操作を使い、保存先ロック、復旧先の作成／コピー／置換失敗、容量不足、繰り返し清掃を確認しています。画面からの最終保存失敗では、backendから返った成功を失敗へ変更し、既存最終PDFと元CADを保持し、新規PDFの保全先を表示・履歴へ残すことを確認しています。

担当を入れ替えたレビューで見つかった生成直後のAutoCAD接続断は、実backendから`output`のない失敗結果を返す経路で再現しました。単一／複数Layoutとも生成PDFを保全し、正しい履歴行のmessage/traceへ保全先を記録することを確認しています。

既存テストのassertを削除したり、失敗テストを無効化したりしていません。印刷環境取得へオプション引数を追加したため、既存`test_rc22_storage_audit.py`の代替probeを`lambda *_, **__: env`へ更新しています。

## 配布確認

ZIPのCRC検査、同梱`MANIFEST_SHA256.txt`による全ファイルの内容照合、ZIPから展開したPythonファイルのコンパイル、テスト結果の同梱を確認しました。ZIP外の`.sha256`は配布ZIP全体のSHA256です。

EXE・仮想環境・Pythonキャッシュ・実行時の復旧ファイルをZIPへ含めません。歴代の更新記録は履歴として残してあり、現行の説明はRC42のファイルです。

## 未実施の確認

検証環境はLinuxです。Windowsレジストリ・AutoCAD COM・プリンター生成・共有違反等の境界を代替しています。実AutoCAD＋Adobe PDF、実UNC／SMB、Windows EXEのビルド・起動は未検証です。実機での確認方法は`実機テスト手順.txt`にあります。
