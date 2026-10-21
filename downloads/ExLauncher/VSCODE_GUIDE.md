# VS Codeから起動・EXE作成

WindowsのPython 3.11または3.12を推奨します。今回の `No module named PyInstaller` は、ビルドに使ったPythonにPyInstallerが未導入だったことが原因です。v1.0.6ではフォルダ内の `.venv` へ必要なパッケージをまとめて導入します。

## 初回の準備

1. ZIPをすべて展開し、VS Codeの「フォルダーを開く」で **main.pyと.vscodeが入っているフォルダ** を開きます。
2. 拡張機能「Python」「Python Debugger」（どちらもMicrosoft）をインストールします。フォルダの推奨拡張にも登録してあります。
3. VS Codeのターミナルで次を実行します。

```powershell
python scripts/build_onedir.py --setup-only
```

初回は `.venv` を作成し、PySide6とPyInstallerをダウンロードします。システムのPythonへインストールしません。準備済みなら再利用します。

4. `Ctrl+Shift+P` → `Python: インタープリターを選択` → `.venv\Scripts\python.exe` を選びます。

「ターミナル → タスクの実行 → ExLauncher: 環境準備」でも準備できます。初回のタスク実行には、現在インストールされているPython 3.11/3.12を選んでください。

## アプリを起動する

**F5** を押し、「ExLauncher: 起動・デバッグ」を選びます。終了・停止はShift+F5です。

ターミナルから起動する場合は次のコマンドです。PowerShellで仮想環境を有効化する操作は不要です。

```powershell
.\.venv\Scripts\python.exe main.py
```

## EXEを作成する

**Ctrl+Shift+B** → 「ExLauncher: EXEを作成」を実行します。ビルドにはF5と同じ `.venv` を使います。`build_onedir.bat` のダブルクリックでも同じ準備・ビルドを実行します。

出力先は `dist\ExLauncher\ExLauncher.exe` です。配布時は **dist\ExLauncherフォルダ全体** を渡してください。`_internal` も必要です。

ターミナルからビルドする場合：

```powershell
python scripts/build_onedir.py
```

既存のdist側のランチャーは終了してからビルドしてください。ビルド成功後に既存の利用者JSONを引き継ぎ、旧出力は `ExLauncher.previous-日時` として残します。

ソース実行時の設定はソースの隣、EXE実行時の設定はEXEの隣に保存されます。ソース横の個人設定はビルドへ自動同梱しません。

Windows上のVS Code・BAT・EXEの実機確認は未実施です。検証した範囲は `validation_v1.0.6.json` を参照してください。
