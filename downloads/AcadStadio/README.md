# AcadStadio — 最新 1.83.0-beta137

[Trial137 アプリソースZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_v1.83.0_TextViewportTrial137.zip)

TEXTでも%%C／%%cのφ、H倍率とSの上下公差をプレビューします。TEXT／MTEXTの作成・編集に文字幅係数を追加し、プレビューとSCRへ反映。MTEXTの部分W書式にも対応しました。書式付きTEXTはCAD出力時にMTEXTとして作成します。特殊記号を持たない指定フォントでは代替フォントを使用します。

ビューポート矩形をAddPViewport、直径／半径寸法をAddDimDiametric／AddDimRadialで直接作成する方式へ変更し、対話入力や一時円の削除へ依存する経路をなくしました。CAD読込完了時は読込画面へ、読込画面を閉じる時はメイン画面へフォーカスを戻します。

コア615件・GUI全93ファイル524件・スモーク成功。操作・制約はZIP内docs/TEXT_VIEWPORT137.md、検証範囲はdocs/VALIDATION.mdを参照してください。

Pythonソース版（EXEなし）。Windowsでの前面復帰・AutoCAD実機での今回のSCR実行・EXEビルドは未確認です。Windowsの制限によって自動的に前面へ戻せない場合があります。以前のDIMEDIT寸法スライド、CP932、寸法設定、UI修正も含みます。

SHA256: `1cdec6e28c17ba099060ba27089929e1a1b97ac2a1ddb5c9bfb0a854601cd811`

## 以前の配布版

# AcadStadio — 1.82.1-beta136

[Trial136 アプリソースZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_v1.82.1_DimensionObliqueTrial136.zip)

「文字・寸法」に「DIMEDIT · 寸法スライド」を追加しました。直前にSELECTがなければ先に選択画面を開き、プレビューで長さ寸法・平行寸法をクリック／囲みで選択します。続いて2点で補助線の方向を指定できます。角度の直接入力と「直角に戻す」にも対応します。

角度はX軸基準の方向として扱い、水平・垂直・平行寸法へ反映します。測定値・文字書式・個別寸法設定・手動文字位置を保持し、DXF group52の読込・座標編集後の再生成にも対応。SCRはDIMEDITのObliqueへ2点で方向を指定します。対象を事前確認し、処理中のエラーはUndoグループで戻します。取消では自動SELECTを含む追加全体を取り消せます。

コア609件・GUI全92ファイル522件・スモーク成功。操作と制約はZIP内docs/DIMENSION_OBLIQUE.md、検証範囲はdocs/VALIDATION.mdを参照してください。

Pythonソース版（EXEなし）。Windows実操作・AutoCAD実機でのSCR実行／DWG COM読込・EXEビルドは未確認です。Trial135の楕円出力・CP932・寸法書式・矢印・ビッグフォント設定・複数ブロック削除、以前のUI修正も含みます。

SHA256: `72a0c37213ab028184f39aa6a9a5586a073395b3458a46f30e71e49748c23b1b`

## 以前の配布版

# AcadStadio — 1.82.0-beta135

[Trial135 アプリソースZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_v1.82.0_CadOutputTrial135.zip)

楕円のSCRを一括作成する方式へ変更し、対話コマンドの点指定待ちへ進む経路をなくしました。日本語のSCRはCP932を維持し、CP932外のBMP文字はAutoLISPの文字列式で復元します。この追加変換を使う場合はAutoCAD 2021以降とLISPSYS=1または2（変更後にAutoCAD再起動）が必要です。変換できない文字や長すぎる行では既存SCRを上書きせず案内します。

寸法文字の中央配置、%%C／%%cのφ、H倍率とSの上下公差を詳細プレビューで表示。寸法スタイルの矢印形状、DIMPOST／DIMTIH／DIMTOH／DIMTOLJと、文字スタイルのビッグフォント使用チェック・ファイル名を読み込み、編集・出力へ保持します。読込後に変更したスタイル項目は寸法の個別設定を残して反映します。ブロックの複数同時削除・取消・Undo／Redoにも対応しました。

