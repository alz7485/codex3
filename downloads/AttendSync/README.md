# AttendSync Trial47

[最新版ZIPをダウンロード（約10.4MB）](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AttendSync/AttendSync_Trial47_Window_Folder_Drop_Complete.zip)

メイン画面内のどこにでも、勤怠データのフォルダ1個をドロップできます。結果表・検索欄・年月入力・ログ欄・ボタンの上も対応します。ドロップ後はフォルダ欄が更新され、「読み込み・照合」で開始します。読み込み中は変更を受け付けません。

フォルダのみ受け付け、ファイル単体・複数フォルダ・Web URL・通常テキストは拒否します。元のフォルダは移動しません。後から追加するメイン画面の子ウィジェットにも対応します。

今回の関連5テストスクリプトが合格しました。新規5メソッドは11か所への実Qtイベント配送・無効データ・読み込み中・別ダイアログ・動的な項目追加を検証しています。キーボード5件と画面解放10件も合格。ZIPのCRCと同梱SHA256を確認しています。

[Trial47の変更と検証](VALIDATION_TRIAL47.md)

Trial46で完了した4人の専門監査と修正を継承しています。照合処理・枠線UI・設定配置・JSONによる項目拡張・画像付き操作マニュアル・onedir構成は維持しています。

[Trial46専門監査](AUDIT_TRIAL46.md) / [Trial46配布物の独立検査](PACKAGE_CHECK_TRIAL46.md)

このZIPはソース版で、Windows用EXEは含みません。Windowsで同梱のEXE化手順に従いbuild_onedir.pyを実行し、生成された dist\AttendSync フォルダ全体（_internalとManualを含む）を渡してください。受取側にPythonは不要です。ExcelジャンプにはMicrosoft Excelが必要です。

Linux/Qt offscreenで検証しています。Windows Explorerからの実ドラッグ、Windows EXE起動、実Excel・プリンター・会社の実データでの確認は未実施です。更新前に既存userdataをバックアップしてください。

ZIP：376ファイル / 10,872,248バイト  
SHA256：`e58133163d7c93e1a17cda32546fcc45a4e73f56738c9321d3b91d457d13dce2`

## Trial47追加監査

全40テストスクリプト、追加の境界試験8件、メイン画面の全84ウィジェットでの実Qtイベント配送が合格しました。修正が必要な問題は見つかりませんでした。ZIPの375ファイルのSHA256と作業ソースが一致し、GitHub掲載ZIPのサイズ・Git blob SHAも一致しています。ZIPは変更していません。

[追加監査報告](AUDIT_TRIAL47.md) / [全40本の実行記録](audits/Trial47/All_Test_Results.json) / [追加試験コード](audits/Trial47/Boundary_Audit.py) / [追加試験ログ](audits/Trial47/Boundary_Audit.log)
