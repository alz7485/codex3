# FolderAdjuster（Windows・監査修正版onedir）

[監査修正版ZIPをダウンロード（Python不要）](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/FolderAdjuster/FolderAdjuster-Windows.zip)

ZIP全体を展開して `FolderAdjuster/FolderAdjuster.exe` を起動してください。`_internal` フォルダも必要です。

本整理の対象解除と同名衝突表示、編集中の絞り込み、途中キャンセル、連続した操作の復元、Windowsの大小文字だけの変更、壊れた履歴の読込を修正しました。LinuxとWindowsで89件のテストが成功し、展開後のEXE起動と設定保存も確認しました。

[ソース版ZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/folder-tool-windows.zip)

ソース版は展開して `start.bat` を実行します。Python 3.10以上が必要です。

[Windows EXEのビルドとダウンロード](https://github.com/alz7485/codex3/actions/workflows/windows-build.yml)

成功した実行の `FolderAdjuster-Windows` をダウンロードしてください。EXE版はPython不要です。

履歴からの復元、進捗・キャンセル、削除プリセット、絞り込み、巻数表示、同名比較を追加しました。詳しくはREADME.mdをご覧ください。

ソース版ZIP SHA256: `0c3b1c11e578b137393e95b1d02b489dd925e8fcb63f3b3d118c001f335d4660`
