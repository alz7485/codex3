"""Pack isolation, declarative schema, cross references and non-destructive reload."""
from copy import deepcopy
from pathlib import Path
import json
import tempfile
import unittest
from companion.growth_content import (ContentError,asset_path,atomic_json,inspect_pack,load_catalog,
    read_json,seed_content,validate_condition,validate_config)

class ContentTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        seed_content(self.root);self.folder=self.root/'base';self.path=self.folder/'pack.json';self.doc=read_json(self.path)
    def save(self):atomic_json(self.path,self.doc)
    def test_shipped_pack_validates_with_small_samples_for_all_characters_and_seven_voices(self):
        c=load_catalog(self.root);self.assertFalse(c.errors);self.assertEqual(c.config['exp_per_hour'],60)
        self.assertEqual(len(c.items['costumes']),1);self.assertEqual(len(c.items['trophies']),0)
        self.assertEqual(len(self.doc['lines'][0]['texts']),7)
    def test_seed_never_overwrites_user_edited_or_corrupt_base(self):
        self.path.write_text('{broken');seed_content(self.root);self.assertEqual(self.path.read_text(),'{broken')
    def test_invalid_json_is_isolated_and_base_failure_stops_growth_explicitly(self):
        (self.root/'bad').mkdir();(self.root/'bad/pack.json').write_text('{bad')
        self.assertTrue(load_catalog(self.root).errors);self.assertIsNotNone(load_catalog(self.root).config)
        self.path.write_text('{bad');self.assertIsNone(load_catalog(self.root).config)
    def test_missing_image_disables_only_costume_and_dependent_reward(self):
        (self.folder/'ribbon.png').unlink();c=load_catalog(self.root)
        self.assertFalse(c.items['costumes']);self.assertFalse(c.items['rewards'])
        self.assertTrue(c.items['lines']);self.assertTrue(c.items['events']);self.assertTrue(c.errors)
    def test_duplicate_item_ids_invalidate_both_definitions(self):
        self.doc['lines'].append(deepcopy(self.doc['lines'][0]));self.save();c=load_catalog(self.root)
        self.assertFalse(c.items['lines']);self.assertTrue(c.items['events'])
    def test_duplicate_pack_ids_invalidate_all_conflicting_packs(self):
        other=self.root/'other';other.mkdir();atomic_json(other/'pack.json',self.doc)
        c=load_catalog(self.root);self.assertFalse(c.items['lines']);self.assertIsNone(c.config)
    def test_cross_pack_refs_are_supported_and_removed_dependencies_cascade(self):
        other=self.root/'extra';other.mkdir();doc=dict(self.doc,id='extra',name='追加',costumes=[],rewards=[],trophies=[],lines=[])
        event=deepcopy(self.doc['events'][0]);event['conditions']=[dict(type='event_count',event_id='base:small_sparkle',op='>=',value=1)];doc['events']=[event]
        atomic_json(other/'pack.json',doc);self.assertIn('extra:small_sparkle',load_catalog(self.root).items['events'])
        self.doc['events'][0]['enabled']=False;self.save();c=load_catalog(self.root)
        self.assertNotIn('extra:small_sparkle',c.items['events'])
    def test_asset_path_rejects_absolute_traversal_and_non_png(self):
        for name in ('../ribbon.png','/ribbon.png','C:/ribbon.png','x\\ribbon.png','ribbon.json'):
            self.assertRaises(ContentError,asset_path,self.folder,name)
    def test_corrupt_or_oversized_png_header_is_rejected_before_decode(self):
        p=self.folder/'bad.png';p.write_bytes(b'not png');self.assertRaises(ContentError,asset_path,self.folder,p.name)
        p.write_bytes(b'\x89PNG\r\n\x1a\n'+b'\x00\x00\x00\rIHDR'+(100000).to_bytes(4,'big')*2)
        self.assertRaises(ContentError,asset_path,self.folder,p.name)
    def test_unknown_types_nan_booleans_and_unsafe_frame_numbers_are_rejected(self):
        for c in (dict(type='python',code='anything'),dict(type='metric',metric='cpu_percent',op='>=',value=float('nan')),dict(type='app_count',op='>=',value=True)):
            self.assertRaises(ContentError,validate_condition,c)
        self.doc['costumes'][0]['variants'][0]['frames']=[28];self.save();self.assertFalse(load_catalog(self.root).items['costumes'])
    def test_disabled_packs_do_not_supply_config_or_items(self):
        self.doc['enabled']=False;self.save();c=load_catalog(self.root)
        self.assertIsNone(c.config);self.assertFalse(c.items['events']);self.assertIn('base',c.packs)
    def test_level_curve_and_sample_exp_fields_use_exp(self):
        self.assertNotIn('"xp"',json.dumps(self.doc));self.assertIn('exp_per_hour',self.doc['config'])
        self.assertEqual(self.doc['config']['exp_interval_seconds'],300)
        c=deepcopy(self.doc['config']);c['level_thresholds']=[0,10,10]
        self.assertRaises(ContentError,validate_config,c)
    def test_invalid_entry_does_not_stop_neighboring_entries(self):
        self.doc['lines'].append(dict(id='bad',enabled=True));self.save();c=load_catalog(self.root)
        self.assertIn('base:company',c.items['lines']);self.assertTrue(c.errors)
    def test_atomic_save_leaves_no_temporary_file_and_partial_read_never_occurs(self):
        atomic_json(self.path,self.doc);self.assertEqual(read_json(self.path),self.doc)
        self.assertFalse(list(self.folder.glob('.*.tmp')))
    def test_atomic_save_hash_matches_exact_utf8_bytes_and_oversized_save_keeps_original(self):
        from companion.growth_content import MAX_JSON,read_json_snapshot
        import hashlib
        digest=atomic_json(self.path,self.doc)
        original=self.path.read_bytes();self.assertEqual(digest,hashlib.sha256(original).hexdigest())
        self.assertNotIn(b'\r\n',original);self.assertEqual(read_json_snapshot(self.path),(self.doc,digest))
        self.assertRaises(ContentError,atomic_json,self.path,{'text':'x'*MAX_JSON})
        self.assertEqual(self.path.read_bytes(),original)
    def test_unreadable_pack_directory_is_reported_without_crashing_or_using_default_config(self):
        from unittest.mock import patch
        with patch.object(Path,'iterdir',side_effect=PermissionError('synthetic')):catalog=load_catalog(self.root)
        self.assertIsNone(catalog.config);self.assertTrue(catalog.errors)
