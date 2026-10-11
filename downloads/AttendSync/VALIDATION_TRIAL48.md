# Trial48 採用アイコンの反映

元の青・緑のアイコンをベースに、書類・時計・チェックの外形をはっきりさせ、各オブジェクトを枠いっぱいまで拡大。時計の枠・針・目盛りは黒に近い焦げ茶。XLSX/CSV内部の小さい四角いセルは薄い枠線。外側はRGBA透過。ユーザー採用済み画像をそのままPNGに使用した。

更新: AttendSync.png、AttendSync.ico、AttendSync_icon_base64.txt、主要5画面と画像マニュアル。Pythonの本番処理・試験・onedirビルドに変更なし。

ICOに16/24/32/48/64/128/256pxの7サイズを格納。PNG/ICOのアルファ、各サイズの復号、ICOとBase64の一致を確認。Qt実Windowが同じ7サイズでアイコンを読み込み可能。小サイズのエッジは標準アンチエイリアスを含む。

メイン画面の未読込・起動月度・照合結果・ダーク・最小サイズの5画面を撮影。合成4人サンプルは一致357/不一致3/要確認0を維持。今回のtest_ui_static.pyとtest_trial39_manual.py合格。画像マニュアルのリンクを維持。Trial47の全40本と境界8件の監査結果はFinalReviewsへ同梱（今回の実行結果と混同しない）。

Windowsビルドはbuild_onedir.pyの既存--icon指定とICOコピーで新アイコンを使用。dist/AttendSync全体を配布。PNGをそのまま置き換えただけでは既存EXEの埋込アイコンは変わらないので、新しいソースでEXEを再ビルドする。

Linux/Python3.12/Qt offscreenで検証。Windows Explorer・タスクバーでの実表示、Windows EXEビルド、実Excel・プリンターは未確認。Windowsのアイコンキャッシュにより旧アイコンが残る可能性がある。ソースZIPにWindows EXEは含まれない。
