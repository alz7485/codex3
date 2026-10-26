"""Named destination validation/migration with disposable synthetic data."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from companion.file_destinations import DestinationStore,validate
from companion.file_drop import FileDropStore,FileDropError,defaults
from scripts.package_source import source_files

class DestinationTests(unittest.TestCase):
    def test_old_paths_are_deduplicated_and_only_saved_on_explicit_save(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);old=FileDropStore(root/'file_drop_settings.json');document=defaults()
            for row in document['rules']:row['destination']=str(root/'archive')
            old.save(document);before=old.path.read_bytes()
            store=DestinationStore(root/'file_destinations.json',old)
            self.assertEqual(len(store.data['destinations']),1);self.assertEqual(store.data['destinations'][0]['name'],'archive')
            self.assertFalse(store.path.exists());self.assertEqual(old.path.read_bytes(),before)
            store.save(store.data);self.assertEqual(DestinationStore(store.path).data,store.data)

    def test_names_paths_ids_and_limits_are_checked(self):
        good=dict(schema_version=1,destinations=[dict(id='a',name='提出用',path='C:\\提出用')])
        self.assertEqual(validate(good),good)
        for field,value in [('name',''),('name','x'*61),('path','relative'),('path','C:\\ok\nno'),('id','../../x')]:
            bad=deepcopy(good);bad['destinations'][0][field]=value
            with self.subTest(field=field,value=value),self.assertRaises(FileDropError):validate(bad)
        bad=deepcopy(good);bad['destinations'].append(dict(id='b',name='提出用',path='D:\\other'))
        with self.assertRaises(FileDropError):validate(bad)
        self.assertEqual(validate(dict(schema_version=1,destinations=[]))['destinations'],[])

    def test_bad_json_is_preserved_and_backups_and_private_files_are_excluded(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);path=root/'file_destinations.json';path.write_text('{broken')
            store=DestinationStore(path);self.assertTrue(store.error);self.assertEqual(path.read_text(),'{broken')
            document=dict(schema_version=1,destinations=[dict(id='a',name='保管',path=str(root/'out'))])
            store.save(document);self.assertEqual(path.with_suffix('.json.bak').read_text(),'{broken')
            (root/'FILE_DESTINATIONS.JSON.TMP').write_text('private')
            self.assertFalse(source_files(root))
