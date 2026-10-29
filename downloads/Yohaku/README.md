# Yohaku v0.37.2

**[onedirビルド用ZIP（約14MB）](https://github.com/alz7485/codex3/raw/refs/heads/main/downloads/Yohaku/Yohaku-v0.37.2-onedir-build.zip)**

[spec単体](Yohaku.spec) · [5行のコマンド](BUILD_ONEDIR.txt) · [SHA-256](Yohaku-v0.37.2-onedir-build.zip.sha256) · [全ソース](Yohaku-v0.37.2-source.zip)

呼び出しの吹き出しは、ボタン以外のクリックで閉じます。デスクトップや他アプリのクリックにも対応し、選択肢ボタンは通常どおり操作できます。入力フォームやファイル処理の選択中には適用しません。[呼び出しの操作](../../Yohaku/docs/CALL_MENU.md)

白い選択肢ボタンを継続します。[画面例](../../Yohaku/docs/speech-choices.png)

複数ファイル・フォルダーの受け渡しと7z解凍を継続します。[使い方と制限](../../Yohaku/docs/FILE_DROP.md)

初期の育成ペース調整を継続します。[育成条件](../../Yohaku/docs/GROWTH_PACING.md)

トロフィー条件34種類と、ZIPの解凍・移動・キャンセルを継続します。[追加条件とZIP処理](../../Yohaku/docs/GROWTH_EXPANDED.md)

育成のステータス画面をリニューアルしました。キャラ・レベル・EXPのカード、成長の数字、解放予定と衣装の案内をまとめています。

育成ホーム・解放一覧・トロフィーの条件と現在値・衣装の試着を追加しました。衣装は組み合わせを確認してから一括装着できます。[育成画面](../../Yohaku/docs/GROWTH.md)

呼び出し後の操作案内・処理結果・レベルアップ・退勤前の既定メッセージ43項目を全7性格にそろえました。会話編集UIの「操作案内」から編集できます。[案内と編集](../../Yohaku/docs/SYSTEM_DIALOGUE.md)

レベルアップ時、つづり・ビット・ペギーそれぞれが約2.8秒喜ぶ専用アニメーションを表示します。[動きの例](../../Yohaku/docs/growth-level-animation.gif)

EXP獲得時、キャラの頭付近に「+5 EXP」など実際の獲得量をフェードイン・フェードアウトしながら下から上へ表示します。通常は5分ごとに5 EXPを付与・JSON保存します。同時の実績報酬は合計し、吹き出しや操作を遮りません。[アニメーション](../../Yohaku/docs/growth-exp.gif) · [レベルアップ](../../Yohaku/docs/growth-level-up.png) · [ステータス画面](../../Yohaku/docs/growth-status.png)

タスクトレイの「一緒に過ごした記録・衣装」でキャラ別の進行と装備を確認します。独立したYohakuContentEditor.exeで会話・演出・実績・レベル報酬・衣装を編集できます。衣装の連続プレビュー、報酬の名前検索、保存競合後の同じパックの再読み込みに対応します。[編集画面](../../Yohaku/docs/growth-editor.png) · [使い方・追加方法・制約](../../Yohaku/docs/GROWTH.md)

ZIPを新しい空の場所に展開し、Yohaku.specとmain.pyが並ぶYohakuフォルダでONEDIR_COMMAND.txtの5行を順に実行します。Windows 11・64bit Python 3.11/3.12を使用し、バッチや仮想環境の有効化は不要です。testsは要求しません。Yohaku.exeとYohakuContentEditor.exeを同じdist/Yohaku内に作成します。_internalを含むフォルダ全体を配布してください。

ユーザー設定・成長・編集したパックは、EXEの隣のDataに保存します。更新時は使用中のData全体も新しいEXEの隣へ持ち越してください。編集済みのbaseパックは上書きしません。[保存先・移行](../../Yohaku/docs/PORTABLE_DATA.md)

成長システム導入前の保存地点は **[yohaku-v0.29.0-before-growth](https://github.com/alz7485/codex3/tree/yohaku-v0.29.0-before-growth/Yohaku)** です。タグは維持しており、実PCのDataは別途バックアップしてください。

つづり・ビット・ペギーの3体と全7性格、予定・メール・ファイル履歴・一時ランチャー・ファイル移動・PDF印刷を継続します。[ファイル処理](../../Yohaku/docs/FILE_DROP.md) · [預ける機能](../../Yohaku/docs/SHELF.md) · [Windows検証](https://github.com/alz7485/codex3/actions/workflows/yohaku-windows.yml)
