# AcadStadio Trial78

[最新版ソースZIP](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_v1.56.0_PreviewDirectEditTrial78.zip)

メイン画面のプレビューで図形をダブルクリックすると、対応するコマンド編集を直接開けます。確定するとメイン画面へ戻り、ブロック編集画面は挟みません。ブロック編集のプレビューから開いた場合は、その画面へ戻って変更を保持します。

重なった図形は編集元のコマンド・行を候補から選択。条件分岐・繰り返し内の作図コマンド、クリックした図形の確認行にも対応。取消し、Undo／Redo、メイン画面の表示範囲の維持をテストしています。使い方は docs/PREVIEW_DIRECT_EDIT.md。

コア373件・実Tk GUI347件合格。DWG／DXF読込の対応範囲は前版と同じで、スプライン読込は未対応です。onedirビルド設定と合成DXFサンプルを同梱。Windows EXE・AutoCAD実機は未検証。ユーザーのDataは含みません。
