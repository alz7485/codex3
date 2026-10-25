"""Three active characters, all voices and lossless legacy-data compatibility."""
from copy import deepcopy
import json
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import tempfile
import unittest

from companion.characters import CHARACTERS
from companion.core import Settings, save_json
from companion.dialogue import (AUTO_PERSONALITY, MAX_BYTES, VOICE_NAMES, DialogueError,
                               DialogueStore, defaults, document_size, read_document, validate)
from companion.dialogue_editor import DialogueEditor
from companion.ui import character_frames, character_pixmap, create_application
from scripts.package_source import source_files


def legacy_document():
    document = defaults()
    for key, voice in zip('FNSH', ('のんびりした同僚', '馴れ馴れしい関西弁', '寡黙な先輩', '孤高のギャンブラー')):
        document['profiles'][key] = dict(voice=voice, description='前の版で編集した説明', tagline='残しておく一言')
    return document


class LightweightCharacterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_application()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def test_three_characters_retain_all_seven_voice_banks(self):
        self.assertEqual(CHARACTERS, {'A': 'つづり', 'B': 'ビット', 'E': 'ペンギー'})
        document = defaults()
        self.assertEqual(set(document['profiles']), set('ABE'))
        self.assertEqual(len(VOICE_NAMES), 7)
        self.assertEqual(set(document['phrases']), set(VOICE_NAMES))
        for bank in document['phrases'].values():
            self.assertEqual(sum(map(len, bank.values())), 217)

    def test_retired_character_settings_fall_back_and_keep_each_explicit_voice(self):
        for retired in 'FNSH':
            for voice in (AUTO_PERSONALITY, *VOICE_NAMES):
                save_json(self.root/'settings.json', vars(Settings(character=retired, personality=voice)))
                loaded = Settings.load(self.root/'settings.json')
                self.assertEqual(loaded.character, 'A')
                self.assertEqual(loaded.personality, voice)

    def test_legacy_profiles_and_custom_lines_survive_read_save_and_backup(self):
        old = legacy_document()
        old['profiles']['A'].update(voice='寡黙な先輩', description='自分の説明', tagline='自分の一言')
        old['phrases']['馴れ馴れしい関西弁']['chat'] = ['編集した関西弁やで。']
        path = self.root/'dialogue.json'
        path.write_text(json.dumps(old, ensure_ascii=False), encoding='utf-8')
        raw = path.read_bytes(); store = DialogueStore(path)
        self.assertFalse(store.error)
        self.assertEqual(path.read_bytes(), raw)
        self.assertEqual(store.data, old)
        store.save(store.data)
        self.assertEqual(path.with_suffix('.json.bak').read_bytes(), raw)
        self.assertEqual(read_document(path), old)
        invalid = deepcopy(old); invalid['profiles']['unknown'] = deepcopy(old['profiles']['A'])
        with self.assertRaises(DialogueError):
            validate(invalid)

    def test_full_legacy_document_remains_valid_without_expansion(self):
        document = legacy_document(); document['padding'] = ''
        document['padding'] = 'x' * (MAX_BYTES - document_size(document))
        path = self.root/'dialogue.json'
        path.write_text(json.dumps(document, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
        raw = path.read_bytes(); self.assertEqual(len(raw), MAX_BYTES)
        store = DialogueStore(path)
        self.assertFalse(store.error); self.assertEqual(store.data, document)
        store.save(store.data); self.assertEqual(path.read_bytes(), raw)

    def test_editor_lists_only_active_characters_and_keeps_retired_metadata(self):
        store = DialogueStore(self.root/'dialogue.json'); store.data = legacy_document()
        editor = DialogueEditor(store)
        try:
            self.assertEqual([editor.profile_key.itemText(i) for i in range(editor.profile_key.count())], list(CHARACTERS.values()))
            self.assertEqual([editor.voice.itemText(i) for i in range(editor.voice.count())], list(VOICE_NAMES))
            old = deepcopy(store.data['profiles'])
            for index, key in enumerate(CHARACTERS):
                editor.profile_key.setCurrentIndex(index)
                editor.description.setText('説明：' + CHARACTERS[key])
                self.assertEqual(editor.draft['profiles'][key]['description'], '説明：' + CHARACTERS[key])
            for key in 'FNSH':
                self.assertEqual(editor.draft['profiles'][key], old[key])
            store.save(editor.draft); self.assertEqual(read_document(store.path), editor.draft)
        finally:
            editor.dirty = False; editor.hide(); editor.deleteLater()

    def test_runtime_artwork_has_only_three_sheets_and_shared_fronts(self):
        project = Path(__file__).resolve().parents[1]
        actual = {p.name for p in (project/'companion/assets/characters').iterdir() if p.is_file()}
        self.assertEqual(actual, {'a_motion.png', 'b_motion.png', 'e_motion.png', 'front_reactions.png', 'motion_layout.json'})
        for character in CHARACTERS:
            frames = character_frames(character)
            self.assertEqual(len(frames), 28)
            self.assertEqual(character_pixmap(character).toImage(), frames[24].toImage())
        self.assertFalse(any(p.relative_to(project).parts[0] == 'docs' and p.suffix in ('.png', '.gif') for p in source_files(project)))
