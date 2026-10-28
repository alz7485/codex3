"""Searchable collection without executing events or changing progression."""
from copy import copy
from PySide6.QtCore import Qt,Signal
from PySide6.QtWidgets import (QComboBox,QHBoxLayout,QLabel,QLineEdit,QPlainTextEdit,QPushButton,QSplitter,QTreeWidget,QTreeWidgetItem,QVBoxLayout,QWidget)
from .dialogue import voice_for
from .growth_records import KIND_LABELS,collection_rows,collection_text
from .growth_presentation import GrowthCombo


def set_detail(widget,text):
    if widget.toPlainText()==text:return
    scroll=widget.verticalScrollBar().value();widget.setPlainText(text);widget.verticalScrollBar().setValue(scroll)


class GrowthCollection(QWidget):
    try_requested=Signal(str)
    def __init__(self,service,parent=None):
        super().__init__(parent);self.service=service;self.character=None;self.rows={};self.signature=None
        layout=QVBoxLayout(self);filters=QHBoxLayout();layout.addLayout(filters)
        self.search=QLineEdit();self.search.setPlaceholderText('名前・パック名で検索');self.search.setAccessibleName('解放したものを検索');filters.addWidget(self.search,1)
        self.kind=GrowthCombo();self.kind.addItem('すべての種類','')
        for key,name in KIND_LABELS.items():self.kind.addItem(name,key)
        self.kind.addItem('未読込の記録','missing');filters.addWidget(self.kind)
        self.state=GrowthCombo()
        for title,value in [('すべての状態',''),('解放済み','unlocked'),('未解放','locked')]:self.state.addItem(title,value)
        filters.addWidget(self.state)
        self.count=QLabel();layout.addWidget(self.count)
        split=QSplitter();layout.addWidget(split,1)
        self.items=QTreeWidget();self.items.setHeaderLabels(['名前','種類','状態・レベル']);self.items.setColumnWidth(0,175);self.items.setColumnWidth(1,75)
        self.items.setRootIsDecorated(False);self.items.setUniformRowHeights(True);split.addWidget(self.items)
        pane=QWidget();detail_layout=QVBoxLayout(pane);self.detail=QPlainTextEdit();self.detail.setReadOnly(True);detail_layout.addWidget(self.detail)
        self.try_button=QPushButton('この衣装を試着');self.try_button.setEnabled(False);self.try_button.clicked.connect(self.try_selected);detail_layout.addWidget(self.try_button)
        split.addWidget(pane);split.setSizes([390,390])
        self.items.currentItemChanged.connect(self.show_detail)
        for field in (self.kind,self.state):field.currentIndexChanged.connect(self.filter_rows)
        self.search.textChanged.connect(self.filter_rows)

    def refresh(self,character):
        service=self.service;p=service.engine.progress(character);catalog=service.engine.catalog
        signature=(id(catalog),character,p['level'],tuple(p['unlocked']),tuple(sorted(p['equipped'].items())))
        if signature!=self.signature:
            old=self.items.currentItem();selected=old.data(0,Qt.ItemDataRole.UserRole) if old else None
            scroll=self.items.verticalScrollBar().value();self.signature=signature;self.character=character
            self.rows={row['key']:row for row in collection_rows(catalog,p,character)}
            blocked=self.items.blockSignals(True);self.items.clear()
            for key,row in self.rows.items():
                level=f' / Lv.{row["level"]}' if row['level'] is not None else ''
                item=QTreeWidgetItem([row['name'],KIND_LABELS.get(row['kind'],'取得記録'),row['state']+level]);item.setData(0,Qt.ItemDataRole.UserRole,key)
                self.items.addTopLevelItem(item)
                if key==selected:self.items.setCurrentItem(item)
            self.items.blockSignals(blocked);self.filter_rows();self.items.verticalScrollBar().setValue(scroll)
        self.show_detail()

    def filter_rows(self,*_):
        query=self.search.text().strip().casefold();shown=0
        for index in range(self.items.topLevelItemCount()):
            item=self.items.topLevelItem(index);row=self.rows[item.data(0,Qt.ItemDataRole.UserRole)]
            pack=row['key'].split(':',1)[0];pack_name=self.service.engine.catalog.packs.get(pack,{}).get('document',{}).get('name','')
            visible=(not query or query in (row['name']+' '+pack_name+' '+pack).casefold())
            visible=visible and (not self.kind.currentData() or self.kind.currentData()==row['kind'])
            visible=visible and (not self.state.currentData() or (self.state.currentData()=='unlocked')==row['unlocked'])
            item.setHidden(not visible);shown+=bool(visible)
        current=self.items.currentItem()
        if current is None or current.isHidden():
            first=next((self.items.topLevelItem(n) for n in range(self.items.topLevelItemCount()) if not self.items.topLevelItem(n).isHidden()),None)
            self.items.setCurrentItem(first)
        self.count.setText(f'{shown}件 / 全{len(self.rows)}件');self.show_detail()

    def show_detail(self,*_):
        current=self.items.currentItem();row=self.rows.get(current.data(0,Qt.ItemDataRole.UserRole)) if current and not current.isHidden() else None
        self.try_button.setEnabled(bool(row and row['kind']=='costumes' and row['unlocked']))
        if row is None:set_detail(self.detail,'条件に合うものはありません。');return
        settings=copy(self.service.host.settings);settings.character=self.character
        voice=voice_for(settings,self.service.host.dialogue.data)
        set_detail(self.detail,collection_text(row,self.service.engine.catalog,self.service.engine.progress(self.character),self.character,voice))

    def try_selected(self):
        current=self.items.currentItem()
        if self.try_button.isEnabled() and current:self.try_requested.emit(current.data(0,Qt.ItemDataRole.UserRole))
