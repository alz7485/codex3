# 余白 / YOHAKU v0.12.0

<img src="../../Yohaku/companion/assets/app/yohaku.png" width="112" alt="余白のアイコン">

仕事に、ひと呼吸。予定とファイル履歴をそっと知らせる、デスクトップの小さな同僚です。

| ダウンロード | サイズ | 検証 |
|---|---|---|
| [ZIP 1/2](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/Yohaku/Yohaku-v0.12.0-source-part1-of-2.zip) | 12.07 MB | [SHA-256](Yohaku-v0.12.0-source-part1-of-2.zip.sha256) |
| [ZIP 2/2](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/Yohaku/Yohaku-v0.12.0-source-part2-of-2.zip) | 12.07 MB | [SHA-256](Yohaku-v0.12.0-source-part2-of-2.zip.sha256) |

**両方のZIPを同じ場所へ展開し、Yohakuフォルダーを統合してください。** 共通のREADME・マニフェスト等は同一内容なので、上書き確認は許可します。片方だけでは必要な素材・コードが揃いません。

それぞれ普通のZIPで、片方ずつテキスト化・復元できます。連結専用のバイナリ分割ではなく、画像やコードの途中では切っていません。実行・onedirビルドに必要な素材、4キャラ、アイコン、設定初期値、直接コマンドを含みます。ビルド済みEXEは含みません。

- 4キャラに正面・正面まばたき・困る・怒る表情を追加。ペンギンの翼は左右1本ずつ。5秒以内に左クリック4回で困る、7回で怒り、10秒触らなければ通常へ。セリフ・回数・秒数はJSONと編集UIで変更可能。右クリック・ドラッグは数えません。
- 会話・予定・新着・退勤前・呼び出しの吹き出しは見出しと×なし。本文と必要な選択肢だけを表示。本文の行数に合う高さで、通常メッセージ・通知はクリックで閉じます。
- 新着は「山田さんからメールが来ました。」のような一文で通知。送信者を別の行へ列挙せず、件数も付けません。件名・本文・添付ファイルを読みません。
- 未読が初期5件以上なら、件数を含む白い通常メッセージの候補に追加。重み2・優先度1で少し選ばれやすくし、約10分の会話機会と1時間の再発言間隔を守ります。未読数の変化だけでは通知しません。
- 未読数は既定の受信トレイから取得。90秒以上古い値や取得不能な値では発言しません。しきい値・優先度・セリフはJSONと編集UIで変更できます。
- ドラッグで自由に配置し位置を保存。別モニターに対応し、画面上部では吹き出しをキャラの下へ表示。
- 左クリックで一言、右クリックで呼び出し。「予定を聞く」「ファイル起動履歴を見る」「設定を開く」「非表示にする」の4行。
- 未承諾・仮承諾の会議も読み込み。既定予定表と受信トレイの会議案内を統合して重複を除外し、一部取得は画面に表示。承諾・辞退・既読化・予定追加は行いません。
- 予定は淡い黄、新着は淡い青。通知領域のアイコンの左クリックでキャラを表示／非表示。
- A：余白ノート、B：事務ロボ、E：まじめなペンギン、F：お茶ねこ。20種の表情・しぐさ＋8コマの歩行。
- 定時までの残り時間は「1時間40分」形式。
- 50話題・596のセリフ。PC操作時間・Office文書数・デスクトップ件数・定時・使用日・予定数・ファイル開き直し等の状況で選択。勤務時間は初期08:30〜17:30。
- 会話文・発生ルール・キャラの性格はJSON保存。アプリ内の編集UIで保存後すぐ反映。バックアップと入出力にも対応。
- ファイル履歴は3か月・最大15,000件。ファイル名欄を拡張し取得元列を削除。ダブルクリックで開き、カレンダーの選択日は青・今日は黄。記録は初期オフ。
- 退勤前通知は初期17:00。時刻・メッセージ・利用者が入力する勤怠URLを設定できます。PC起動時刻と経過時間を添え、サイトを開くか選択します。URL未登録なら設定へ案内。自動入力・送信は行いません。

[正面と連打への反応](../../Yohaku/docs/front-reactions.png) · [退勤前通知](../../Yohaku/docs/departure-preview.png) · [履歴画面](../../Yohaku/docs/history-calendar.png) · [コンパクトなメッセージ](../../Yohaku/docs/draggable-preview.png) · [未読の一言・予定・新着通知](../../Yohaku/docs/notification-colors.png) · [編集画面](../../Yohaku/docs/dialogue-editor.png) · [発生ルール](../../Yohaku/docs/dialogue-rules.png) · [JSONの仕様](../../Yohaku/docs/DIALOGUE_JSON.md)

## Windowsでonedirを作る

2つのZIPの展開・統合後、64bit Python 3.11を導入したWindows 11で、Yohakuフォルダーをターミナルで開きます。
**両方に同梱した `ONEDIR_COMMAND.txt` の5行を順に貼り付けます。バッチや仮想環境の有効化は不要です。**

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean Yohaku.spec
.\.venv\Scripts\python.exe scripts\collect_licenses.py dist\Yohaku
.\.venv\Scripts\python.exe -c "import shutil; shutil.make_archive('Yohaku-v0.12.0-windows-x64-onedir', 'zip', 'dist', 'Yohaku')"
```

Python 3.12の場合は、1行目を `py -3.12 -m venv .venv` に置き換えます。

出力は `dist\Yohaku\Yohaku.exe` と `Yohaku-v0.12.0-windows-x64-onedir.zip`。
EXEだけを取り出さず、onedir ZIP全体を展開して配布してください。
GitHubの「Actions」→「Build YOHAKU Windows onedir」→「Run workflow」でも作成できます。

[詳しい手順とソース](../../Yohaku/README.md) · [取得範囲](../../Yohaku/docs/CONTEXT_NOTIFICATIONS.md) · [アプリ名とアイコン](../../Yohaku/docs/BRAND.md)

133テスト通過（Linux / Qt offscreen・合成データ・COMモック）。Windows実機、実Outlook・Office、Windows EXEのビルド・実行は未検証です。
