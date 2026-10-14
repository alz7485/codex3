# Microsoft 365 初回接続設定（Trial54）

新しいOutlookはMicrosoft Graph経由で下書き保存・送信します。会社のMicrosoftアプリIDとテナントIDの登録が必要です。

1. Microsoft Entraの「アプリの登録」で会社用アプリを作成し、会社のサポートするアカウント種別を設定します。
2. 「認証」でモバイル/デスクトップアプリのプラットフォームと `http://localhost` のリダイレクトURIを登録します。パブリッククライアントとして使い、クライアントシークレットは不要です。
3. Microsoft Graphの **委任権限** `User.Read`、`Mail.ReadWrite` を追加します。自動送信を使う場合は `Mail.Send` も追加し、会社の方針に合わせて同意を設定します。
4. アプリのアプリケーション（クライアント）IDとディレクトリ（テナント）IDを控えます。
5. 勤怠チェッカーの「設定→メール」で、送信するMicrosoft 365アカウントと上記2つのIDを入力します。必須To/CC、差出人名・敬称、件名・本文・署名を設定して保存します。
6. 初回のメール作成時にブラウザで指定アカウントへサインインします。自動送信初期OFFは下書き保存、ONは対象社員を選んで実行すると送信します。勤怠読み込みだけでは送信しません。

本文の `{differences}` の位置へ社員ごとの不一致を差し込みます。実際の送信元は接続したアカウントです。Windowsの認証情報はWindowsユーザーに紐づけて暗号化保存します。

同内容の二重処理を履歴で防ぎ、通信エラーによる結果不明時に自動再送しません。Outlook側で下書き・送信済みを確認してください。送信受付は配達完了を保証しません。

本リリースでは模擬APIで検証し、会社テナントでの実接続・実送信は未検証です。初回は自動送信OFFで下書き内容を確認してください。

[Microsoft: 下書き作成と権限](https://learn.microsoft.com/en-us/graph/api/user-post-messages) / [Microsoft: 送信と権限](https://learn.microsoft.com/en-us/graph/api/message-send) / [Microsoft: デスクトップアプリ登録](https://learn.microsoft.com/en-us/entra/identity-platform/scenario-desktop-app-registration)
