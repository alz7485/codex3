# Trial5 現状UI確認・46画面

確認対象: AcadStadio_v1.20.4_DWGImportTrial5.zip（アプリ内表示1.20.4-beta5）。

添付ZIPのCRCと全ファイルSHA256を確認し、実際のTk画面を46枚撮影しました。製品ファイル188件は撮影前後で変更なし。改善案の実装・新バージョン公開は行っていません。

主な追加: コマンド種類を選んで追加／主要入力と詳細の分離／表の列・セルから参照挿入／複数表と行指定／日本語名のプロジェクト変数／条件入力補助／DWGから設定取得。

撮影環境はLinux/Tk（1440×1000）。Windowsの枠・フォントには差があります。35はDWG読取前の実画面、36〜39・45〜46は表示用サンプルデータです。AutoCAD実機・DWG実読取は未実施。

初期サイズでは表参照・DWG読込の下部ボタンが狭くなるため、23→44、36→45、39→46で拡大前後を比較できます。コードは修正していません。

資料番号を指定すると、その画面を基に改善点を検討できます。

[全画像＋ブラウザ用一覧をZIPで保存](AcadStadio_Trial5_UI_Review.zip)

## メイン

<details>
<summary>01 作図：ブロック一覧とプレビュー</summary>

![01 作図：ブロック一覧とプレビュー](01.png)

</details>

<details>
<summary>02 作図：選択フロー</summary>

![02 作図：選択フロー](02.png)

</details>

<details>
<summary>03 生成SCR</summary>

![03 生成SCR](03.png)

</details>

<details>
<summary>04 入力表</summary>

![04 入力表](04.png)

</details>

<details>
<summary>05 小さいウィンドウ（1040×680）</summary>

![05 小さいウィンドウ（1040×680）](05.png)

</details>

## 管理

<details>
<summary>06 プロジェクト一覧</summary>

![06 プロジェクト一覧](06.png)

</details>

<details>
<summary>07 プロジェクト構成ツリー</summary>

![07 プロジェクト構成ツリー](07.png)

</details>

## ブロック・コマンド

<details>
<summary>08 ブロック編集：条件を省略した状態</summary>

![08 ブロック編集：条件を省略した状態](08.png)

</details>

<details>
<summary>09 ブロック編集：実行条件を開いた状態</summary>

![09 ブロック編集：実行条件を開いた状態](09.png)

</details>

<details>
<summary>10 コマンド追加メニュー</summary>

![10 コマンド追加メニュー](10.png)

</details>

<details>
<summary>11 コマンド入力：線分</summary>

![11 コマンド入力：線分](11.png)

</details>

<details>
<summary>12 コマンド入力：円</summary>

![12 コマンド入力：円](12.png)

</details>

<details>
<summary>13 コマンド入力：長方形</summary>

![13 コマンド入力：長方形](13.png)

</details>

<details>
<summary>14 コマンド入力：文字</summary>

![14 コマンド入力：文字](14.png)

</details>

<details>
<summary>15 コマンド入力：寸法</summary>

![15 コマンド入力：寸法](15.png)

</details>

<details>
<summary>16 コマンド入力：条件分岐</summary>

![16 コマンド入力：条件分岐](16.png)

</details>

<details>
<summary>17 コマンド入力：繰り返し</summary>

![17 コマンド入力：繰り返し](17.png)

</details>

<details>
<summary>18 コマンド入力：ブロック呼出</summary>

![18 コマンド入力：ブロック呼出](18.png)

</details>

<details>
<summary>19 コマンド入力：システム変数</summary>

![19 コマンド入力：システム変数](19.png)

</details>

<details>
<summary>20 コマンド入力：ユーザー登録コマンド</summary>

![20 コマンド入力：ユーザー登録コマンド](20.png)

</details>

<details>
<summary>21 円：詳細設定と参照一覧を開いた状態</summary>

![21 円：詳細設定と参照一覧を開いた状態](21.png)

</details>

## 入力補助

<details>
<summary>22 かんたん条件入力</summary>

![22 かんたん条件入力](22.png)

</details>

