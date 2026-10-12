# 勤怠チェッカー Trial51

- [必要ファイル版ZIP](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AttendSync/AttendSync_Trial51_Essentials.zip)
- [完全版ZIP](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AttendSync/AttendSync_Trial51_Visual_Guide_Complete.zip)
- [図解操作ガイドPDF（14ページ）](AttendSync_Trial51_図解操作ガイド.pdf) / [単独HTML](AttendSync_Trial51_図解操作ガイド.html)
- [メイン画面](Trial51_Main.png) / [変更内容](CHANGES_TRIAL51.md) / [検証結果](VALIDATION_TRIAL51.md)

タイトル下の説明削除、名称変更、アイコンの水色背景透過、右上ボタン間隔6px。マニュアルは画面別1〜2ページの図解へ簡略化しました。全41テスト成功。ソース版ZIPで、Windows EXEは未同梱です。

以下は過去版の説明です。

# AttendSync Trial50 — 監査6件の修正版

## GitHubからダウンロード

- [必要ファイル版ZIP](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AttendSync/AttendSync_Trial50_Essentials.zip)：実行/ビルド用ソース・アイコン・操作マニュアル。テスト・監査資料・サンプルを省略。
- [完全版ZIP](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AttendSync/AttendSync_Trial50_All_Fixes_Complete.zip)：検証ログ・テスト・監査/引き継ぎ資料を含む。

両方とも同じTrial50アプリソースです。Windows EXEを含む配布版はWindowsでビルドして作成します。

最新版: [AttendSync_Trial50_All_Fixes_Complete.zip](AttendSync_Trial50_All_Fixes_Complete.zip) / [SHA256](AttendSync_Trial50_All_Fixes_Complete.zip.sha256)

同姓同名の自動誤対応、キャッシュ保存失敗時のデータ脱落、構造不正キャッシュ、社員番号重複検査、テーマ即時反映、印刷ダイアログ残留を修正しました。既存40本＋追加1本の計41本成功。実Qtの補足試験も成功。

[変更内容](CHANGES_TRIAL50.md) / [検証結果](VALIDATION_TRIAL50.md)。旧版の自動対応に同姓同名があれば元社員番号・スタッフIDを確認し、社員ID管理から訂正してください。既存対応は自動削除しません。

ソース版ZIPです。Windowsでbuild_onedir.pyを実行してdist/AttendSync全体を配布します。Windows実機・実Excel・実プリンターは未検証。

以下は同梱を継承したTrial49マニュアルの説明です。

# AttendSync Trial49 — 詳細操作マニュアル

[詳細操作マニュアルPDF（59ページ）](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AttendSync/AttendSync_Trial49_%E8%A9%B3%E7%B4%B0%E6%93%8D%E4%BD%9C%E3%83%9E%E3%83%8B%E3%83%A5%E3%82%A2%E3%83%AB.pdf)  
[単独HTML版をダウンロード（画像・PDF内蔵）](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AttendSync/AttendSync_Trial49_%E8%A9%B3%E7%B4%B0%E6%93%8D%E4%BD%9C%E3%83%9E%E3%83%8B%E3%83%A5%E3%82%A2%E3%83%AB.html)  
[マニュアル同梱の最新版ZIP（約9.8MB）](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AttendSync/AttendSync_Trial49_Detailed_Manual_Complete.zip)

18章・画面画像22箇所（21種類）の詳しいマニュアルです。初回の準備から、毎月の照合、全数確認、項目追加、診断、保存先、会社への配布と更新まで説明しています。

- 入力フォルダの中身、2か月CSV、XLSX・CSVの標準列。
- PCの起動日と月度、年またぎ・うるう年、全画面フォルダドロップ。
- 読み込み／完全再読み込み／中止、社員番号とスタッフIDの対応。
- 全数＝項目数×人数×日数、未照合・追加要確認、完了チェックリスト。
- 詳細対比表、Excelへの移動、検索、結果印刷・PDF保存。
- 読み込み速度・範囲、休憩の照合ON、未開示の列の追加、改名・削除。
- 比較方法、表示と照合の独立、JSON保存、数式・エラーの対処表。
- バックアップ・復元、保存先の切替、Windows onedirビルド・会社への配布、FAQ。

アプリの右上「操作マニュアル」またはF1からHTMLを開き、上部「PDFで読む」で同梱PDFも開けます。PDFにはページ番号付き目次、クリック可能な章リンクと18章のしおりがあります。

単独HTMLは保存してブラウザーで開いてください。画像とPDFを内蔵し、インターネット不要です。検索・画像拡大・PDF保存も使えます。

既存onedir版はアプリ終了後に Manual フォルダ全体を更新すれば、新マニュアルを利用できます。本番Python、照合・設定・キャッシュ、採用アイコンに変更はありません。Trial47の全画面ドロップを維持しています。

[今回の変更と検証](VALIDATION_TRIAL49.md) / [Trial47の監査](AUDIT_TRIAL47.md) / [Trial46専門監査](AUDIT_TRIAL46.md)

マニュアル関連10テストが合格。ブラウザーレンダリングで画像読込、検索・Enter、画像拡大・Esc、狭い画面、印刷時の説明展開を確認。単独HTMLのPDF保存、最終PDFと内蔵データの一致、PDF全ページ・目次・しおり・空白ページなし、ZIPのCRC・SHA256を確認しています。実画面の撮影版はマニュアルに明記しています。

最新版ZIPはソース版で、Windows EXEは含みません。新規配布はWindowsで build_onedir.py を実行して生成した dist\AttendSync フォルダ全体を渡します。受取側にPythonは不要です。ExcelジャンプにはMicrosoft Excelが必要です。Windows実機のEXE・実Excel・プリンター・会社の未開示帳票は未確認です。

ZIP：390ファイル / 10,262,760バイト  
SHA256：`d28abd4677243af8e8f0237eb435132f8932d84b9c66b3d35e32a086d702d5f1`
