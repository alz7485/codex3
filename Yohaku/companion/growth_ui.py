"""Progress window and integration; routine notifications always have priority."""
from datetime import datetime
from pathlib import Path
import subprocess
import sys
import time
import math

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFormLayout, QHBoxLayout, QLabel,
    QMainWindow, QPushButton, QProgressBar, QTabWidget, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from .characters import CHARACTERS
from .core import Notice
from .costumes import CostumeRenderer
from .dialogue import voice_for
from .growth import GrowthEngine, GrowthStore, session_locked
from .growth_content import load_catalog, seed_content
from .growth_editor_widgets import frame_caption
from .exp_popup import ExpPopup


class GrowthWindow(QMainWindow):
    def __init__(self, service):
        super().__init__(); self.service = service
        self.setWindowTitle('Yohaku — 一緒に過ごした記録'); self.resize(780,650)
        root = QWidget(); self.setCentralWidget(root); layout = QVBoxLayout(root)
        self.character = QComboBox()
        for key,name in CHARACTERS.items(): self.character.addItem(name,key)
        self.character.setCurrentIndex(list(CHARACTERS).index(service.host.settings.character))
        self.character.currentIndexChanged.connect(self.refresh)
        layout.addWidget(self.character)
        self.summary = QLabel(); self.summary.setWordWrap(True); layout.addWidget(self.summary)
        self.exp_bar=QProgressBar();self.exp_bar.setRange(0,1000);self.exp_bar.setTextVisible(False);self.exp_bar.setMaximumHeight(9);layout.addWidget(self.exp_bar)
        self.status = QLabel(); self.status.setWordWrap(True); layout.addWidget(self.status)
        tabs = QTabWidget(); layout.addWidget(tabs,1)
        trophy_page = QWidget(); tl = QVBoxLayout(trophy_page)
        self.trophies = QTreeWidget(); self.trophies.setHeaderLabels(['トロフィー','状態・日時','説明／最高値'])
        self.trophies.setColumnWidth(0,180); self.trophies.setColumnWidth(1,180); tl.addWidget(self.trophies)
        tabs.addTab(trophy_page,'トロフィー')
        costume_page = QWidget(); cl = QVBoxLayout(costume_page)
        from .ui import Mascot
        self.preview = Mascot(200); self.preview.frame_index=24; cl.addWidget(self.preview,alignment=Qt.AlignmentFlag.AlignCenter)
        self.frame = QComboBox()
        for n in range(28): self.frame.addItem(frame_caption(n),n)
        self.frame.setCurrentIndex(24); self.frame.currentIndexChanged.connect(self.preview_frame); cl.addWidget(self.frame)
        form=QFormLayout(); cl.addLayout(form); self.slots={}
        for slot,name in (('head','頭'),('body','体'),('accessory','アクセサリー')):
            combo=QComboBox();self.slots[slot]=combo;form.addRow(name,combo)
            combo.currentIndexChanged.connect(lambda _,s=slot:self.equip(s))
        note=QLabel('衣装は自動装着しません。対応していないフレーム・小道具の動作中は非表示です。\n無効・削除したパックの取得記録も保持します。');note.setWordWrap(True);cl.addWidget(note);cl.addStretch()
        tabs.addTab(costume_page,'衣装')
        self.packs=QTreeWidget();self.packs.setHeaderLabels(['パック','状態']);tabs.addTab(self.packs,'コンテンツ')
        row=QHBoxLayout();layout.addLayout(row)
        reload_button=QPushButton('パックを再読み込み');reload_button.clicked.connect(service.reload);row.addWidget(reload_button)
        edit=QPushButton('別ウィンドウでコンテンツを編集');edit.clicked.connect(service.open_editor);row.addWidget(edit)
        self.refresh()

    def preview_frame(self): self.preview.frame_index=self.frame.currentData();self.preview.update()

    def refresh(self):
        service=self.service;character=self.character.currentData();p=service.engine.progress(character)
        config=service.engine.catalog.config
        threshold=config['level_thresholds'][p['level']] if config and p['level']<len(config['level_thresholds']) else None
        self.summary.setText(f'{CHARACTERS[character]}  Lv.{p["level"]}    EXP {p["exp"]:.1f}'+(f' / 次のレベル {threshold:g}' if threshold is not None else '')+
                             f'\n一緒に過ごした時間：{int(p["seconds"]//3600)}時間{int(p["seconds"]%3600//60)}分')
        if config:
            remaining=max(0,math.ceil(config['exp_interval_seconds']-p['exp_seconds']))
            self.summary.setText(self.summary.text()+f'\n起動時間のEXP：次の獲得まであと{remaining//60}分{remaining%60:02}秒（スリープ・ロック中は初期設定で停止）')
        self.exp_bar.setVisible(threshold is not None)
        if threshold is not None:
            base=config['level_thresholds'][p['level']-1]
            self.exp_bar.setValue(round(max(0,min(1,(p['exp']-base)/(threshold-base)))*1000))
        self.status.setText(service.error_text())
        selected=self.trophies.currentItem()
        selected=selected.data(0,Qt.ItemDataRole.UserRole) if selected is not None else None
        scroll=self.trophies.verticalScrollBar().value()
        self.trophies.clear();known=set()
        for key,item in service.engine.catalog.items['trophies'].items():
            if character not in item['characters']:continue
            known.add(key);record=p['trophies'].get(key);hidden=item['hidden'] and not record
            row=QTreeWidgetItem(['？？？' if hidden else item['name'],record['at'][:19].replace('T',' ') if record else '未達成',
                                '秘密のトロフィーです。' if hidden else item['description']+(f' / 最高値 {p["best"][key]:g}' if key in p['best'] else '')])
            if not hidden and item.get('icon'):row.setIcon(0,QIcon(str(item['root']/item['icon'])))
            row.setData(0,Qt.ItemDataRole.UserRole,key)
            self.trophies.addTopLevelItem(row)
            if key==selected:self.trophies.setCurrentItem(row)
        for key,record in p['trophies'].items():
            if key not in known:
                row=QTreeWidgetItem([key,record['at'][:19],'取得済み（パックが無効または削除されています）'])
                row.setData(0,Qt.ItemDataRole.UserRole,key);self.trophies.addTopLevelItem(row)
                if key==selected:self.trophies.setCurrentItem(row)
        self.trophies.verticalScrollBar().setValue(scroll)
        catalog=service.engine.catalog
        if getattr(self,'pack_signature',None)!=id(catalog):
            self.pack_signature=id(catalog);self.packs.clear()
            for key,pack in catalog.packs.items():
                self.packs.addTopLevelItem(QTreeWidgetItem([pack['document']['name']+' / '+key,'有効' if pack['document']['enabled'] else '無効']))
            for error in catalog.errors:self.packs.addTopLevelItem(QTreeWidgetItem(['読み込みの問題',error]))
        signature=(id(catalog),character,tuple(sorted(p['equipped'].items())),tuple(p['unlocked']))
        if signature==getattr(self,'costume_signature',None) or any(w.view().isVisible() for w in self.slots.values()):return
        self.costume_signature=signature;self.preview.set_character(character)
        for slot,combo in self.slots.items():
            combo.blockSignals(True);combo.clear();combo.addItem('装着しない','')
            for key,item in service.engine.catalog.items['costumes'].items():
                if item['slot']==slot and character in item['characters'] and key in p['unlocked']:combo.addItem(item['name'],key)
            equipped=p['equipped'].get(slot,'')
            if equipped and combo.findData(equipped)<0:combo.addItem('未読込の衣装（記録保持）',equipped)
            combo.setCurrentIndex(max(0,combo.findData(equipped)));combo.blockSignals(False)
        renderer=CostumeRenderer();renderer.configure(service.engine.catalog,p,character);self.preview.costumes=renderer;self.preview.update()

    def equip(self,slot):
        try:self.service.engine.equip(self.character.currentData(),slot,self.slots[slot].currentData())
        except (OSError,ValueError) as e:self.status.setText(str(e));return
        self.service.apply_costumes();self.refresh()


