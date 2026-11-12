# AcadStadio

最新: **1.61.0-beta90**

[ソースZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_v1.61.0_LayoutCommandsTrial90.zip)

「空間・レイアウト」分類を追加しました。

- モデル／レイアウト／ビューポート内へ切り替え。
- レイアウトの作成・選択・複製・名前変更。
- 矩形ビューポート作成、番号指定、ロック・解除、表示中心・尺度。
- システム変数を1コマンドで最大100項目設定。数値式、文字列、各行／一度の実行に対応。

終了時は元の作図空間・取得済みシステム設定を復元します。作成したレイアウトやビューポートは残します。プレビューで用紙・ビューポート投影は再現しません。既存ビューポート番号はCADのCVPORTで確認してください。説明は同梱docs/LAYOUT_COMMANDS.mdを参照してください。

検証: コア408件、関連GUI7件成功。GUI全体の再実行、Windows/AutoCAD実機確認は未実施です。ソース、サンプル、onedir EXE化コマンド同梱。
