# 余白 / YOHAKU v0.6.1

<img src="../../Yohaku/companion/assets/app/yohaku.png" width="112" alt="余白のアイコン">

仕事に、ひと呼吸。予定とファイル履歴をそっと知らせる、デスクトップの小さな同僚です。

[完全ソースZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/Yohaku/Yohaku-v0.6.1-source.zip)

- A：余白ノート、B：事務ロボ、E：まじめなペンギン、F：お茶ねこ。設定から切り替え。
- 歩行・表情アニメーション。クリックで問いかけと縦4行の選択肢。
- 「予定を聞く」「一言を聞く」は吹き出し内。「ファイル起動履歴を見る」「設定を開く」は専用画面。
- ファイル履歴は設定でオンにした場合だけ。このPC内に保存し、日付別に表示。

## Windowsでonedirを作る

ZIPをすべて展開し、64bit Python 3.11を導入したWindows 11で、`Yohaku`フォルダーをターミナルで開きます。
**同梱の `ONEDIR_COMMAND.txt` の5行を順に貼り付けて実行してください。バッチや仮想環境の有効化は不要です。**

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean Yohaku.spec
.\.venv\Scripts\python.exe scripts\collect_licenses.py dist\Yohaku
.\.venv\Scripts\python.exe -c "import shutil; shutil.make_archive('Yohaku-v0.6.1-windows-x64-onedir', 'zip', 'dist', 'Yohaku')"
```

Python 3.12の場合は、1行目を `py -3.12 -m venv .venv` に置き換えます。

3行目がonedirを作るコマンドです。`Yohaku.spec`でフォルダー形式・アイコン・素材を指定しています。
出力：`dist\Yohaku\Yohaku.exe` と、作業フォルダー直下の `Yohaku-v0.6.1-windows-x64-onedir.zip`。
**EXEだけを取り出さず、onedir ZIP全体を展開して配布してください。**

このダウンロードはソースZIPです。ビルド済みEXEは含みません。
GitHubの「Actions」→「Build YOHAKU Windows onedir」→「Run workflow」でも作成できます。

[ソース・詳しい手順](../../Yohaku/README.md) · [アイコンとアプリ名](../../Yohaku/docs/BRAND.md) · [クリック時の画面](../../Yohaku/docs/click-menu.png)

42テスト通過（Linux / Qt offscreen）。Windows実機、実Outlook・Office、Windows用EXEのビルド・実行は未検証です。

SHA-256: `5cd51c3aeeb1e324157ae255278ed03f1b04e652960bf07ed3b136880ce61805`
