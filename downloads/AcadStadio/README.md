# AcadStadio

最新: **1.63.0-beta92**

[ソースZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_v1.63.0_LayerCommandsTrial92.zip)

標準の「設定」分類に再作図・レイヤー変更を追加しました。

- 再作図：現在のビュー／全ビューを選択。
- レイヤー変更：色、線種、線の太さ、印刷、表示、フリーズ、ロック、透明度、説明、名前を一括変更。空欄は変更しません。
- 登録コマンドの旧15例を初期登録から削除。読み込み時も未使用・未変更の例だけ整理し、使用中または編集済みの定義は保持。
- 線種読込・寸法スタイルの作成等はCAD設定へ集約。

空間別タブと連動するブロック一覧、レイアウト込みDWG／DXF読込、システム変数の一括設定も含みます。レイヤー変更の説明は同梱docs/COMMAND_REGISTRATION.mdを参照してください。

検証: コア417件、関連GUI26件成功。GUI全体の再実行、Windows/AutoCAD実機確認は未実施です。ソース、サンプル、onedir EXE化コマンド同梱。