<details>
<summary>23 表参照：列・固定セルの選択</summary>

補助画面の確認用に、寸法一覧というサンプル表と日本語名の変数を一時追加。

![23 表参照：列・固定セルの選択](23.png)

</details>

<details>
<summary>24 表参照：変数による行指定</summary>

補助画面用のサンプル表・変数を使用。

![24 表参照：変数による行指定](24.png)

</details>

<details>
<summary>44 表参照：ウィンドウを広げた状態</summary>

初期サイズと比較するため、操作でウィンドウを拡大。補助画面用サンプル表を使用。

![44 表参照：ウィンドウを広げた状態](44.png)

</details>

## 作図設定

<details>
<summary>25 作図設定：対象行</summary>

![25 作図設定：対象行](25.png)

</details>

<details>
<summary>26 作図サイズ・共通設定</summary>

![26 作図サイズ・共通設定](26.png)

</details>

<details>
<summary>27 任意の共通設定</summary>

![27 任意の共通設定](27.png)

</details>

<details>
<summary>28 プロジェクト全体の変数</summary>

![28 プロジェクト全体の変数](28.png)

</details>

<details>
<summary>29 設定プリセット</summary>

![29 設定プリセット](29.png)

</details>

## CAD設定

<details>
<summary>30 CAD初期設定：レイヤー</summary>

![30 CAD初期設定：レイヤー](30.png)

</details>

<details>
<summary>31 CAD初期設定：文字スタイル</summary>

![31 CAD初期設定：文字スタイル](31.png)

</details>

<details>
<summary>32 CAD初期設定：寸法スタイル</summary>

![32 CAD初期設定：寸法スタイル](32.png)

</details>

<details>
<summary>33 CAD初期設定：線種読込</summary>

![33 CAD初期設定：線種読込](33.png)

</details>

<details>
<summary>34 レイヤー色パレット</summary>

![34 レイヤー色パレット](34.png)

</details>

## DWG読込

<details>
<summary>35 DWG設定読込：読取前</summary>

AutoCAD実機での読取は行っていません。

![35 DWG設定読込：読取前](35.png)

</details>

<details>
<summary>36 DWG設定読込：レイヤー（表示例）</summary>

表示用サンプルデータです。AutoCAD・DWG実読取は未実施。

![36 DWG設定読込：レイヤー（表示例）](36.png)

</details>

<details>
<summary>37 DWG設定読込：文字スタイル（表示例）</summary>

表示用サンプルデータです。AutoCAD・DWG実読取は未実施。

![37 DWG設定読込：文字スタイル（表示例）](37.png)

</details>

<details>
<summary>38 DWG設定読込：寸法スタイル（表示例）</summary>

表示用サンプルデータです。AutoCAD・DWG実読取は未実施。

![38 DWG設定読込：寸法スタイル（表示例）](38.png)

</details>

<details>
<summary>39 DWG設定読込：線種（表示例）</summary>

表示用サンプルデータです。AutoCAD・DWG実読取は未実施。

![39 DWG設定読込：線種（表示例）](39.png)

</details>

<details>
<summary>45 DWG読込：拡大表示・レイヤー</summary>

ウィンドウを拡大した比較用画面。表示用サンプルデータ、実DWGは未読取。

![45 DWG読込：拡大表示・レイヤー](45.png)

</details>

<details>
<summary>46 DWG読込：拡大表示・線種</summary>

ウィンドウを拡大した比較用画面。表示用サンプルデータ、実DWGは未読取。

![46 DWG読込：拡大表示・線種](46.png)

</details>

## 登録コマンド

<details>
<summary>40 ユーザー登録コマンド一覧</summary>

![40 ユーザー登録コマンド一覧](40.png)

</details>

<details>
<summary>41 登録コマンドの編集</summary>

![41 登録コマンドの編集](41.png)

</details>

## 確認・出力

<details>
<summary>42 プロジェクト検査</summary>

![42 プロジェクト検査](42.png)

</details>

<details>
<summary>43 SCR書き出し</summary>

![43 SCR書き出し](43.png)

</details>

