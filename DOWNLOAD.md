# FolderAdjuster（Windows・onedir版）

[onedir版ZIPをダウンロード（Python不要）](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/FolderAdjuster/FolderAdjuster-Windows.zip)

ZIP全体を展開して `FolderAdjuster/FolderAdjuster.exe` を起動してください。`_internal` フォルダも必要です。EXE単体を移動しないでください。

監査で再読み込み・キャンセル時の一覧不整合を修正。LinuxとWindowsで77件のテストが成功し、展開後の起動と設定保存も確認しました。

[ソース版ZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/folder-tool-windows.zip)

ソース版は展開して `start.bat` を実行します。Python 3.10以上が必要です。

[Windows EXEのビルドとダウンロード](https://github.com/alz7485/codex3/actions/workflows/windows-build.yml)

成功した実行の `FolderAdjuster-Windows` をダウンロードしてください。EXE版はPython不要です。

履歴からの復元、進捗・キャンセル、削除プリセット、絞り込み、巻数表示、同名比較を追加しました。詳しくはREADME.mdをご覧ください。

ソース版ZIP SHA256: `82ef83368bd79a36a92db8013b7c111ae5a8e1a6bb5e7bfbebba99223fbdbf01`
