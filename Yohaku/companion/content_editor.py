"""Independent Japanese GUI for declarative packs, including layer previews."""
from copy import deepcopy
from datetime import date
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import time

from PySide6.QtCore import QDate, QLockFile, Qt, QTime, QTimer
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDateEdit, QDialog, QDialogButtonBox,
    QDoubleSpinBox, QFileDialog, QFormLayout, QHBoxLayout, QInputDialog, QLabel, QLineEdit,
    QListWidget, QMainWindow, QMessageBox, QPlainTextEdit, QPushButton, QScrollArea,
    QSpinBox, QSplitter, QStackedWidget, QTabWidget, QTimeEdit, QVBoxLayout, QWidget)

from .characters import CHARACTERS
from .costumes import CostumeRenderer
from .dialogue import VOICE_NAMES
from .growth_content import (CONDITIONS, EXPRESSIONS, KINDS, NUMERIC, ContentError, asset_path,
    atomic_json, identifier, inspect_pack, load_catalog, read_json, read_json_snapshot, require, seed_content,
    validate_condition, validate_config)
from .metrics import METRICS
from .growth_editor_widgets import FramePicker,RewardPicker,frame_caption

KIND_NAMES = dict(lines='追加セリフ',events='演出',trophies='トロフィー',costumes='衣装',rewards='レベル報酬')


def spin(value,low,high,decimals=2):
    widget=QDoubleSpinBox();widget.setRange(low,high);widget.setDecimals(decimals);widget.setValue(value);return widget


def combo(options,value=None):
    widget=QComboBox()
    for key,label in options:widget.addItem(label,key)
    widget.setCurrentIndex(max(0,widget.findData(value)));return widget


def action(text,callback):
    b=QPushButton(text);b.clicked.connect(callback);return b


def sample_item(kind,identifier_value='new_item'):
    item=dict(id=identifier_value,name='新しい'+KIND_NAMES[kind],enabled=True,level=1,characters=['A','B','E'])
    if kind in ('lines','events','trophies'):
        item.update(conditions=[],expression='happy',texts={'*':'一緒に過ごした記録が増えました。'},exp=0)
    if kind in ('lines','events'):item.update(probability=.05,cooldown_minutes=60,daily_limit=1,priority=0)
    if kind=='events':item['effect']='pose'
    if kind=='trophies':item.update(hidden=False,description='PCの利用状況に基づく記録です。',icon='')
    if kind=='costumes':item.update(slot='accessory',layer='accessory',variants=[])
    if kind=='rewards':item['unlock']=[]
    return item


class ConditionDialog(QDialog):
    def __init__(self,parent=None,condition=None):
        super().__init__(parent);self.setWindowTitle('条件を編集');self.resize(500,300)
        self.original=condition or dict(type='total_minutes',op='>=',value=60)
        outer=QVBoxLayout(self);self.kind=combo(CONDITIONS.items(),self.original['type']);outer.addWidget(self.kind)
        self.container=QWidget();self.form=QFormLayout(self.container);outer.addWidget(self.container)
        self.status=QLabel();self.status.setWordWrap(True);outer.addWidget(self.status)
        controls=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        controls.accepted.connect(self.accept);controls.rejected.connect(self.reject);outer.addWidget(controls)
        self.kind.currentIndexChanged.connect(self.build);self.build()

    def build(self):
        while self.form.rowCount():self.form.removeRow(0)
        c=self.original if self.kind.currentData()==self.original['type'] else {};kind=self.kind.currentData();self.fields={}
        if kind in NUMERIC:
            self.fields['op']=combo((('>=','以上'),('<=','以下'),('==','等しい')),c.get('op','>='));self.form.addRow('比較',self.fields['op'])
            self.fields['value']=spin(c.get('value',1),-1e9 if kind=='metric' else 0,1e9);self.form.addRow('値',self.fields['value'])
        if kind=='metric':self.fields['metric']=combo(METRICS.items(),c.get('metric'));self.form.addRow('集計値',self.fields['metric'])
        if kind=='event_count':self.fields['event_id']=QLineEdit(c.get('event_id',''));self.form.addRow('演出ID（pack:item）',self.fields['event_id'])
        if kind=='day_kind':self.fields['value']=combo((('business','営業日'),('holiday','休日')),c.get('value'));self.form.addRow('日区分',self.fields['value'])
        if kind in ('time_range','date_range'):
            for key,title in (('start','開始'),('end','終了')):
                if kind=='time_range':
                    w=QTimeEdit(QTime.fromString(c.get(key,'08:30' if key=='start' else '17:30'),'HH:mm'));w.setDisplayFormat('HH:mm')
                else:
                    w=QDateEdit(QDate.fromString(c.get(key,date.today().isoformat()),'yyyy-MM-dd'));w.setCalendarPopup(True);w.setDisplayFormat('yyyy-MM-dd')
                self.fields[key]=w;self.form.addRow(title,w)

    def value(self):
        result={'type':self.kind.currentData()}
        for key,w in self.fields.items():
            result[key]=(w.currentData() if isinstance(w,QComboBox) else w.value() if isinstance(w,QDoubleSpinBox) else
                         w.time().toString('HH:mm') if isinstance(w,QTimeEdit) else w.date().toString('yyyy-MM-dd') if isinstance(w,QDateEdit) else w.text())
        return validate_condition(result)

    def accept(self):
        try:self.value()
        except ValueError as e:self.status.setText(str(e));return
        super().accept()


