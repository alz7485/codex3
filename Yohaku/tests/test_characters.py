"""Approved characters, legacy conversation preservation and editor integration."""
from copy import deepcopy
import json
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import tempfile
import unittest

from companion.characters import CHARACTERS, LEGACY_CHARACTERS, NEW_PROFILES
from companion.core import Settings, save_json
from companion.dialogue import (AUTO_PERSONALITY, MAX_BYTES, DialogueError, DialogueStore,
                               defaults, document_size, read_document, validate, voice_for)
from companion.dialogue_editor import DialogueEditor
from companion.ui import Panel, character_frames, create_application


class AddedCharacterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_application()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def test_approved_species_names_and_recommended_voices(self):
        expected = {'N': ('なぎ', '馴れ馴れしい関西弁'),
                    'S': ('しずく', '寡黙な先輩'), 'H': ('すみ', '孤高のギャンブラー')}
        self.assertEqual(len(CHARACTERS), 7)
        for key, (name, voice) in expected.items():
            self.assertEqual(CHARACTERS[key], name)
            settings = Settings(character=key)
            self.assertEqual(voice_for(settings), voice)
            save_json(self.root/'settings.json', vars(settings))
            self.assertEqual(Settings.load(self.root/'settings.json').character, key)
            settings.personality = '冷静な案内役'
            self.assertEqual(voice_for(settings), '冷静な案内役')

    def test_old_four_profiles_gain_three_without_rewriting_custom_words_or_source(self):
        old = defaults()
        old['profiles'] = {key: old['profiles'][key] for key in LEGACY_CHARACTERS}
        old['profiles']['A'].update(voice='寡黙な先輩', description='自分の説明', tagline='自分の一言')
        old['phrases']['馴れ馴れしい関西弁']['chat'] = ['編集した関西弁やで。']
        path = self.root/'dialogue.json'
        path.write_text(json.dumps(old, ensure_ascii=False), encoding='utf-8')
        raw = path.read_bytes()
        store = DialogueStore(path)
        self.assertFalse(store.error)
        self.assertEqual(path.read_bytes(), raw)
        for key in LEGACY_CHARACTERS:
            self.assertEqual(store.data['profiles'][key], old['profiles'][key])
        for key in ('phrases', 'rules', 'options'):
            self.assertEqual(store.data[key], old[key])
        self.assertEqual({key: store.data['profiles'][key] for key in NEW_PROFILES}, NEW_PROFILES)
        store.save(store.data)
        self.assertEqual(path.with_suffix('.json.bak').read_bytes(), raw)
        self.assertEqual(read_document(path), store.data)

    def test_existing_new_profile_edits_are_preserved_and_unknown_ids_rejected(self):
        document = defaults()
        document['profiles']['H'].update(voice='馴れ馴れしい関西弁', tagline='ここは自分の言葉。')
        path = self.root/'dialogue.json'
        path.write_text(json.dumps(document, ensure_ascii=False), encoding='utf-8')
        self.assertEqual(read_document(path), document)
        document['profiles']['unknown'] = deepcopy(document['profiles']['A'])
        with self.assertRaises(DialogueError):
            validate(document)

    def test_full_legacy_document_uses_new_characters_without_data_loss(self):
        document = defaults()
        document['profiles'] = {key: document['profiles'][key] for key in LEGACY_CHARACTERS}
        # Unknown metadata is preserved for user tooling, and counts toward the cap.
        document['custom_padding'] = ''
        document['custom_padding'] = 'x' * (MAX_BYTES - document_size(document))
        path = self.root/'dialogue.json'
        path.write_text(json.dumps(document, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
        raw = path.read_bytes()
        self.assertEqual(len(raw), MAX_BYTES)
        store = DialogueStore(path)
        self.assertFalse(store.error)
        self.assertEqual(store.data, document)
        for key, profile in NEW_PROFILES.items():
            settings = Settings(character=key, personality=AUTO_PERSONALITY)
            self.assertEqual(voice_for(settings, store.data), profile['voice'])
            panel = Panel(settings, store)
            try:
                self.assertEqual(panel.profile(key), tuple(profile.values()))
            finally:
                panel.hide(); panel.deleteLater()
        store.save(store.data)
        self.assertEqual(path.read_bytes(), raw)

    def test_editor_targets_each_new_profile_and_preserves_other_profiles(self):
        store = DialogueStore(self.root/'dialogue.json')
        editor = DialogueEditor(store)
        try:
            old = deepcopy(store.data['profiles'])
            for key in NEW_PROFILES:
                editor.profile_key.setCurrentIndex(tuple(CHARACTERS).index(key))
                self.assertEqual(editor.profile_voice.currentText(), NEW_PROFILES[key]['voice'])
                editor.description.setText('編集した説明：' + CHARACTERS[key])
                self.assertEqual(editor.draft['profiles'][key]['description'], '編集した説明：' + CHARACTERS[key])
            for key in LEGACY_CHARACTERS:
                self.assertEqual(editor.draft['profiles'][key], old[key])
            store.save(editor.draft)
            self.assertEqual(read_document(store.path), editor.draft)
        finally:
            editor.dirty = False; editor.hide(); editor.deleteLater()

    def test_every_new_animation_frame_is_transparent_nonempty_and_unique_walk_cycle(self):
        for key in NEW_PROFILES:
            frames = character_frames(key)
            self.assertEqual(len(frames), 28)
            self.assertEqual(len({(frame.width(), frame.height()) for frame in frames}), 1)
            for index, frame in enumerate(frames):
                image = frame.toImage()
                self.assertTrue(image.hasAlphaChannel())
                self.assertEqual(image.pixelColor(0, 0).alpha(), 0)
                self.assertTrue(any(image.pixelColor(x, y).alpha() > 128
                                    for x in range(0, image.width(), 5)
                                    for y in range(0, image.height(), 5)), (key, index))
            self.assertEqual(len({bytes(frame.toImage().constBits()) for frame in frames[16:24]}), 8)
