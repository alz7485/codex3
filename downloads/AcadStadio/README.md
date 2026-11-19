# AcadStadio — 最新 1.77.0-beta125

[Trial125 アプリソースZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_v1.77.0_ViewportInputTrial125.zip)

- ビューポートの画面指定前に初期値の仮枠が表示される問題を修正。用紙の2角とモデルの表示中心を指定して作成します。
- 角の点をドラッグ：枠サイズ。中心の点をドラッグ：枠移動。枠内をドラッグ：モデルの表示内容を移動。
- 中ボタンのパン・ズーム後に点や補助表示が図形とずれる問題を修正。
- 円の上下左右における接線同士の交点を、仮想交点・左上／右上／左下／右下として選択できます。円を選ぶと補助枠を表示し、中心・半径・直径変更にも追従する点参照として保存します。

コア580件・関連GUI40件、スモーク検証成功。GUI全件の今回の再実行はしていません。操作・検証範囲はZIP内README.md、docs/PREVIEW_INPUT.md、docs/VALIDATION.mdを参照してください。

Pythonソース版（EXEなし）。Windows実操作・AutoCAD実機・EXEビルドは未確認です。

SHA256: `1df84e2f5945a38c665c77fafc255dd69f558160724fe96cf52a2d2de77fe989`

## 以前の配布版

# AcadStadio — 1.76.1-beta123

[Trial123 アプリソースZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_v1.76.1_CommandPointTrial123.zip)

作図位置の指定は「図形をクリック → 表示されたコマンドの点をクリック」の2段階です。

図形本体を選んだだけではXYを確定しません。選択した線分の始点・中点・終点、円の中心・上下左右などを水色の丸と名前で表示します。点をクリックするとX・Yを点参照として保存し、元コマンドの変更に追従します。点の選択待ち中は空白クリックでXYを追加せず、Escで解除できます。

寸法の測定対象・HATCH境界・TRIM等の対象指定は従来の操作を維持。関連GUI24件・コア31件、スモーク検証成功。全件の今回の再実行は行っていません。

Trial122以前の修正を含むPythonソース版（EXEなし）。Windows実操作・AutoCAD実機は未確認です。詳しくはZIP内docs/PREVIEW_INPUT.mdとdocs/VALIDATION.mdを参照してください。

SHA256: `8f6bdeee9d9275f647bc41b14a4978f7f43a65ac21bc96ff4ae0e959e0c7a342`

## 以前の配布版

# AcadStadio — 1.76.0-beta122

[Trial122 アプリソースZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_v1.76.0_PointSnapTrial122.zip)

プレビューで既存コマンドの端点・中点・円中心などに近づくと、スナップ枠と「コマンド／点名（点参照）」を表示します。クリックした点のX・Yを点参照として保存し、元コマンドの変更に追従します。

同一図形の同じ位置にある別名候補は統合し、別図形の重なりは候補を選べます。空白位置の座標指定とAltによるスナップ解除も維持しています。

関連GUI29件・関連コア31件、スモーク検証成功。保存した参照と参照元変更への追従を照合しました。全件の今回の再実行はしていません。詳しくはZIP内docs/VALIDATION.mdとdocs/PREVIEW_INPUT.mdを参照してください。

Trial121以前の修正を含むPythonソース版（EXEなし）。Windows実操作・AutoCAD実機は未確認です。

SHA256: `fe14ceb14e7aa5f5db4d38a1eb872d1a4628a50905441bdc589bf67605d82290`

## 以前の配布版

# AcadStadio — 1.75.3-beta121

[Trial121 アプリソースZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_v1.75.3_PreviewSpaceTrial121.zip)

作図先が「コマンドに従う」「モデル」のとき、実際のタブ名と一致せず、プレビューのクリックが拒否される問題を修正しました。

X11のOSマウスイベントでコマンド追加→2点クリック→線分保存を確認。関連GUI5ファイル・37件、スモーク検証成功。コア・GUI全件の今回の再実行は行っていません。Trial120以前の文字書式・SELECT・レイアウト・プレビュー入力も含みます。