コア596件・GUI全91ファイル515件・スモーク成功。操作・制約はZIP内docs/CAD_OUTPUT135.md、検証範囲はdocs/VALIDATION.mdを参照してください。「スライド寸法」は対象コマンドの確認待ちで、今回の追加対応には含みません。

Pythonソース版（EXEなし）。SHX／ビッグフォントの字形は代替表示です。Windows実操作・AutoCAD実機でのSCR実行・EXEビルドは未確認です。変数UI、コンパクトな共通ボタン、Enter2回の点入力・コマンド確定など従来の修正も含みます。

SHA256: `63c3ba9e8c18dad15d6aef4ccd4332cef945a5c02a011a9b9b4c1c681524ace9`

## 以前の配布版

# AcadStadio — 1.81.0-beta134

[Trial134 アプリソースZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_v1.81.0_VariableUiTrial134.zip)

変数画面の「＋」が入力欄を空にするだけだった操作を見直し、「＋ 変数を追加」で編集可能な行を追加する方式に変更しました。重複しない「新しい変数1」等と値0を初期入力し、名前と値・式を一覧で直接編集できます。続けて追加しても入力済みの値は残ります。

参照メニューから表の列・セルや他の変数を指定でき、確認値と入力エラーを表示します。「適用して閉じる」でまとめて反映し、取消・Undo／Redoも利用できます。行がないプロジェクトでも定数を追加できます。共通のコンパクトなボタンサイズを維持しています。

コア583件・関連GUI6ファイル75件・スモーク検証成功。GUI全件の今回の再実行はしていません。操作はZIP内docs/VARIABLES.md、検証範囲はdocs/VALIDATION.mdを参照してください。

メイン画面の整理、全UIのコンパクトなボタン、Enter2回の点入力・コマンド確定も含みます。Pythonソース版（EXEなし）。Windows実操作・AutoCAD実機・EXEビルドは未確認です。

SHA256: `6fdf2d77b0c823b459d11b121220498c675595c6c51d9af2250ff6fc009c1888`

## 以前の配布版

# AcadStadio — 1.80.1-beta133

[Trial133 アプリソースZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_v1.80.1_EnterConfirmTrial133.zip)

線分・ポリラインなどで、点を順にクリック → Enterで点指定を確定 → もう一度Enterでコマンドを追加・反映して閉じる流れに対応しました。通常EnterとテンキーEnterを使えます。

点数不足では追加せず、数値欄の操作・複数行文字の改行・別コマンドの点選択の確定を維持。WindowsでEnterを押し続けたキーリピートだけでは追加しません。点参照の追従とUndo、従来のマウス操作も維持します。

コア583件・関連GUI7ファイル63件・スモーク検証成功。GUI全件の今回の再実行はしていません。操作はZIP内docs/PREVIEW_INPUT.md、検証範囲はdocs/VALIDATION.mdを参照してください。

メイン画面の整理と全UIのコンパクトなボタンを含みます。Pythonソース版（EXEなし）。Windows実操作・AutoCAD実機・EXEビルドは未確認です。

SHA256: `238c0b34279c652b84b4b145860b872e0472256b4875f4fbc03a62d8cde2df22`

## 以前の配布版

# AcadStadio — 1.80.0-beta132

[Trial132 アプリソースZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_v1.80.0_MainUiTrial132.zip)

メイン画面の左側をブロック一覧に集約し、入力表・確認行をプレビュー上部へ移しました。設定は右上、検査・SCR表示は出力の詳細に整理しています。図形をクリックすると、選択したコマンドの編集・紐づけ支援へ進めます。重なりの候補選択、パン、従来のダブルクリック編集を維持しています。

