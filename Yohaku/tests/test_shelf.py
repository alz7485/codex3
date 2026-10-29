"""Calendar-bound reference retention; original documents are never modified."""
from copy import deepcopy
from datetime import datetime,timedelta
import json
from pathlib import Path
import tempfile
import unittest
from companion.shelf import ShelfStore,ShelfError,next_reset,validate
from scripts.package_source import source_files

class ShelfTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.store=ShelfStore(self.root/'shelf.json');self.now=datetime(2026,10,26,12,30)
        self.file=self.root/'sample.txt';self.file.write_bytes(b'original')
    def test_daily_boundary_is_five_and_exact_boundary_starts_a_new_period(self):
        self.assertEqual(next_reset(datetime(2026,10,26,4,59),'day'),datetime(2026,10,26,5))
        self.assertEqual(next_reset(datetime(2026,10,26,5),'day'),datetime(2026,10,27,5))
        self.store.add(self.file,datetime(2026,10,26,4,59));self.assertEqual(len(self.store.prune(datetime(2026,10,26,4,59,59))),1)
        self.assertEqual(self.store.prune(datetime(2026,10,26,5)),[]);self.assertEqual(self.file.read_bytes(),b'original')
    def test_week_month_and_year_rollover_and_unlimited(self):
        self.assertEqual(next_reset(datetime(2026,10,25,23,59),'week'),datetime(2026,10,26))
        self.assertEqual(next_reset(datetime(2026,10,26),'week'),datetime(2026,11,2))
        self.assertEqual(next_reset(datetime(2026,12,31,23,59),'month'),datetime(2027,1,1))
        self.assertEqual(next_reset(datetime(2026,11,1),'month'),datetime(2026,12,1))
        self.assertIsNone(next_reset(self.now,'forever'))
        for period,due in [('week',datetime(2026,11,2)),('month',datetime(2026,11,1))]:
            store=ShelfStore(self.root/(period+'.json'));store.set_period(period,self.now);store.add(self.file,self.now)
            self.assertEqual(len(store.prune(due-timedelta(seconds=1))),1);self.assertEqual(store.prune(due),[])
    def test_redeposit_refreshes_one_reference_and_remove_keeps_file_and_folder(self):
        first=self.store.add(self.file,self.now);second=self.store.add(self.file,self.now+timedelta(hours=1))
        self.assertEqual(first,second);self.assertEqual(len(self.store.data['items']),1)
        folder=self.root/'folder';folder.mkdir();(folder/'inside.txt').write_bytes(b'keep')
        identifier=self.store.add(folder,self.now);self.store.remove(identifier);self.store.remove(first)
        self.assertEqual(self.store.data['items'],[]);self.assertEqual(self.file.read_bytes(),b'original')
        self.assertEqual((folder/'inside.txt').read_bytes(),b'keep')
    def test_restart_prunes_elapsed_boundaries_and_period_change_applies_to_existing_items(self):
        self.store.set_period('forever',self.now);self.store.add(self.file,self.now)
        later=self.now+timedelta(days=500);loaded=ShelfStore(self.store.path)
        self.assertEqual(len(loaded.prune(later)),1)
        loaded.set_period('day',later);self.assertFalse(loaded.data['items']);self.assertTrue(self.file.exists())
        self.assertEqual(ShelfStore(self.store.path).data['period'],'day')
    def test_invalid_json_preserved_and_bad_paths_ids_and_periods_rejected(self):
        self.store.path.write_text('{broken');loaded=ShelfStore(self.store.path);self.assertTrue(loaded.error)
        with self.assertRaises(ShelfError):loaded.add(self.file,self.now)
        self.assertEqual(self.store.path.read_text(),'{broken')
        row=dict(id='test',path=str(self.file),kind='file',added_at=self.now.isoformat())
        good=dict(schema_version=1,period='day',items=[row])
        self.assertEqual(validate(good),good)
        for field,value in [('path','relative'),('kind','command'),('id','../bad'),('added_at','bad'),('added_at','9999-12-31T00:00:00')]:
            candidate=deepcopy(good);candidate['items'][0][field]=value
            with self.subTest(field=field),self.assertRaises(ShelfError):validate(candidate)
        with self.assertRaises(ShelfError):validate(dict(good,period='hour'))
    def test_shelf_json_and_backups_are_private_and_missing_originals_remain_registered(self):
        self.store.add(self.file,self.now);self.file.unlink()
        self.assertEqual(len(self.store.prune(self.now)),1)
        self.store.set_period('forever',self.now)
        (self.root/'SHELF.JSON.TMP').write_text('private')
        self.assertFalse(source_files(self.root))

    def test_batch_deposit_is_atomic_on_capacity_and_save_failure(self):
        from unittest.mock import patch
        first=self.root/'first.txt';second=self.root/'second.txt';first.write_bytes(b'a');second.write_bytes(b'b')
        before=deepcopy(self.store.data)
        with patch('companion.shelf.MAX_ITEMS',1),self.assertRaises(ShelfError):self.store.add_many((first,second),self.now)
        self.assertEqual(self.store.data,before)
        with patch.object(self.store,'save',side_effect=OSError('full')),self.assertRaises(OSError):self.store.add_many((first,second),self.now)
        self.assertEqual(self.store.data,before);self.assertEqual(first.read_bytes(),b'a');self.assertEqual(second.read_bytes(),b'b')
        ids=self.store.add_many((first,second),self.now);self.assertEqual(len(ids),2);self.assertEqual([row['path'] for row in self.store.data['items']],[str(first),str(second)])
