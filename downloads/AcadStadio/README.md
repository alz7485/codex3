# AcadStadio Trial70

[最新版ソースZIP](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_v1.51.0_CornerTreatmentTrial70.zip)

「編集・複写」に日本語表記の「面取り」「角丸め」を追加。2本の独立した直線を選択し、面取り距離1・2／丸め半径を指定します。処理後の線・円弧をプレビューし、元の線と作成した図形への点参照も更新します。専用アイコンとサンプルJSON／SCRを同梱。対応範囲は docs/DRAWING_COMMANDS.md を参照してください。

ポリラインは新規2点・閉じない（0）で開始。2点では閉じないのみ選択でき、3点目を追加すると閉じる（1）を初期選択します。3点以上では切り替えや変数・式を使用可能。3点以上の範囲では明示的な選択を保持し、2点へ戻すと0に戻ります。

コア350件・実Tk GUI327件、すべて合格。前点ボタン・点参照拡張、フランジと継手の部分サンプルも含みます。Windows EXE・AutoCAD実機は未検証。onedir EXE化コマンド同梱。ユーザープロジェクトのDataは含みません。
