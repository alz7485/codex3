"""7z extraction into a private staging directory with bounded disk writers."""
from pathlib import Path
from types import SimpleNamespace
import os

from .file_drop import FileDropError,MAX_ENTRIES,MAX_EXPANDED_BYTES,archive_members


def extract_7z(source,stage,password):
    import py7zr
    from py7zr.io import Py7zIO,WriterFactory
    handles=[]
    try:
        with py7zr.SevenZipFile(source,'r',password=password or None) as archive:
            if len(archive.files)>MAX_ENTRIES:raise FileDropError('解凍は10,000項目・合計1GiBまでです。')
            rows=[]
            for item in archive.files:
                if item.is_symlink or item.is_junction or item.is_socket or not (item.is_directory or item.is_file):
                    raise FileDropError('リンクや特殊ファイルを含む7zは解凍できません。')
                if type(item.uncompressed) is not int or item.uncompressed<0:raise FileDropError('7zのサイズ情報が不正です。')
                rows.append(SimpleNamespace(filename=item.filename,file_size=item.uncompressed,external_attr=0,
                                            is_dir=lambda directory=item.is_directory:directory))
            members=archive_members(SimpleNamespace(infolist=lambda:rows));expected={}
            for row,relative in members:
                output=stage.joinpath(*relative.parts)
                if row.is_dir():output.mkdir(parents=True,exist_ok=True)
                else:
                    output.parent.mkdir(parents=True,exist_ok=True)
                    expected[os.path.normcase(str(output.resolve()))]=(output,row.file_size)
            class Writer(Py7zIO):
                def __init__(self,path,limit):
                    self.stream=path.open('x+b');self.limit=limit;self.length=0;handles.append(self)
                def write(self,data):
                    end=self.stream.tell()+len(data)
                    if end>self.limit or end>MAX_EXPANDED_BYTES:raise FileDropError('解凍サイズの上限を超えています。')
                    written=self.stream.write(data);self.length=max(self.length,end);return written
                def read(self,size=None):return self.stream.read(-1 if size is None else size)
                def seek(self,offset,whence=0):
                    position=self.stream.seek(offset,whence)
                    if not 0<=position<=self.limit:raise FileDropError('7zの書き込み位置が不正です。')
                    return position
                def flush(self):self.stream.flush()
                def size(self):return self.length
            class Factory(WriterFactory):
                def create(self,filename):
                    key=os.path.normcase(str(Path(filename).resolve()))
                    if key not in expected:raise FileDropError('未登録の解凍先です。')
                    output,limit=expected[key];return Writer(output,limit)
            archive.extractall(path=stage,factory=Factory())
            for writer in handles:writer.flush()
            if any(not path.is_file() or path.stat().st_size!=size for path,size in expected.values()):
                raise FileDropError('7zの解凍結果を確認できません。')
    except FileDropError:raise
    except Exception:
        raise FileDropError('7zを解凍できません。パスワード・圧縮データ・対応形式を確認してください。元ファイルは保持しています。') from None
    finally:
        for writer in handles:writer.stream.close()
