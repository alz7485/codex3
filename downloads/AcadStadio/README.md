# AcadStadio

最新: **v1.59.0-beta84 — 参照点と移動量を別入力へ**

[更新ZIP](AcadStadio_v1.59.0_SeparateCoordinatesTrial84.zip) / [SHA256](AcadStadio_v1.59.0_SeparateCoordinatesTrial84.zip.sha256)

始点・終点・中間点の各軸に参照点と移動量の別入力欄を追加しました。座標は参照点＋移動量で計算し、参照点の空欄は0です。参照点100・移動量100なら座標200になります。数値・表・変数・式に対応し、点参照の別窓はコマンドの点だけを選びます。点の選び直しで移動量を保持します。表・変数・参照元の使用値は元の座標入力へ挿入でき、元に戻す／再編集にも対応します。プロジェクトは従来の座標式で保存します。

コア394件・GUI370件、計764件が通過。ソースとWindows onedir EXEビルド手順を同梱。Windows実機のAutoCAD・EXE動作は未確認です。使い方は docs/COORDINATE_VALUES.md を参照してください。