class GrowthService:
    def __init__(self,host):
        self.host=host;self.window=None;self.error='';self.closed=False;self.notifications=[]
        self.content_root=host.path/'content';self.store=GrowthStore(host.path/'growth.json')
        try:seed_content(self.content_root)
        except OSError as e:self.error='サンプルパックを準備できません。保存先をご確認ください。'
        self.engine=GrowthEngine(self.store,load_catalog(self.content_root))
        self.exp_popup=ExpPopup(host.resident,allowed=self.exp_visible,animated=lambda:host.settings.animation)
        self.renderer=CostumeRenderer();host.resident.costumes=self.renderer
        self.apply_costumes();self.write_errors()
        self.sample()
        self.timer=QTimer(host);self.timer.setInterval(5000);self.timer.timeout.connect(self.sample);self.timer.start()

    def error_text(self):return self.error or self.store.error or ('\n'.join(self.engine.catalog.errors[:5])) or '成長データはData/growth.json、追加パックはData/contentに保存します。'

    def write_errors(self):
        errors=([self.store.error] if self.store.error else [])+self.engine.catalog.errors
        if self.error:errors.insert(0,self.error)
        try:
            path=self.host.path/'growth-content.log'
            # Bounded, current diagnostic report, without PC titles/paths/content.
            path.write_text('\n'.join(errors[:200])+'\n',encoding='utf-8')
        except OSError:pass

    def sample(self):
        if self.closed:return
        h=self.host
        try:
            now=datetime.now().astimezone();locked=session_locked();notices=[]
            previous=self.engine.last_character
            if previous is not None and previous!=h.settings.character:
                notices+=self.engine.step(previous,now,h.engine.context,self.calendar(),self.work(),locked=locked)
            notices+=self.engine.step(h.settings.character,now,h.engine.context,
                       self.calendar(),self.work(),locked=locked)
            for notice in notices:
                if notice['kind']=='exp' and notice['character']==h.settings.character:self.show_exp_gain(notice['amount'])
            self.notifications=(self.notifications+[n for n in notices if n['kind']!='exp'])[-20:];self.error='';self.apply_costumes()
        except (OSError,ValueError,TypeError,KeyError) as e:
            self.error='成長を保存できませんでした。保存先とData/growth.jsonをご確認ください。';self.write_errors()
        if self.window and self.window.isVisible():self.window.refresh()

    def work(self):return tuple(self.host.dialogue.data['options'][k] for k in ('work_start','work_end'))

    def calendar(self):
        options=self.host.engine.context_options
        return None if options.error else options.calendar()

    def exp_visible(self):
        h=self.host
        return (not self.closed and not h.hidden and not h.user_hidden and h.resident.isVisible()
                and getattr(self,'exp_character',h.settings.character)==h.settings.character)

    def show_exp_gain(self,amount):
        if session_locked():return
        self.exp_character=self.host.settings.character
        self.exp_popup.show_gain(amount)

    def apply_costumes(self):
        h=self.host;p=self.engine.progress(h.settings.character)
        signature=(h.settings.character,tuple(sorted(p['equipped'].items())),tuple(p['unlocked']))
        if getattr(self,'signature',None)!=signature:
            if getattr(self,'signature',None) and self.signature[0]!=h.settings.character:self.exp_popup.cancel()
            self.signature=signature;self.renderer.configure(self.engine.catalog,p,h.settings.character);h.resident.update()

    def reload(self):
        try:
            notices=self.engine.reload(load_catalog(self.content_root))
            self.notifications=(self.notifications+notices)[-20:];self.error=''
        except (OSError,ValueError,TypeError,KeyError):
            self.error='追加コンテンツの解放を保存できませんでした。記録を初期化せず停止しています。'
        self.signature=None;self.apply_costumes();self.write_errors()
        if self.window:self.window.refresh()

    def show(self):
        if not self.window:self.window=GrowthWindow(self);self.window.setWindowIcon(self.host.brand_icon)
        self.window.refresh();self.window.show();self.window.raise_();self.window.activateWindow()

    def open_editor(self):
        try:
            if getattr(sys,'frozen',False):
                editor=Path(sys.executable).parent/'YohakuContentEditor.exe'
                args=([str(editor)] if editor.exists() else [sys.executable,'--content-editor'])+['--content-root',str(self.content_root)]
            else:args=[sys.executable,str(Path(__file__).resolve().parents[1]/'content_editor_main.py'),'--content-root',str(self.content_root)]
            subprocess.Popen(args,close_fds=True)
        except OSError:self.error='コンテンツエディタを起動できません。';self.show()

    def next_notice(self,now):
        h=self.host
        if self.closed:return None
        if self.error or self.store.error or not self.engine.catalog.config:return None
        if not h.settings.chatter or h.hidden or h.user_hidden or h.pending_reaction is not None:return None
        if h.engine.paused_until and now<h.engine.paused_until:return None
        from .core import is_quiet
        if is_quiet(now,h.settings):return None
        if any(w is not None and w.isVisible() for w in (h.bubble,h.panel,h.history_window,h.editor,h.reminder_editor,h.context_editor,self.window,
                h.preview,h.menu,h.file_drop_service.editor,h.file_drop_service.destination_editor,h.file_drop_service.print_dialog)):return None
        if QApplication.activeModalWidget() is not None or QApplication.activePopupWidget() is not None or session_locked():return None
        if h.file_drop_service.busy:return None
        if (not h.resident.isVisible() or h.resident.press_position is not None or h.resident.drop_hover or h.resident.dragging
                or h.resident.mail_raised or h.resident.calendar_checking or h.resident.taking_notes
                or h.resident.held_icon is not None):return None
        if h.dialogue.data['options']['suppress_during_meetings'] and any(e.start<=now<e.end for e in h.events):return None
        voice=voice_for(h.settings,h.dialogue.data)
        self.notifications=[n for n in self.notifications if n['character']==h.settings.character]
        if self.notifications:
            n=self.notifications.pop(0)
            if n['kind']=='level':
                h.motion.start_soon()
                if h.settings.animation:h.resident.level_up.start()
                return Notice('',h.engine.system_phrase('growth_level',{'level':n['level']}),True,expression='happy',kind='notification')
            item=self.engine.catalog.items['trophies'].get(n['key'])
            if item:return Notice('',item['texts'].get(voice,item['texts'].get('*',item['name']))+'\n'+h.engine.system_phrase('growth_trophy',{'name':item['name']}),True,expression=item['expression'],kind='notification')
            return None
        try:item=self.engine.choose_event(h.settings.character,voice,now,h.engine.context,self.calendar(),self.work())
        except (OSError,ValueError,TypeError,KeyError):self.error='演出の記録を保存できませんでした。';return None
        if item:
            if item['exp']>0:self.show_exp_gain(item['exp'])
            self.notifications=(self.notifications+self.engine.pending)[-20:];self.engine.pending=[]
            if item.get('effect')=='sparkle':h.resident.start_growth_effect()
            return Notice('',item['texts'].get(voice,item['texts'].get('*','')),expression=item['expression'])
        return None

    def shutdown(self):
        if self.closed:return
        self.sample();self.closed=True;self.timer.stop()
        self.exp_popup.cancel()
        self.host.resident.level_up.cancel()
        try:self.engine.flush()
        except (OSError,ValueError):self.error='終了時の成長記録を保存できませんでした。';self.write_errors()
        if self.window:self.window.hide()
