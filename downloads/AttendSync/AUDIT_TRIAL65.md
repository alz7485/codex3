# Trial65 集約・最終監査

6役の独立テストで見つかった指摘を原因ごとにまとめ、9件を修正しました。各担当の再試験、別担当の最終監査8本、全52回帰スクリプトが成功しました。

Windows実機・実COM・実送信は未検証です。旧ハッシュしかなく移行前に宛先表示名が変更されている場合の履歴照合には制約があります。以下の最終監査報告に詳細を記載しています。

# Trial65 独立最終監査

対象：`AttendSync_Trial65_Independent_Audit_Complete/AttendSync`。比較元：Trial64 Classic Outlook COM。
最終監査担当は製品ソースを変更していない。6担当の再現・再試験証拠と64→65の差分を確認し、別途8本の統合受入テストを実行した。

## 判定

**監査で再現した9原因は修正済み。独立最終監査の8統合テストは全成功。未解決の確認済み実害はない。**

修正途中のOutlook再試験で見つかった「必須Toが空だと社員宛先も空になる」問題も追加の第9原因として含め、最終修正後のOutlook13テスト成功と最終監査の実宛先保持を確認した。修正前の失敗ログを成功と数えていない。

## 原因単位の集約

| # | 原因・実害 | 修正の確認 |
|---|---|---|
| 1 | 正しいBase64で包まれた不正JSON等の復旧snapshotが社員情報を壊す | 全snapshotをUTF-8/JSON/保存schemaで検証してから復旧。不正なら社員2ファイル不変・journal保持。未知の正当な拡張情報は維持 |
| 2 | 不完全なcache.valuesを使い、元データの不一致を一致にする | 設定上の全キー・値型・period検証状態を確認し、不正cacheは原本を再解析。CSV/XLSX双方を確認 |
| 3 | clock/duration設定変更後に旧XLSX cacheを使い、空欄数式0を誤判定 | 抽出に影響するclockキー集合をparserとtagで共通化。ON/OFFだけではtag不変、集合変更はtag変更 |
| 4 | 省略可能な旧scalar設定でKeyErrorとなり読込全体が停止 | 共通read_configで既定値を補完。直接解析・ReadWorker・tag・GUI保存を確認。元cfgと未知拡張を保持 |
| 5 | 秒差は不一致になるがUI/メールに双方同じ分表示が出る | 非0秒を表示し9:00:01と9:00:02を区別。分単位表示・翌日表記・長時間の境界も再確認 |
| 6 | XLSX対象年月が未知/別表記だと前年を当年と解釈し一致にする | 既知日本語/区切り形式を解析して年違いを拒否。空欄・未知はperiod_unverifiedとして一致判定を保留。cache往復・表示filter後も要確認を維持 |
| 7 | 一部社員をメール処理した後、残り社員の実行ボタンが戻らない | QThread.finished後に操作を戻す。未処理のみ継続し、処理済/処理不明を再処理しない |
| 8 | COMで使わない宛先表示名変更が同じメールの再送を許す | 実COM内容を基にv2指紋。旧COM/Graph履歴のaliasを作り、移行後の表示名変更でも外部操作しない |
| 9 | 厳格なアドレス解析で空の必須Toとの連結が社員宛先を空にする | 空の追加Toを連結しない。先頭末尾の区切りを除去。非空なのに全空解析なら明示エラー。通常/表示名付き/区切り付き宛先を確認 |

複数担当による同じcache不完全・clock cache指摘は重複計上していない。

## 各担当の最終証拠

