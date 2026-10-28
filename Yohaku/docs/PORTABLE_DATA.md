# ユーザーデータの保存先（v0.29.0）

現在の保存先は **Yohaku.exeと同じフォルダのData** です。ソースの `python main.py` で起動した場合は、main.pyと同じフォルダのDataになります。PowerShellの作業フォルダやonedirの `_internal` の中には作りません。

```text
Yohaku/
├─ Yohaku.exe
├─ _internal/
└─ Data/
   ├─ settings.json
   ├─ dialogue.json
   ├─ reminders.json
   ├─ one_shot_notifications.json
   ├─ file_destinations.json
   ├─ shelf.json
   └─ files.sqlite3
```

最初の起動時にDataを用意し、settings.jsonを作成します。ほかのJSONは利用・編集・保存に応じて作成します。

| ファイル | 内容 |
|---|---|
| settings.json | キャラ・位置・表示・接続・履歴のオン/オフ等 |
| dialogue.json | 会話、性格、会話ロジック |
| reminders.json / one_shot_notifications.json | 登録通知 / 一度きりの通知 |
| context_options.json / topic_preferences.json | 営業日・対象ファイル等 / 話題の表示設定 |
| file_drop_settings.json / file_destinations.json | ファイル操作の設定 / 移動先の表示名とパス |
| shelf.json | 預けたものの参照と保持期間 |
| history.json / usage.json | 通知済み状態等 / PC利用状況の集計 |
| files.sqlite3 | ファイル起動履歴。記録をオンにした場合に保存 |

各JSONのバックアップもData内です。同梱の素材・初期値としてのJSONは、ユーザー設定とは別にアプリの素材フォルダに残ります。

## v0.28.2以前からの初回移行

以前の保存先は `%LOCALAPPDATA%\Yohaku`（通常は `C:\Users\ユーザー名\AppData\Local\Yohaku`）でした。

- **Dataがない場合**、旧保存先の既知の設定JSON・JSONバックアップ・ファイル履歴DBをコピーします。元の保存先は削除しません。
- **Dataが既にある場合**、空フォルダであってもそちらを優先します。旧保存先との混合や上書きはしません。
- コピーは一時フォルダで完了してからDataとして確定します。途中で失敗した場合は起動を止め、未完了のDataを使いません。原因を解消して起動し直すと再試行します。
- 旧版が起動中の場合は、終了を案内して移行を止めます。履歴DBはSQLiteのバックアップ機能で、確定済みの最新記録も取り込みます。
- Dataに書き込めない場合はエラーを表示します。別の場所へ保存先を戻すことはありません。アプリを自分が書き込めるフォルダへ置いてください。

## 今後の更新とバックアップ

1. 起動中のYohakuを終了します。
2. 現在のDataフォルダ全体をバックアップします。
3. 新しいonedirを別の空フォルダへ配置します。
4. 現在のDataを、新しいYohaku.exeの隣へコピーします。
5. 新版を起動し、キャラ・会話・通知・移動先・履歴を確認します。

更新先に既存のDataがある場合はバックアップし、使いたいDataを選んで配置してください。アプリは既存のDataを優先します。Dataを持ち越さない新しい配置先では、旧LocalAppDataのコピーまたは初期設定からの起動となります。

配布ソースZIP・onedirビルド用ZIP・EXEの素材には、使用中のDataを同梱しません。ビルドしたアプリで自分の設定を継続する場合も、使用中のDataをEXEの隣へ別途コピーしてください。

成長システムの進行はData/growth.json、編集コンテンツはData/content、診断はData/growth-content.logに保存します。これらもData全体と一緒にバックアップ・更新先へコピーしてください。
