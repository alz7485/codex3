import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from core import suggested_name, plan, execute, validate_name, folder_size, collisions, execute_with_deletions, deletion_mask, name_from_mask, normalize_punctuation


class FolderTests(unittest.TestCase):
    def test_punctuation_rules(self):
        cases = {'作品!': '作品！', '作品！': '作品！', '！！': '!!', '!!!': '!!!', '!！!': '!!!', '!？': '！？', '？!': '？！', '!?': '！？', '?!': '？！', '!!？': '！！？', '？!!': '？！！', '作品?': '作品?', '作品[特別!]': '作品[特別！]'}
        for source, expected in cases.items():
            with self.subTest(source=source):
                self.assertEqual(normalize_punctuation(source), expected)
                self.assertEqual(normalize_punctuation(expected), expected)

    def test_punctuation_after_deletion_and_filesystem(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            original = '作品![タグ]！'
            (root / original).mkdir()
            new = normalize_punctuation(name_from_mask(original, deletion_mask(original)))
            self.assertEqual(new, '作品!!')
            ops, groups = plan(root, [(original, new)])
            execute(ops, groups)
            self.assertTrue((root / '作品!!').is_dir())

    def test_title_with_brackets_can_be_preserved(self):
        name = '[先頭]作品(副題)[特別版](作者)[末尾]'
        start, end = name.index('(副題)'), name.index('(作者)')
        overrides = {i: False for i in range(start, end)}
        self.assertEqual(name_from_mask(name, deletion_mask(name, overrides=overrides)), '作品(副題)[特別版]')

    def test_partial_removal_inside_square(self):
        name = '作品[残す 消す]'
        overrides = {i: False for i in range(name.index('['), name.index(']') + 1)}
        for i in range(name.index(' 消す'), name.index(']')):
            overrides[i] = True
        self.assertEqual(name_from_mask(name, deletion_mask(name, overrides=overrides)), '作品[残す]')

    def test_custom_group_used_for_collision_and_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            name = '[タグ]作品(副題)(作者)'
            (root / name).mkdir()
            groups = {name: '自分で選択[分類](補足)'}
            rows = [(name, '作品(副題)')]
            self.assertEqual(collisions(root, rows, True, group_names=groups), [])
            execute_with_deletions(root, rows, True, True, set(), groups)
            self.assertTrue((root / groups[name] / '作品(副題)').is_dir())

    def test_double_brackets_are_one_square_segment(self):
        self.assertEqual(suggested_name('作品[(作者)](分類)', False, True), '作品(分類)')
        self.assertEqual(suggested_name('作品[(作者)](分類)', True, False), '作品[(作者)]')
        self.assertEqual(suggested_name('作品[(作者)]', True, True, {0}), '作品[(作者)]')

    def test_duplicate_size_and_selected_deletion(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            for name, contents in [('作品(A)', 'large data'), ('作品', 'small')]:
                (root / name).mkdir()
                (root / name / 'data').write_text(contents)
            rows = [('作品(A)', '作品')]
            pairs = collisions(root, rows)
            self.assertEqual(len(pairs), 1)
            self.assertGreater(folder_size(root / '作品(A)'), folder_size(root / '作品'))
            ops, groups, backup = execute_with_deletions(root, rows, False, False, {root / '作品'})
            self.assertEqual((root / '作品/data').read_text(), 'large data')
            self.assertTrue((backup / 'restore.json').exists())

    def test_duplicate_sources_larger_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            for name in ['a(A)', 'a(B)']:
                (root / name).mkdir()
            rows = [('a(A)', 'a'), ('a(B)', 'a')]
            self.assertEqual(len(collisions(root, rows)), 1)
            execute_with_deletions(root, rows, False, False, {root / 'a(A)'})
            self.assertTrue((root / 'a').exists())

    def test_deletion_restored_when_plan_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            for name in ['a', 'b', 'c']:
                (root / name).mkdir()
            with self.assertRaises(RuntimeError):
                execute_with_deletions(root, [('b', 'c')], False, False, {root / 'a'})
            self.assertTrue((root / 'a').is_dir())

    def test_protect_specific_occurrence(self):
        self.assertEqual(suggested_name('作品(作者)[タグ](作者)', True, True, {2}), '作品(作者)')
        self.assertEqual(suggested_name('作品（作者）［タグ］', True, False), '作品［タグ］')

    def test_group_and_rename(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            for name in ['作品(A)[タグ]', '別作品(A)']:
                (root / name).mkdir()
                (root / name / 'data.txt').write_text('keep')
            rows = [(name, suggested_name(name, True, True)) for name in ['作品(A)[タグ]', '別作品(A)']]
            ops, groups = plan(root, rows, True, True)
            execute(ops, groups)
            self.assertEqual((root / 'A/作品/data.txt').read_text(), 'keep')
            self.assertTrue((root / 'A/別作品').is_dir())
            self.assertEqual(plan(root, [('A', 'A')]), ([], set()))

    def test_collision(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / 'a').mkdir()
            (root / 'b').mkdir()
            with self.assertRaises(ValueError):
                plan(root, [('a', 'b')])
            with self.assertRaises(ValueError):
                plan(root, [('a', 'C'), ('b', 'c')])

    def test_create_without_move(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / '作品(A)').mkdir()
            ops, groups = plan(root, [('作品(A)', '作品(A)')], True)
            execute(ops, groups)
            self.assertTrue((root / 'A').is_dir())
            self.assertTrue((root / '作品(A)').is_dir())

    def test_rollback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            for name in ['a(A)', 'b(A)']:
                (root / name).mkdir()
            ops, groups = plan(root, [('a(A)', 'a'), ('b(A)', 'b')], True, True)
            original = Path.rename
            def fail_second(path, destination):
                if path.name == 'b(A)':
                    raise OSError('simulated failure')
                return original(path, destination)
            with patch.object(Path, 'rename', fail_second), self.assertRaises(RuntimeError):
                execute(ops, groups)
            self.assertTrue((root / 'a(A)').is_dir())
            self.assertTrue((root / 'b(A)').is_dir())
            self.assertFalse((root / 'A').exists())

    def test_invalid_names(self):
        for name in ['', '..', 'a/b', 'CON.txt', 'bad.', 'x:y']:
            with self.subTest(name=name), self.assertRaises(ValueError):
                validate_name(name)


if __name__ == '__main__':
    unittest.main()
