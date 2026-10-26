# Yohaku v0.25.0

**[onedirでEXE化するためのZIP（約11.1MB）](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/Yohaku/Yohaku-v0.25.0-onedir-build.zip)**

[specファイル単体](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/Yohaku/Yohaku.spec) · [コマンドと手順](BUILD_ONEDIR.txt) · [SHA-256](Yohaku-v0.25.0-onedir-build.zip.sha256)

ZIPだけを新しい場所へ展開し、Yohaku.specとmain.pyが並ぶYohakuフォルダーでONEDIR_COMMAND.txtの5行を順番に実行してください。Windowsの64bit Python 3.11または3.12を使用します。バッチファイルは不要です。

テストフォルダーはビルドにも実行にも不要です。このセットにはtestsを含めず、検査マニフェストも実際に同梱するファイルだけに揃えています。分割版や以前のソースと混ぜる必要はありません。spec単体を使用する場合も本体と素材を含むZIPが必要です。

出力はdist/Yohaku/Yohaku.exeです。EXEだけではなく、_internalを含むdist/Yohakuフォルダー全体を配布してください。ZIPと同じspecファイルを単独でもダウンロードできます。テキスト化はしていません。

v0.25.0は3体に受け取り・メール通知・予定確認の計9ポーズを追加しました。OSのファイル／フォルダーアイコンを手に持ち、新着メールでは大きな薄い水色の手紙、予定・リマインダーでは予定表を見せます。ペンギンの名前は「ペギー」に統一し、全7性格を引き継ぎます。時刻・メールなどを色と太字で強調し、登録通知・単発通知では選択した文字の太字と色をJSONに保存できます。[文字の強調](../../Yohaku/docs/MESSAGE_FORMAT.md)[3体の表示例](../../Yohaku/docs/prop-poses.png)

キャラへのファイルのドロップに対応しています。通常ファイルは移動、PDFは移動・印刷、ZIPは移動して解凍。拡張子・移動先・ボタン・パスワードのひな形を専用画面とJSONで編集できます。月は`{month}`で01〜12、`{month1}`で1〜12です。選ぶまで実行せず、上書きは行いません。[使い方とJSON](../../Yohaku/docs/FILE_DROP.md) · [処理を選ぶ画面](../../Yohaku/docs/file-drop.png)

アプリはつづり・ビット・ペギーの3体と全7性格・1,519文を含みます。[アプリの説明](../../Yohaku/README.md) · [ビルド検証](https://github.com/alz7485/codex3/actions/workflows/yohaku-windows.yml)
