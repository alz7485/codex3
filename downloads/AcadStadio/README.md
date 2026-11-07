# AcadStadio Trial77

[最新版ソースZIP](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_v1.55.0_CADDrawingImportTrial77.zip)

「ファイル」にDWG／DXFからプロジェクトを作成、作図だけ追加、の2機能を追加しました。対応するモデル空間の2D図形を実際の数値で登録し、作図・寸法・テキストの3ブロックに分けます。新規プロジェクトはレイヤー・文字／寸法スタイル・線種・図面設定も取り込み、作図だけ追加では設定・表・変数を保持します。

DXFはezdxfで直接読込。DWGは起動中のWindows版AutoCADで一時コピーをDXFへ変換し、元ファイルは保存しません。未対応・省略する項目は読込画面で報告します。表の寸法列・点参照の自動生成は行わず、自動参照への置換は次回予定として記録しています。

コア369件・実Tk GUI343件合格、最終の読込関連9件・UI4件も合格。同梱の docs/CAD_DRAWING_IMPORT.md に対応範囲と制限、examples/CAD読込サンプル に合成DXF・登録JSON・SCRを用意しました。新しい依存ezdxf==1.4.4とonedirビルド設定を追加。Windows EXE・AutoCAD実機は未検証。ユーザーのDataは含みません。
