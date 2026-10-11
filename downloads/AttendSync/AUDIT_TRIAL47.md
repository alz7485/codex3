# AttendSync Trial47 追加監査（2026-10-11）

## 判定

この環境で確認できる範囲では、修正が必要な不具合を再現しなかった。Trial47のコードと配布ZIPを維持する。ソースやZIPの差し替えは不要。今回の記録はZIPと別に掲載する。

## 実行結果

- 全40テストスクリプトを個別プロセスで再実行し、40本すべて合格。構文確認も合格。重複する試験メソッドは合算しない。詳細: audits/Trial47/All_Test_Results.json。
- 追加の境界試験8メソッド合格。メイン画面の全84ウィジェットに実QtのDragEnter／DragMove／Dropイベントを配送し、受理・フォルダ欄の更新・コピー操作を確認。
- すでに生成・表示済みの入力欄を後からメイン画面へ移しても対応。検索欄へのパス文字列混入なし。
- Copyを提供するドロップはCopyで受理。Moveのみ／Linkのみは拒否。元フォルダの保持を確認。
- DragEnter後にフォルダを削除するとDropを拒否し、以前のフォルダ欄を保持。
- フォルダ欄が無効の場合、ドロップを拒否して入力保持。
- 実QThreadを実行中にドロップしてもフォルダを変更しない。
- メインウィンドウを2個開いても、受け取ったウィンドウだけを更新。
- NULを含む不正なローカルURLを例外終了せず拒否。
- Trial47の既存試験でファイル単体・複数フォルダ・存在しないパス・Web URL・通常テキストの拒否、別ダイアログへの影響なし、自動読込なし、設定ファイルへの自動保存なしを確認。
- 全40本には照合・キャッシュ・全数・社員ID・起動月度・設定追加・未知JSON属性保持・キーボード・画面解放・マニュアル・印刷PDF・Excel連携モックの既存回帰試験を含む。

## 静的レビューと配布物

本番Pythonの差分はmain.pyのみ。照合エンジン・設定保存・キャッシュ・onedirビルドに追加変更なし。フィルターはメイン画面内のウィジェットに限定し、アプリ全体には設置しない。ChildPolishedで後から追加した子ウィジェットにも設置する。設定・詳細など独立ウィンドウには適用しない。

ZIP CRC合格、SHA256合格。manifestの375ファイルすべてをZIP内データと作業ソースの両方に照合し一致。manifest自身を含め376ファイル。GitHub掲載ZIPのサイズ・Git blob SHAも一致。

対象ZIP: AttendSync_Trial47_Window_Folder_Drop_Complete.zip
サイズ: 10,872,248バイト
SHA256: `e58133163d7c93e1a17cda32546fcc45a4e73f56738c9321d3b91d457d13dce2`
Git blob SHA: `065b15f1cf3ff8273bf5997bf8af50757860994b`

追加試験の実行コード・ログはaudits/Trial47/Boundary_Audit.py、Boundary_Audit.logを参照。実行コードはsys.pathの作業パスを展開先のAttendSyncに変更すれば再実行できる。元ZIPのtest_trial47_folder_drop.pyを利用する。

## 検証の範囲

Linux/Python3.12/PySide6のoffscreen環境で、実Qtイベントと実QThreadを使って検証。Windows ExplorerのOSドラッグ配送、Windows EXEの実ビルド・起動、高DPI、実Excel・プリンター・未開示の会社データは未検証。OSタイトルバー・枠はアプリの描画領域外。今回の監査をWindows実機確認の代わりにはしない。
