"""Connect explicit drop choices to the bounded file operation engine."""
from copy import deepcopy
from datetime import datetime
from pathlib import Path
import threading

from PySide6.QtCore import QObject, Signal


from .core import Notice
from .file_drop import ARCHIVE_EXTENSIONS,FileDropError, FileDropStore, execute, file_identity, dropped_item
from .file_destinations import DestinationStore
from .file_batch import selection,group_kind,check_identities,execute_batch


class FileDropController(QObject):
    completed = Signal(object, str)

    def __init__(self, owner):
        super().__init__(owner)
        self.owner=owner;self.busy=False;self.closed=False;self.editor=None;self.destination_editor=None
        self.print_dialog=None;self.pending=None;self.rule=None;self.identity=None;self.pending_kind=None;self.stage=None
        self.pending_items=();self.identities=();self.pending_kinds=();self.rules=();self.pending_group=None
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
        if not self.busy:
            self.pending=self.rule=self.identity=self.pending_kind=self.stage=None
            self.pending_items=self.identities=self.pending_kinds=self.rules=();self.pending_group=None

    def drop(self,path):
        if not self.allowed():return
        self.cancel_pending()
        try:
            paths=selection(path);identities=tuple(file_identity(item) for item in paths)
        except (FileDropError,OSError,TypeError):
            self.message(self.owner.engine.system_phrase('drop_invalid'));return
        self.store.__init__(self.store.path)
        if not self.store.data['enabled']:return
        self.pending_items=paths;self.identities=identities;self.pending_group=group_kind(paths)
        self.pending_kinds=tuple('folder' if item.is_dir() else 'file' for item in paths)
        self.rules=tuple(deepcopy(self.store.matching_rule(item)) for item in paths)
        self.pending=paths[0];self.identity=identities[0];self.pending_kind=self.pending_kinds[0];self.rule=self.rules[0]
        self.stage='action';self.show_choices()

    def show_choices(self):
        c=self.owner
        if not self.pending_items or c.hidden or c.user_hidden or self.busy:return
        if self.stage in ('destination','extract_destination'):self.destinations.__init__(self.destinations.path,self.store)
        error=self.store.error or (self.destinations.error if self.stage in ('destination','extract_destination') else '')
        c.bubble.show_drop_stage(self.pending_items,self.stage,self.destinations.data['destinations'],error)
        c.resident.hold_items(self.pending_items);c.engine.last_display=datetime.now().astimezone()
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
        if (self.busy or self.closed or not self.pending_items or not c.bubble.isVisible()
                or c.bubble.current!='file_drop' or c.hidden or c.user_hidden or self.store.error or not self.store.data['enabled']):return
        paths=self.pending_items;group=self.pending_group
        if self.stage=='action':
            allowed={'move','extract'} if group=='archive' else {'move','shelve','print_pdf'} if group=='pdf' else {'move','shelve'}
            if action not in allowed:return
        try:
            if self.stage=='action' and action=='shelve':
                # References allow file contents to change, but never their kind.
                for path,kind in zip(paths,self.pending_kinds):
                    if ('folder' if dropped_item(path).is_dir() else 'file')!=kind:raise FileDropError('種類が変更されています。')
            else:check_identities(paths,self.identities)
        except (FileDropError,OSError):
            self.message(c.engine.system_phrase('drop_changed'));return
        if self.stage=='action':
            if action=='shelve':
                try:
                    if len(paths)==1:c.shelf_service.deposit(paths[0])
                    else:c.shelf_service.deposit_many(paths)
                    self.message(c.engine.system_phrase('deposit_ok')+('\n'+str(len(paths))+'項目' if len(paths)>1 else ''))
                    self.cancel_pending()
                except (ValueError,OSError):self.message(c.engine.system_phrase('deposit_failed'))
                return
            if action=='extract':self.stage='extract_destination'
            elif action=='move':self.stage='destination'
            elif action=='print_pdf':self.stage='paper'
            self.show_choices();return
        if self.stage in ('destination','extract_destination') and action.startswith('destination:'):
            if self.destinations.error:return
            row=next((r for r in self.destinations.data['destinations'] if r['id']==action.removeprefix('destination:')),None)
            if row is None:return
            operation='extract' if self.stage=='extract_destination' else 'move';rules=[]
            for path,saved in zip(paths,self.rules):
                rules.append(dict(id='selected',label=row['name'],extensions=[path.suffix.lower()] if operation=='extract' else ['<folder>'] if path.is_dir() else ['*'],
                                  destination=row['path'],password_template=(saved or {}).get('password_template','') if operation=='extract' else '',
                                  actions=[dict(action=operation,label='解凍する' if operation=='extract' else '移動する')]))
            def perform(operation,path,rule,now):return execute(operation,path,rule,now)
        elif self.stage=='paper' and action in ('paper:a4','paper:a3','paper:auto') and group=='pdf':
            paper=action.removeprefix('paper:');operation='print_pdf';rules=[None]*len(paths)
            def perform(operation,path,rule,now):
                from .pdf_print import print_pdf
                return {'printed':print_pdf(path,paper)}
        else:return
        rules=deepcopy(rules);expected=self.identities;now=datetime.now().astimezone();self.busy=True
        for choice in list(c.bubble.drop_buttons.values())+list(c.bubble.drop_extra_buttons.values()):choice.setEnabled(False)
        c.bubble.drop_settings_button.setEnabled(False);c.bubble.drop_cancel.setEnabled(False)
        c.bubble.drop_notice.setText(c.engine.system_phrase('processing'));c.bubble.drop_notice.show();c.bubble.resize_text();c.position()
        def work():
            if len(paths)>1:
                result=execute_batch(paths,expected,operation,rules,now,perform);error=result.pop('error','')
            else:
                try:
                    check_identities(paths,expected);result,error=perform(operation,paths[0],rules[0],now),''
                except FileDropError as problem:result,error={},str(problem)
                except Exception:result,error={},'処理を完了できません。ファイル・移動先・プリンターを確認してください。'
            try:self.completed.emit(result,error)
            except RuntimeError:pass
        threading.Thread(target=work,name='Yohaku-file-operation',daemon=False).start()

    def finished(self, result, error):
        self.busy=False;self.cancel_pending()
        self.owner.resident.clear_props()
        if self.closed:
            return
        phrase=self.owner.engine.system_phrase
        if result.get('batch'):
            total=result['total'];completed=result['completed']
            if error:text=phrase('operation_failed')+'\n'+error
            elif result['operation']=='print_pdf':text=phrase('print_sent')
            elif result['operation']=='extract':text=phrase('extracted_only',{'path':str(total)+'件'})
            else:text=phrase('moved',{'path':str(total)+'件'})
            text+='\n完了: '+str(len(completed))+'/'+str(total)+'件'
            if completed:text+='\n'+'\n'.join('✓ '+row['name'] for row in completed)
            if any(row['result'].get('source_retained') for row in completed):text+='\n'+phrase('source_retained')
            if result['remaining']:text+='\n未処理（失敗した項目を含む）:\n'+'\n'.join('・'+name for name in result['remaining'])
        elif error:
            text = phrase('operation_failed')+'\n'+error
        elif 'printed' in result:
            text = phrase('print_sent' if result['printed'] else 'print_cancelled')
        elif result.get('extracted'):
            text = phrase('extracted_only' if result.get('source_preserved') else 'extracted',{'path':result['extracted']})
        else:
            text = phrase('moved',{'path':result.get('path','')})
            if result.get('source_retained'):
                text += '\n'+phrase('source_retained')
        c = self.owner
        if not self.closed and not c.hidden and not c.user_hidden and c.bubble.isVisible():
            if c.bubble.current == 'one_shot':
                c.bubble.inline_mail.setText(text); c.bubble.inline_mail.show()
                c.bubble.resize_text(); c.position(); return
            if c.bubble.current != 'file_drop' and (c.bubble.interactive or c.bubble.notice and c.bubble.notice.important):
                c.bubble.text.setText(c.bubble.text.text()+'\n\n'+text)
                c.bubble.resize_text(); c.position(); return
        self.message(text)
