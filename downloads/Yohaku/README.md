# Yohaku v0.19.2

仕事に、ひと呼吸。予定とファイル履歴を知らせるデスクトップの小さな同僚です。

| ダウンロード | サイズ | 検証 |
|---|---|---|
| [ZIP 1/2](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/Yohaku/Yohaku-v0.19.2-source-part1-of-2.zip) | 12.86 MB | [SHA-256](Yohaku-v0.19.2-source-part1-of-2.zip.sha256) |
| [ZIP 2/2](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/Yohaku/Yohaku-v0.19.2-source-part2-of-2.zip) | 12.86 MB | [SHA-256](Yohaku-v0.19.2-source-part2-of-2.zip.sha256) |

**両方のZIPを同じ場所へ展開し、Yohakuフォルダーを統合してください。** 共通のREADME・マニフェスト・コマンドは同一内容です。片方ずつテキスト化・復元できる普通のZIPです。バイナリの分割連結は不要です。

v0.19.2では、通常メッセージ20秒・通知1分に変更しました。起動・クリック後はおおむね1秒以内に歩き始め、通常メッセージを出したまま、0.4〜1.2秒の短い休止で歩きます。選択肢や通知入力中、連打反応では停止します。[表示時間と歩行](../../Yohaku/docs/TIMING_MOTION.md)

v0.19.1では、吹き出しの通知時刻をHH:mm全体で入力・貼り付けできるようにし、過去日と今日の過去時刻を登録できないようにしました。未完成・不正・期限切れの入力ではOKが無効になります。監査7件（日跨ぎ予定、JSON検証・容量境界、割合の読み上げ名、条件一覧）も修正しています。[修正内容](../../Yohaku/docs/FIXES_0_19_1.md)

あわせて12話題と252件のセリフを追加しました。全76話題、7性格それぞれ217件、計1,519件です。

- 今日の計測時間に対する操作の割合を、最低計測量と%で判定。会話編集の専用フォームから変更できます。
- 今日の残りの予定数・時間・最大同時件数・次の予定の長さを、取得済みの新しい完全な予定表から算出します。
- 操作再開と近い予定、文書数とメモリ、予定前の電源、定時前の片づけ、金曜の引き継ぎも通常会話の候補になります。
- 旧設定の編集内容を保ち、新しい話題だけを一度追加。既に200件なら上限を超えて増やしません。追加で2MiBを超えるときも追加を見送り、既存設定を使用します。
- 先輩の心の声は「…」だけの返事で表示。孤高の債務者は体言止め・倒置法を軸にします。
- 単発通知、吹き出しのファイル履歴と予定、Outlook予定表へのボタン、3か月の全履歴検索なども同梱します。
- ディスクの空き容量は扱いません。会話はローカルの定型文で、追加の外部送信・文書内容の収集はありません。

[条件と初期値](../../Yohaku/docs/EXTENDED_LOGIC.md) · [割合の編集画面](../../Yohaku/docs/ratio-condition.png) · [7性格の表示例](../../Yohaku/docs/personality-examples.png) · [使い方](../../Yohaku/README.md)

## Windowsでonedirを作る

両方のZIPを展開・統合後、64bit Python 3.11を導入したWindowsでYohakuフォルダーを開きます。
`ONEDIR_COMMAND.txt` の5行を順に貼り付けます。バッチや仮想環境の有効化は不要です。

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean Yohaku.spec
.\.venv\Scripts\python.exe scripts\collect_licenses.py dist\Yohaku
.\.venv\Scripts\python.exe -c "import shutil; shutil.make_archive('Yohaku-v0.19.2-windows-x64-onedir', 'zip', 'dist', 'Yohaku')"
```

Python 3.12では1行目を `py -3.12 -m venv .venv` に変更します。
出力は `dist\Yohaku\Yohaku.exe` と `Yohaku-v0.19.2-windows-x64-onedir.zip`。EXEだけを取り出さず、onedir全体を配布してください。ここで配布する2つのZIPはソースで、ビルド済みEXEを含みません。

309件のテストをLinux / Qt offscreen・合成データ・COMモックで確認しています。Windows実機、実Outlook・Office、Windows EXEのビルドと実行は未検証です。
