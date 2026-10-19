# 別のAttendSyncフォルダへ設定を移す場合

この設定ZIPは監査体制だけを含み、アプリ本体や社員データを含みません。このリポジトリでは既に設置済みです。

1. 設定ZIPを一時フォルダへ展開します。
2. AttendSyncの`main.py`と`engine.py`があるフォルダへ、`AGENTS.md`、`.codex/`、`docs/audit/`、`scripts/audit_control.py`、`tests/test_audit_framework.py`を配置します。
3. 既存のAGENTS.mdや.codex/config.tomlがある場合は上書きせず、元の内容を保持して監査用の節・設定だけを統合します。既存の`[agents]`節は二重に作らず、その節へ必要なキーを追加します。同名の役定義・スクリプト・文書がある場合も差分を確認して統合してください。モデル・権限・既存の並列上限を無断で変えないでください。
4. `.gitignore`へ必要に応じて`audit-runs/`を追加します。社員データや監査中のログを公開しないでください。
5. Python 3.11以上で `python scripts/audit_control.py check` と `python scripts/audit_control.py resolve` を実行して構成と対象を確認します。
6. ローカルCodexでこのプロジェクトを開き直します。既存の信頼設定・ホスト権限を尊重し、利用できるサブエージェント機能を確認します。名前付き役が使えないホストではAGENTS.mdに従い役の指示を実spawnへ渡します。

「通常監査して」「完成監査して」「修正後監査して」のいずれかで監査を依頼できます。設定ZIPの検証記録は構築時のものであり、設置先の製品を監査済みにするものではありません。
