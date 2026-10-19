# AttendSyncの監査体制

プロジェクトを開いたCodexへ、そのまま次のいずれかを指示します。

- `通常監査して`：主要6グループを並列確認して統括。
- `完成監査して`：12専門役を分離して全分野を確認し、別の統括役がクロスレビュー。
- `修正後監査して`：差分・依存箇所・既存機能の副作用と元の指摘を確認して統括。

`Trial65を完成監査して`、`この差分を修正後監査して` のように対象や基準も指定できます。監査だけではコードを修正しません。修正する場合は監査報告を受けて別途指示してください。

## 設定ファイル

- `AGENTS.md`：3指示のルーティング、無変更原則、実行順序。
- `.codex/config.toml`：公式 `[agents]` 設定。最大同時サブエージェント6。モデル/プロバイダ/権限/グローバル設定は変更しません。
- `.codex/agents/*.toml`：指定の12専門役＋統括役の13定義。公式の `name` / `description` / `developer_instructions` 形式。
- `.codex/audit.toml`：このプロジェクト独自の編成・対象選択メタデータ。Codex本体の設定schemaではありません。
- `PROTOCOL.md` / `REPORT_TEMPLATE.md`：実行・報告・完成判定の共通仕様。
- `scripts/audit_control.py`：構成の検査、編成表示、対象解決の補助。これ自体はサブエージェントや製品テストを起動しません。

```text
python scripts/audit_control.py check
python scripts/audit_control.py plan --mode normal
python scripts/audit_control.py plan --mode complete --capacity 6
python scripts/audit_control.py plan --mode postfix --changed classic_outlook.py outlook_mail.py
python scripts/audit_control.py resolve
```

## 対象選択と成果物

このリポジトリは別製品も含むため、未指定時はAttendSyncの最大Trial番号の完全版ZIPを使います。AttendSyncの直接ソースフォルダへ監査キットを設置した場合は直接ソースを選びます。既存の公開ZIPや製品コードは変更しません。

報告・再現コード・ログは一時監査領域か`audit-runs/`へ保存します。`audit-runs/`はgitignore対象で、報告を公開する操作は自動では行いません。必要な時だけ明示的に依頼してください。

## 実環境の制約

現在のホストは主担当＋最大6並列です。完成監査は通常6役×2巡、その後に統括役を起動します。ホストのspawn APIは`agent_type`非対応なので、定義を読み初期指示に渡す方式を使用します。名前付きカスタム役を直接指定できるCodexでは役名で利用できます。

カスタム役は親の権限を継承します。役のTOMLに`sandbox_mode`を書いて個別の読み取り専用権限を設定する方式は使いません。原本無変更の指示と一時コピー上のテスト、前後の差分・ハッシュ確認を組み合わせます。設定はCodexの起動時に読まれるため、ローカルCodexで既に開いていた場合はプロジェクトを開き直して適用を確認してください。

今回の構築検証は監査設定と実際の並列起動を確認するもので、製品の通常/完成/修正後監査を実施済みにするものではありません。

この環境ではグローバルCodexホームとプロジェクト信頼設定が読み取り専用のため、ローカルCLIによる設定の受理・名前付き役の自動登録は未検証です。既存の信頼・権限設定は変更していません。現在のホストでは役定義を初期指示として渡す方式で実際に起動できました。確認結果と残存する制約は [構築検証記録](VALIDATION.md) を参照してください。補助スクリプトにはPython 3.11以上が必要です。

## 公式仕様

確認日：2026-10-18。ローカル確認対象：codex-cli 0.159.0-alpha.3。

- [Codexのサブエージェント](https://developers.openai.com/codex/multi-agent)
- [AGENTS.mdの読み込み](https://developers.openai.com/codex/guides/agents-md)
- [設定リファレンス](https://developers.openai.com/codex/config-reference)

設定名・スキーマは実行環境の版に依存します。適用できない環境では制約を報告し、AGENTS.mdと役の指示を実spawnへ渡す方式で代替します。設定を書いただけで現セッションへ自動登録されたとは扱いません。
