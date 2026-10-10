# AttendSync Trial45

[最新版ZIPをダウンロード（約10.3MB）](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AttendSync/AttendSync_Trial45_Bordered_UI_Complete.zip)

採用された枠線付きUIを実装しました。配置と照合処理を維持し、各エリア・入力欄・設定グループの境界を見やすくしています。

- 各エリアと入力欄の枠線を青みのあるグレーで強調。
- 照合結果の表に縦横の罫線を表示。
- 設定グループに薄い背景を付け、保存ボタンの上に区切り線を追加。
- ライト／ダーク双方に対応。読み込み速度と範囲は設定の先頭、月度処理はXLSX設定の末尾です。
- 後からの項目追加・改名・照合条件追加・未知のJSON属性保持に対応。
- 起動時はPCの日付の年・月を対象月度に指定（10/16も10月度）。社員ID管理は未紐づけを初期表示し、未紐づけ0人なら全員を表示します。
- Trial44の社員ID保存・空白ID判定・新規社員フィルター修正を継承しています。

![Trial45 枠線付きメイン画面](Trial45_Main.png)

![Trial45 枠線付き設定画面](Trial45_Settings.png)

全数は「ON照合項目数 × 読み込み済みXLSX社員数 × 月度日数」です。一致・不一致・判定要確認・未照合の内訳を表示します。欠落・重複・読み込み失敗などがある場合は全数一致とは表示しません。未読込社員の人数は全数に含められないため、読み込み診断も確認してください。

全35テストスクリプト成功。UI・設定・マニュアルの関連54テストも成功。120人合成サンプルは一致10,797／不一致3／予定10,800項目を維持。[検証報告](AUDIT_TRIAL45.md)を参照してください。

## 会社へのonedir配布

このZIPはソース版です。Windowsでrequirements-build.txtを導入し、build_onedir.pyを実行してください。生成された `dist\AttendSync` フォルダ全体を渡します。`AttendSync.exe`、`_internal`、`Manual` 等をそのまま保持してください。受け取り先へのPython導入は不要です。ExcelジャンプにはMicrosoft Excelが必要です。

ZIP展開後、CODEX_START_HERE.txt と AttendSync/README.md を参照してください。ビルド済みWindows EXEは含みません。

設定・社員ID・キャッシュはEXE隣のuserdataに保存し、書込不可の場合は%LOCALAPPDATA%\AttendSyncを使用します。更新前に旧userdataをバックアップしてください。Trial43以前でCSV未読込のままID管理を保存した場合は、スタッフIDに表示用「—」が混入していないか確認し、誤ったIDを元のCSVと照合して登録し直してください。

画像付き操作マニュアル18章を同梱。主要画面はTrial45で撮影し、補足画面はTrial42から継承しています。Windows実機・EXE起動・Excel COM実機・実プリンター・今回のマニュアルの実ブラウザー確認は未実施です。

SHA256: `7e9557625cf2b9d0656dc2706bd180136dcb3e43d0a7d84e9c6bf7dfeb7a9309`
