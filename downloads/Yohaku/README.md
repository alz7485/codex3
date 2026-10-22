# 余白 / YOHAKU v0.8.0

<img src="../../Yohaku/companion/assets/app/yohaku.png" width="112" alt="余白のアイコン">

仕事に、ひと呼吸。予定とファイル履歴をそっと知らせる、デスクトップの小さな同僚です。

[完全ソースZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/Yohaku/Yohaku-v0.8.0-source.zip)

- 会話文と発生ロジックはJSONに保存。アプリ内の編集画面で変更し、保存後すぐ反映。
- セリフや話題の追加・削除、時間帯・曜日・予定前後・表情・重み・再発言間隔、キャラの性格、全体の頻度・表示秒数を編集可能。JSON入出力・取り消し・初期値へのリセット・バックアップも用意。
- 各キャラ16種の表情・しぐさ＋8コマの歩行。約60fpsを目安に加減速・呼吸・体の揺れを描画。
- A：気の利くノート、B：几帳面なロボ、E：まじめな応援ペンギン、F：お茶好きののんびりねこ。固有の性格を設定から切り替え。
- 計392のセリフを約10分ごと。時間帯・曜日・予定の前後で話題を変え、繰り返しを抑制。
- 吹き出しは約1分表示。キャラをクリックすると問いかけと縦4行の選択肢。
- キャラ・吹き出しを右クリックして非表示。タスクバーの通知領域に常駐し、アイコンを左クリックすると表示／非表示を切り替え。
- 「予定を聞く」「一言を聞く」は吹き出し内。「ファイル起動履歴を見る」「設定を開く」は専用画面。
- ファイル履歴は設定でオンにした場合だけ。このPC内に保存し、カレンダーで日付を選択。

[会話の編集画面](../../Yohaku/docs/dialogue-editor.png) · [発生ルールの編集](../../Yohaku/docs/dialogue-rules.png) · [JSONの仕様](../../Yohaku/docs/DIALOGUE_JSON.md)

[動作プレビュー](../../Yohaku/docs/motion-preview.gif) · [表情一覧](../../Yohaku/docs/expression-preview.png) · [性格・会話のルール](../../Yohaku/docs/CONVERSATION.md)

## Windowsでonedirを作る

ZIPをすべて展開し、64bit Python 3.11を導入したWindows 11で、`Yohaku`フォルダーをターミナルで開きます。
**同梱の `ONEDIR_COMMAND.txt` の5行を順に貼り付けて実行してください。バッチや仮想環境の有効化は不要です。**

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean Yohaku.spec
.\.venv\Scripts\python.exe scripts\collect_licenses.py dist\Yohaku
.\.venv\Scripts\python.exe -c "import shutil; shutil.make_archive('Yohaku-v0.8.0-windows-x64-onedir', 'zip', 'dist', 'Yohaku')"
```

Python 3.12の場合は、1行目を `py -3.12 -m venv .venv` に置き換えます。

3行目がonedirを作るコマンドです。`Yohaku.spec`でフォルダー形式・アイコン・全キャラの素材を指定しています。
出力：`dist\Yohaku\Yohaku.exe` と、作業フォルダー直下の `Yohaku-v0.8.0-windows-x64-onedir.zip`。
**EXEだけを取り出さず、onedir ZIP全体を展開して配布してください。**

このダウンロードはソースZIPです。ビルド済みEXEは含みません。
GitHubの「Actions」→「Build YOHAKU Windows onedir」→「Run workflow」でも作成できます。

[ソース・詳しい手順](../../Yohaku/README.md) · [アイコンとアプリ名](../../Yohaku/docs/BRAND.md) · [クリック時の画面](../../Yohaku/docs/click-menu.png)

70テスト通過（Linux / Qt offscreen）。Windows実機、実Outlook・Office、Windows用EXEのビルド・実行は未検証です。

SHA-256: `b9396489e759df4a7cd85fd5f4418827689b5081016972fdb9b00607f7f090b3`
