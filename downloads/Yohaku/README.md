# 余白 / YOHAKU v0.6.0

<img src="../../Yohaku/companion/assets/app/yohaku.png" width="112" alt="余白のアイコン">

仕事に、ひと呼吸。予定とファイル履歴をそっと知らせる、デスクトップの小さな同僚です。

[完全ソースZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/Yohaku/Yohaku-v0.6.0-source.zip)

- A：余白ノート、B：事務ロボ、E：まじめなペンギン、F：お茶ねこ。設定から切り替え。
- 歩行・表情アニメーション。クリックで問いかけと縦4行の選択肢。
- 「予定を聞く」「一言を聞く」は吹き出し内。「ファイル起動履歴を見る」「設定を開く」は専用画面。
- ファイル履歴は設定でオンにした場合だけ。このPC内に保存し、日付別に表示。

## Windowsでonedirを作る

ZIPをすべて展開し、64bit Python 3.11または3.12を導入したWindows 11で `BuildWindows.cmd` を実行します。
`Yohaku.spec`、`scripts/build_onedir.py`、アイコン（PNG / ICO）、4キャラとアニメーション素材を同梱しています。

出力：`dist\Yohaku\Yohaku.exe` と `release\Yohaku-v0.6.0-windows-x64-onedir.zip`。
**EXEだけを取り出さず、onedir ZIP全体を展開して配布してください。**

このダウンロードはソースZIPです。ビルド済みEXEは含みません。
GitHubの「Actions」→「Build YOHAKU Windows onedir」→「Run workflow」でも作成できます。

[ソース・詳しい手順](../../Yohaku/README.md) · [アイコンとアプリ名](../../Yohaku/docs/BRAND.md) · [クリック時の画面](../../Yohaku/docs/click-menu.png)

42テスト通過（Linux / Qt offscreen）。Windows実機、実Outlook・Office、Windows用EXEのビルド・実行は未検証です。

SHA-256: `8127f876e15af9e82d712ef9330e4e2cdaa4d108eb990856ff0710eec7fc3c3c`