Pythonソース版（EXEなし）。Windows・AutoCAD実機・EXEビルドは未確認です。操作と検証範囲はZIP内のREADME.mdとdocs/VALIDATION.mdを参照してください。

SHA256: `3df1365e63562b14173179edac193cb3d3b25918acf4274781ed5c795711fdd0`

## 以前の配布版

# AcadStadio — 1.75.2-beta120

[Trial120 アプリソースZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_v1.75.2_PreviewClickTrial120.zip)

- メインのコマンド一覧から追加すると、プレビューの点指定が自動で始まるよう修正。点を2つクリックして線分を作成できます。
- 作図・編集のプレビュー入力と、数値・式の詳細表示を含みます。
- LEADER/MULTILEADERの矢印・注記の読み込み、%%Cのφ表示、MTEXTの文字高さ倍率・上下公差表示も含みます。引出線は描画要素へ分解して読み込みます。

関連GUI3ファイル・33件、スモーク検証が成功。コア・GUI全件の今回の再実行は行っていません。詳細はZIP内 docs/VALIDATION.md と docs/CAD_TEXT.md を参照してください。

Pythonソース版（EXEなし）。依存は `python -m pip install -r requirements.txt` で導入し、`python src/main.py` で起動してください。Windowsのマウス実操作・AutoCAD実機・EXEビルドは未確認です。

SHA256: `0c9e2787868103ec4100043408513be8aa99d817f3de6e55f4600cf774dc3fec`

[SHA256ファイル](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_v1.75.2_PreviewClickTrial120.zip.sha256)

## 以前の配布版

# AcadStadio — 1.72.3-beta108

[Trial108 アプリソースZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_v1.72.3_PointAxisFlowTrial108.zip)

点参照の確定後は **X → Y → 次の点のXY**、**XY → 次の点のXY** と進みます。参照元・選んだ参照点を引き継ぎ、最後の点を確定すると終了します。

関連GUI30件成功。ボタン・Enter・テンキーEnter・右クリックメニュー、3頂点の連続入力とキャンセルを検証しました。小さな入力先切替の変更のためコア・全GUIは再実行していません。

Pythonソース版（EXEなし）。Windows／AutoCAD実機は未確認。配布はGitHubのみ。SELECTの新機能はこの版には含みません。

SHA256: `27e5671519aea71ba0303bd560bcb89d0f9c68e59a1f32473cdb15f2634773df`

## 以前の配布・UI画像

# AcadStadio — 1.72.2-beta107

[Trial107 アプリソースZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_v1.72.2_PreviewTabsTrial107.zip)

[画面例：モデル・レイアウト・＋と「名前」列](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/UI_Trial107_PreviewTabs.png)

- プレビューの「＋」を常に最後へ配置。モデル → 各レイアウト → ＋の順になり、追加・複製・改名・削除・Undo後も右端を維持。
- ブロック一覧の列見出し「ブロック名」を「名前」に変更。列キーとデータ構造は維持。

関連GUI15件成功。実画面でモデル・A4・A3・＋の順と「名前」見出しを確認、画面例外0。小さな表示変更のためコア・全GUIの再実行は行っていません。Trial106までの機能と試用データを含みます。

Pythonソース版（EXEなし）。Windows／AutoCAD実機は未確認。配布はGitHubのみ。

SHA256: `fbde99395e842ddf3c0ed4c5a172f3fdc43e7bda2aa5e5aab745a33a1e7588c5`

## 以前の配布・UI画像

# AcadStadio — 1.72.1-beta106

[Trial106 アプリソースZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_v1.72.1_BlockOrderDisplayTrial106.zip)

画面例：[親フォルダ名と順番](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/UI_Trial106_ParentAndOrder.png) ／ [解放後](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/UI_Trial106_Released.png)

