# FolderAdjuster（Windows・名前変更／削除エラー対策版）

[最新版onedir ZIPをダウンロード（Python不要）](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/FolderAdjuster/FolderAdjuster-Windows.zip)

ZIP全体を展開して `FolderAdjuster/FolderAdjuster.exe` を起動してください。`_internal` フォルダも必要です。

長い名前や階層を退避先に重ねる問題を修正。共有ロックの短時間再試行、対象と原因の表示、アプリ横のoperation-errors.logを追加。Windowsの97件のテストと展開後のEXE起動確認が成功しました。

[ソース版ZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/folder-tool-windows.zip)

ソース版は展開して `start.bat` を実行します。Python 3.10以上が必要です。

[Windows EXEのビルドとダウンロード](https://github.com/alz7485/codex3/actions/workflows/windows-build.yml)

成功した実行の `FolderAdjuster-Windows` をダウンロードしてください。EXE版はPython不要です。

履歴からの復元、進捗・キャンセル、削除プリセット、絞り込み、巻数表示、同名比較を追加しました。詳しくはREADME.mdをご覧ください。

ソース版ZIP SHA256: `b671cacc41ceeef609d148c1385caa4c8c85edaa05ae900210e1fe7b32a19c8c`