ボタンのコンパクト化はメインだけでなく、入力表・コマンド追加と編集・CAD設定・プリセット・紐づけ支援など全UIに反映。文字サイズ・20pxアイコンを保ち、余白と不要な最小幅を縮めました。Linuxの確認環境では標準ボタンの高さが約28pxです。Windowsの表示倍率やフォントで実寸は変わります。

コア583件、GUI全88ファイル493件（スキップなし）、スモーク検証成功。最終調整後の関連7ファイル59件も成功。操作はZIP内docs/MAIN_UI.md、検証範囲はdocs/VALIDATION.mdを参照してください。

Pythonソース版（EXEなし）。Windows実操作・AutoCAD実機・EXEビルドは未確認です。

SHA256: `a1bbc608da2c05ceb44f353caa685afc6fadf8c583e2498ccfe6c2c0453272b2`

## 以前の配布版

# AcadStadio — 1.79.0-beta131

[Trial131 アプリソースZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_v1.79.0_LinkUiTrial131.zip)

紐づけ支援を「1 変更する図形と項目 → 2 参照元を選ぶ → 3 確認して適用」に整理しました。プレビューで図形を選び、表の列または参照元の図形・点を選択します。図形だけでは点を自動決定せず、点を明示選択してから適用できます。

変更前後の確認欄はスクロールしても見える位置に固定。一覧・全項目・確認状況・表の全列表示は必要なときだけ開きます。適用前の試算とUndoを維持しています。

コア583件・関連GUI4ファイル12件・スモーク検証成功。GUI全件の今回の再実行はしていません。操作はZIP内docs/LINK_ASSISTANCE.md、検証範囲はdocs/VALIDATION.mdを参照してください。

Pythonソース版（EXEなし）。Windows実操作・AutoCAD実機・EXEビルドは未確認です。

SHA256: `a81fd9c4c4e53ff7b52d146aff4f7951ddcae54144aad99af89e820d578c5de6`

## 以前の配布版

# AcadStadio — 1.78.1-beta130

[Trial130 アプリソースZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_v1.78.1_CircleAngleTrial130.zip)

円を選択した後、円周の途中をクリックすると角度入力の小窓が開きます。クリック位置の角度を初期値とし、右向き0°・反時計回り正で入力できます。「この点を使用」で確定すると、元円と角度の点参照として保存し、中心・半径の変更にも追従します。キャンセル時は点を追加しません。

従来の中心・四半円点・仮想交点の直接選択も維持。角度には数値・数式・表参照を使用できます。

コア583件・関連GUI35件、スモーク検証成功。最終調整後の関連コア2件・GUI2件も成功。GUI全件の今回の再実行はしていません。詳細はZIP内docs/VALIDATION.mdとdocs/PREVIEW_INPUT.mdを参照してください。

Pythonソース版（EXEなし）。Windows実操作・AutoCAD実機・EXEビルドは未確認です。

SHA256: `18fece396f01e207bc6f73038d87e009ee3a5bad8a90294c8f78319f55ad9948`

## 以前の配布版

# AcadStadio — 1.78.0-beta129

[Trial129 アプリソースZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_v1.78.0_WorkflowUiTrial129.zip)

[画面例：ブロック編集（Linux/Tk）](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/UI_Trial129_BlockEditor.png) ／ [カテゴリ選択（Linux/Tk）](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/UI_Trial129_CommandCategories.png)

- 新規ブロック名に、重複しない「新しいブロック(n)」を初期入力。
- 「選択したコマンドまで表示」で範囲の行を薄く塗る表示を撤去。
- コマンド一覧・ブロック一覧でCtrl+↑/↓により表示中の先頭/末尾へ移動。
- 作図先の選択欄を撤去し、ブロック一覧の所属モデル/レイアウトを入力先に固定。SPACEは新規作成から除外。保存済みデータの読み込み互換を維持。
- VIEWPORTを「線・形状」へ移し、「設定・制御」を統合。
- 入力表の窓を1600×940（画面範囲内）へ拡大。
- 参照は正本と同じコマンド名・アイコンに［参照］を付けて表示。

