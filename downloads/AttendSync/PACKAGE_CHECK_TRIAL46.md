# AttendSync Trial46 最終配布ZIP 独立確認

実施日: 2026-10-10。対象: `/workspace/outputs/AttendSync_Trial46_Final_Reviewed_Complete.zip`。本体・既存レポート・ZIPは変更していない。この確認結果はZIP外の別ファイルに保存する。

**判定: 最終ソース配布ZIPの構成・整合性チェックはすべて合格。** WindowsのEXEビルド・会社PCでの起動・実Excel・実プリンターは未検証であり、ソースZIPの確認と区別する。

| 確認 | 結果 |
| --- | --- |
| SHA256 | `fbf4257dc6ebc1ec2db67b6b907e523c37c829ce6dccf729c4b2f54445711cc8`、指定期待値と一致 |
| サイズ | 10,861,458 bytes |
| ファイル数 | 372、うちmanifest記載371ファイル |
| ZIP CRC | `ZipFile.testzip()` が None、破損なし |
| MANIFEST SHA256 | 全371件一致 |
| MANIFEST網羅性 | manifestを除く実ファイル集合と記載集合が完全一致 |
| 重複・危険パス | エントリー名重複なし、絶対パス・`..` なし |
| onedir構成 | `--onedir`、`--windowed`、QtSvg hidden import、Manual/ICOコピー、userdata作成が同梱コードに存在 |
| 保存先修正 | fallbackのwrite/flush probe、起動初期化エラー保持とWindowでの再送出を同梱コードで確認 |
| 画像付きマニュアル | 22のローカルPNG参照がすべてZIP内に存在し、PNGヘッダーも正常 |
| 専門レビュー | Engine / Settings / UI / Distribution の4本をFinalReviews内に同梱 |
| 新規回帰テスト | engine / startup / keyboard / dialog_lifecycle の4本を同梱 |
| 全体テスト記録 | TEST_RESULTS_TRIAL46.jsonのresultsは39本・全passed=true。ZIP内のtest_*.py集合と完全一致 |
| 最終修正後の追試記録 | 同JSONのfinal_header_followupは5本・全passed=true。対応するテスト本体も存在 |
| START_HERE | Trial46表記。README、CHANGES_TRIAL46、AUDIT_TRIAL46、VALIDATION_TRIAL46、FinalReviewsの案内と実在を確認。旧Trial44/45案内なし |
| 個人設定・ビルド環境の除外 | userdata、build、dist、.venv、__pycache__、.gitをZIPに含まない |
| XLSX/CSVデータ | 128ファイル、すべて文書化された合成SampleData / SampleData_120内。これら以外の勤怠XLSX/CSVなし |
| 対象ソースとの一致 | main.py / runtime_paths.py / build_onedir.py / test_trial46_startup.py / START_HERE.txt / TEST_RESULTS_TRIAL46.jsonのbytesが修正対象ソースと一致 |

検証スクリプト: `/tmp/final_distribution_review/check_final_package46.py`。機械可読結果: `/tmp/final_distribution_review/package46_results.json`。

このZIPのテスト結果JSONは配布された記録の件数・合格状態・対応テストの存在を検証したもので、この確認作業で39本すべてを再実行したという意味ではない。保存先修正の独立6ケースと配布・マニュアル・Excelモック・印刷の独立確認は既存配布レビュー報告の通り。

Trial45で指摘したP3のSTART_HERE旧版案内は、最終Trial46 ZIPでは修正済み。P2保存先エラーは修正・独立再確認済みで、そのコードが最終ZIPに入っていることも確認した。

最終配布物はWindowsでonedirビルドするための完全ソースZIPで、ビルド済みEXEは含まない。会社へ渡す実行用成果物はWindowsで生成した `dist/AttendSync` フォルダ全体となる。
