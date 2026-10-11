from safety import is_link, confined, destination_exists, move_no_replace, recovery_folder, write_recovery
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from settings import Settings
from history import History
from work import WorkToken, working, Cancelled
import queue
import threading
import sys
from highlight_tree import HighlightTree
from core import segments, suggested_name, plan, collisions, folder_size, execute_with_deletions, deletion_mask, name_from_mask, group_name, normalize_punctuation


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('FolderAdjuster')
        assets = Path(__file__).resolve().parent / 'assets'
        try:
            self.app_icon = tk.PhotoImage(file=str(assets / 'FolderAdjuster.png'))
            self.iconphoto(True, self.app_icon)
            if sys.platform == 'win32':
                self.iconbitmap(str(assets / 'FolderAdjuster.ico'))
        except (tk.TclError, OSError):
            pass
        self.geometry('1400x850')
        self.minsize(1000, 700)
        self.root_path = None
        self.book_root = None
        self.settings = Settings()
        self.history = History(self.settings.path.parent / 'operation-history')
        self.active_work = None
        self.square_scope = tk.StringVar(value='すべて')
        self.list_filter = tk.StringVar(value='全件')
        self.preset_name = tk.StringVar()
        presets = self.settings.data.get('presets', {})
        self.presets = presets if isinstance(presets, dict) else {}
        query = self.settings.data.get('delete_query', '')
        self.delete_query = tk.StringVar(value=query if isinstance(query, str) else '')
        self.query_save_job = None
        self.rows, self.protected, self.manual = {}, {}, {}
        self.overrides, self.group_names = {}, {}
        self.editor = None
        self.editor_finish = None
        self.round = tk.BooleanVar(value=True)
        self.square = tk.BooleanVar(value=True)
        self.group = tk.BooleanVar()
        self.move = tk.BooleanVar()
        tabs = ttk.Notebook(self)
        tabs.pack(fill='both', expand=True)
        folders_tab = ttk.Frame(tabs)
        books_tab = ttk.Frame(tabs, padding=20)
        tabs.add(folders_tab, text='フォルダ名変更・作成・移動')
        tabs.add(books_tab, text='本の整理・リネーム')
        ttk.Label(books_tab, text='本の整理・リネーム', font=('', 18)).pack(anchor='w', pady=(0, 12))
        ttk.Label(books_tab, text='本の整理専用の対象フォルダを選択してください。\n選択したフォルダ → タイトル → 本データ の構成を対象にします。').pack(anchor='w', pady=(0, 16))
        ttk.Button(books_tab, text='本の整理用フォルダを選択', command=self.choose_books).pack(anchor='w')
        self.book_path_label = ttk.Label(books_tab, text='未選択', wraplength=1000)
        self.book_path_label.pack(anchor='w', pady=12)
        self.book_rename_button = ttk.Button(books_tab, text='1. 本フォルダにタイトル・巻数を付ける', command=self.rename_books, state='disabled')
        self.book_rename_button.pack(anchor='w', pady=8)
        self.book_images_button = ttk.Button(books_tab, text='2. 画像を自然順で連番化・画像以外を削除', command=self.number_images, state='disabled')
        self.book_images_button.pack(anchor='w', pady=8)
        ttk.Label(books_tab, text='各処理で変更内容を確認してから実行します。\n巻数リネームは本フォルダ名を変更します。\n画像整理は各本データフォルダ内の画像名を変更し、画像以外を復元用に退避します。', wraplength=1000).pack(anchor='w', pady=20)
        ttk.Button(books_tab, text='操作履歴・元に戻す', command=self.show_history).pack(anchor='w', pady=8)
        top = ttk.Frame(folders_tab, padding=12)
        top.pack(fill='x')
        ttk.Button(top, text='フォルダ操作用の親フォルダを選択', command=self.choose).pack(side='left')
        self.path_label = ttk.Label(top, text='フォルダを選択してください')
        self.path_label.pack(side='left', padx=12)
        ttk.Button(top, text='操作履歴・元に戻す', command=self.show_history).pack(side='right')
        options = ttk.Frame(folders_tab, padding=(12, 0))
        options.pack(fill='x')
        for text, var in [('(…) を削除', self.round), ('[…] を削除', self.square), ('(…) の文字列で分類フォルダを作成', self.group), ('分類フォルダへ移動', self.move)]:
            ttk.Checkbutton(options, text=text, variable=var, command=self.options_changed).pack(side='left', padx=6)
        rules = ttk.Frame(folders_tab, padding=(12, 6))
        rules.pack(fill='x')
        ttk.Label(rules, text='角括弧の削除範囲:').pack(side='left')
        scope = ttk.Combobox(rules, textvariable=self.square_scope, values=('すべて', '先頭だけ', '末尾だけ'), state='readonly', width=10)
        scope.pack(side='left', padx=6)
        scope.bind('<<ComboboxSelected>>', lambda e: self.options_changed())
        ttk.Label(rules, text='削除プリセット:').pack(side='left', padx=(12, 0))
        self.preset_box = ttk.Combobox(rules, textvariable=self.preset_name, values=tuple(self.presets), width=20)
        self.preset_box.pack(side='left', padx=6)
        ttk.Button(rules, text='保存', command=self.save_preset).pack(side='left')
        ttk.Button(rules, text='適用', command=self.apply_preset).pack(side='left', padx=6)
        ttk.Label(rules, text='表示:').pack(side='left', padx=(12, 0))
        filter_box = ttk.Combobox(rules, textvariable=self.list_filter, values=('全件', '変更あり', '同名衝突', '実行対象'), state='readonly', width=10)
        filter_box.pack(side='left', padx=6)
        filter_box.bind('<<ComboboxSelected>>', lambda e: self.refresh())
        cleanup = ttk.LabelFrame(folders_tab, text='指定文字列を含むファイルの削除（全下位フォルダを検索）', padding=8)
        cleanup.pack(fill='x', padx=12, pady=8)
        ttk.Entry(cleanup, textvariable=self.delete_query).pack(side='left', fill='x', expand=True)
        ttk.Button(cleanup, text='削除対象を検索・確認', command=self.preview_file_deletion).pack(side='left', padx=8)
        ttk.Label(cleanup, text='半角スペースでOR指定：広告 サンプル .txt *.url').pack(side='left')
        self.delete_query.trace_add('write', self.queue_query_save)
        self.protocol('WM_DELETE_WINDOW', self.close_app)
        ttk.Label(folders_tab, text='直下のフォルダが対象です。変更後の名前はダブルクリックで編集。削除を解除するには行を選び、下の赤い箇所をクリック。作成フォルダ名もダブルクリックで編集できます。', padding=12).pack(anchor='w')
        frame = ttk.Frame(folders_tab, padding=(12, 0))
        frame.pack(fill='both', expand=True)
        self.tree = HighlightTree(frame, columns=('original', 'new', 'group', 'target'), show='tree headings', selectmode='browse')
        self.tree.heading('#0', text='実行')
        self.tree.column('#0', width=55, stretch=False)
        for key, title in [('original', '元の名前'), ('new', '変更後の名前（直接編集可）'), ('group', '作成フォルダ名（編集可）'), ('target', '移動・変更先')]:
            self.tree.heading(key, text=title)
            self.tree.column(key, width=300)
        scrollbar = ttk.Scrollbar(frame, orient='vertical', command=self.tree.yview)
        horizontal = ttk.Scrollbar(frame, orient='horizontal', command=self.tree.xview)
        horizontal.pack(side='bottom', fill='x')
        def sync_scroll(scroll, *args):
            scroll.set(*args)
            self.commit_editor()
            self.tree.schedule_redraw()
        self.tree.configure(yscrollcommand=lambda *args: sync_scroll(scrollbar, *args), xscrollcommand=lambda *args: sync_scroll(horizontal, *args))
        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        self.tree.bind('<<TreeviewSelect>>', self.show_parts)
        self.tree.bind('<Double-1>', self.edit)
        self.tree.bind('<Button-1>', self.toggle_row)
        self.parts = ttk.LabelFrame(folders_tab, text='赤＝削除予定：クリックで解除、ドラッグで任意の範囲を選択（残す部分は色なし）', padding=10)
        self.parts.pack(fill='x', padx=12, pady=12)
        bottom = ttk.Frame(folders_tab, padding=12)
        bottom.pack(fill='x')
        ttk.Button(bottom, text='選択行を自動の名前に戻す', command=self.reset_name).pack(side='left')
        ttk.Button(bottom, text='再読み込み', command=self.load).pack(side='left', padx=8)
        ttk.Button(bottom, text='プレビューを確認して実行', command=self.apply).pack(side='right')
        self.status = ttk.Label(folders_tab, text='未実行', padding=12)
        self.status.pack(anchor='w')
        self.after_idle(self.restore_paths)

    def queue_query_save(self, *args):
        if self.query_save_job:
            self.after_cancel(self.query_save_job)
        self.query_save_job = self.after(500, self.save_query)

    def run_work(self, label, function):
        """Run filesystem work off the Tk thread; cancel at safe checkpoints."""
        token = WorkToken()
        result = queue.Queue()
        previous = self.grab_current()
        window = tk.Toplevel(self)
        window.title(label)
        window.geometry('620x200')
        window.transient(self)
        window.grab_set()
        text = ttk.Label(window, text='準備中', padding=16, wraplength=580)
        text.pack(fill='x')
        bar = ttk.Progressbar(window, mode='indeterminate')
        bar.pack(fill='x', padx=16)
        bar.start(15)
        def cancel():
            token.cancelled.set()
            button.config(state='disabled')
            text.config(text='キャンセル中。安全な状態へ戻すまでお待ちください…')
        button = ttk.Button(window, text='キャンセル', command=cancel)
        button.pack(pady=12)
        window.protocol('WM_DELETE_WINDOW', cancel)
        self.active_work = token
        def worker():
            try:
                with working(token):
                    value = function()
                result.put((True, value))
            except Exception as error:
                result.put((False, error))
        values = []
        def poll():
            try:
                values.append(result.get_nowait())
            except queue.Empty:
                if not token.cancelled.is_set():
                    text.config(text=f'{token.message}\n確認・処理 {token.count:,} ステップ')
                window.after(40, poll)
                return
            bar.stop()
            window.destroy()
        threading.Thread(target=worker, daemon=True).start()
        window.after(10, poll)
        self.wait_window(window)
        self.active_work = None
        if previous is not None and previous.winfo_exists():
            previous.grab_set()
        success, value = values[0]
        if not success:
            if isinstance(value, Cancelled):
                self.status.config(text=str(value))
            raise value
        return value

    def save_preset(self):
        name = self.preset_name.get().strip()
        if not name:
            messagebox.showinfo('名前未入力', 'プリセット名を入力してください。')
            return
        updated = {**self.presets, name: {'round': self.round.get(), 'square': self.square.get(), 'scope': self.square_scope.get(), 'query': self.delete_query.get()}}
        try:
            self.settings.save_value('presets', updated)
        except OSError as error:
            messagebox.showerror('保存失敗', str(error))
            return
        self.presets = updated
        self.preset_box.config(values=tuple(self.presets))
        self.status.config(text=f'削除プリセット「{name}」を保存しました')

    def apply_preset(self):
        rule = self.presets.get(self.preset_name.get().strip())
        if not isinstance(rule, dict):
            messagebox.showinfo('未選択', '保存したプリセットを選択してください。')
            return
        self.round.set(bool(rule.get('round', True)))
        self.square.set(bool(rule.get('square', True)))
        self.square_scope.set(rule.get('scope', 'すべて') if rule.get('scope') in ('すべて', '先頭だけ', '末尾だけ') else 'すべて')
        self.delete_query.set(rule.get('query', '') if isinstance(rule.get('query', ''), str) else '')
        self.options_changed()

    def auto_mask(self, iid):
        scope = {'すべて': 'all', '先頭だけ': 'leading', '末尾だけ': 'trailing'}[self.square_scope.get()]
        return deletion_mask(self.rows[iid][0], self.round.get(), self.square.get(), self.overrides[iid], scope)

    def show_history(self):
        try:
            entries = self.history.entries()
        except (OSError, ValueError) as error:
            messagebox.showerror('履歴の読み込み失敗', str(error))
            return
        dialog = tk.Toplevel(self)
        dialog.title('操作履歴・元に戻す')
        dialog.geometry('1050x620')
        ttk.Label(dialog, text='操作後にファイルが変更されている場合や元の場所が埋まっている場合は、上書きせず復元を止めます。関連する操作は新しい履歴から順に戻してください。', padding=12, wraplength=1000).pack(anchor='w')
        tree = ttk.Treeview(dialog, columns=('time', 'label', 'status', 'count'), show='headings', selectmode='browse')
        for column, title in [('time', '実行日時'), ('label', '操作'), ('status', '状態'), ('count', '移動ステップ')]:
            tree.heading(column, text=title)
        tree.pack(fill='both', expand=True, padx=12)
        labels = {'completed': '完了・復元可能', 'undone': '復元済み', 'rolled_back': '取消・復元済み', 'failed': '失敗・要確認', 'running': '未完了・要確認', 'unreadable': '読み込み不能'}
        for i, (_, data) in enumerate(entries):
            from datetime import datetime
            time = data.get('time', '')
            try:
                time = datetime.fromisoformat(time).astimezone().strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                pass
            tree.insert('', 'end', iid=str(i), values=(time, data.get('label', ''), labels.get(data['status'], data['status']), len(data['moves'])))
        def undo():
            selection = tree.selection()
            if not selection:
                return
            path, data = entries[int(selection[0])]
            if data['status'] != 'completed':
                messagebox.showinfo('復元対象外', '完了した操作を選んでください。', parent=dialog)
                return
            if not messagebox.askokcancel('復元の確認', f'「{data["label"]}」を元に戻しますか？', parent=dialog):
                return
            try:
                self.run_work('元に戻す', lambda: self.history.undo(path))
            except Cancelled:
                return
            except (OSError, ValueError, RuntimeError) as error:
                messagebox.showerror('復元失敗', str(error), parent=dialog)
                return
            data['status'] = 'undone'
            tree.set(selection[0], 'status', '復元済み')
            self.load()
            messagebox.showinfo('復元完了', '元の名前・場所に戻しました。', parent=dialog)
        buttons = ttk.Frame(dialog, padding=12)
        buttons.pack(fill='x')
        ttk.Button(buttons, text='閉じる', command=dialog.destroy).pack(side='left')
        ttk.Button(buttons, text='選択した操作を元に戻す', command=undo).pack(side='right')
        dialog.transient(self)
        dialog.grab_set()

    def commit_editor(self):
        if self.editor_finish is not None:
            self.editor_finish()

    def save_query(self):
        if self.query_save_job:
            self.after_cancel(self.query_save_job)
        self.query_save_job = None
        try:
            self.settings.save_value('delete_query', self.delete_query.get())
        except OSError as error:
            messagebox.showwarning('検索文字列の保存失敗', str(error))

    def close_app(self):
        if self.active_work is not None:
            self.active_work.cancelled.set()
            return
        if self.query_save_job:
            self.save_query()
        self.destroy()

    def preview_file_deletion(self):
        from file_cleanup import search_files, delete_files
        if not self.root_path:
            messagebox.showinfo('対象未選択', 'フォルダ操作用の親フォルダを選択してください。')
            return
        root = self.root_path.resolve()
        query = self.delete_query.get()
        self.save_query()
        try:
            candidates = self.run_work('ファイル検索', lambda: search_files(root, query))
        except Cancelled:
            return
        except (OSError, ValueError) as error:
            messagebox.showerror('検索失敗', str(error))
            return
        if not candidates:
            messagebox.showinfo('対象なし', '一致するファイルはありません。')
            return
        dialog = tk.Toplevel(self)
        dialog.title('ファイル削除の確認：クリックで対象を解除')
        dialog.geometry('1000x780')
        ttk.Label(dialog, text=f'対象フォルダ: {root}\nOR検索: {query}\n行をクリックして削除対象から解除・再選択できます。', padding=12, wraplength=950).pack(anchor='w')
        frame = ttk.Frame(dialog, padding=12)
        frame.pack(fill='both', expand=True)
        tree = ttk.Treeview(frame, columns=('path', 'size'), show='tree headings', selectmode='browse')
        tree.heading('#0', text='削除')
        tree.column('#0', width=55, stretch=False)
        tree.heading('path', text='対象ファイル（親フォルダからの相対パス）')
        tree.column('path', width=760)
        tree.heading('size', text='バイト数')
        tree.column('size', width=110, stretch=False)
        scroll = ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
        horizontal = ttk.Scrollbar(frame, orient='horizontal', command=tree.xview)
        horizontal.pack(side='bottom', fill='x')
        tree.configure(yscrollcommand=scroll.set, xscrollcommand=horizontal.set)
        tree.pack(side='left', fill='both', expand=True)
        scroll.pack(side='right', fill='y')
        selected = set(range(len(candidates)))
        tree.tag_configure('excluded', foreground='#888888')
        for i, item in enumerate(candidates):
            tree.insert('', 'end', iid=str(i), text='☑', values=(str(item.source.relative_to(root)), f'{item.before[0]:,}'))
        count_label = ttk.Label(dialog, padding=(12, 0))
        count_label.pack(anchor='w')
        def update_count():
            count_label.config(text=f'削除対象 {len(selected)} 件 / 検索結果 {len(candidates)} 件。削除ファイルは復元用に退避します。')
        def toggle(event):
            row = tree.identify_row(event.y)
            if not row:
                return
            i = int(row)
            if i in selected:
                selected.remove(i)
            else:
                selected.add(i)
            tree.item(row, text='☑' if i in selected else '☐', tags=() if i in selected else ('excluded',))
            update_count()
        tree.bind('<Button-1>', toggle)
        def all_rows(enabled):
            selected.clear()
            if enabled:
                selected.update(range(len(candidates)))
            for i in range(len(candidates)):
                tree.item(str(i), text='☑' if enabled else '☐', tags=() if enabled else ('excluded',))
            update_count()
        def confirm():
            chosen = [candidates[i] for i in sorted(selected)]
            if not chosen:
                messagebox.showinfo('対象なし', '削除対象が選択されていません。', parent=dialog)
                return
            if not messagebox.askokcancel('最終確認', f'チェックした {len(chosen)} 件を削除（復元用に退避）しますか？\n対象: {root}', parent=dialog):
                return
            try:
                backup = self.run_work('ファイル削除', lambda: self.history.run('指定文字列のファイル削除', lambda: delete_files(root, chosen)))
            except Cancelled:
                return
            except (OSError, ValueError, RuntimeError) as error:
                messagebox.showerror('削除失敗', str(error), parent=dialog)
                return
            dialog.destroy()
            messagebox.showinfo('削除完了', f'{len(chosen)} 件を削除しました。\n復元用の退避先:\n{backup}\n元の場所は restore.json に記録しています。')
        buttons = ttk.Frame(dialog, padding=12)
        buttons.pack(fill='x')
        ttk.Button(buttons, text='全選択', command=lambda: all_rows(True)).pack(side='left')
        ttk.Button(buttons, text='全解除', command=lambda: all_rows(False)).pack(side='left', padx=6)
        ttk.Button(buttons, text='キャンセル', command=dialog.destroy).pack(side='left', padx=6)
        ttk.Button(buttons, text='選択したファイルを削除', command=confirm).pack(side='right')
        update_count()
        dialog.transient(self)
        dialog.grab_set()

    def restore_paths(self):
        folder = self.settings.remembered('folder_path')
        books = self.settings.remembered('book_path')
        if folder:
            try:
                available = folder.is_dir()
            except OSError:
                available = False
            if available:
                self.root_path = folder
                self.path_label.config(text=str(folder))
                self.load()
            else:
                self.path_label.config(text=f'{folder}（見つかりません。再選択してください）')
        if books:
            try:
                available = books.is_dir()
            except OSError:
                available = False
            if available:
                self.book_root = books
                self.book_path_label.config(text=str(books))
                self.book_rename_button.config(state='normal')
                self.book_images_button.config(state='normal')
            else:
                self.book_path_label.config(text=f'{books}（見つかりません。再選択してください）')
        if self.settings.warning:
            messagebox.showwarning('設定の読み込み', self.settings.warning)

    def remember_path(self, key, path):
        try:
            self.settings.save_path(key, path)
        except OSError as error:
            messagebox.showwarning('選択パスの保存失敗', f'今回の操作はできますが、次回用のパスを保存できませんでした。\n{error}')

    def choose(self):
        directory = filedialog.askdirectory(initialdir=self.settings.initial_directory('folder_path'), title='フォルダ操作用の親フォルダを選択')
        if directory:
            self.root_path = Path(directory).resolve()
            self.path_label.config(text=directory)
            self.remember_path('folder_path', self.root_path)
            self.load()

    def choose_books(self):
        directory = filedialog.askdirectory(title='本の整理専用：タイトルフォルダが入っている親フォルダを選択', initialdir=self.settings.initial_directory('book_path'))
        if directory:
            self.book_root = Path(directory).resolve()
            self.remember_path('book_path', self.book_root)
            self.book_path_label.config(text=str(self.book_root))
            self.book_rename_button.config(state='normal')
            self.book_images_button.config(state='normal')

    def number_images(self):
        from images import plan_images, plan_non_images, execute_image_cleanup
        if not self.book_root:
            return
        root = self.book_root.resolve()
        try:
            items, non_images = self.run_work('画像一覧の作成', lambda: (plan_images(root), plan_non_images(root)))
        except Cancelled:
            return
        except (OSError, ValueError) as error:
            messagebox.showerror('画像の読み込み失敗', str(error))
            return
        if not items and not non_images:
            messagebox.showinfo('画像なし', '親フォルダ → タイトル → 本データ → 画像 の構成で、対象画像が見つかりませんでした。')
            return
        preview = tk.Toplevel(self)
        preview.title('本の整理：画像連番・削除の確認')
        preview.geometry('1000x600')
        books = {item.source.parent for item in items}
        changed = sum(item.source != item.destination for item in items)
        ttk.Label(preview, text=f'本の整理対象: {root}\n{len(books)} 画像を含む本データフォルダ / {len(items)} 画像 / 名前変更 {changed} 件 / 画像以外の削除 {len(non_images)} 件\n各本データフォルダごとに001から開始。画像以外は下位フォルダも含め復元用フォルダへ退避します。', padding=12).pack(anchor='w')
        frame = ttk.Frame(preview, padding=12)
        frame.pack(fill='both', expand=True)
        tree = ttk.Treeview(frame, columns=('book', 'old', 'new'), show='headings')
        for column, title in [('book', 'タイトル / 本データ'), ('old', '元の画像名（自然順）'), ('new', '変更後')]:
            tree.heading(column, text=title)
            tree.column(column, width=300)
        scroll = ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
        horizontal = ttk.Scrollbar(frame, orient='horizontal', command=tree.xview)
        horizontal.pack(side='bottom', fill='x')
        tree.configure(yscrollcommand=scroll.set, xscrollcommand=horizontal.set)
        tree.pack(side='left', fill='both', expand=True)
        scroll.pack(side='right', fill='y')
        for item in items:
            tree.insert('', 'end', values=(str(item.source.parent.relative_to(root)), item.source.name, item.destination.name))
        tree.tag_configure('delete', foreground='#ad2020')
        for item in non_images:
            tree.insert('', 'end', values=(str(item.source.parent.relative_to(root)), item.source.name, '削除（復元用に退避）'), tags=('delete',))
        def confirm():
            try:
                # Reject stale preview, including added/removed images.
                count, backup = self.run_work('画像の整理', lambda: self.history.run('画像連番・画像以外の削除', lambda: execute_image_cleanup(root, items, non_images)))
            except Cancelled:
                return
            except (OSError, ValueError, RuntimeError) as error:
                messagebox.showerror('連番変更失敗', str(error), parent=preview)
                return
            preview.destroy()
            messagebox.showinfo('画像整理完了', f'{count} 件の画像名を変更し、画像以外 {len(non_images)} 件を削除しました。' + (f'\n復元用の退避先：\n{backup}\n元の場所は restore.json に記録しています。' if backup else ''))
        buttons = ttk.Frame(preview, padding=12)
        buttons.pack(fill='x')
        ttk.Button(buttons, text='キャンセル', command=preview.destroy).pack(side='left')
        ttk.Button(buttons, text='連番変更・画像以外の削除を実行', command=confirm).pack(side='right')
        preview.transient(self)
        preview.grab_set()

    def rename_books(self):
        from books import discover_books
        if not self.book_root:
            return
        root = self.book_root.resolve()
        try:
            books = self.run_work('巻数の推測', lambda: discover_books(root))
        except Cancelled:
            return
        except (OSError, ValueError) as error:
            messagebox.showerror('読み込み失敗', str(error))
            return
        if not books:
            messagebox.showinfo('対象なし', 'タイトルフォルダ内に本データフォルダがありません。')
            return
        dialog = tk.Toplevel(self)
        dialog.title('本フォルダ名：タイトル・巻数の確認')
        dialog.geometry('1100x620')
        ttk.Label(dialog, text=f'本の整理対象: {root}\n右端の数字を巻数として推測。直後がsなら「相当」。変更後の名前はダブルクリックで編集できます。\n実行欄をクリックで対象から除外。数字なし・0巻は初期状態で対象外です。内容・画像名は変更しません。', padding=12).pack(anchor='w')
        book_filter = tk.StringVar(value='全件')
        filters = ttk.Frame(dialog, padding=(12, 0))
        filters.pack(fill='x')
        ttk.Label(filters, text='表示:').pack(side='left')
        selector = ttk.Combobox(filters, textvariable=book_filter, values=('全件', '変更あり', '巻数不明', '同名衝突'), state='readonly', width=12)
        selector.pack(side='left', padx=6)
        ttk.Label(filters, text='黄色の部分が推測した巻数です。絞り込みは表示のみで、実行対象のチェックは維持します。').pack(side='left')
        frame = ttk.Frame(dialog, padding=12)
        frame.pack(fill='both', expand=True)
        tree = HighlightTree(frame, columns=('title', 'old', 'new'), show='tree headings', selectmode='browse', highlight_column='old', highlight_color='#ffe9a3', highlight_foreground='#674200')
        tree.heading('#0', text='実行')
        tree.column('#0', width=50, stretch=False)
        for column, title in [('title', '親タイトル'), ('old', '現在の本フォルダ名'), ('new', '変更後の名前（編集可）')]:
            tree.heading(column, text=title)
            tree.column(column, width=330)
        scroll = ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
        horizontal = ttk.Scrollbar(frame, orient='horizontal', command=tree.xview)
        horizontal.pack(side='bottom', fill='x')
        tree.configure(yscrollcommand=scroll.set, xscrollcommand=horizontal.set)
        tree.pack(side='left', fill='both', expand=True)
        scroll.pack(side='right', fill='y')
        names = {str(i): book.suggested or book.source.name for i, book in enumerate(books)}
        enabled = {str(i): book.suggested is not None for i, book in enumerate(books)}
        for i, book in enumerate(books):
            tree.insert('', 'end', iid=str(i), text='☑' if enabled[str(i)] else '☐', values=(book.source.parent.name, book.source.name, names[str(i)]))
        inferred = {}
        for i, book in enumerate(books):
            mask = [False] * len(book.source.name)
            if book.inferred_range:
                start, end = book.inferred_range
                mask[start:end] = [True] * (end-start)
            inferred[str(i)] = (book.source.name, mask)
        tree.set_highlights(inferred)
        def filter_rows(event=None):
            mode = book_filter.get()
            conflicts = set()
            if mode == '同名衝突':
                targets = {}
                for i, book in enumerate(books):
                    key = str(book.source.parent / names[str(i)]).casefold()
                    targets.setdefault(key, []).append(str(i))
                    destination = book.source.parent / names[str(i)]
                    if destination != book.source and destination_exists(destination):
                        conflicts.add(str(i))
                for rows in targets.values():
                    if len(rows) > 1:
                        conflicts.update(rows)
            for i, book in enumerate(books):
                iid = str(i)
                visible = mode == '全件' or mode == '巻数不明' and book.suggested is None or mode == '変更あり' and names[iid] != book.source.name or mode == '同名衝突' and iid in conflicts
                if visible:
                    tree.move(iid, '', 'end')
                else:
                    tree.detach(iid)
                    tree.selection_remove(iid)
            tree.schedule_redraw()
        selector.bind('<<ComboboxSelected>>', filter_rows)
        editor = [None]
        commit = [None]
        def scroll_books(scrollbar, *args):
            scrollbar.set(*args)
            tree.schedule_redraw()
            if commit[0] is not None:
                commit[0]()
        tree.configure(yscrollcommand=lambda *args: scroll_books(scroll, *args), xscrollcommand=lambda *args: scroll_books(horizontal, *args))
        def toggle(event):
            row = tree.identify_row(event.y)
            if row and tree.identify_column(event.x) == '#0':
                enabled[row] = not enabled[row]
                tree.item(row, text='☑' if enabled[row] else '☐')
        def edit(event):
            row = tree.identify_row(event.y)
            if not row or tree.identify_column(event.x) != '#3' or editor[0]:
                return
            box = tree.bbox(row, 'new')
            if not box:
                return
            entry = ttk.Entry(tree)
            editor[0] = entry
            entry.insert(0, names[row])
            entry.place(x=box[0], y=box[1], width=box[2], height=box[3])
            entry.focus_set()
            entry.select_range(0, 'end')
            def finish(event=None, save=True):
                if editor[0] is not entry:
                    return
                if save:
                    names[row] = normalize_punctuation(entry.get())
                    tree.set(row, 'new', names[row])
                    filter_rows()
                editor[0] = None
                commit[0] = None
                entry.destroy()
            commit[0] = finish
            entry.bind('<Return>', finish)
            entry.bind('<FocusOut>', finish)
            entry.bind('<Escape>', lambda e: finish(save=False))
        tree.bind('<Button-1>', toggle)
        tree.bind('<Double-1>', edit)
        def confirm():
            if commit[0] is not None:
                commit[0]()
            by_title = {}
            for i, book in enumerate(books):
                if enabled[str(i)]:
                    by_title.setdefault(book.source.parent, []).append((book.source.name, names[str(i)]))
            if not by_title:
                messagebox.showinfo('対象なし', '実行する行を選んでください。', parent=dialog)
                return
            batches = []
            try:
                for title, rows in by_title.items():
                    deleted = set()
                    while True:
                        pairs = collisions(title, rows, deleted=deleted)
                        if not pairs:
                            break
                        first, second, destination = pairs[0]
                        choice = self.choose_duplicate(first, second, destination)
                        dialog.grab_set()
                        if choice is None:
                            return
                        deleted.add(choice)
                    # Validate names and source availability before any mutation.
                    from core import validate_name
                    for old, new in rows:
                        validate_name(new)
                        source = title / old
                        if is_link(source) or not source.is_dir():
                            raise ValueError(f'元のフォルダが見つかりません: {source}')
                    plan(title, rows, deleted=deleted)
                    batches.append((title, rows, deleted))
            except Cancelled:
                return
            except (OSError, ValueError) as error:
                messagebox.showerror('実行できません', str(error), parent=dialog)
                return
            deletions = [path for _, _, deleted in batches for path in deleted]
            summary = f'{sum(len(rows) for _, rows, _ in batches)} 行を処理します。\n削除（復元用に退避）: {len(deletions)} 件\n' + '\n'.join(str(p) for p in deletions)
            if not messagebox.askokcancel('最終確認', summary + '\n一覧の名前へ変更しますか？', parent=dialog):
                return
            count, completed, backups = 0, [], []
            try:
                for title, rows, deleted in batches:
                    ops, _, backup = self.run_work('本フォルダ名の変更', lambda: self.history.run(f'本フォルダ名変更: {title.name}', lambda: execute_with_deletions(title, rows, False, False, deleted)))
                    count += len(ops)
                    completed.append(title.name)
                    if backup:
                        backups.append(str(backup))
            except Cancelled:
                return
            except (OSError, ValueError, RuntimeError) as error:
                messagebox.showerror('処理失敗', f'{error}\n完了済みタイトル: ' + ('、'.join(completed) or 'なし') + '\n完了済みタイトルの変更は保持されています。', parent=dialog)
                dialog.destroy()
                return
            dialog.destroy()
            messagebox.showinfo('本フォルダ名の変更完了', f'{count} 件のフォルダ名を変更しました。' + ('\n削除対象の退避先:\n' + '\n'.join(backups) if backups else ''))
        buttons = ttk.Frame(dialog, padding=12)
        buttons.pack(fill='x')
        ttk.Button(buttons, text='キャンセル', command=dialog.destroy).pack(side='left')
        ttk.Button(buttons, text='確認して本フォルダ名を変更', command=confirm).pack(side='right')
        dialog.transient(self)
        dialog.grab_set()

    def load(self):
        if not self.root_path:
            return
        if self.editor:
            self.editor.destroy()
            self.editor = None
            self.editor_finish = None
        # Detached filter rows still exist in Treeview and must be removed too.
        for iid in tuple(self.rows):
            if self.tree.exists(iid):
                self.tree.delete(iid)
        self.rows, self.protected, self.manual = {}, {}, {}
        self.overrides, self.group_names = {}, {}
        self.tree.set_highlights({})
        self.show_parts()
        try:
            root = self.root_path
            names = self.run_work('フォルダの読み込み', lambda: sorted(p.name for p in root.iterdir() if p.is_dir() and not is_link(p) and p.name.casefold() != '.folder-tool-trash'))
        except Cancelled:
            return
        except OSError as error:
            self.status.config(text='読み込み失敗。一覧を再読み込みしてください。')
            messagebox.showerror('読み込み失敗', str(error))
            return
        for index, name in enumerate(names):
            iid = str(index)
            self.rows[iid] = [name, True]
            self.protected[iid] = set()
            self.overrides[iid] = {}
            self.group_names[name] = normalize_punctuation(group_name(name))
            self.tree.insert('', 'end', iid=iid)
        self.refresh()
        self.show_parts()
        self.status.config(text=f'{len(names)} フォルダを読み込みました')

    def new_name(self, iid):
        name = self.rows[iid][0]
        return normalize_punctuation(self.manual.get(iid, name_from_mask(name, self.auto_mask(iid))))

    def refresh(self):
        from core import group_name
        for iid, (name, enabled) in self.rows.items():
            new = self.new_name(iid)
            group = self.group_names[name] if self.move.get() else ''
            target = f'{group} / {new}' if group else new
            self.tree.item(iid, text='☑' if enabled else '☐', values=(name, new, self.group_names[name], target))
        self.tree.set_highlights({iid: (name, self.removal_mask(iid) if enabled else [False] * len(name)) for iid, (name, enabled) in self.rows.items()})
        mode = self.list_filter.get()
        conflicts = set()
        if mode == '同名衝突' and self.root_path:
            rows = [(name, self.new_name(iid)) for iid, (name, enabled) in self.rows.items() if enabled]
            root, move, groups = self.root_path, self.move.get(), dict(self.group_names)
            try:
                pairs = self.run_work('同名衝突の確認', lambda: collisions(root, rows, move, group_names=groups))
                conflicts = {path.name for first, second, _ in pairs for path in (first, second)}
            except Cancelled:
                return
            except (OSError, ValueError) as error:
                self.status.config(text=str(error))
        hidden = []
        for iid, (name, enabled) in self.rows.items():
            visible = mode == '全件' or mode == '実行対象' and enabled or mode == '同名衝突' and name in conflicts
            if mode == '変更あり':
                visible = self.new_name(iid) != name or bool(self.move.get() and self.group_names[name]) or bool(self.group.get() and self.group_names[name])
            if visible:
                self.tree.move(iid, '', 'end')
            else:
                self.tree.detach(iid)
                hidden.append(iid)
        for iid in self.tree.selection():
            if iid in hidden:
                self.tree.selection_remove(iid)

    def removal_mask(self, iid):
        name = self.rows[iid][0]
        if iid in self.manual:
            from difflib import SequenceMatcher
            mask = [False] * len(name)
            for operation, start, end, _, _ in SequenceMatcher(None, name, self.new_name(iid), autojunk=False).get_opcodes():
                if operation in ('delete', 'replace'):
                    mask[start:end] = [True] * (end-start)
            return mask
        return self.auto_mask(iid)

    def toggle_row(self, event):
        iid = self.tree.identify_row(event.y)
        if iid and self.tree.identify_column(event.x) == '#0':
            self.rows[iid][1] = not self.rows[iid][1]
            self.refresh()
            self.show_parts()

    def show_parts(self, event=None):
        for widget in self.parts.winfo_children():
            widget.destroy()
        selection = self.tree.selection()
        if not selection:
            ttk.Label(self.parts, text='行を選択すると、括弧部分を個別に保護できます。').pack(anchor='w')
            return
        iid = selection[0]
        name = self.rows[iid][0]
        text = tk.Text(self.parts, height=3, wrap='char', font=('Yu Gothic UI', 12), exportselection=False)
        text.pack(fill='x')
        text.insert('1.0', name)
        text.tag_configure('remove', background='#ffd7d7', foreground='#9b1717')
        def paint():
            mask = self.removal_mask(iid) if self.rows[iid][1] else [False] * len(name)
            text.tag_remove('remove', '1.0', 'end')
            for i, remove in enumerate(mask):
                tag = 'remove' if remove else None
                if tag:
                    # Tk's +Nc counts displayed Unicode characters in both 8.6 and 9.
                    text.tag_add(tag, f'1.0+{i}c', f'1.0+{i+1}c')
        def adjust(start, end, remove):
            if iid in self.manual:
                self.overrides[iid] = dict(enumerate(self.removal_mask(iid)))
            for i in range(start, end):
                self.overrides[iid][i] = remove
            self.manual.pop(iid, None)
            self.refresh()
            paint()
        def selection(remove):
            try:
                start = len(text.get('1.0', 'sel.first'))
                end = len(text.get('1.0', 'sel.last'))
            except (tk.TclError, TypeError):
                return
            adjust(start, end, remove)
        def click(event):
            if text.tag_ranges('sel'):
                return
            index = len(text.get('1.0', text.index(f'@{event.x},{event.y}')))
            if index >= len(name):
                return
            mask = self.removal_mask(iid)
            # Clicking a bracket toggles the whole bracket; arbitrary selections override parts.
            start, end = index, index + 1
            for match in segments(name):
                if match.start() <= index < match.end():
                    start, end = match.span()
                    break
            adjust(start, end, not mask[index])
        text.bind('<ButtonRelease-1>', click)
        text.bind('<Key>', lambda event: 'break')
        text.bind('<<Paste>>', lambda event: 'break')
        text.bind('<<Cut>>', lambda event: 'break')
        controls = ttk.Frame(self.parts)
        controls.pack(fill='x', pady=6)
        ttk.Button(controls, text='選択範囲を残す', command=lambda: selection(False)).pack(side='left')
        ttk.Button(controls, text='選択範囲を削除', command=lambda: selection(True)).pack(side='left', padx=6)
        def extract():
            try:
                value = text.get('sel.first', 'sel.last').strip()
            except tk.TclError:
                return
            self.group_names[name] = normalize_punctuation(value)
            self.refresh()
        ttk.Button(controls, text='選択範囲を作成フォルダ名にする', command=extract).pack(side='left')
        paint()

    def options_changed(self):
        self.refresh()
        self.show_parts()

    def edit(self, event):
        iid = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)
        if not iid or column not in ('#2', '#3'):
            return
        if self.editor:
            self.editor.focus_set()
            return
        field = 'new' if column == '#2' else 'group'
        box = self.tree.bbox(iid, field)
        if not box:
            return
        entry = ttk.Entry(self.tree)
        self.editor = entry
        entry.insert(0, self.new_name(iid) if field == 'new' else self.group_names[self.rows[iid][0]])
        entry.place(x=box[0], y=box[1], width=box[2], height=box[3])
        entry.focus_set()
        entry.select_range(0, 'end')
        def finish(event=None, save=True):
            if self.editor is not entry:
                return
            if save:
                if field == 'new':
                    self.manual[iid] = entry.get()
                else:
                    self.group_names[self.rows[iid][0]] = normalize_punctuation(entry.get())
            self.editor = None
            self.editor_finish = None
            entry.destroy()
            self.refresh()
            self.show_parts()
        self.editor_finish = finish
        entry.bind('<Return>', finish)
        entry.bind('<FocusOut>', finish)
        entry.bind('<Escape>', lambda e: finish(save=False))

    def reset_name(self):
        for iid in self.tree.selection():
            self.manual.pop(iid, None)
        self.refresh()
        self.show_parts()

    def apply(self):
        if not self.root_path:
            return
        self.commit_editor()
        try:
            rows = [(name, self.new_name(iid)) for iid, (name, enabled) in self.rows.items() if enabled]
            deleted = set()
            while True:
                pairs = collisions(self.root_path, rows, self.move.get(), deleted, self.group_names)
                if not pairs:
                    break
                first, second, destination = pairs[0]
                choice = self.choose_duplicate(first, second, destination)
                if choice is None:
                    return
                deleted.add(choice)
            operations, groups = plan(self.root_path, rows, self.group.get(), self.move.get(), self.group_names, deleted=deleted)
        except Cancelled:
            return
        except (OSError, ValueError) as error:
            messagebox.showerror('実行できません', str(error))
            return
        new_groups = [g for g in groups if not g.exists()]
        if not operations and not new_groups and not deleted:
            messagebox.showinfo('変更なし', '実行する変更がありません。')
            return
        preview = tk.Toplevel(self)
        preview.title('実行前の確認')
        preview.geometry('850x500')
        ttk.Label(preview, text=f'名前変更・移動 {len(operations)} 件 / フォルダ作成 {len(new_groups)} 件 / 削除（退避） {len(deleted)} 件', padding=12).pack()
        text = tk.Text(preview, wrap='word')
        text.pack(fill='both', expand=True, padx=12)
        for source in sorted(deleted):
            text.insert('end', f'削除（復元用の .folder-tool-trash へ退避）: {source}\n')
        for group in sorted(new_groups):
            text.insert('end', f'作成: {group.name}\n')
        for op in operations:
            text.insert('end', f'{op.source.name}\n  → {op.destination.relative_to(self.root_path)}\n')
        text.config(state='disabled')
        def confirm():
            try:
                # Revalidate after the preview in case the filesystem changed.
                root, create, move, names = self.root_path, self.group.get(), self.move.get(), dict(self.group_names)
                current_ops, current_groups, backup = self.run_work('フォルダ整理', lambda: self.history.run('フォルダ名変更・作成・移動', lambda: execute_with_deletions(root, rows, create, move, deleted, names)))
            except Cancelled:
                return
            except (OSError, ValueError, RuntimeError) as error:
                messagebox.showerror('処理失敗', str(error), parent=preview)
                return
            preview.destroy()
            self.load()
            self.status.config(text=f'完了：名前変更・移動 {len(current_ops)} 件、作成 {len(new_groups)} 件')
            if backup:
                messagebox.showinfo('削除対象の退避先', f'削除したフォルダはここに保存しました。\n{backup}\n復元元の場所は restore.json に記録しています。')
        buttons = ttk.Frame(preview, padding=12)
        buttons.pack(fill='x')
        ttk.Button(buttons, text='キャンセル', command=preview.destroy).pack(side='left')
        ttk.Button(buttons, text='この内容で実行', command=confirm).pack(side='right')
        preview.transient(self)
        preview.grab_set()

    def choose_duplicate(self, first, second, destination):
        from comparison import summarize
        left, right = self.run_work('同名フォルダの比較', lambda: (summarize(first), summarize(second)))
        first_size, second_size = left['bytes'], right['bytes']
        dialog = tk.Toplevel(self)
        dialog.title('同名フォルダ：削除する側を選択')
        dialog.geometry('950x540')
        choice = tk.IntVar(value=0 if first_size >= second_size else 1)
        result = []
        ttk.Label(dialog, text=f'変更先: {destination}\n削除するフォルダを選択してください。大きい側が初期選択されています。\n削除対象は復元用フォルダへ退避します。', padding=12, wraplength=800).pack(anchor='w')
        decision = ttk.Label(dialog, padding=12, wraplength=900)
        decision.pack(anchor='w')
        def show_decision(*args):
            delete, keep = (first, second) if choice.get() == 0 else (second, first)
            decision.config(text=f'削除（退避）する側: {delete}\n残す側: {keep}')
        choice.trace_add('write', show_decision)
        show_decision()
        for index, (path, summary) in enumerate([(first, left), (second, right)]):
            size = summary['bytes']
            ttk.Radiobutton(dialog, text=f'こちらを削除: {path}\n容量: {size:,} バイト（{size / 1024**2:,.2f} MiB） / ファイル {summary["files"]:,} 件 / 画像 {summary["images"]:,} 件', variable=choice, value=index).pack(anchor='w', padx=12, pady=8)
        different = ttk.Label(dialog, text='片側だけにあるファイル（先頭5件ずつ）:\n左: ' + '、'.join(sorted(left['names']-right['names'])[:5]) + '\n右: ' + '、'.join(sorted(right['names']-left['names'])[:5]), wraplength=900, padding=12)
        different.pack(anchor='w')
        def accept():
            result.append([first, second][choice.get()])
            dialog.destroy()
        buttons = ttk.Frame(dialog, padding=12)
        buttons.pack(fill='x')
        ttk.Button(buttons, text='全体をキャンセル', command=dialog.destroy).pack(side='left')
        ttk.Button(buttons, text='選択を確定（まだ削除しません）', command=accept).pack(side='right')
        dialog.transient(self)
        dialog.grab_set()
        self.wait_window(dialog)
        return result[0] if result else None


if __name__ == '__main__':
    app = App()
    if '--smoke-test' in sys.argv:
        app.withdraw()
        app.update()
        if app.title() != 'FolderAdjuster':
            raise RuntimeError('Unexpected application title')
        destination = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
        if app.settings.path != destination / 'settings.json':
            raise RuntimeError('Settings must be beside executable')
        if app.history.directory != destination / 'operation-history':
            raise RuntimeError('History must be beside executable')
        if not hasattr(app, 'app_icon'):
            raise RuntimeError('Application icon was not loaded')
        probe = Settings(destination / 'FolderAdjuster.smoke-settings.json')
        probe.save_value('probe', '設定の保存')
        if Settings(probe.path).data.get('probe') != '設定の保存':
            raise RuntimeError('Settings persistence failed')
        probe.path.unlink()
        (destination / 'FolderAdjuster.smoke-test.txt').write_text('Tk startup completed', encoding='utf-8')
        app.close_app()
    else:
        app.mainloop()