| 担当 | 最終修正版の結果 | 証拠 |
|---|---|---|
| 破壊・故障注入 | 20/20本＋追加49条件成功 | `../destructive/audit_faults_trial65.log`, `recheck_extra65.log` |
| 誤操作・変な使用 | 22条件成功 | `../misuse/recheck_trial65.log`, `recheck_trial65.json` |
| 欠損・不正データ | 10/10本、実cache経路・年月プローブ成功 | `../missing/retest65.log`, `worker_cache65.log`, `period65.log` |
| 誤判定・集計 | 独立4本成功、1,212月/19,392 assertions、実XLSX20ケース、UI36組 | `../judgment/audit_suite_trial65.log`, `verify65_boundaries.log` |
| 設定変更・移行 | 15/15本＋実データ省略6条件成功 | `../settings/results_trial65.log`, `verify_defaults_data.log` |
| Outlook COM | 拡張13/13本成功 | `../outlook/probe65.log` |
| 独立最終監査 | 独自8/8本成功 | `verify_final.py`, `verify_final.log` |

本数と条件数は粒度が違うため、合算した「総テスト数」にはしていない。製品同梱の全回帰スクリプト実行結果はroot担当の別の回帰記録で管理する。

## 独自統合受入の内容

1. 対象月未確定のXLSXをJSON cache相当へ往復し、一致に変わらず、欠損月filterでも隠さない。
2. 当年の日本語・空白付き・YYYY-MM・YYYY/MMの4形式を受理し、同じ4形式の前年を拒否する。
3. 復旧snapshotの不正読込metadata3種を全件無変更で拒否し、正当な未知入れ子拡張を保持して復旧する。
4. 非解析設定・照合ON/OFFはtag不変、clock集合変更はtag変更、6scalar省略時のtagを既定値補完後と一致させる。
5. 実XLSXとCSVの秒差を照合し、UI用値と社員別生成本文に秒差が残る。必須To未指定でも社員宛先が残る。
6. 旧COM/Graphの送信済履歴をそれぞれ移行し、後の表示名変更でも合成COMの作成/送信を実行しない。
7. COMで無視される表示名だけの変更は新規送信にせず、実際の本文変更は新しい内容として処理する。
8. 単純/表示名付き/先頭末尾区切り付きのメールアドレスを保持し、不正アドレスを黙殺しない。

再実行：

```sh
QT_QPA_PLATFORM=offscreen /workspace/attendsync-audit/venv/bin/python /workspace/attendsync-audit/trial65-audit/final/verify_final.py
```

## 確認の範囲・制約

Linux / Python 3.12 / PySide6 offscreen、合成TemporaryDirectory、模擬COMのみを使った。実データ・実COM・実Outlook/Excel接続・認証・ネットワーク・git操作・実メール送信は実行していない。Windows実機のCOM接続、Outlookセキュリティ確認画面、Exchange権限、オフライン送信待ち、実配送・実印刷機は未検証。COM Sendの成功は「送信要求済み」であり、配達完了を保証しない。

重複防止は同じデータフォルダの処理履歴が維持されている範囲に限る。旧Trial64/Graphの履歴はハッシュのみで、旧時点の表示名を既に変更している場合、過去の実payloadを復元できず完全な移行照合はできない。旧履歴と一致した場合はv2 aliasを保存するため、その後の表示名変更は防げる。この移行制約を「修正完了によって過去すべての重複を防げる」と表現してはならない。

## 全回帰記録の最終確認

root担当の `/workspace/attendsync-audit/trial65-validation/existing_results.json` を確認し、**全52スクリプトがreturncode 0**で終了していることを確認した。新設 `test_trial65_audit_regressions.py` は12テスト成功。全回帰の実行記録は担当別の独立監査件数と分けて扱う。

初回に `test_trial30_dynamic_failures.py` が、ASTで抜き出したReadWorkerの実行名前空間へ追加依存 `read_config` を注入していなかったためNameErrorとなった。その後の差分を独立確認し、engineのimportとAST用nsへのread_config追加のみで、故障注入や期待値を緩めていないことを確認した。再実行ログは破損XLSX・cache再利用・statエラー注入・ファイル集計整合性の全成功を示す。

`test_trial62_audit_regressions.py` の正常cache fixtureは、新しい完全性要件に合わせ全valuesキーを持つよう更新されている。不正schemaを拒否する期待値は維持されている。

最終判定：**9原因の修正確認、独立最終受入8/8成功、全52回帰スクリプト成功。実機・旧履歴移行に関する上記制約を明記した状態でリリース可能。**
