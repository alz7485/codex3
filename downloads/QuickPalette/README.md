# QuickPalette

## v2.0.30 Trial 31 — 入力判定の誤起動修正

[修正版ZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/QuickPalette/QuickPalette_v2.0.30_Trial31.zip)

読み取り専用欄や一覧・ボタンにキャレット／選択情報があると入力可能と誤判定する経路を修正しました。非入力・読み取り専用・無効状態を先に確認し、選択取得を対応する編集クラスに限定します。現在のフォーカスと無関係なキャレットやメニュー操作中の入力判定も見直しました。

更新済みソース、標準25テーマ、アイコン、Windows用ビルド手順、検証結果を収録。EXEは含みません。

自動テスト34項目成功。Win32入力判定はAPIを模擬した検証で、Windows実機では未確認です。判定不能（UNKNOWN）の例外アプリ設定は維持しています。詳細はZIP内の `VALIDATION.txt` を参照してください。

SHA-256: `43dce73fcc34ee864ff1a870376209337fb25fd19307ccea5272f95fd2ad3a11`

## 前版

[v2.0.29 Trial 30 ZIP](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/QuickPalette/QuickPalette_v2.0.29_Trial30.zip)
