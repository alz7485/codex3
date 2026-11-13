# AcadStadio

## 文字プレビュー・表の列追加の修正版（1.65.1-beta95）

[ソースZIPを直接ダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_v1.65.1_TextPreviewMetricsTrial95.zip)

文字サイズ・配置・ズーム追従、数値から表の列を作る機能、ホバー強調と1クリック決定の簡易候補ポップアップを含みます。2026-11-14に、公開済みTrial93からこのチャットの修正を再構成して配布しました。以前の作業環境のZIPそのものではなく、再構成して検証した版です。

コア429件・関連GUI41件成功。Windows／AutoCAD実機および今回の全GUI一括確認は未実施。Python版は `python -m pip install -r requirements.txt` を実行してください。SHXや未導入フォントは代替表示です。EXEは含みません。

## 既存の配布版

既存版: **1.65.0-beta95**

[ソースZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_v1.65.0_RepeatCirclePointTrial95.zip)

円・点の入力欄の下に＋を追加しました。入力中の図形を確定し、同じ枠で次の図形を入力します。追加済みの図形はプレビューに残ります。円の半径／直径の指定と値を引き継ぎ、次の中心Xを全選択します。追加分は個別の標準コマンドとして保存します。

追加済みがある場合、キャンセルは入力中のみ取り消します。詳しくは同梱docs/CONTINUOUS_FIGURES.mdを参照してください。

候補選択は右クリックメニューと同じ簡易ポップアップです。マウスを合わせると図形を強調し、1クリックで候補を決定します。交点は2図形を強調。

**コア423件・全GUI398件（69ファイル）成功**。フルログ・docs/VALIDATION.mdを同梱しています。Trial93のGUI監査修正も含みます。交点は単一線分・円に対応。Windows/AutoCAD実機確認は未実施です。ソース、サンプル、onedir EXE化コマンド同梱。
