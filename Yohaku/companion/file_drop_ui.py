"""Connect explicit drop choices to the bounded file operation engine."""
from copy import deepcopy
from datetime import datetime
from pathlib import Path
import threading

from PySide6.QtCore import QObject, Signal


from .core import Notice
from .file_drop import FileDropError, FileDropStore, execute, file_identity, dropped_item
from .file_destinations import DestinationStore


class FileDropController(QObject):
    completed = Signal(object, str)

    def __init__(self, owner):
        super().__init__(owner)
        self.owner=owner;self.busy=False;self.closed=False;self.editor=None;self.destination_editor=None
        self.print_dialog=None;self.pending=None;self.rule=None;self.identity=None;self.stage=None
        self.store=FileDropStore(owner.path/'file_drop_settings.json')
        self.destinations=DestinationStore(owner.path/'file_destinations.json',self.store)
        self.completed.connect(self.finished)
        owner.resident.file_dropped.connect(self.drop);owner.resident.drop_allowed=self.allowed
        owner.panel.file_drop_requested.connect(self.show_editor)
        owner.bubble.file_action_requested.connect(self.run)
        owner.bubble.file_settings_requested.connect(self.show_destination_editor)
        owner.bubble.hidden.connect(self.cancel_pending)
        owner.menu.addAction('ドロップしたファイルの処理',self.show_editor)
        owner.menu.addAction('移動先を編集',self.show_destination_editor)

    def allowed(self):
        c=self.owner
        return (not self.closed and not self.busy and self.store.data['enabled'] and not c.hidden and not c.user_hidden
                and c.pending_reaction is None and not (c.bubble.isVisible() and c.bubble.current=='one_shot'))

    def cancel_pending(self):
        if not self.busy:self.pending=self.rule=self.identity=self.stage=None

    def drop(self,path):
        if not self.allowed():return
        self.cancel_pending()
        try:self.pending=dropped_item(path);self.identity=file_identity(self.pending)
        except (FileDropError,OSError):
            self.message('通常のファイルかフォルダーを1つドロップしてください。リンクは対象外です。');return
        self.store.__init__(self.store.path)
        if not self.store.data['enabled']:
            self.cancel_pending();return
        self.stage='action';self.show_choices()

    def show_choices(self):
        c=self.owner
        if self.pending is None or c.hidden or c.user_hidden or self.busy:return
        if self.stage=='destination':self.destinations.__init__(self.destinations.path,self.store)
        error=self.store.error or (self.destinations.error if self.stage=='destination' else '')
        c.bubble.show_drop_stage(self.pending,self.stage,self.destinations.data['destinations'],error)
        c.resident.hold_item(self.pending);c.engine.last_display=datetime.now().astimezone()
        c.motion.face_front();c.resident.frame_index=24;c.resident.update();c.position()

    def show_editor(self):
        if self.closed:return
        if self.editor is None:
            from .file_drop_editor import FileDropEditor
            self.editor=FileDropEditor(self.store);self.editor.setWindowIcon(self.owner.brand_icon)
            self.editor.saved.connect(self.settings_saved)
            self.editor.destinations_requested.connect(self.show_destination_editor)
        elif not self.editor.dirty:self.editor.reload()
        self.editor.show();self.editor.raise_();self.editor.activateWindow()

    def show_destination_editor(self):
        if self.closed or self.busy:return
        self.owner.bubble.dismiss()
        self.destinations.__init__(self.destinations.path,self.store)
        if self.destination_editor is None:
            from .destination_editor import DestinationEditor
            self.destination_editor=DestinationEditor(self.destinations);self.destination_editor.setWindowIcon(self.owner.brand_icon)
        elif not self.destination_editor.dirty:self.destination_editor.reload()
        self.destination_editor.show();self.destination_editor.raise_();self.destination_editor.activateWindow()

    def hide_editors(self):
        for editor in (self.editor,self.destination_editor):
            if editor:editor.hide()

    def settings_saved(self):
        if not self.store.data['enabled']:
            self.owner.bubble.dismiss();return
        if self.owner.bubble.isVisible() and self.owner.bubble.current=='file_drop':self.show_choices()

    def message(self,text):
        c=self.owner
        if self.closed or c.hidden or c.user_hidden:return
        c.bubble.display(Notice('',text));c.position()

    def run(self,action):
        c=self.owner
        if (self.busy or self.closed or self.pending is None or not c.bubble.isVisible()
                or c.bubble.current!='file_drop' or c.hidden or c.user_hidden or self.store.error or not self.store.data['enabled']):return
        try:
            path=dropped_item(self.pending)
            if file_identity(path)!=self.identity:raise FileDropError('変更されています。')
        except (FileDropError,OSError):
            self.message('ファイルを確認できないか、変更されています。もう一度ドロップしてください。');return
        if self.stage=='action':
            if action=='move':self.stage='destination';self.show_choices()
            elif action=='print_pdf' and path.is_file() and path.suffix.lower()=='.pdf':self.stage='paper';self.show_choices()
            return
        if self.stage=='destination' and action.startswith('destination:'):
            if self.destinations.error:return
            identifier=action.removeprefix('destination:')
            # Use the exact displayed snapshot, never a newly changed JSON path.
            row=next((r for r in self.destinations.data['destinations'] if r['id']==identifier),None)
            if row is None:return
            rule=dict(id='selected',label=row['name'],extensions=['<folder>'] if path.is_dir() else ['*'],
                      destination=row['path'],password_template='',actions=[dict(action='move',label='移動する')])
            task=lambda:execute('move',path,deepcopy(rule),datetime.now().astimezone())
        elif self.stage=='paper' and action in ('paper:a4','paper:a3','paper:auto'):
            paper=action.removeprefix('paper:')
            def task():
                from .pdf_print import print_pdf
                return {'printed':print_pdf(path,paper)}
        else:return
        self.busy=True
        for choice in list(c.bubble.drop_buttons.values())+list(c.bubble.drop_extra_buttons.values()):choice.setEnabled(False)
        c.bubble.drop_settings_button.setEnabled(False);c.bubble.drop_cancel.setEnabled(False)
        c.bubble.drop_notice.setText('処理しています。');c.bubble.drop_notice.show();c.bubble.resize_text();c.position()
        expected=self.identity
        def work():
            try:
                if file_identity(dropped_item(path))!=expected:raise FileDropError('ファイルが変更されています。もう一度ドロップしてください。')
                result,error=task(),''
            except FileDropError as problem:result,error={},str(problem)
            except Exception:result,error={},'処理を完了できません。ファイル・移動先・プリンターを確認してください。'
            try:self.completed.emit(result,error)
            except RuntimeError:pass
        threading.Thread(target=work,name='Yohaku-file-operation',daemon=False).start()

    def finished(self, result, error):
        self.busy = False; self.pending = None; self.rule = None; self.identity = None; self.stage = None
        self.owner.resident.clear_props()
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
            if result.get('source_retained'):
                text += '\n元の場所に残った項目があります。移動先を確認してから整理してください。'
        c = self.owner
        if not self.closed and not c.hidden and not c.user_hidden and c.bubble.isVisible():
            if c.bubble.current == 'one_shot':
                c.bubble.inline_mail.setText(text); c.bubble.inline_mail.show()
                c.bubble.resize_text(); c.position(); return
            if c.bubble.current != 'file_drop' and (c.bubble.interactive or c.bubble.notice and c.bubble.notice.important):
                c.bubble.text.setText(c.bubble.text.text()+'\n\n'+text)
                c.bubble.resize_text(); c.position(); return
        self.message(text)
