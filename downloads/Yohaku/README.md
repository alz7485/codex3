# Yohaku v0.27.1

自動保存後も「預ける」を利用でき、一覧上の新着メール文は1分後に消えるよう修正しました。「預ける」と「預けたものを見る」の一時ランチャーを使えます。本体は移動・削除せず、アイコン付き一覧からダブルクリックで開きます。保持期間を1日・1週間・1ヶ月・無期限から設定できます。[使い方とリセット](../../Yohaku/docs/SHELF.md) · [表示例](../../Yohaku/docs/shelf.png)

**[onedir用ZIP（約11.2MB）](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/Yohaku/Yohaku-v0.27.1-onedir-build.zip)**

[spec単体](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/Yohaku/Yohaku.spec) · [5行のコマンドと手順](BUILD_ONEDIR.txt) · [SHA-256](Yohaku-v0.27.1-onedir-build.zip.sha256)

ZIPを新しい空の場所へ展開し、Yohaku.specとmain.pyが並ぶYohakuフォルダーでONEDIR_COMMAND.txtの5行を順番に実行します。Windows 11の64bit Python 3.11/3.12を使用し、バッチや仮想環境の有効化は不要です。testsは同梱・要求しません。検査マニフェストは実際のビルド用ファイルだけです。_internalを含むdist/Yohakuフォルダー全体を配布してください。テキスト化・分割はしていません。

PDFを渡すと「ファイルを預ける・移動する・印刷する・キャンセル」、その他のファイル・フォルダーは「預ける・移動する・キャンセル」。次の吹き出しで移動先の表示名を選びます。「移動先を編集する」は吹き出しを閉じ、名前とフルパスを＋ボタンで追加する編集画面を開きます。JSONに保存します。

PDFの印刷は、次の吹き出しからA4・A3・用紙サイズに合わせる、を押すとWindowsの既定プリンターへ直接送信します。A4を超えるページはA3に収め、文書の色も自動判定します。ZIPも含むその他のファイルは移動のみです。3体の小道具ポーズ・全7性格・通知の文字装飾は継続します。

[操作・JSON・印刷の詳細](../../Yohaku/docs/FILE_DROP.md) · [吹き出しの表示例](../../Yohaku/docs/file-drop.png) · [移動先の編集画面](../../Yohaku/docs/file-drop-settings.png) · [Windows検証](https://github.com/alz7485/codex3/actions/workflows/yohaku-windows.yml)
