from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock
from companion.file_batch import selection,group_kind,execute_batch
from companion.file_drop import FileDropError,file_identity

class FileBatchTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.out=self.root/'out';self.out.mkdir()
    def file(self,name):
        path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'content');return path
    def rules(self,paths):return [dict(destination=str(self.out)) for _ in paths]
    def run_batch(self,paths,perform):return execute_batch(paths,tuple(file_identity(p) for p in paths),'move',self.rules(paths),datetime.now(),perform)
    def test_selection_deduplicates_and_classifies_only_homogeneous_file_groups(self):
        a=self.file('a.PDF');b=self.file('b.pdf');z=self.file('c.ZIP');s=self.file('d.7z');folder=self.root/'folder.pdf';folder.mkdir()
        self.assertEqual(selection([a,a,b]),(a,b));self.assertEqual(group_kind((a,b)),'pdf')
        self.assertEqual(group_kind((z,s)),'archive')
        for paths in ((a,z),(a,folder),(folder,folder)):self.assertEqual(group_kind(paths),'other')
        with self.assertRaises(FileDropError):selection([a]*501)
    def test_stops_at_first_failure_and_reports_completed_and_remaining(self):
        paths=tuple(self.file(n) for n in ('a','b','c'));calls=[]
        def perform(action,path,rule,now):
            calls.append(path.name)
            if path.name=='b':raise FileDropError('failed')
            return {'path':str(path)}
        result=self.run_batch(paths,perform)
        self.assertEqual(calls,['a','b']);self.assertEqual([r['name'] for r in result['completed']],['a'])
        self.assertEqual(result['remaining'],['b','c']);self.assertEqual(result['error'],'failed')
    def test_collision_existing_target_and_overlapping_selection_fail_before_operations(self):
        a=self.file('one/same.txt');b=self.file('two/SAME.txt');perform=Mock()
        self.assertTrue(self.run_batch((a,b),perform)['error']);perform.assert_not_called()
        (self.out/a.name).write_bytes(b'keep');self.assertTrue(self.run_batch((a,),perform)['error']);perform.assert_not_called()
        folder=self.root/'one';self.assertTrue(self.run_batch((folder,a),perform)['error']);perform.assert_not_called()
        self.assertEqual((self.out/a.name).read_bytes(),b'keep')
    def test_changed_member_is_detected_before_any_operation(self):
        paths=(self.file('a'),self.file('b'));ids=tuple(file_identity(p) for p in paths);paths[1].write_bytes(b'changed')
        perform=Mock();result=execute_batch(paths,ids,'move',self.rules(paths),datetime.now(),perform)
        self.assertEqual(result['completed'],[]);self.assertEqual(result['remaining'],['a','b']);perform.assert_not_called()
