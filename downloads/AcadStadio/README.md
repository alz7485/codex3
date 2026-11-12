# AcadStadio

最新: **1.59.1-beta85**

[ソースZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_v1.59.1_ContinuousPointPickTrial85.zip)

- 円弧は数値の3点をcommand-sへ一括で渡す方式へ変更。
- 作図前にTILEMODE=1、OSNAPCOORD=1。終了時に元の値・作図空間・UCSを復元。
- 点参照はX→同じ点のY、XY/Y→次の点のXへ続けて入力。参照元を引き継ぎ、新規座標は0。
- プレビュー通常線1px、選択線2px。参照点と移動量は別入力。

検証: コア398件、関連GUI6件成功。GUI全体の再実行、Windows/AutoCAD実機確認は未実施です。
ZIPにはソース、サンプル、onedir EXE化コマンドを同梱しています。