class ContentEditor(QMainWindow):
    def __init__(self,content_root):
        super().__init__();self.root=Path(content_root);seed_content(self.root)
        self.document=None;self.folder=None;self.original_hash=None;self.current_index=-1;self.current_kind='lines';self.filling=False;self.dirty=False
        self.preview_timer=QTimer(self);self.preview_timer.setInterval(33)
        self.preview_timer.timeout.connect(self.advance_preview)
        self.setWindowTitle('Yohaku コンテンツエディタ');self.resize(1140,800)
        root=QWidget();self.setCentralWidget(root);outer=QVBoxLayout(root)
        header=QHBoxLayout();outer.addLayout(header);self.pack_combo=QComboBox();header.addWidget(self.pack_combo,1)
        header.addWidget(action('新しいパック',self.new_pack));header.addWidget(action('パックを取り込む',self.import_pack))
        header.addWidget(action('保存内容を再読み込み',self.reload_pack))
        self.pack_combo.currentIndexChanged.connect(self.open_selected_pack)
        self.tabs=QTabWidget();outer.addWidget(self.tabs,1)
        content=QWidget();layout=QVBoxLayout(content);self.tabs.addTab(content,'コンテンツ')
        meta=QHBoxLayout();layout.addLayout(meta);self.pack_name=QLineEdit();self.pack_enabled=QCheckBox('このパックを有効にする')
        meta.addWidget(QLabel('パック名'));meta.addWidget(self.pack_name,1);meta.addWidget(self.pack_enabled)
        splitter=QSplitter();layout.addWidget(splitter,1);left=QWidget();ll=QVBoxLayout(left)
        self.kind=combo([(k,KIND_NAMES[k]) for k in KINDS],'lines');ll.addWidget(self.kind)
        self.items=QListWidget();ll.addWidget(self.items,1)
        row=QHBoxLayout();ll.addLayout(row)
        row.addWidget(action('＋追加',self.add_item));row.addWidget(action('複製',self.duplicate));row.addWidget(action('削除',self.delete_item))
        splitter.addWidget(left);scroll=QScrollArea();scroll.setWidgetResizable(True);self.details=QWidget();self.form=QFormLayout(self.details);scroll.setWidget(self.details);splitter.addWidget(scroll)
        self.preview_panel=QWidget(objectName='card');self.preview_panel.setMinimumWidth(280)
        self.preview_layout=QVBoxLayout(self.preview_panel);splitter.addWidget(self.preview_panel);splitter.setSizes([230,570,310]);self.preview_panel.hide()
        self.config_page=QWidget();self.config_form=QFormLayout(self.config_page);self.tabs.addTab(self.config_page,'成長の全体設定（base）')
        self.status=QLabel();self.status.setWordWrap(True);outer.addWidget(self.status)
        footer=QHBoxLayout();outer.addLayout(footer)
        footer.addWidget(action('検証',self.check));footer.addWidget(action('保存',self.save));footer.addWidget(QLabel('保存後、Yohakuの「パックを再読み込み」で反映します。'),1)
        self.kind.currentIndexChanged.connect(self.change_kind);self.items.currentRowChanged.connect(self.select_item)
        self.refresh_packs()

    def refresh_packs(self,select=None):
        self.pack_combo.blockSignals(True);self.pack_combo.clear()
        for folder in sorted(self.root.iterdir()):
            if folder.is_dir() and not folder.name.startswith('.') and (folder/'pack.json').is_file():self.pack_combo.addItem(folder.name,str(folder))
        if select:self.pack_combo.setCurrentIndex(max(0,self.pack_combo.findData(str(select))))
        else:self.pack_combo.setCurrentIndex(max(0,self.pack_combo.findData(str(self.root/'base'))))
        self.pack_combo.blockSignals(False);self.open_selected_pack()

    def reload_pack(self):
        return self.open_selected_pack(force=True)

    def open_selected_pack(self, _index=None, *, force=False):
        folder=self.pack_combo.currentData()
        if not folder:return
        if self.document is not None and self.folder==Path(folder) and not force:return
        if self.document is not None and self.changed():
            answer=QMessageBox.question(self,'未保存の編集','未保存の編集を破棄して保存内容を読み込みますか？')
            if answer!=QMessageBox.StandardButton.Yes:
                self.pack_combo.blockSignals(True);self.pack_combo.setCurrentIndex(self.pack_combo.findData(str(self.folder)));self.pack_combo.blockSignals(False);return
        try:
            document,digest=read_json_snapshot(Path(folder)/'pack.json');_,errors=inspect_pack(document,Path(folder))
            require(not errors,'このパックには不正な項目があります。\n'+'\n'.join(errors[:10]))
        except (OSError,ValueError,TypeError) as e:
            self.status.setText(str(e))
            if self.folder is not None:
                self.pack_combo.blockSignals(True);self.pack_combo.setCurrentIndex(self.pack_combo.findData(str(self.folder)));self.pack_combo.blockSignals(False)
            return
        self.folder=Path(folder);self.document=document;self.saved_document=deepcopy(document)
        self.original_hash=digest
        self.current_index=-1;self.current_kind=self.kind.currentData();self.pack_name.setText(document['name']);self.pack_enabled.setChecked(document['enabled']);self.dirty=False
        self.build_config();self.fill_list();self.status.setText('ID: '+document['id']+' ／ '+str(self.folder))

    def changed(self):
        self.flush();return self.document!=self.saved_document

    def fill_list(self,selected=0):
        self.items.blockSignals(True);self.items.clear()
        if self.document:
            for item in self.document[self.current_kind]:self.items.addItem(item.get('name','不正な項目') if isinstance(item,dict) else '不正な項目')
        self.items.blockSignals(False);self.current_index=-1
        if self.items.count():self.items.setCurrentRow(min(selected,self.items.count()-1));self.select_item(self.items.currentRow())
        else:self.build_item(None)

    def change_kind(self):
        self.flush();self.current_kind=self.kind.currentData();self.current_index=-1;self.fill_list()

    def select_item(self,index):
        if self.filling or index==self.current_index:return
        self.flush();self.current_index=index
        self.build_item(self.document[self.current_kind][index] if self.document and index>=0 else None)

    def clear_form(self):
        self.stop_preview()
        self.preview_panel.hide()
        while self.preview_layout.count():
            child=self.preview_layout.takeAt(0).widget()
            if child is not None:child.deleteLater()
        while self.form.rowCount():self.form.removeRow(0)

    def build_item(self,item):
        self.filling=True;self.clear_form();self.fields={}
        if not isinstance(item,dict):self.filling=False;return
        k=self.current_kind;self.editing=deepcopy(item)
        def field(key,title,widget):self.fields[key]=widget;self.form.addRow(title,widget);return widget
        field('id','固定ID（取得後は変更しない）',QLineEdit(str(item.get('id',''))))
        field('name','表示名',QLineEdit(str(item.get('name',''))))
        enabled=QCheckBox('有効');enabled.setChecked(item.get('enabled',True));field('enabled','状態',enabled)
        field('level','解放レベル',spin(item.get('level',1),1,100,0))
        charrow=QWidget();cr=QHBoxLayout(charrow);self.char_checks={}
        for key,name in CHARACTERS.items():
            c=QCheckBox(name);c.setChecked(key in item.get('characters',[]));cr.addWidget(c);self.char_checks[key]=c
        self.form.addRow('対象キャラ',charrow)
        if k in ('lines','events','trophies'):
            field('expression','表情',combo([(s,s) for s in EXPRESSIONS],item.get('expression')))
            field('exp','報酬EXP',spin(item.get('exp',0),0,100000))
            self.fields['exp'].setEnabled(k!='lines')
            text_tabs=QTabWidget();self.text_fields={}
            for voice in ('*',*VOICE_NAMES):
                w=QPlainTextEdit(item.get('texts',{}).get(voice,''));w.setMaximumHeight(130);self.text_fields[voice]=w;text_tabs.addTab(w,'共通' if voice=='*' else voice)
            self.form.addRow('性格別セリフ（空欄は共通）',text_tabs)
            self.conditions=deepcopy(item.get('conditions',[]));self.condition_list=QListWidget();self.condition_list.setMaximumHeight(120);self.form.addRow('すべて満たす条件（AND）',self.condition_list)
            buttons=QWidget();br=QHBoxLayout(buttons);br.addWidget(action('条件を追加',self.add_condition));br.addWidget(action('条件を編集',self.edit_condition));br.addWidget(action('条件を削除',self.delete_condition));self.form.addRow(buttons);self.refresh_conditions()
        if k in ('lines','events'):
            for key,title,value,lo,hi,dec in (('probability','抽選1回あたりの確率（0〜1）',.05,0,1,4),('cooldown_minutes','再発生しない時間（分）',60,1,525600,1),('daily_limit','1日の上限',1,1,100,0),('priority','優先度',0,0,100,0)):
                field(key,title,spin(item.get(key,value),lo,hi,dec))
            if k=='events':field('effect','演出',combo((('pose','表情のみ'),('sparkle','小さなきらめき')),item.get('effect')))
        if k=='trophies':
            field('description','説明',QLineEdit(item.get('description','')))
            hidden=QCheckBox('未達成時は？？？で表示');hidden.setChecked(item.get('hidden',False));field('hidden','秘密',hidden)
            field('icon','アイコン（任意）',QLineEdit(item.get('icon','')))
            self.form.addRow(action('アイコン画像を選ぶ',lambda:self.choose_image(self.fields['icon'])))
        if k=='rewards':
            field('unlock','解放するID（1行1件 pack:item）',QPlainTextEdit('\n'.join(item.get('unlock',[]))))
            self.form.addRow(action('名前から解放するものを選ぶ',self.choose_rewards))
        if k=='costumes':
            field('slot','装備枠',combo((('head','頭'),('body','体'),('accessory','アクセサリー')),item.get('slot')))
            field('layer','描画順',combo((('back','本体の後ろ'),('front','本体の前'),('accessory','一番手前')),item.get('layer')))
            self.variant_widgets=[];self.variants_container=QWidget();self.variants_layout=QVBoxLayout(self.variants_container);self.form.addRow(self.variants_container)
            for v in item.get('variants',[]):self.add_variant(v)
            self.form.addRow(action('＋対応画像・フレームを追加',lambda:self.add_variant()))
            from .ui import Mascot
            self.preview_panel.show();self.preview_layout.addWidget(QLabel('衣装プレビュー'))
            self.preview=Mascot(240);self.preview.frame_index=24;self.preview_layout.addWidget(self.preview,alignment=Qt.AlignmentFlag.AlignHCenter)
            self.preview_character=combo(CHARACTERS.items(),item['characters'][0]);self.preview_layout.addWidget(self.preview_character)
            self.preview_frame=combo([(n,frame_caption(n)) for n in range(28)],24);self.preview_layout.addWidget(self.preview_frame)
            self.preview_frame.currentIndexChanged.connect(self.select_preview_frame)
            self.preview_character.currentIndexChanged.connect(self.preview_character_changed)
            self.preview_flipped=QCheckBox('反対向きで確認（通常・歩行）');self.preview_layout.addWidget(self.preview_flipped)
            self.preview_flipped.toggled.connect(lambda value:self.flip_preview(value))
            self.preview_mode=combo((('walk','歩行（16〜23）'),('front','正面とまばたき（24〜25）'),('expressions','通常・表情（0〜15）')),'walk')
            self.preview_layout.addWidget(QLabel('連続プレビュー'));self.preview_layout.addWidget(self.preview_mode)
            self.preview_mode.currentIndexChanged.connect(self.stop_preview)
            self.play_button=action('再生',self.toggle_preview);self.preview_layout.addWidget(self.play_button)
            self.preview_layout.addWidget(action('現在の入力でプレビュー',self.update_preview));self.preview_layout.addStretch()
        self.filling=False
        if k=='costumes' and item.get('variants'):self.update_preview()

    def add_variant(self,value=None):
        v=value or dict(character='A',frames=[24,25],image='',x=0,y=0,scale=1)
        widget=QWidget();form=QFormLayout(widget);fields={}
        for key,title,w in (('character','キャラ',combo(CHARACTERS.items(),v['character'])),('frames','フレーム（カンマ区切り）',QLineEdit(','.join(map(str,v['frames'])))),('image','画像',QLineEdit(v['image'])),('x','X',spin(v['x'],-2048,2048)),('y','Y',spin(v['y'],-2048,2048)),('scale','倍率',spin(v['scale'],.05,8))):fields[key]=w;form.addRow(title,w)
        form.addRow(action('画像を選ぶ',lambda:self.choose_image(fields['image'])))
        form.addRow(action('対応フレームを選ぶ',lambda:self.choose_frames(fields['frames'])))
        fields['removed']=QCheckBox('この対応画像を削除する');form.addRow(fields['removed'])
        self.variant_widgets.append(fields);self.variants_layout.addWidget(widget)

    def choose_image(self,field):
        filename,_=QFileDialog.getOpenFileName(self,'透過PNGを選択',str(self.folder),'PNG (*.png)')
        if not filename:return
        source=Path(filename)
        try:
            asset_path(source.parent,source.name)
            folder=self.folder/'images';folder.mkdir(exist_ok=True)
            name=hashlib.sha256(source.read_bytes()).hexdigest()[:20]+'.png';target=folder/name
            if not target.exists():shutil.copyfile(source,target)
            field.setText('images/'+name)
        except (OSError,ValueError) as e:self.status.setText(str(e))

    def choose_frames(self,field):
        selected=[int(s.strip()) for s in field.text().split(',') if s.strip().isdigit() and 0<=int(s.strip())<=27]
        dialog=FramePicker(selected,self)
        if dialog.exec():field.setText(','.join(map(str,dialog.selected())))

    def reward_options(self):
        catalog=load_catalog(self.root)
        options={key:KIND_NAMES[kind]+' / '+item['name'] for kind in ('costumes','lines','events')
                 for key,item in catalog.items[kind].items() if not key.startswith(self.document['id']+':')}
        # Include unsaved content in this pack without requiring a save cycle.
        for kind in ('costumes','lines','events'):
            for item in self.document[kind]:
                if isinstance(item,dict) and item.get('enabled') and identifier(item.get('id')):
                    options[self.document['id']+':'+item['id']]=KIND_NAMES[kind]+' / '+str(item.get('name',item['id']))
        return options

    def choose_rewards(self):
        dialog=RewardPicker(self.reward_options(),self.fields['unlock'].toPlainText().splitlines(),self)
        if dialog.exec():self.fields['unlock'].setPlainText('\n'.join(dialog.selected()))

    def item_value(self):
        result=deepcopy(self.editing)
        for key,w in self.fields.items():
            result[key]=(w.currentData() if isinstance(w,QComboBox) else w.isChecked() if isinstance(w,QCheckBox) else
                         (int(w.value()) if key in ('level','daily_limit','priority') else w.value()) if isinstance(w,QDoubleSpinBox) else
                         w.toPlainText().splitlines() if key=='unlock' else w.text())
        result['characters']=[c for c,w in self.char_checks.items() if w.isChecked()]
        if self.current_kind in ('lines','events','trophies'):
            result['conditions']=deepcopy(self.conditions);result['texts']={v:w.toPlainText() for v,w in self.text_fields.items() if w.toPlainText().strip()}
        if self.current_kind=='costumes':
            result['variants']=[]
            for fields in self.variant_widgets:
                if fields['removed'].isChecked():continue
                frames=fields['frames'].text().split(',')
                # Keep an invalid draft as text so save validation can report it.
                result['variants'].append(dict(character=fields['character'].currentData(),frames=[int(s.strip()) if s.strip().isdigit() else s for s in frames],image=fields['image'].text(),x=fields['x'].value(),y=fields['y'].value(),scale=fields['scale'].value()))
        return result

    def flush(self):
        if self.filling or self.document is None:return
        if self.current_index>=0 and self.fields:self.document[self.current_kind][self.current_index]=self.item_value()
        self.document['name']=self.pack_name.text();self.document['enabled']=self.pack_enabled.isChecked()
        if self.document['id']=='base' and hasattr(self,'config_fields'):
            c=self.document['config']
            for key,w in self.config_fields.items():c[key]=w.currentData() if isinstance(w,QComboBox) else w.isChecked() if isinstance(w,QCheckBox) else w.value()
            c['level_thresholds']=[w.value() for w in self.level_values]

    def add_item(self):
        if self.document is None:return
        self.flush();ids={i.get('id') for kind in KINDS for i in self.document[kind] if isinstance(i,dict)};n=1
        while 'item_'+str(n) in ids:n+=1
        self.document[self.current_kind].append(sample_item(self.current_kind,'item_'+str(n)));self.fill_list(len(self.document[self.current_kind])-1)

    def duplicate(self):
        if self.current_index<0:return
        self.flush();item=deepcopy(self.document[self.current_kind][self.current_index]);ids={i.get('id') for k in KINDS for i in self.document[k] if isinstance(i,dict)}
        n=1
        while 'copy_'+str(n) in ids:n+=1
        item['id']='copy_'+str(n);item['name']+=' のコピー';self.document[self.current_kind].append(item);self.fill_list(len(self.document[self.current_kind])-1)

    def delete_item(self):
        if self.current_index<0:return
        self.flush();del self.document[self.current_kind][self.current_index];self.current_index=-1;self.fill_list()

    def refresh_conditions(self):
        self.condition_list.clear()
        for c in self.conditions:self.condition_list.addItem(CONDITIONS.get(c.get('type'),'未知')+' / '+' '.join(str(v) for k,v in c.items() if k!='type'))

    def add_condition(self):
        d=ConditionDialog(self)
        if d.exec():self.conditions.append(d.value());self.refresh_conditions()

    def edit_condition(self):
        n=self.condition_list.currentRow()
        if n<0:return
        d=ConditionDialog(self,self.conditions[n])
        if d.exec():self.conditions[n]=d.value();self.refresh_conditions()

    def delete_condition(self):
        n=self.condition_list.currentRow()
        if n>=0:del self.conditions[n];self.refresh_conditions()

    def build_config(self):
        while self.config_form.rowCount():self.config_form.removeRow(0)
        self.config_fields={};self.level_values=[]
        if self.document['id']!='base':self.config_form.addRow(QLabel('全体設定はbaseパックで編集します。'));return
        c=self.document['config']
        for key,title,lo,hi in (('exp_per_hour','1時間のEXP（仮値60）',0,10000),('exp_interval_seconds','EXP獲得・保存の間隔（秒・初期300）',5,3600),('event_interval_seconds','抽選機会の間隔（秒）',30,3600),('idle_threshold_seconds','操作ありの許容アイドル（秒）',5,600)):
            w=spin(c[key],lo,hi);self.config_fields[key]=w;self.config_form.addRow(title,w)
        w=combo((('calendar','暦日'),('business','営業日（会社カレンダー）')),c['streak_mode']);self.config_fields['streak_mode']=w;self.config_form.addRow('連続起動日数',w)
        w=QCheckBox('Windowsロック中も起動時間に含める');w.setChecked(c['count_locked']);self.config_fields['count_locked']=w;self.config_form.addRow(w)
        self.level_list=QWidget();self.level_form=QFormLayout(self.level_list)
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(self.level_list);scroll.setMinimumHeight(220);self.config_form.addRow('レベル別の累計必要EXP',scroll)
        for value in c['level_thresholds']:self.add_level(value)
        row=QWidget();rl=QHBoxLayout(row);rl.addWidget(action('＋レベルを追加',lambda:self.add_level()));rl.addWidget(action('最後のレベルを削除',self.remove_level));self.config_form.addRow(row)
        self.config_form.addRow(QLabel('スリープ・終了中は加算しません。数値変更で獲得済みレベルやアイテムを取り消すことはありません。'))

    def add_level(self,value=None):
        if len(self.level_values)>=100:return
        if value is None:value=(self.level_values[-1].value()+60*len(self.level_values)) if self.level_values else 0
        w=spin(value,0,1e12);self.level_values.append(w);self.level_form.addRow('Lv.'+str(len(self.level_values)),w)

    def remove_level(self):
        if len(self.level_values)>2:self.level_values.pop();self.level_form.removeRow(self.level_form.rowCount()-1)

    def update_preview(self):
        try:
            from .growth_content import validate_item, Catalog
            item=validate_item('costumes',self.item_value(),self.folder);item.update(key='preview',root=self.folder)
            character=self.preview_character.currentData();self.preview.set_character(character);self.preview.frame_index=self.preview_frame.currentData()
            catalog=Catalog();catalog.items['costumes']['preview']=item
            renderer=CostumeRenderer();renderer.configure(catalog,dict(equipped={item['slot']:'preview'},unlocked=['preview']),character)
            self.preview.costumes=renderer;self.preview.flipped=self.preview_flipped.isChecked();self.preview.update();self.status.setText('現在の入力でプレビューしています。保存はまだ行っていません。');return True
        except (OSError,ValueError,TypeError) as e:self.status.setText(str(e));return False

    def stop_preview(self,*_):
        self.preview_timer.stop()
        if hasattr(self,'play_button'):
            # The button belongs to the old form until clear_form completes.
            try:self.play_button.setText('再生')
            except RuntimeError:pass

    def select_preview_frame(self,*_):
        self.stop_preview();self.preview.previous_frame=None
        self.preview.frame_index=self.preview_frame.currentData();self.preview.update()

    def flip_preview(self,value):self.preview.flipped=value;self.preview.update()

    def preview_character_changed(self,*_):
        self.stop_preview();self.update_preview()

    def toggle_preview(self):
        if self.preview_timer.isActive():self.stop_preview();return
        if not self.update_preview():return
        self.preview_sequence={'walk':tuple(range(16,24)),'front':(24,25),'expressions':tuple(range(16))}[self.preview_mode.currentData()]
        self.preview_started=time.monotonic();self.play_button.setText('停止')
        self.preview.previous_frame=None;self.preview.frame_index=self.preview_sequence[0]
        self.preview_frame.blockSignals(True);self.preview_frame.setCurrentIndex(self.preview_frame.findData(self.preview_sequence[0]));self.preview_frame.blockSignals(False)
        self.preview_timer.start();self.preview.update()

    def advance_preview(self):
        if not self.preview_timer.isActive() or self.current_kind!='costumes':return
        period=.125 if self.preview_mode.currentData()=='walk' else .6
        frame=self.preview_sequence[int(max(0,time.monotonic()-self.preview_started)/period)%len(self.preview_sequence)]
        if frame!=self.preview.frame_index:
            self.preview.previous_frame=self.preview.frame_index;self.preview.previous_flipped=self.preview.flipped
            self.preview.frame_index=frame;self.preview.frame_changed_at=time.monotonic()
            self.preview_frame.blockSignals(True);self.preview_frame.setCurrentIndex(self.preview_frame.findData(frame));self.preview_frame.blockSignals(False)
        self.preview.update()

    def validate_document(self):
        require(self.document is not None,'有効なパックを開くか、新しいパックを作ってください。')
        self.flush();valid,errors=inspect_pack(self.document,self.folder)
        require(not errors,'\n'.join(errors[:20]))
        catalog=load_catalog(self.root);known={key:kind for kind,items in catalog.items.items() for key in items if not key.startswith(self.document['id']+':')}
        for kind,items in valid.items():
            for item in items:
                if item['enabled']:known[self.document['id']+':'+item['id']]=kind
        for kind,items in valid.items():
            for item in items:
                for ref in item.get('unlock',[]):require(known.get(ref) in ('costumes','lines','events'),item['id']+': 解放先のIDが不正です。')
                for c in item.get('conditions',[]):
                    if c['type']=='event_count':require(known.get(c['event_id'])=='events','演出IDの参照先が不正です。')
        return valid

    def check(self):
        try:self.validate_document();self.status.setText('検証に成功しました。保存で反映できます。');return True
        except (OSError,ValueError,TypeError,KeyError) as e:self.status.setText(str(e));return False

    def save(self):
        if not self.check():return False
        lock=QLockFile(str(self.folder/'.editor.lock'));lock.setStaleLockTime(30000)
        if not lock.tryLock(0):self.status.setText('別のエディタが保存中です。');return False
        try:
            path=self.folder/'pack.json';digest=hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
            require(digest==self.original_hash,'別の編集でパックが更新されました。「保存内容を再読み込み」で確認してください。未保存の編集はまだ残っています。')
            if path.exists():atomic_json(self.folder/'pack.json.bak',read_json(path))
            self.original_hash=atomic_json(path,self.document);self.saved_document=deepcopy(self.document)
            self.status.setText('保存しました。Yohakuの成長画面からパックを再読み込みしてください。');return True
        except (OSError,ValueError) as e:self.status.setText(str(e));return False
        finally:lock.unlock()

    def new_pack(self):
        name,ok=QInputDialog.getText(self,'新しいパック','パックID（英小文字・数字・_・-・.）')
        if not ok:return
        try:
            require(identifier(name),'IDの形式が不正です。');require(not (self.root/name).exists(),'同名のパックが存在します。')
            catalog=load_catalog(self.root);require(name not in catalog.packs,'同じパックIDが存在します。')
            folder=self.root/name;folder.mkdir()
            atomic_json(folder/'pack.json',dict(schema_version=1,id=name,name=name,enabled=True,**{k:[] for k in KINDS}));self.refresh_packs(folder)
        except (OSError,ValueError) as e:self.status.setText(str(e))

    def import_pack(self):
        filename,_=QFileDialog.getOpenFileName(self,'取り込むパックのpack.jsonを選ぶ',str(self.root),'JSON (*.json)')
        if not filename:return
        try:
            source=Path(filename);doc=read_json(source);valid,errors=inspect_pack(doc,source.parent);require(not errors,'\n'.join(errors[:10]))
            target=self.root/doc['id'];require(not target.exists() and doc['id'] not in load_catalog(self.root).packs,'同じIDのパックが存在します。')
            with tempfile.TemporaryDirectory(prefix='.import-',dir=self.root) as temp:
                staged=Path(temp)/doc['id'];staged.mkdir();images=set()
                for item in valid['costumes']:
                    images.update(v['image'] for v in item['variants'])
                images.update(i['icon'] for i in valid['trophies'] if i.get('icon'))
                for name in images:
                    original=asset_path(source.parent,name);dest=staged/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(original,dest)
                atomic_json(staged/'pack.json',doc);staged.rename(target)
            self.refresh_packs(target)
        except (OSError,ValueError,TypeError) as e:self.status.setText(str(e))

    def closeEvent(self,event):
        if self.document is not None and self.changed():
            answer=QMessageBox.question(self,'未保存の編集','保存せずに閉じますか？')
            if answer!=QMessageBox.StandardButton.Yes:event.ignore();return
        event.accept()

    def hideEvent(self,event):
        self.stop_preview();super().hideEvent(event)


def run(content_root=None):
    from .storage import data_directory
    from .ui import create_application,lock_data_directory
    app=create_application();app.setQuitOnLastWindowClosed(True)
    try:
        if content_root is None and not data_directory().exists():
            guard=lock_data_directory(data_directory());guard.unlock()
        editor=ContentEditor(Path(content_root) if content_root else data_directory()/'content')
    except (OSError,ValueError) as e:QMessageBox.critical(None,'Yohaku コンテンツエディタ',str(e));return 1
    editor.show()
    return app.exec()