コア581件成功。GUI全86ファイル・480件を実行し、修正後の関連46件の再検証も成功。最終的に失敗・時間切れなし。スモーク成功。詳しくはZIP内docs/WORKFLOW_UI.mdとdocs/VALIDATION.mdを参照してください。

Pythonソース版（EXEなし）。Windows実操作・AutoCAD実機・EXEビルドは未確認です。

SHA256: `6b81218674c20b2995412946a4d99e80b72eec1843bb01d33e573fd476c0e08a`

## 以前の配布版

# AcadStadio — 1.77.3-beta128

[Trial128 アプリソースZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_v1.77.3_WindowsSnapTrial128.zip)

WindowsでNumLockがONのとき、Alt押下と誤判定してスナップ・コマンド選択が解除され、クリック位置が数値になる問題を修正しました。

NumLockがONでも「図形本体を選択 → 表示されたコマンドの点を選択 → 点参照として保存」ができます。プレビューで暗い色に表示される通常図形は、自動ガイド化されたものではありません。ガイド図形も点参照の参照元として選べます。

コア581件・関連GUI32件、スモーク検証成功。WindowsのNumLockイベント状態をLinux/Tk上で再現して検証しています。Windows実機・AutoCAD実機・EXEビルドは未確認です。詳細はZIP内docs/VALIDATION.mdを参照してください。

Trial127以前の修正を含むPythonソース版（EXEなし）。

SHA256: `05ddf6eac37b24ff9b79437349bb6297939e42ae14c9d934c3b6763064f8fd0a`

## 以前の配布版

# AcadStadio — 1.77.2-beta127

[Trial127 アプリソースZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_v1.77.2_GuidePointTrial127.zip)

ガイド化した灰色の図形が点参照の候補から除外され、クリックしてもコマンドの点を選べない問題を修正しました。

ガイド本体をクリック → 表示された始点・中点・終点・中心・円の仮想交点などをクリックすると、点参照として保存します。ガイドのブロック/コマンドIDを参照するため、元ガイドの変更にも追従します。SELECTによる図形操作からガイドを除外する仕様は維持しています。

関連GUI31件・関連コア15件、スモーク検証成功。保存・JSON再読込後の追従とガイド円の仮想交点も確認。全件の今回の再実行はしていません。

Trial126以前の修正を含むPythonソース版（EXEなし）。Windows実操作・AutoCAD実機・EXEビルドは未確認です。

SHA256: `1601b0304903a0c0de5be06607d3ae68a37a8228a5e3a41772fe209485eedaab`

## 以前の配布版

# AcadStadio — 1.77.1-beta126

[Trial126 アプリソースZIPをダウンロード](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/AcadStadio_v1.77.1_ProjectListTrial126.zip)

[画面例：プロジェクト一覧と右クリックメニュー（Linux/Tk）](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/AcadStadio/UI_Trial126_ProjectList.png)

- プロジェクト一覧の上部を新規作成・フォルダ作成・削除の3操作に整理。「開く」「保存」「別名保存」を一覧から削除しました。
- プロジェクトはリストから開きます。右クリックで移動・名前変更・削除を行えます。右クリックしただけでは開きません。
- フォルダの移動時も編集中プロジェクトの保存先を追従。同名ファイルを上書きせず、取消時はデータを維持します。

関連GUI24件・関連コア8件、スモーク検証成功。最終のボタン表示調整後も関連GUI5件が成功しました。全件の今回の再実行はしていません。前版までのビューポート・パン・点参照・円の仮想交点の修正も含みます。

Pythonソース版（EXEなし）。Windows実操作・AutoCAD実機・EXEビルドは未確認です。

SHA256: `220bd1c2e72408119212cebd58dbda27e0d9c4239c28bdd41ab7167f402e7d00`

## 以前の配布版

# AcadStadio — 1.77.0-beta125

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
