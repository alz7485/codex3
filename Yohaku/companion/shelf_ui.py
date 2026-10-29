"""Speech-list launcher operations; removal touches only the local JSON."""
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import QObject,QTimer,QUrl,Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMenu
from .file_drop import dropped_item,FileDropError
from .shelf import ShelfStore,ShelfError


class ShelfController(QObject):
    def __init__(self,owner):
        super().__init__(owner);self.owner=owner;self.popup=None;self.store=ShelfStore(owner.path/'shelf.json')
        owner.bubble.hidden.connect(self.close_popup)
        owner.bubble.content_changing.connect(self.close_popup)
        self.mail_timer=QTimer(self);self.mail_timer.setSingleShot(True);self.mail_timer.setInterval(60000)
        self.mail_timer.timeout.connect(self.expire_mail)
        owner.bubble.hidden.connect(self.cancel_mail)
        owner.bubble.content_changing.connect(self.cancel_mail)
        owner.bubble.shelf_open_requested.connect(self.open_item)
        owner.bubble.shelf_context_requested.connect(self.context_menu)
        owner.panel.shelf_period_requested.connect(self.change_period)
        self.timer=QTimer(self);self.timer.setInterval(60000);self.timer.timeout.connect(self.expire)
        self.sync_setting();self.expire();self.timer.start()
    def now(self):return datetime.now().astimezone()
    def cancel_mail(self):
        self.mail_timer.stop();self.owner.bubble.shelf_mail.hide()
    def expire_mail(self):
        self.cancel_mail();c=self.owner
        if c.bubble.isVisible() and c.bubble.current=='shelf':
            c.bubble.resize_text();c.position()
    def show_mail(self,notice):
        c=self.owner
        if not c.bubble.isVisible() or c.bubble.current!='shelf':return
        c.bubble.shelf_mail.set_message(notice.text,styles=notice.styles)
        c.bubble.shelf_mail.show();self.mail_timer.start(60000)
        c.bubble.resize_text();c.position()
    def sync_setting(self):
        field=self.owner.panel.shelf_period
        blocked=field.blockSignals(True);field.setCurrentIndex(field.findData(self.store.data['period']));field.blockSignals(blocked)
        self.owner.panel.shelf_status.setText(self.store.error or '本体は移動しません。期間変更は現在の一覧にも適用します。削除・期限切れは一覧の登録だけを外します。')
    def change_period(self,period):
        try:self.store.set_period(period,self.now());self.refresh()
        except (ShelfError,OSError):self.sync_setting();self.owner.panel.shelf_status.setText('保持期間を保存できません。設定ファイルをご確認ください。');return
        self.sync_setting()
    def expire(self):
        try:
            before=len(self.store.data['items']);self.store.prune(self.now())
            if before!=len(self.store.data['items']):self.refresh()
        except (ShelfError,OSError):self.owner.panel.shelf_status.setText(self.store.error or '期限切れの登録を整理できません。保存先をご確認ください。')
    def show(self):
        c=self.owner
        if c.hidden or c.user_hidden:return
        try:items=self.store.prune(self.now());error=''
        except (ShelfError,OSError):items=[];error=c.engine.system_phrase('shelf_load_failed')+('\n'+self.store.error if self.store.error else '')
        c.bubble.show_shelf(items,error);c.position()
    def refresh(self):
        if self.owner.bubble.isVisible() and self.owner.bubble.current=='shelf':self.show()
    def deposit(self,path):
        self.store.add(path,self.now());self.refresh()
    def deposit_many(self,paths):
        self.store.add_many(paths,self.now());self.refresh()
    def lookup(self,identifier):
        return next((row for row in self.store.prune(self.now()) if row['id']==identifier),None)
    def report(self,text):
        c=self.owner
        if c.bubble.isVisible() and c.bubble.current=='shelf':
            c.bubble.text.setText(text);c.bubble.resize_text();c.position()
    def open_item(self,identifier):
        try:
            row=self.lookup(identifier)
            if row is None:self.refresh();return
            path=dropped_item(row['path'])
            if path.is_dir()!=(row['kind']=='folder'):raise ShelfError('種類が変わっています。')
            if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))):raise ShelfError('開けません。')
        except (ShelfError,FileDropError,OSError):self.report(self.owner.engine.system_phrase('shelf_open_failed'))
    def open_parent(self,identifier):
        try:
            row=self.lookup(identifier)
            if row is None:self.refresh();return
            if row['kind']!='file':return
            folder=Path(row['path']).parent
            if not folder.is_dir() or not QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder))):raise ShelfError('開けません。')
        except (ShelfError,OSError):self.report(self.owner.engine.system_phrase('parent_open_failed'))
    def remove(self,identifier):
        try:self.store.remove(identifier);self.refresh()
        except (ShelfError,OSError):self.report(self.owner.engine.system_phrase('shelf_remove_failed'))
    def menu_for(self,row):
        menu=QMenu(self.owner.bubble)
        if row['kind']=='file':menu.addAction('フォルダを開く',lambda:self.open_parent(row['id']))
        menu.addAction('削除',lambda:self.remove(row['id']))
        return menu
    def close_popup(self):
        menu=self.popup;self.popup=None
        if menu is not None:menu.close();menu.deleteLater()
    def context_menu(self,point):
        c=self.owner
        if c.bubble.current!='shelf':return
        item=c.bubble.file_links.itemAt(point)
        if item is None:return
        c.bubble.file_links.setCurrentItem(item)
        try:row=self.lookup(item.data(Qt.ItemDataRole.UserRole))
        except (ShelfError,OSError):self.report(self.owner.engine.system_phrase('shelf_lookup_failed'));return
        if row is None:self.refresh();return
        self.close_popup();menu=self.menu_for(row);self.popup=menu
        def release():
            if self.popup is menu:self.popup=None
            menu.deleteLater()
        menu.aboutToHide.connect(release)
        menu.popup(c.bubble.file_links.viewport().mapToGlobal(point))
