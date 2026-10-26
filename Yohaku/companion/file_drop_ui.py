"""Connect explicit drop choices to the bounded file operation engine."""
from copy import deepcopy
from datetime import datetime
from pathlib import Path
import threading

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from .core import Notice
from .file_drop import FileDropError, FileDropStore, execute, file_identity, regular_file


class FileDropController(QObject):
    completed = Signal(object, str)

    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner; self.busy = False; self.closed = False; self.editor = None
        self.print_dialog = None
        self.pending = None; self.rule = None; self.identity = None
        self.store = FileDropStore(owner.path/'file_drop_settings.json')
        self.completed.connect(self.finished)
        owner.resident.file_dropped.connect(self.drop)
        owner.resident.drop_allowed = self.allowed
        owner.panel.file_drop_requested.connect(self.show_editor)
        owner.bubble.file_action_requested.connect(self.run)
        owner.bubble.file_settings_requested.connect(self.show_editor)
        owner.menu.addAction('ドロップしたファイルの処理', self.show_editor)

    def allowed(self):
        c = self.owner
        return (not self.closed and not self.busy and self.store.data['enabled']
                and not c.hidden and not c.user_hidden
                and c.pending_reaction is None
                and not (c.bubble.isVisible() and c.bubble.current == 'one_shot'))

    def drop(self, path):
        if not self.allowed():
            return
        self.pending = self.rule = self.identity = None
        try:
            self.pending = regular_file(path); self.identity = file_identity(self.pending)
        except (FileDropError, OSError):
            self.message('通常のファイルを1つドロップしてください。フォルダーやリンクは対象外です。'); return
        # External JSON edits apply on the next drop; no user-authored content is
        # discarded or rewritten just by loading the settings.
        self.store.__init__(self.store.path)
        self.show_choices()

    def show_choices(self):
        c = self.owner
        if self.pending is None or c.hidden or c.user_hidden or self.busy:
            return
        self.rule = self.store.matching_rule(self.pending)
        error = self.store.error or ('この拡張子の処理が登録されていません。' if self.rule is None else '')
        c.bubble.show_drop_choices(self.pending, self.rule, error)
        c.engine.last_display = datetime.now().astimezone()
        c.motion.face_front(); c.resident.frame_index = 24; c.resident.update(); c.position()

    def show_editor(self):
        if self.closed:
            return
        if self.editor is None:
            from .file_drop_editor import FileDropEditor
            self.editor = FileDropEditor(self.store)
            self.editor.setWindowIcon(self.owner.brand_icon)
            self.editor.saved.connect(self.settings_saved)
        elif not self.editor.dirty:
            self.editor.reload()
        self.editor.show(); self.editor.raise_(); self.editor.activateWindow()

    def settings_saved(self):
        if self.owner.bubble.isVisible() and self.owner.bubble.current == 'file_drop':
            self.show_choices()

    def message(self, text):
        c = self.owner
        if self.closed or c.hidden or c.user_hidden:
            return
        c.bubble.display(Notice('', text)); c.position()

    def run(self, action):
        c = self.owner
        if (self.busy or self.closed or self.pending is None or self.rule is None
                or not c.bubble.isVisible() or c.bubble.current != 'file_drop'
                or c.hidden or c.user_hidden):
            return
        if action not in {row['action'] for row in self.rule['actions']}:
            return
        try:
            path = regular_file(self.pending)
            if file_identity(path) != self.identity:
                raise FileDropError('ファイルが変更されています。もう一度ドロップしてください。')
        except (FileDropError, OSError):
            self.message('ファイルを確認できないか、変更されています。もう一度ドロップしてください。'); return
        rule = deepcopy(self.rule); now = datetime.now().astimezone()
        self.busy = True
        for choice in c.bubble.drop_buttons.values():
            choice.setEnabled(False)
        c.bubble.drop_settings_button.setEnabled(False); c.bubble.drop_cancel.setEnabled(False)
        c.bubble.drop_notice.setText('処理しています。'); c.bubble.drop_notice.show(); c.bubble.resize_text(); c.position()
        if action == 'print_pdf':
            try:
                from .pdf_print import print_pdf
                printed = print_pdf(path, c.panel if c.panel.isVisible() else None,
                                    on_dialog=lambda dialog: setattr(self, 'print_dialog', dialog))
                self.finished({'printed': printed}, '')
            except FileDropError as error:
                self.finished({}, str(error))
            except Exception:
                self.finished({}, '印刷を開始できません。PDFとプリンターを確認してください。')
            finally:
                self.print_dialog = None
            return

        def work():
            try:
                result, error = execute(action, path, rule, now), ''
            except FileDropError as problem:
                result, error = {}, str(problem)
            except Exception:
                result, error = {}, '処理を完了できません。ファイルと移動先を確認してください。'
            try:
                self.completed.emit(result, error)
            except RuntimeError:
                pass  # The application may have been closed by the OS.
        # Do not abandon an in-flight copy just because the Qt event loop exits.
        threading.Thread(target=work, name='Yohaku-file-operation', daemon=False).start()

    def finished(self, result, error):
        self.busy = False; self.pending = None; self.rule = None; self.identity = None
        if self.closed:
            return
        if error:
            text = error
        elif 'printed' in result:
            text = '印刷データを送信しました。' if result['printed'] else '印刷をキャンセルしました。'
        elif result.get('extracted'):
            text = '移動して解凍しました。\n' + result['extracted']
        else:
            text = '移動しました。\n' + result.get('path', '')
        c = self.owner
        if not self.closed and not c.hidden and not c.user_hidden and c.bubble.isVisible():
            if c.bubble.current == 'one_shot':
                c.bubble.inline_mail.setText(text); c.bubble.inline_mail.show()
                c.bubble.resize_text(); c.position(); return
            if c.bubble.current != 'file_drop' and (c.bubble.interactive or c.bubble.notice and c.bubble.notice.important):
                c.bubble.text.setText(c.bubble.text.text()+'\n\n'+text)
                c.bubble.resize_text(); c.position(); return
        self.message(text)
