# Yohaku v0.23.0

**[onedirでEXE化するためのZIP（約8.0MB）](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/Yohaku/Yohaku-v0.23.0-onedir-build.zip)**

[specファイル単体](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/Yohaku/Yohaku.spec) · [コマンドと手順](BUILD_ONEDIR.txt) · [SHA-256](Yohaku-v0.23.0-onedir-build.zip.sha256)

ZIPだけを新しい場所へ展開し、Yohaku.specとmain.pyが並ぶYohakuフォルダーでONEDIR_COMMAND.txtの5行を順番に実行してください。Windowsの64bit Python 3.11または3.12を使用します。バッチファイルは不要です。

テストフォルダーはビルドにも実行にも不要です。このセットにはtestsを含めず、検査マニフェストも実際に同梱するファイルだけに揃えています。分割版や以前のソースと混ぜる必要はありません。spec単体を使用する場合も本体と素材を含むZIPが必要です。

出力はdist/Yohaku/Yohaku.exeです。EXEだけではなく、_internalを含むdist/Yohakuフォルダー全体を配布してください。ZIPと同じspecファイルを単独でもダウンロードできます。テキスト化はしていません。

アプリはつづり・ビット・ペンギーの3体と全7性格・1,519文を含みます。[アプリの説明](../../Yohaku/README.md) · [ビルド検証](https://github.com/alz7485/codex3/actions/workflows/yohaku-windows.yml)
