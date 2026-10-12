# RC40 検証記録

RC39を基準に、Adobe PDFの検出名と元CADパスの引き渡しを修正しました。

- 全体テスト: `QT_QPA_PLATFORM=offscreen python -X faulthandler -m pytest -q`
- 結果: **325 passed**、失敗・スキップなし。
- Pythonコンパイル: `python -m compileall -q app main.py tests` 成功。
- 更新したビルド説明書の回帰テスト: 4 passed。
- Python 3.12.14 / PySide6 6.8.3 / pypdf 6.20.0 / pytest 9.1.1。

追加した8件では、登録元CAD名から半角スペース＋(1)のPDF名を生成する処理、日本語・空白・UNC・複数ピリオド・元名の(1)、元データ名がない場合、通常出力／複数Layout出力の元CADパス伝播を確認しています。

AutoCADが変換後の別名を返す状況をモックで再現し、元CAD名の(1).pdfを取り込めることを確認しました。最終PDF名や変換後図面名が一致する別ファイルは採用せず保持します。半角スペースなし・全角スペース・(2)などを標準経路で採用しないことも確認しています。

RC39の連続出力テストとCOMの2値変換経由の出力テストは、ご指摘の確定した生成名「元CAD名 (1).pdf」に合わせています。一般的な候補照合ヘルパーの互換APIは保持し、実出力経路には完全な検出名を明示して渡しています。

このクラウドはLinuxです。Windowsレジストリ・AutoCAD COMはテスト用に差し替え、PDF処理・Qtテストを実行しています。実AutoCAD＋Adobe PDFでの生成、Windows EXEのビルド・起動は未検証です。
