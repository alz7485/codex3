# AcadStadio

## 最新：1.69.0-beta100 — DWG読込後の表作成・Excel割当サンプル

[テストデータだけをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_ImportTableTestData_Trial100.zip)

[サンプル同梱のTrial100アプリソースZIP](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_v1.69.0_ImportTableSamplesTrial100.zip)

テストデータの `plate_base.dwg` と `plate_values.xlsx` から始めてください。Excel先頭行と同じ幅160・高さ100・4穴φ12の固定図面、変更用2行、3部品の比較用DWG/DXF/PDF、読込直後／Excel読込済み／割当完成のJSON、SCR、手順書を同梱しています。DXFでも同じ試験ができます。

- Excelなしで数値から列を作り、セルへ値を入れる試験。
- Excelの穴径÷2を半径へ割り当て、品番文字を品番列へ割り当てる試験。
- 完成例の3行分57図形は、独立して作図した期待図面と数値・配置が一致。
- 読込文字の内部表記がExcelの文字列と一致しない問題を修正。品番の割当にはTrial100以降を使用してください。
- コア468件・全GUI408件成功。実DXF読込・実xlsx読込からのGUI操作も検証しています。

DWGはGNU LibreDWGの構築APIで生成したAC1015形式です。再変換して基準19図形・期待57図形の数値と配置の一致を確認。Windows／AutoCAD実機でのDWG読込・SCR実行は未確認です。寸法注記は試験用の線と文字で、ネイティブDIMENSIONではありません。

アプリZIPはPythonソース版（EXEなし）。SHA256は各ZIPの隣の `.sha256` ファイルを参照してください。今後の配布はGitHubのみです。

## 以前の配布版

## 1.68.1-beta99 — 高倍率表示の継承ヒント修正

[Trial99 ソースZIPを直接ダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_v1.68.1_InheritedHintDpiTrial99.zip)

- 高倍率表示で継承ヒントの色番号・尺度が省略される問題を修正。空欄・継承状態・SCRは維持。
- GUIテストの元のAssertionErrorを保持し、None結果の二次エラーに隠れないよう改善。
- 全GUIで判明した文字縮小フィルターによる文字高さ・基準線のずれも修正。既存試験の許容幅は変更していません。
- コア462件・全GUI406件成功。高倍率1.5／2.0の回帰テストと修正前後の記録を同梱。

Pythonソース版（EXEなし）。Windows／AutoCAD実機・SCR実行は未確認です。詳しい原因・確認範囲はZIP内 docs/INHERITED_HINT_DPI.md、docs/VALIDATION.md を参照してください。

SHA256: `f206393ba64882e12cba820fc74ad059e6ca5ba7c741d752afc8f819690f5beb`

## 以前の配布版

## 1.68.0-beta98 — 文字と線種の修正

[Trial98 ソースZIPを直接ダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_v1.68.0_TextAndLinetypeTrial98.zip)

- 直径・度・±記号を表示と文字幅・FIT配置の計算へ反映。
- 元フォントの検索、ISO系代替書体、小さい文字の描画を改善。
- 単純線種を図形の長さに基づく線片として描き、255画素制限による崩れを修正。
- Trial97の寸法文字の中央揃え・CAD読込表示の修正も含みます。

コア457件・全GUI405件成功。最終の文字縮小処理後に関連GUI21件も成功。元の文字高さ・LTSCALEは任意に変更していません。SHXなどの代替表示、未対応のLEADER／複数境界HATCH読込の制限は残ります。Windows／AutoCAD実機・SCR実行は未確認です。

Pythonソース版（EXEなし）。依存関係は `python -m pip install -r requirements.txt` で導入してください。検証ログと詳しい制限はZIPに同梱しています。

SHA256: `4ebfc09164e9c0a3abd4b97bd5a93b917a46659e7dd5fbc7f79d118511d5a2ec`

## 以前の配布版

## 1.66.0-beta96 — モデル・レイアウトのフォルダ

[Trial96 ソースZIPを直接ダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_v1.66.0_SpaceFoldersTrial96.zip)

- ブロック一覧のCtrl+Aで、折りたたみも含め検索に一致するブロックを全選択。
- 「モデル」フォルダを初期作成し、削除・改名・移動を禁止。「未分類」を廃止。
- 低いモデルタブの横の「＋」でレイアウトを作成し、同名のフォルダとタブを追加。
- タブ選択時は対応フォルダだけを展開。フォルダの改名にタブ名も追従。
- レイアウト削除は件数を確認し、配下のブロックとタブも削除。Undo／Redoに対応。
- レイアウトフォルダとブロックを右クリック／Ctrl+Dでコピー。点ID・選択セットIDとコピー内の直接参照を更新。
- ブロック編集下部の分割・結合ボタンを削除。

コア438件・全GUI403件成功。空レイアウトの作図先候補を含む関連34件も追加確認。Windows／AutoCAD実機は未確認です。Python版は `python -m pip install -r requirements.txt` を実行してください。EXEは含みません。詳しい操作説明とログをZIPに同梱しています。

## 以前の配布版

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
