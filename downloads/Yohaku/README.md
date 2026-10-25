# Yohaku v0.23.0

つづり・ビット・ペンギーの3体と、全7種類の性格を選べるデスクトップの小さな相棒です。

| ダウンロード | サイズ | 検証 |
|---|---|---|
| [ZIP 1/2](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/Yohaku/Yohaku-v0.23.0-source-part1-of-2.zip) | 4.08 MB | [SHA-256](Yohaku-v0.23.0-source-part1-of-2.zip.sha256) |
| [ZIP 2/2](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/Yohaku/Yohaku-v0.23.0-source-part2-of-2.zip) | 4.04 MB | [SHA-256](Yohaku-v0.23.0-source-part2-of-2.zip.sha256) |

両方を同じ場所に展開し、Yohakuフォルダーを統合してください。独立した通常のZIPなので、片方ずつテキスト化・復元できます。共通のREADME・マニフェスト・コマンドは同じ内容です。

v0.22.0の2つのZIP合計 31.37 MBから、8.12 MBへ約74%削減しました。廃止した4体の素材と重複する静止画を削除し、大きな説明用画像・GIFはGitHub閲覧に分けています。実行用の素材・ソース・ビルド用コードはすべて同梱しています。実行時の画像ダウンロードはありません。

全76話題・7性格それぞれ217文、計1,519文のセリフは維持します。編集した会話・条件・性格の個別指定も引き継ぎます。廃止したキャラを選択していた場合はつづりに切り替えます。

静かな時間は自動会話と通知だけを休み、キャラの動きを継続します。設定・履歴・編集画面を開いたままでも歩けます。起動・再表示・ドラッグ終了後も短い待ちで再開します。呼び出し・リンク付きの吹き出し・通知入力・連打反応・ドラッグ中は立ち止まり、歩行オフ・アニメーションオフ・非表示・画面共有・おやすみは尊重します。

[キャラ・互換性・動作の説明](../../Yohaku/docs/NEW_CHARACTERS.md) · [実装画像](../../Yohaku/docs/new-characters.png) · [導入と更新](../../Yohaku/docs/INSTALL_UPDATE.md) · [全機能の使い方](../../Yohaku/README.md)

## Windowsでonedirを作る

64bit Python 3.11を導入したWindowsで、2つのZIPを展開・統合後のYohakuフォルダーを開き、ONEDIR_COMMAND.txtの5行を順に実行します。バッチファイルや仮想環境の有効化は不要です。

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean Yohaku.spec
.\.venv\Scripts\python.exe scripts\collect_licenses.py dist\Yohaku
.\.venv\Scripts\python.exe -c "import shutil; shutil.make_archive('Yohaku-v0.23.0-windows-x64-onedir', 'zip', 'dist', 'Yohaku')"
```

Python 3.12の場合は1行目を `py -3.12 -m venv .venv` に変更します。
出力は `dist\Yohaku\Yohaku.exe` と `Yohaku-v0.23.0-windows-x64-onedir.zip` です。EXEだけを取り出さず、onedir全体を配布してください。ここで配布する2つのソースZIPにはビルド済みEXEを含みません。

337件の合成データによるテストをLinux / Qt offscreenで確認。Windowsでのテスト・EXEビルド・描画チェックは[Actions](https://github.com/alz7485/codex3/actions/workflows/yohaku-windows.yml)で確認できます。実Outlook・物理PCのトレイやDPI・長時間常駐は自動確認の対象外です。