フォルダを先頭に固定していたため、フォルダ化したブロックの「4・5・6」が「1・2・3」より先に見える問題を修正しました。フォルダの表示位置は含まれる最初の実行ブロックに合わせ、作図データとSCRの順序は変えません。

「順」の同じ列内に、番号の左へ親フォルダ名を表示します（例：モデル 1、部品A 4）。列は増やしません。長い名前は表示だけを省略し、ガイドGは維持します。

コア500件・全GUI425件成功。Trial105の旧表示順を保存したデータでも追加3件が成功し、実画面も確認しました。表示修正でデータやSCRが変わらず、解放でも作図順を維持することを検証しています。Trial105の機能・試用データも含みます。

Pythonソース版（EXEなし）。Windows／AutoCAD実機は未確認。配布はGitHubのみ。

SHA256: `e0bf6afa166c426b5b7ba1569917dda079b0a4d3694d5b19e6b3972386491d77`

## 以前の配布・UI画像

# AcadStadio — 1.72.0-beta105

[Trial105 アプリソースZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_v1.72.0_PreviewFigureFoldersTrial105.zip)

画面例：[範囲選択](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/UI_Trial105_Selection.png) ／ [フォルダ化・専用アイコン](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/UI_Trial105_Folder.png) ／ [フォルダ解放](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/UI_Trial105_Released.png)

- プレビューを囲んで追加・解除し、同じモデル／レイアウト配下にフォルダを作成。作図・寸法・テキストへ分類し、空の種類は省略。寸法は一体で選択。
- 読込時・フォルダ化時は図形ごとの属性を保持。フォルダまたはブロックを右クリックして「属性順に整理」したときだけ、並び替えと重複属性の削除を実行。
- ブロック一覧の「フォルダを解放」で、内容を一階層上の元の表示位置へ展開。作図順・コマンド・SCRを維持。各操作はUndo 1回分。
- モデルは立方体、レイアウトは用紙の専用アイコン。通常フォルダと区別でき、ルートは解放不可。
- 表の式と点参照を維持・補修し、処理前後の図形と属性を照合。選択は元コマンド単位で表の全行へ反映します。
- `examples/範囲フォルダ化テスト` に3部品・30図形のDXF（ネイティブ寸法を含む）、選択前・フォルダ化後・整理後のJSONと手順を同梱。

コア500件・全GUI424件成功。凡例の最後の並び順補強後、関連25件も成功。実画面は例外0。詳細な検証時点と範囲はZIP内docs/VALIDATION.mdを参照してください。条件・繰返し・変数・図形編集操作を含むブロックの部分移動は対象外です。

Pythonソース版（EXEなし）。Windows／AutoCAD実機は未確認。配布はGitHubのみ。

SHA256: `00eb98bfa98bc7b3ab0f35e42fd0f0157ad45416940d85ab6a07acc1472a9f6b`

## 以前の配布・UI画像

# AcadStadio — 1.71.1-beta104

[Trial104 アプリソースZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_v1.71.1_SettingReferenceNavigationTrial104.zip)

[参照件数と使用箇所の強調の画面例](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/UI_Trial104_SettingReferenceNavigation.png)

- 右クリック →「参照先へ移動」で正本行を選択して表示。入れ子内は正本を含む行へ移動し、内部の場所を案内。
- 「この正本の使用箇所を強調」で正本を青、参照を黄色に表示。「強調を解除」で戻せます。
- 正本と参照の詳細に「参照○件」を表示。追加・正本化・削除・Undo後も更新。
- 表示操作は保存データ・SCR・Undo履歴を変更しません。対象は同ブロック内の作図属性・システム変数・レイヤー編集。再作図は対象外です。

コア487件・全GUI418件成功。実画面も確認しました。Trial103の分割・正本削除時の選択・設定参照サンプルを含みます。

Pythonソース版（EXEなし）。Windows／AutoCAD実機は未確認。配布はGitHubのみ。

