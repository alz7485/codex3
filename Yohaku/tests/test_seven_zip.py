from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch,Mock
import unittest
import py7zr
from companion.file_drop import defaults,execute,FileDropError,FileDropStore

class SevenZipTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name);self.out=self.root/'out';self.out.mkdir()
        self.rule=defaults()['rules'][1];self.rule.update(destination=str(self.out),password_template='pass{month}',actions=[dict(action='extract',label='解凍する')])
    def test_regular_and_encrypted_header_archives_extract_and_keep_source(self):
        for password in (None,'pass10'):
            name='plain' if password is None else 'encrypted';source=self.root/(name+'.7z')
            with py7zr.SevenZipFile(source,'w',password=password,header_encryption=password is not None) as archive:
                archive.writestr(b'hello','dir/note.txt');archive.writestr(b'','empty.txt')
            result=execute('extract',source,self.rule,datetime(2026,10,1))
            self.assertTrue(source.exists());self.assertTrue(result['source_preserved'])
            self.assertEqual((self.out/name/'dir/note.txt').read_bytes(),b'hello');self.assertEqual((self.out/name/'empty.txt').read_bytes(),b'')
    def test_wrong_password_keeps_source_and_publishes_nothing(self):
        source=self.root/'secret.7z'
        with py7zr.SevenZipFile(source,'w',password='different',header_encryption=True) as archive:archive.writestr(b'hello','note.txt')
        with self.assertRaises(FileDropError):execute('extract',source,self.rule,datetime(2026,10,1))
        self.assertTrue(source.exists());self.assertEqual(list(self.out.iterdir()),[])
    def test_unsafe_members_links_and_size_limits_are_rejected_before_extraction(self):
        source=self.root/'unsafe.7z';source.write_bytes(b'fake')
        base=dict(filename='note.txt',uncompressed=5,is_directory=False,is_file=True,is_symlink=False,is_junction=False,is_socket=False)
        for update in ({'filename':'../outside'},{'filename':'C:/outside'},{'is_symlink':True},{'uncompressed':1024**3+1}):
            archive=Mock();archive.files=[SimpleNamespace(**dict(base,**update))];archive.__enter__=Mock(return_value=archive);archive.__exit__=Mock(return_value=False)
            with patch('py7zr.SevenZipFile',return_value=archive),self.assertRaises(FileDropError):execute('extract',source,self.rule,datetime(2026,10,1))
            archive.extractall.assert_not_called();self.assertTrue(source.exists());self.assertEqual(list(self.out.iterdir()),[])
    def test_writer_enforces_actual_size_and_legacy_zip_rule_supplies_7z_password(self):
        source=self.root/'overflow.7z';source.write_bytes(b'fake')
        member=SimpleNamespace(filename='note.txt',uncompressed=1,is_directory=False,is_file=True,is_symlink=False,is_junction=False,is_socket=False)
        archive=Mock();archive.files=[member];archive.__enter__=Mock(return_value=archive);archive.__exit__=Mock(return_value=False)
        def extractall(path,factory):factory.create(str(path/'note.txt')).write(b'oversize')
        archive.extractall.side_effect=extractall
        with patch('py7zr.SevenZipFile',return_value=archive),self.assertRaises(FileDropError):execute('extract',source,self.rule,datetime(2026,10,1))
        self.assertEqual(list(self.out.iterdir()),[])
        store=FileDropStore(self.root/'settings.json');document=defaults();document['rules'][1]['extensions']=['.zip'];document['rules'][1]['password_template']='saved{month}'
        store.save(document);rule=store.matching_rule(source)
        self.assertEqual(rule['password_template'],'saved{month}');self.assertIn('.7z',rule['extensions'])
