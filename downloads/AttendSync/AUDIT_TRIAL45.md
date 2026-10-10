# AttendSync Trial45 枠線付きUIの検証

採用されたイメージを実装した。各エリア・入力欄・設定グループの枠線を強調し、照合結果に縦横の罫線を表示。設定グループの薄い背景と、保存ボタンの上の区切り線を追加。ライト／ダーク双方で確認した。

変更したPythonはmain.py、ui_theme.py、settings_dialog.pyの3ファイル。Pythonの追加・削除はない。engine.py、runtime_paths.py、manual.py、build_onedir.pyはTrial44と同一。社員ID監査修正、起動時のPC月度指定、全数計算、項目追加・改名・照合条件追加・未知JSON属性保持を維持する。

## 実施した検証

- 全35テストスクリプト合格。実行原本はTEST_RESULTS_TRIAL45.json。
- UI・設定・マニュアルの関連54テスト合格。ライト／ダーク、最小1040×690メイン、最小780×580設定、検索・フィルター・テーマ切替・保存を確認。
- 新しい設定グループ背景と表ヘッダーに対する本文・説明文字のコントラスト比は両テーマとも4.5以上。
- 120人合成サンプルは一致10,797／不一致3／要確認0、予定10,800項目を維持。
- 実Qtで19画面を再撮影。マニュアルの主要画面16枚を更新、残る補足画面11枚はTrial42を継承。Previewのライト設定別名3枚も更新。
- マニュアル18章・画像・内部リンク・F1・既定ブラウザー呼出・onedirへの完全コピーを確認。
- ZIPのCRC、各ファイルのSHA256一覧、実データ・userdata・キャッシュ・仮想環境・build・distの除外を確認。

## 会社へ渡すonedir

Windowsでrequirements-build.txtを導入してbuild_onedir.pyを実行する。生成されたdist\AttendSyncフォルダ全体を配布する。AttendSync.exe、_internal、Manual等を保持し、EXE単体を移動しない。受け取り先へのPython導入は不要。ExcelジャンプにはMicrosoft Excelが必要。

設定・社員ID・キャッシュはEXE隣のuserdataに保存し、書込不可の場合は%LOCALAPPDATA%\AttendSyncへ保存する。更新前に旧userdataをバックアップして引き継ぐ。onefile対応は採用していない。

## 確認範囲

Linux/Python3.12/Qt offscreenで検証したソース版。ビルド済みWindows EXEは同梱しない。Windows実機・Excel COM実機・実プリンター・今回のマニュアルの実ブラウザー確認・Windows EXE起動速度は未検証。今回起動時間を再測定していない。Trial44のソース測定をWindows EXE速度として扱わない。

既存の社員IDに表示用「—」が混入していた場合はAUDIT_TRIAL44.mdの確認手順を参照する。
