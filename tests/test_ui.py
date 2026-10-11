"""Tk interaction checks; run with an available DISPLAY on Linux."""
import os
from pathlib import Path
import tempfile
import tkinter as tk
from tkinter import ttk
import unittest
from unittest.mock import patch
from app import App
from settings import Settings


@unittest.skipUnless(os.name == 'nt' or os.environ.get('DISPLAY'), 'GUI display required')
class UITests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.settings = Settings(self.root / 'settings.json')
        self.patcher = patch('app.Settings', lambda: self.settings)
        self.patcher.start()
        self.app = App()
        self.app.update()

    def tearDown(self):
        self.app.close_app()
        self.patcher.stop()
        self.directory.cleanup()

    def test_preset_restore_and_display_filter_keep_checks(self):
        folders = self.root / 'folders'; folders.mkdir()
        for name in ['[先頭]作品[末尾]', '変更なし']:
            (folders / name).mkdir()
        self.app.root_path = folders
        self.app.round.set(False)
        self.app.square_scope.set('先頭だけ')
        self.app.delete_query.set('.txt 広告')
        self.app.preset_name.set('先頭タグ')
        self.app.save_preset()
        self.app.load()
        self.app.list_filter.set('変更あり')
        self.app.refresh()
        self.assertEqual(len(self.app.tree.get_children()), 1)
        self.assertTrue(all(row[1] for row in self.app.rows.values()))
        self.app.close_app()
        self.app = App()
        self.app.update()
        self.app.preset_name.set('先頭タグ')
        self.app.apply_preset()
        self.assertEqual(self.app.square_scope.get(), '先頭だけ')
        self.assertEqual(self.app.delete_query.get(), '.txt 広告')

    def test_background_progress_returns_result(self):
        self.assertEqual(self.app.run_work('確認', lambda: 42), 42)
        self.assertIsNone(self.app.active_work)

    def test_tabs_keep_independent_paths_and_query_across_restart(self):
        folders = self.root / 'folders'
        books = self.root / 'books'
        folders.mkdir(); books.mkdir()
        with patch('app.filedialog.askdirectory', return_value=str(folders)):
            self.app.choose()
        with patch('app.filedialog.askdirectory', return_value=str(books)):
            self.app.choose_books()
        self.app.delete_query.set('広告 .txt')
        self.app.save_query()
        self.app.close_app()
        self.app = App(); self.app.update()
        self.assertEqual(self.app.root_path, folders)
        self.assertEqual(self.app.book_root, books)
        self.assertEqual(self.app.delete_query.get(), '広告 .txt')
        tabs = next(w for w in self.app.winfo_children() if isinstance(w, ttk.Notebook))
        self.assertEqual(len(tabs.tabs()), 2)

    def test_highlight_click_and_selected_range_with_emoji(self):
        folders = self.root / 'folders'
        folders.mkdir()
        name = '😀作品[削除](保存)'
        (folders / name).mkdir()
        self.app.root_path = folders
        self.app.load()
        self.app.tree.selection_set('0')
        self.app.update()
        text = next(w for w in self.app.parts.winfo_children() if isinstance(w, tk.Text))
        ranges = text.tag_ranges('remove')
        self.assertEqual(text.get(ranges[0], ranges[-1]), '[削除](保存)')
        # Protect a precise selected range through the actual button callback.
        start = text.search('(保存)', '1.0')
        text.tag_add('sel', start, f'{start}+4c')
        controls = next(w for w in self.app.parts.winfo_children() if isinstance(w, ttk.Frame))
        next(w for w in controls.winfo_children() if w.cget('text') == '選択範囲を残す').invoke()
        self.assertEqual(self.app.new_name('0'), '😀作品(保存)')
        text.tag_remove('sel', '1.0', 'end')
        start = text.search('[削除]', '1.0')
        x, y, width, height = text.bbox(start)
        text.event_generate('<ButtonPress-1>', x=x+width//2, y=y+height//2)
        text.event_generate('<ButtonRelease-1>', x=x+width//2, y=y+height//2)
        self.app.update()
        self.assertEqual(self.app.new_name('0'), name)

    def test_file_confirmation_click_excludes_row_without_deleting(self):
        folders = self.root / 'folders'
        folders.mkdir()
        file = folders / 'a.txt'
        file.write_text('keep')
        self.app.root_path = folders
        self.app.delete_query.set('.txt')
        self.app.preview_file_deletion()
        self.app.update()
        dialog = next(w for w in self.app.winfo_children() if isinstance(w, tk.Toplevel))
        frame = next(w for w in dialog.winfo_children() if isinstance(w, ttk.Frame) and any(isinstance(c, ttk.Treeview) for c in w.winfo_children()))
        tree = next(w for w in frame.winfo_children() if isinstance(w, ttk.Treeview))
        x, y, width, height = tree.bbox('0', 'path')
        tree.event_generate('<ButtonPress-1>', x=x+10, y=y+height//2)
        self.app.update()
        self.assertEqual(tree.item('0', 'text'), '☐')
        self.assertEqual(file.read_text(), 'keep')
        dialog.destroy()

    def test_direct_edit_of_folder_name(self):
        folders = self.root / 'folders'
        folders.mkdir()
        (folders / '作品(作者)').mkdir()
        self.app.root_path = folders
        self.app.load(); self.app.update()
        x, y, width, height = self.app.tree.bbox('0', 'new')
        class Event:
            pass
        event = Event()
        event.x, event.y = x+10, y+height//2
        self.app.edit(event)
        entry = self.app.editor
        self.assertIsNotNone(entry)
        entry.delete(0, 'end'); entry.insert(0, '手動編集!')
        entry.focus_force(); self.app.update()
        entry.event_generate('<Return>'); self.app.update()
        self.assertIsNone(self.app.editor)
        self.assertEqual(self.app.new_name('0'), '手動編集！')

    def test_original_column_only_highlights_deletions_and_updates(self):
        folders = self.root / 'folders'
        folders.mkdir()
        name = '[削除]作品(保存)'
        (folders / name).mkdir()
        self.app.root_path = folders
        self.app.load(); self.app.update()
        canvas = self.app.tree.cells['0']
        self.assertEqual(len(canvas.find_withtag('remove')), 2)
        start = name.index('(保存)')
        self.app.overrides['0'].update({i: False for i in range(start, len(name))})
        self.app.refresh(); self.app.update()
        self.assertEqual(len(canvas.find_withtag('remove')), 1)
        self.assertEqual(self.app.tree.highlights['0'][1][start:], [False] * len('(保存)'))
        # Clicking the cell overlay still selects the native row.
        canvas.event_generate('<ButtonPress-1>', x=10, y=8)
        canvas.event_generate('<ButtonRelease-1>', x=10, y=8)
        self.app.update()
        self.assertEqual(self.app.tree.selection(), ('0',))
        text = next(w for w in self.app.parts.winfo_children() if isinstance(w, tk.Text))
        self.assertFalse(text.tag_ranges('keep'))
        self.app.rows['0'][1] = False
        self.app.refresh(); self.app.update()
        self.assertEqual(len(canvas.find_withtag('remove')), 0)

    def test_highlight_scroll_and_manual_name_edit(self):
        folders = self.root / 'folders'
        folders.mkdir()
        for i in range(50):
            (folders / f'{i:02d}作品[タグ]').mkdir()
        self.app.root_path = folders
        self.app.load(); self.app.update()
        self.app.tree.yview_moveto(1)
        self.app.update()
        self.assertIn('49', self.app.tree.cells)
        self.assertNotIn('0', self.app.tree.cells)
        self.app.manual['49'] = '49作品[タグ]'
        self.app.refresh(); self.app.update()
        self.assertEqual(len(self.app.tree.cells['49'].find_withtag('remove')), 0)
        self.app.tree.xview_moveto(1)
        self.app.update()
        self.app.tree.xview_moveto(0)
        self.app.update()
        self.assertIn('49', self.app.tree.cells)

    def test_excluded_row_has_no_lower_highlight(self):
        folders = self.root / 'folders'
        folders.mkdir()
        (folders / '作品[タグ]').mkdir()
        self.app.root_path = folders
        self.app.load(); self.app.tree.selection_set('0'); self.app.update()
        x, y, width, height = self.app.tree.bbox('0', '#0')
        self.app.tree.event_generate('<ButtonPress-1>', x=x+5, y=y+height//2)
        self.app.update()
        text = next(w for w in self.app.parts.winfo_children() if isinstance(w, tk.Text))
        self.assertFalse(self.app.rows['0'][1])
        self.assertFalse(text.tag_ranges('remove'))

    def test_click_on_manually_removed_character_restores_it(self):
        folders = self.root / 'folders'
        folders.mkdir()
        (folders / 'abc[タグ]').mkdir()
        self.app.root_path = folders
        self.app.load(); self.app.tree.selection_set('0')
        self.app.manual['0'] = 'ac[タグ]'
        self.app.refresh(); self.app.show_parts(); self.app.update()
        text = next(w for w in self.app.parts.winfo_children() if isinstance(w, tk.Text))
        x, y, width, height = text.bbox('1.1')
        text.event_generate('<ButtonPress-1>', x=x+width//2, y=y+height//2)
        text.event_generate('<ButtonRelease-1>', x=x+width//2, y=y+height//2)
        self.app.update()
        self.assertEqual(self.app.new_name('0'), 'abc[タグ]')

    def test_scroll_commits_inline_editor(self):
        folders = self.root / 'folders'
        folders.mkdir()
        for i in range(50):
            (folders / f'{i:02d}作品[タグ]').mkdir()
        self.app.root_path = folders
        self.app.load(); self.app.update()
        x, y, _, height = self.app.tree.bbox('0', 'new')
        class Event:
            pass
        event = Event(); event.x = x+10; event.y = y+height//2
        self.app.edit(event)
        self.app.editor.delete(0, 'end'); self.app.editor.insert(0, '編集済み')
        self.app.tree.yview_moveto(1); self.app.update()
        self.assertIsNone(self.app.editor)
        self.assertEqual(self.app.new_name('0'), '編集済み')

    def test_preview_commits_edit_without_enter(self):
        folders = self.root / 'folders'
        folders.mkdir()
        (folders / '作品[タグ]').mkdir()
        self.app.root_path = folders
        self.app.load(); self.app.update()
        x, y, _, height = self.app.tree.bbox('0', 'new')
        class Event:
            pass
        event = Event(); event.x=x+10; event.y=y+height//2
        self.app.edit(event)
        self.app.editor.delete(0, 'end'); self.app.editor.insert(0, '確定前の入力')
        self.app.apply(); self.app.update()
        self.assertEqual(self.app.new_name('0'), '確定前の入力')
        dialog = next(w for w in self.app.winfo_children() if isinstance(w, tk.Toplevel))
        text = next(w for w in dialog.winfo_children() if isinstance(w, tk.Text))
        self.assertIn('確定前の入力', text.get('1.0', 'end'))
        self.assertTrue((folders / '作品[タグ]').is_dir())
        dialog.destroy()

    def test_book_confirmation_commits_edit_without_enter(self):
        books = self.root / 'books'
        (books / 'title/book_v02').mkdir(parents=True)
        self.app.book_root = books
        self.app.rename_books(); self.app.update()
        dialog = next(w for w in self.app.winfo_children() if isinstance(w, tk.Toplevel))
        frame = next(w for w in dialog.winfo_children() if isinstance(w, ttk.Frame) and any(isinstance(c, ttk.Treeview) for c in w.winfo_children()))
        tree = next(w for w in frame.winfo_children() if isinstance(w, ttk.Treeview))
        x, y, _, height = tree.bbox('0', 'new')
        for _ in range(2):
            tree.event_generate('<ButtonPress-1>', x=x+10, y=y+height//2)
            tree.event_generate('<ButtonRelease-1>', x=x+10, y=y+height//2)
        self.app.update()
        entry = next(w for w in tree.winfo_children() if isinstance(w, ttk.Entry))
        entry.delete(0, 'end'); entry.insert(0, 'invalid/name')
        controls = next(w for w in dialog.winfo_children() if isinstance(w, ttk.Frame) and any(isinstance(c, ttk.Button) and c.cget('text') == '確認して本フォルダ名を変更' for c in w.winfo_children()))
        confirm = next(w for w in controls.winfo_children() if w.cget('text') == '確認して本フォルダ名を変更')
        with patch('app.messagebox.showerror') as errors, patch('app.messagebox.askokcancel', return_value=False):
            confirm.invoke()
            self.assertEqual(errors.call_count, 1)
            self.assertIn('invalid/name', str(errors.call_args))
        self.assertTrue((books / 'title/book_v02').is_dir())
        dialog.destroy()

    def test_mousewheel_on_highlighted_cell_scrolls_table(self):
        folders = self.root / 'folders'
        folders.mkdir()
        for i in range(50):
            (folders / f'{i:02d}作品[タグ]').mkdir()
        self.app.root_path = folders
        self.app.load(); self.app.update()
        before = self.app.tree.yview()[0]
        canvas = self.app.tree.cells['0']
        canvas.event_generate('<MouseWheel>', delta=-120, x=20, y=8)
        self.app.update()
        self.assertGreater(self.app.tree.yview()[0], before)


if __name__ == '__main__':
    unittest.main()