SHA256: `b67fe0abaefe3549fe89b3c15288114b2bf79eba826921e884aea9e2fa5b5f3e`

## 以前の配布・UI画像

# AcadStadio — 1.71.0-beta103

[Trial103 アプリソースZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_v1.71.0_LocalSettingReferencesTrial103.zip)

同ブロック内の作図属性・システム変数（単体／複数）・レイヤー編集を参照できます。ブロック編集で設定を選択し、右クリック →「参照を追加」。参照からの編集は正本を編集し、使用箇所へ反映します。再作図は対象外です。

- 分割時に正本が別ブロックへ離れた場合、最初の参照を正本化し、後続の参照を付け替え。
- 正本削除は「すべて正本化」「最初だけ正本化して残りを付け替え」「キャンセル」。削除・置換はUndo 1回分。
- 複製と参照を選べます。正本と参照を一緒に複製すると、複製した正本へ付け替えます。
- `examples/設定参照テスト` に3カテゴリ、1行9図形の実行例と操作手順を同梱。
- コア487件、全GUI414件成功。最後の分割・入れ子削除補強後にも関連21件（新規1件を含む）が成功。検証時点の詳細はZIP内docs/VALIDATION.md。

Pythonソース版（EXEなし）。Windows／AutoCAD実機は未確認。配布はGitHubのみ。

SHA256: `948fb3cec6e32d739e2551537703ee7b65c0bc23ed671249a0a22f7bdc050aff`

## 以前の配布・UI画像

# AcadStadio — 1.70.1-beta102

[Trial102 アプリソースZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_v1.70.1_AppearanceDedupTrial102.zip)

DWG／DXFから読み込んだ値を作図属性コマンドへ分ける際、直前と同じ属性ならコマンドを作成しません。最初の設定と、色・レイヤー・線種・尺度・文字／寸法スタイルが変わる箇所は残します。

- 同梱サンプルは19図形分の属性を5コマンドに集約。図形の座標・属性・文字は維持。
- 保存・再編集後も重複しません。手入力だけのブロックは従来どおりです。
- コア477件・全GUI411件成功。実DXF読込後の編集・保存・再編集を含めて検証。
- Trial101のUI改善とSCR選択行プレビューを含みます。

Pythonソース版（EXEなし）。Windows／AutoCAD実機は未確認。配布はGitHubのみです。

## 以前の配布・UI画像

# AcadStadio — 1.70.0-beta101

[Trial101 アプリソースZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_v1.70.0_UiAndScriptPreviewTrial101.zip)

[変更後のUI画像・HTMLギャラリー](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_UIReview_Trial101.zip)

- 01：上段をプロジェクト一覧、開く、保存、プロジェクト名、Undo／Redoの順へ。検査・SCR関連は右側。
- 11：点参照小窓の詳細ボタン・座標結果行を削除しコンパクト化。交点・接点は直接選択と右クリックから設定。
- 15：レイヤー一覧の色欄に実色の四角を表示。
- 18：SCRにプレビュー表示ボタン。選択行の命令までの作図状態と、その命令の黄色い強調。選択解除で最終状態。複数行命令は完了時の状態と行範囲を表示。

コア471件・全GUI410件成功。画像は実Linux / Tk 8.6。Pythonソース版（EXEなし）、Windows／AutoCAD実機は未確認。SCRプレビューはアプリの対応作図範囲です。配布はGitHubのみ。

SHA256（本体）：`dcf9b2102fbf64057841b33e1b3fcfe4aed6c314c12728da4c924533a10ccbca`

## 以前の配布・画像

# AcadStadio

[Trial100のUI画像18枚・HTMLギャラリーをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_UIReview_Trial100.zip)

ZIPを展開してindex.htmlを開くと、番号付きで各画面を原寸確認できます。Linux / Tk 8.6での実画面です。アプリのUIは変更していません。

## 1.69.0-beta100 — DWG読込後の表作成・Excel割当サンプル

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
