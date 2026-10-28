"""Create a self-contained onedir build ZIP, with its own no-tests manifest."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import zipfile

PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT))
from companion.metadata import VERSION
from scripts.package_source import source_files


def create_kit(project,output):
    project=Path(project);output=Path(output)
    files={p.relative_to(project).as_posix():p.read_bytes() for p in source_files(project)
           if not (p.relative_to(project).parts[0] in ('tests','.github') or p.name.startswith('preview') or p.name in ('BuildWindows.cmd','SPLIT_README.txt'))}
    commands=files['ONEDIR_COMMAND.txt'].decode('utf-8').replace('\r\n','\n')
    guide=f'''# Yohaku v{VERSION} onedirビルド用セット

このZIPだけを新しい空のフォルダーへ展開してください。testsフォルダーは不要です。
Windows 11の64bit Python 3.11または3.12を使用します。
Yohaku.specとmain.pyが並ぶYohakuフォルダーでPowerShellを開き、次の5行を順番に実行してください。バッチや仮想環境の有効化は不要です。

```powershell
{commands}```

Python 3.12の場合は1行目を `py -3.12 -m venv .venv` に変更します。
出力はdist/Yohaku/Yohaku.exeとYohaku-v{VERSION}-windows-x64-onedir.zipです。
同じフォルダーに独立した編集ツールYohakuContentEditor.exeも作成します。
_internalを含むdist/Yohakuフォルダー全体を配布してください。

起動するとYohaku.exeの隣のDataにユーザー設定を保存します。初回にDataがない場合は旧LocalAppDataからコピーします。更新時は使用中のDataも新しいEXEの隣へ持ち越してください。使用中のDataはこのビルド用ZIPやEXEの素材に含めません。
成長・トロフィー・衣装はタスクトレイの「一緒に過ごした記録・衣装」から確認します。経験値はEXP表記です。通常は5分ごとに付与・保存し、獲得した量をキャラの頭付近でフェード・上昇表示します。独立エディタでパックを保存した後、成長画面の「パックを再読み込み」で反映します。進行はData/growth.json、コンテンツはData/content/<パックID>/pack.jsonに分離しています。詳しくはdocs/GROWTH.mdを参照してください。

ファイル／フォルダーを「預ける」で一時ランチャーに登録できます。本体は移動・削除しません。保持は1日・1週間・1ヶ月・無期限から設定します。
PDFは吹き出しから預ける・移動・印刷、その他のファイル／フォルダーは預ける・移動を選べます。
移動先は表示名とフルパスを登録し、PDF印刷はA4・A3・用紙サイズに合わせる、から選択します。
印刷はWindowsの既定プリンターへ直接送信し、カラー／モノクロは文書から自動判定します。
つづり・ビット・ペギーの3体と全7性格を含みます。

このセットの検査マニフェストは実際の同梱ファイルだけを対象にしています。
旧版や通常のソースZIPと混ぜず、このZIPを単独で展開してください。単体specだけでは本体・素材が足りないため、初回はZIPを使用します。
'''
    files['README.md']=guide.encode('utf-8')
    files['BUILD_ONEDIR.txt']=guide.replace('\n','\r\n').encode('utf-8-sig')
    manifest={name:hashlib.sha256(data).hexdigest() for name,data in sorted(files.items())}
    files['MANIFEST_SHA256.json']=(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
        for name,data in sorted(files.items()):archive.writestr('Yohaku/'+name,data)
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:raise RuntimeError('ZIP CRC error')
        for name,digest in manifest.items():
            if hashlib.sha256(archive.read('Yohaku/'+name)).hexdigest()!=digest:raise RuntimeError('ZIP digest error')
    digest=hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix('.zip.sha256').write_text(digest+'  '+output.name+'\n',encoding='ascii')
    print(f'{output}: {len(manifest)} files, {output.stat().st_size} bytes, no tests')
    return files

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=PROJECT/'release'/f'Yohaku-v{VERSION}-onedir-build.zip')
    create_kit(PROJECT,parser.parse_args().output)
