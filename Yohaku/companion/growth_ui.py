"""Progress window and integration; routine notifications always have priority."""
from datetime import datetime
from pathlib import Path
import subprocess
import sys
import time
import math

from PySide6.QtCore import QSize, QTimer, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFormLayout, QHBoxLayout, QLabel,
    QMainWindow, QPlainTextEdit, QPushButton, QProgressBar, QScrollArea, QSplitter, QStyle, QTabWidget, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from .characters import CHARACTERS
from .core import Notice
from .costumes import CostumeRenderer
from .dialogue import voice_for
from .growth import GrowthEngine, GrowthStore, session_locked
from .growth_content import load_catalog, seed_content,seed_examples
from .growth_editor_widgets import frame_caption
from .exp_popup import ExpPopup
from .growth_records import collection_rows,next_unlocks,trophy_text
from .growth_records_ui import GrowthCollection,set_detail
from .growth_presentation import GROWTH_STYLE,GrowthCombo,MetricCard,PortraitStage,card,text_label


class GrowthWindow(QMainWindow):
    def __init__(self, service):
        super().__init__();self.service=service
        self.setWindowTitle('Yohaku — 一緒に過ごした記録');self.setMinimumSize(800,650)
        area=self.screen().availableGeometry();self.resize(min(980,max(800,area.width()-48)),min(820,max(650,area.height()-48)))
        self.setStyleSheet(GROWTH_STYLE)
        root=QWidget();root.setObjectName('growthRoot');self.setCentralWidget(root)
        layout=QVBoxLayout(root);layout.setContentsMargins(24,22,24,20);layout.setSpacing(15)
        header=QHBoxLayout();layout.addLayout(header)
        title=QVBoxLayout();title.setSpacing(4);header.addLayout(title,1)
        title.addWidget(text_label('一緒に過ごした記録','growthTitle'))
        self.subtitle=text_label('少しずつ育つ、いつもの相棒。','growthSubtitle');title.addWidget(self.subtitle)
        header.addWidget(text_label('記録を見るキャラ'))
        self.character=GrowthCombo();self.character.setMinimumWidth(155);self.character.setIconSize(QSize(24,24));self.character.setAccessibleName('記録を見るキャラクター')
        from .ui import Mascot,character_pixmap
        for key,name in CHARACTERS.items():self.character.addItem(QIcon(character_pixmap(key)),name,key)
        self.character.setCurrentIndex(list(CHARACTERS).index(service.host.settings.character));header.addWidget(self.character)
        self.character.currentIndexChanged.connect(self.refresh)

        hero,hero_layout=card('growthHero',16);layout.addWidget(hero)
        hero_row=QHBoxLayout();hero_row.setSpacing(22);hero_layout.addLayout(hero_row)
        self.portrait_stage=PortraitStage();self.home_preview=Mascot(126);self.home_preview.frame_index=24
        self.portrait_stage.content.addWidget(self.home_preview,alignment=Qt.AlignmentFlag.AlignCenter);hero_row.addWidget(self.portrait_stage)
        hero_info=QVBoxLayout();hero_info.setContentsMargins(0,5,12,5);hero_info.setSpacing(10);hero_row.addLayout(hero_info,1)
        identity=QHBoxLayout();self.hero_name=text_label('','growthName');identity.addWidget(self.hero_name)
        self.level_badge=text_label('','growthLevel');self.level_badge.setAlignment(Qt.AlignmentFlag.AlignCenter);identity.addStretch();identity.addWidget(self.level_badge);hero_info.addLayout(identity)
        exp_row=QHBoxLayout();self.next_level=text_label('','growthNext');exp_row.addWidget(self.next_level,1)
        self.exp_value=text_label();self.exp_value.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignVCenter);exp_row.addWidget(self.exp_value);hero_info.addLayout(exp_row)
        self.exp_bar=QProgressBar();self.exp_bar.setRange(0,1000);self.exp_bar.setTextVisible(False);self.exp_bar.setFixedHeight(10);self.exp_bar.setAccessibleName('次のレベルまでのEXP');hero_info.addWidget(self.exp_bar)
        self.summary=text_label();hero_info.addWidget(self.summary)

        tabs=QTabWidget();self.tabs=tabs;tabs.setDocumentMode(True);tabs.tabBar().setDrawBase(False);layout.addWidget(tabs,1)
        home=QScrollArea();home.setWidgetResizable(True);home.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        home_body=QWidget();home.setWidget(home_body);hl=QVBoxLayout(home_body);hl.setContentsMargins(0,1,2,2);hl.setSpacing(14)
        stats=QHBoxLayout();stats.setSpacing(12);hl.addLayout(stats)
        self.metrics={}
        for key,label in (('time','一緒に過ごした時間'),('speech','会話・演出'),('costumes','衣装'),('trophies','トロフィー')):
            metric=MetricCard(label);self.metrics[key]=metric;stats.addWidget(metric,1)
        cards=QHBoxLayout();cards.setSpacing(14);hl.addLayout(cards)
        reward,reward_layout=card();cards.addWidget(reward,3)
        reward_heading=QHBoxLayout();reward_heading.addWidget(text_label('次に解放されるもの','growthSection'));reward_heading.addStretch()
        self.reward_level=text_label('','growthRewardLevel');reward_heading.addWidget(self.reward_level);reward_layout.addLayout(reward_heading)
        self.next_reward=text_label('','growthSection');reward_layout.addWidget(self.next_reward);reward_layout.addStretch()
        library_button=QPushButton('解放一覧を見る');library_button.setObjectName('growthPrimary');reward_layout.addWidget(library_button)
        wardrobe,wardrobe_layout=card();cards.addWidget(wardrobe,2)
        wardrobe_layout.addWidget(text_label('いまの装い','growthSection'));self.equipment_summary=text_label();wardrobe_layout.addWidget(self.equipment_summary);wardrobe_layout.addStretch()
        costume_button=QPushButton('衣装を試す');wardrobe_layout.addWidget(costume_button)
        hl.addWidget(text_label('自分のペースで、一緒の時間を重ねていきましょう。'));hl.addStretch()
        tabs.addTab(home,'育成ホーム')

        trophy_page=QWidget();tl=QVBoxLayout(trophy_page);tl.setContentsMargins(0,1,0,0)
        trophy_split=QSplitter(Qt.Orientation.Vertical);tl.addWidget(trophy_split)
        self.trophies=QTreeWidget();self.trophies.setHeaderLabels(['トロフィー','状態・日時','説明／最高値'])
        self.trophies.setColumnWidth(0,185);self.trophies.setColumnWidth(1,180);self.trophies.setRootIsDecorated(False);trophy_split.addWidget(self.trophies)
        self.trophy_detail=QPlainTextEdit();self.trophy_detail.setReadOnly(True);self.trophy_detail.setAccessibleName('トロフィーの条件と記録');trophy_split.addWidget(self.trophy_detail);trophy_split.setSizes([180,170])
        self.trophies.currentItemChanged.connect(self.show_trophy_detail);tabs.addTab(trophy_page,'トロフィー')
        self.collection=GrowthCollection(service);self.collection.try_requested.connect(self.try_costume);tabs.addTab(self.collection,'解放一覧')
        library_button.clicked.connect(lambda:tabs.setCurrentWidget(self.collection))

        costume_page=QScrollArea();costume_page.setWidgetResizable(True);costume_page.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.costume_page=costume_page;costume_body=QWidget();costume_page.setWidget(costume_body)
        cl=QHBoxLayout(costume_body);cl.setContentsMargins(0,1,2,2);cl.setSpacing(16)
        fitting,fitting_layout=card();cl.addWidget(fitting,2)
        self.preview=Mascot(180);self.preview.frame_index=24;fitting_layout.addWidget(self.preview,alignment=Qt.AlignmentFlag.AlignCenter)
        self.frame=GrowthCombo();self.frame.setAccessibleName('衣装を確認する動作')
        for n in range(28):self.frame.addItem(frame_caption(n),n)
        self.frame.setCurrentIndex(24);self.frame.currentIndexChanged.connect(self.preview_frame);fitting_layout.addWidget(self.frame);fitting_layout.addStretch()
        controls,controls_layout=card();cl.addWidget(controls,3)
        controls_layout.addWidget(text_label('衣装を組み合わせる','growthSection'))
        form=QFormLayout();form.setSpacing(12);controls_layout.addLayout(form);self.slots={}
        for slot,name in (('head','頭'),('body','体'),('accessory','アクセサリー')):
            combo=GrowthCombo();combo.setAccessibleName(name+'の試着');self.slots[slot]=combo;form.addRow(name,combo)
            combo.currentIndexChanged.connect(lambda _,s=slot:self.equip(s))
        self.apply_equipment=QPushButton('この組み合わせを装着');self.apply_equipment.setObjectName('growthPrimary');self.apply_equipment.clicked.connect(self.save_equipment);controls_layout.addWidget(self.apply_equipment)
        reset=QPushButton('装着中に戻す');reset.clicked.connect(self.reset_equipment);controls_layout.addWidget(reset)
        self.trial_status=text_label();controls_layout.addWidget(self.trial_status)
        controls_layout.addWidget(text_label('対応していない動作では衣装を非表示にします。'));controls_layout.addStretch()
        tabs.addTab(costume_page,'衣装');costume_button.clicked.connect(lambda:tabs.setCurrentWidget(costume_page))
        self.packs=QTreeWidget();self.packs.setHeaderLabels(['パック','状態']);self.packs.setRootIsDecorated(False);tabs.addTab(self.packs,'コンテンツ')

        self.status=text_label('','growthError');self.status.hide();layout.addWidget(self.status)
        footer=QHBoxLayout();layout.addLayout(footer)
        footer.addWidget(text_label('Yohaku  /  育成と装い'));footer.addStretch()
        reload_button=QPushButton('再読み込み');reload_button.setToolTip('追加・編集したコンテンツパックを再読み込みします。');reload_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload));reload_button.clicked.connect(service.reload);footer.addWidget(reload_button)
        edit=QPushButton('コンテンツを編集');edit.setToolTip('独立したコンテンツエディタを開きます。');edit.clicked.connect(service.open_editor);footer.addWidget(edit)
        self.refresh()

    def preview_frame(self): self.preview.frame_index=self.frame.currentData();self.preview.update()

    def refresh(self):
        service=self.service;character=self.character.currentData();p=service.engine.progress(character)
        config=service.engine.catalog.config
        threshold=config['level_thresholds'][p['level']] if config and p['level']<len(config['level_thresholds']) else None
        self.hero_name.setText(CHARACTERS[character]);self.level_badge.setText(f'Lv.{p["level"]}')
        self.exp_value.setText(f'{p["exp"]:g}'+(f' / {threshold:g} EXP' if threshold is not None else ' EXP'))
        if config:
            remaining=max(0,math.ceil(config['exp_interval_seconds']-p['exp_seconds']))
            self.summary.setText(f'次のEXP獲得まで あと{remaining//60}分{remaining%60:02}秒')
            self.summary.setToolTip('このキャラを常駐キャラに選んでいる間に進みます。EXPは一定間隔でまとめて獲得し、スリープ中は停止します。'+('ロック中も加算する設定です。' if config['count_locked'] else 'ロック中も停止します。'))
        else:self.summary.setText('EXPの計測は停止中です。コンテンツの設定をご確認ください。')
        self.exp_bar.setVisible(threshold is not None)
        if threshold is not None:
            base=config['level_thresholds'][p['level']-1]
            self.exp_bar.setValue(round(max(0,min(1,(p['exp']-base)/(threshold-base)))*1000))
        self.refresh_home(character,p,threshold)
        self.collection.refresh(character)
        has_error=bool(getattr(service,'error','') or service.store.error or service.engine.catalog.errors)
        self.status.setVisible(has_error)
        self.status.setText(service.error_text() if has_error else '')
        selected=self.trophies.currentItem()
        selected=selected.data(0,Qt.ItemDataRole.UserRole) if selected is not None else None
        scroll=self.trophies.verticalScrollBar().value()
        blocked=self.trophies.blockSignals(True);self.trophies.clear();known=set()
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
        if self.trophies.currentItem() is None:self.trophies.setCurrentItem(self.trophies.topLevelItem(0))
        self.trophies.blockSignals(blocked);self.trophies.verticalScrollBar().setValue(scroll);self.show_trophy_detail()
        catalog=service.engine.catalog
        if getattr(self,'pack_signature',None)!=id(catalog):
            self.pack_signature=id(catalog);self.packs.clear()
            for key,pack in catalog.packs.items():
                self.packs.addTopLevelItem(QTreeWidgetItem([pack['document']['name']+' / '+key,'有効' if pack['document']['enabled'] else '無効']))
            for error in catalog.errors:self.packs.addTopLevelItem(QTreeWidgetItem(['読み込みの問題',error]))
        signature=(id(catalog),character,tuple(sorted(p['equipped'].items())),tuple(p['unlocked']))
        same_character=getattr(self,'trial_character',None)==character
        if signature==getattr(self,'costume_signature',None):return
        if same_character and any(w.view().isVisible() for w in self.slots.values()):return
        if not same_character:
            for combo in self.slots.values():combo.hidePopup()
        preserve=same_character and getattr(self,'equipment_base',None)==p['equipped']
        trial={slot:combo.currentData() for slot,combo in self.slots.items()} if preserve else dict(p['equipped'])
        self.trial_character=character;self.equipment_base=dict(p['equipped'])
        self.costume_signature=signature;self.preview.set_character(character)
        removed_trial=False
        for slot,combo in self.slots.items():
            combo.blockSignals(True);combo.clear();combo.addItem('装着しない','')
            for key,item in service.engine.catalog.items['costumes'].items():
                if item['slot']==slot and character in item['characters'] and key in p['unlocked']:combo.addItem(item['name'],key)
            equipped=p['equipped'].get(slot,'')
            if equipped and combo.findData(equipped)<0:combo.addItem('未読込の衣装（記録保持）',equipped)
            candidate=trial.get(slot,'')
            if combo.findData(candidate)<0:candidate=equipped;removed_trial=True
            combo.setCurrentIndex(max(0,combo.findData(candidate)));combo.blockSignals(False)
        self.equip(None)
        if removed_trial:self.trial_status.setText('再読み込みで使えなくなった試着候補を、装着記録に戻しました。')

    def equip(self,slot):
        character=self.character.currentData();p=self.service.engine.progress(character)
        trial={slot:combo.currentData() for slot,combo in self.slots.items() if combo.currentData()}
        preview=dict(p,equipped=trial);renderer=CostumeRenderer();renderer.configure(self.service.engine.catalog,preview,character)
        self.preview.costumes=renderer;self.preview.update()
        changed=trial!=p['equipped'];self.apply_equipment.setEnabled(changed and self.service.store.writable)
        self.trial_status.setText('試着中です。「装着」を押すまで常駐キャラと保存データは変わりません。' if changed else '装着中の組み合わせを表示しています。')

    def save_equipment(self):
        equipped={slot:combo.currentData() for slot,combo in self.slots.items() if combo.currentData()}
        try:self.service.engine.equip_set(self.character.currentData(),equipped)
        except (OSError,ValueError):self.trial_status.setText('装着内容を保存できませんでした。試着内容は残しています。保存先と成長データをご確認ください。');return
        self.service.apply_costumes();self.costume_signature=None;self.refresh()
        self.trial_status.setText('装着内容を保存しました。')

    def reset_equipment(self):
        self.trial_character=None;self.costume_signature=None;self.refresh()

    def try_costume(self,key):
        item=self.service.engine.catalog.items['costumes'].get(key)
        if not item:return
        combo=self.slots[item['slot']];index=combo.findData(key)
        if index<0:return
        self.tabs.setCurrentWidget(self.costume_page);combo.setCurrentIndex(index)

    def refresh_home(self,character,p,threshold):
        catalog=self.service.engine.catalog
        self.next_level.setText(f'次のレベルまで あと{max(0,threshold-p["exp"]):g} EXP' if threshold is not None else '現在のレベル上限に到達' if catalog.config else '育成コンテンツの設定を確認してください。')
        rows=collection_rows(catalog,p,character)
        counts={kind:sum(row['unlocked'] for row in rows if row['kind']==kind) for kind in ('lines','events','costumes')}
        hours,minutes=divmod(int(p['seconds']//60),60)
        self.metrics['time'].value.setText((f'{hours:,}時間' if hours else '')+(f'{minutes}分' if minutes or not hours else ''))
        self.metrics['time'].hint.setText('このキャラとの累計')
        self.metrics['speech'].value.setText(f'{counts["lines"]+counts["events"]:,} 種類')
        self.metrics['speech'].hint.setText(f'会話 {counts["lines"]} ・ 演出 {counts["events"]}')
        self.metrics['costumes'].value.setText(f'{counts["costumes"]:,} 点')
        self.metrics['costumes'].hint.setText('全'+str(sum(row['kind']=='costumes' for row in rows))+'点のうち解放済み')
        self.metrics['trophies'].value.setText(f'{len(p["trophies"]):,} 個');self.metrics['trophies'].hint.setText('これまでに取得')
        clothing=[]
        for slot,title in (('head','頭'),('body','体'),('accessory','アクセサリー')):
            key=p['equipped'].get(slot);name=catalog.items['costumes'].get(key,{}).get('name','記録を保持した衣装') if key else '装着なし'
            clothing.append(title+'　'+name)
        self.equipment_summary.setText('\n'.join(clothing))
        upcoming=next_unlocks(catalog,p,character)
        self.reward_level.setVisible(bool(upcoming))
        if upcoming:
            self.reward_level.setText(f'Lv.{upcoming[0]["level"]}')
            names='\n'.join('・'+row['name'] for row in upcoming[:5])
            if len(upcoming)>5:names+=f'\nほか{len(upcoming)-5}件'
            self.next_reward.setText(names)
        else:self.next_reward.setText('現在のパックには、この先の解放予定はありません。\nコンテンツエディタで追加できます。' if catalog.config else '有効な育成パックが読み込めると表示します。')
        signature=(id(catalog),character,tuple(sorted(p['equipped'].items())),tuple(p['unlocked']))
        if signature!=getattr(self,'home_signature',None):
            self.home_signature=signature;self.home_preview.set_character(character);self.portrait_stage.set_character(character)
            renderer=CostumeRenderer();renderer.configure(catalog,p,character);self.home_preview.costumes=renderer;self.home_preview.update()

    def show_trophy_detail(self,*_):
        current=self.trophies.currentItem()
        if current is None:set_detail(self.trophy_detail,'トロフィーを選ぶと条件と記録を確認できます。');return
        character=self.character.currentData();host=self.service.host;engine=self.service.engine
        active=character==host.settings.character
        metrics=dict(host.engine.context) if active and host.settings.context_enabled else {}
        if active and host.settings.context_enabled and engine.last_character==character:metrics['growth_active_minutes']=engine.active_seconds/60
        text=trophy_text(current.data(0,Qt.ItemDataRole.UserRole),engine.catalog,engine.progress(character),character,
                         datetime.now().astimezone(),metrics,self.service.calendar(),self.service.work(),active)
        set_detail(self.trophy_detail,text)


class GrowthService:
    def __init__(self,host):
        self.host=host;self.window=None;self.error='';self.closed=False;self.notifications=[]
        self.content_root=host.path/'content';self.store=GrowthStore(host.path/'growth.json')
        try:seed_content(self.content_root);seed_examples(self.content_root)
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
