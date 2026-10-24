"""Structured local calendar, watched targets and topic preference controls."""
from copy import deepcopy
from datetime import datetime
from uuid import uuid4
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QCheckBox,QComboBox,QFileDialog,QFormLayout,QHBoxLayout,QMainWindow,
    QMessageBox,QPlainTextEdit,QSpinBox,QTabWidget,QTreeWidget,QTreeWidgetItem,QWidget)
from .context_options import ContextOptionsError
from .ui import box,button,label


class ContextOptionsEditor(QMainWindow):
    saved=Signal()

    def __init__(self,store,preferences,dialogue):
        super().__init__()
        self.store=store; self.preferences=preferences; self.dialogue=dialogue
        self.loading=True; self.topic_loading=True; self.dirty=False
        self.setWindowTitle('Yohaku — 休日・対象ファイル・話題の表示')
        self.resize(980,760); self.setMinimumSize(760,620)
        root=QWidget(objectName='panel'); self.setCentralWidget(root); layout=box(root,22,12)
        layout.addWidget(label('話しかける条件を、仕事に合わせる。','heading'))
        self.tabs=QTabWidget(); layout.addWidget(self.tabs,1)
        page=QWidget(); body=box(page,18,12)
        self.japanese=QCheckBox('日本の祝日・振替休日・国民の休日を除く（2000〜2099年）')
        body.addWidget(self.japanese)
        row=QHBoxLayout(); self.weekdays=[]
        for title in ('月','火','水','木','金','土','日'):
            check=QCheckBox(title); self.weekdays.append(check); row.addWidget(check)
        body.addLayout(row)
        body.addWidget(label('会社休日：YYYY-MM-DDを1行に1件。祝日の法改正・臨時休日もここで補えます。','muted',True))
        self.holidays=QPlainTextEdit(); self.holidays.setAccessibleName('会社休日の日付一覧');body.addWidget(self.holidays,1)
        body.addWidget(label('特別営業日：休日・祝日・営業曜日より優先します。YYYY-MM-DDを1行に1件。','muted',True))
        self.workdays=QPlainTextEdit();self.workdays.setAccessibleName('特別営業日の日付一覧');body.addWidget(self.workdays,1)
        body.addWidget(label('従来の「平日」は月〜金のままです。「営業日」の会話条件・登録通知で、このカレンダーを使います。','muted',True))
        self.tabs.addTab(page,'営業日・休日')
        page=QWidget();body=box(page,18,12)
        body.addWidget(label('登録した対象をファイル履歴の記録と照合します。フォルダーの中身は走査しません。利用するには履歴記録をオンにし、会話編集で対象と記録条件を選びます。','muted',True))
        self.targets=QTreeWidget();self.targets.setHeaderLabels(['管理用の名前','ファイル・フォルダーの保存先','種類'])
        self.targets.setRootIsDecorated(False);self.targets.setColumnWidth(0,180);self.targets.setColumnWidth(1,500)
        self.targets.setAccessibleName('会話条件に使う対象ファイルとフォルダー');body.addWidget(self.targets,1)
        row=QHBoxLayout()
        row.addWidget(button('ファイルを追加',lambda:self.add_target('file')))
        row.addWidget(button('フォルダーを追加',lambda:self.add_target('folder')))
        row.addWidget(button('選択を削除',self.remove_target));body.addLayout(row)
        body.addWidget(label('ダブルクリックで名前や保存先を編集できます。フォルダーは配下の保存先に一致する記録を合計します。「今日の記録にない」は実際の未使用を断定しません。','muted',True))
        self.tabs.addTab(page,'対象ファイル')
        page=QWidget();form=QFormLayout(page)
        self.gap=QSpinBox();self.gap.setRange(0,120);self.gap.setSuffix(' 分')
        form.addRow('この間隔以内なら連続会議',self.gap)
        form.addRow(label('会議時間は重複を除いて合計します。連続件数は現在または次の会議から数えます。部分取得や古い予定では判定しません。','muted',True))
        self.tabs.addTab(page,'会議')
        page=QWidget();body=box(page,18,14)
        body.addWidget(label('このタブは操作するとすぐ保存・反映します。会話文や元の発生条件は変更しません。','muted',True))
        self.topic=QComboBox();self.topic.setAccessibleName('表示を調整する話題');body.addWidget(self.topic)
        self.muted=QCheckBox('今日はこの話題を休む（翌日には自動で解除）')
        self.reduced=QCheckBox('この話題を減らす（同じ話題の間隔を2倍にする）')
        body.addWidget(self.muted);body.addWidget(self.reduced)
        body.addWidget(button('この話題の表示設定を戻す',self.reset_topic))
        self.topic_status=label('','muted',True);body.addWidget(self.topic_status);body.addStretch()
        self.tabs.addTab(page,'話題の表示')
        self.status=label('','muted',True);layout.addWidget(self.status)
        row=QHBoxLayout();row.addWidget(button('保存済みに戻す',self.revert));row.addStretch()
        row.addWidget(button('休日・対象・会議設定を保存して反映',self.save,'primary'));layout.addLayout(row)
        self.japanese.toggled.connect(self.mark_dirty)
        for check in self.weekdays:check.toggled.connect(self.mark_dirty)
        self.holidays.textChanged.connect(self.mark_dirty);self.workdays.textChanged.connect(self.mark_dirty)
        self.targets.itemChanged.connect(self.mark_dirty);self.gap.valueChanged.connect(self.mark_dirty)
        self.topic.currentIndexChanged.connect(self.load_topic)
        self.muted.toggled.connect(self.save_topic);self.reduced.toggled.connect(self.save_topic)
        self.revert()

    def mark_dirty(self,*_):
        if not self.loading:
            self.dirty=True;self.status.setText('編集中です。休日・対象・会議の設定は保存後に反映します。')

    def revert(self):
        self.loading=True
        data=self.store.data;calendar=data['calendar']
        self.japanese.setChecked(calendar['japanese_holidays'])
        for i,check in enumerate(self.weekdays):check.setChecked(i in calendar['weekdays'])
        self.holidays.setPlainText('\n'.join(calendar['holidays']));self.workdays.setPlainText('\n'.join(calendar['workdays']))
        self.targets.clear()
        for target in data['targets']:self.add_row(target)
        self.gap.setValue(data['consecutive_gap_minutes'])
        self.topic_loading=True; self.topic.clear()
        for rule in self.dialogue.data['rules']:
            if rule['trigger']=='auto':self.topic.addItem(rule['label'],rule['id'])
        self.loading=False;self.dirty=False;self.load_topic()
        self.status.setText(self.store.error or self.preferences.error or '休日・対象ファイル・会議の設定を変更できます。')

    def add_row(self,target):
        item=QTreeWidgetItem([target['label'],target['path'],'ファイル' if target['kind']=='file' else 'フォルダー'])
        item.setData(0,Qt.ItemDataRole.UserRole,target['id'])
        item.setFlags(item.flags()|Qt.ItemFlag.ItemIsEditable);self.targets.addTopLevelItem(item)

    def add_target(self,kind):
        if self.targets.topLevelItemCount()>=30:
            self.status.setText('対象は30件までです。');return
        path=QFileDialog.getOpenFileName(self,'対象ファイルを選択')[0] if kind=='file' else QFileDialog.getExistingDirectory(self,'対象フォルダーを選択')
        if path:
            from pathlib import PureWindowsPath
            self.add_row({'id':uuid4().hex,'label':PureWindowsPath(path).name or path,'path':path,'kind':kind});self.mark_dirty()

    def remove_target(self):
        for item in self.targets.selectedItems():self.targets.takeTopLevelItem(self.targets.indexOfTopLevelItem(item))
        self.mark_dirty()

    def candidate(self):
        data=deepcopy(self.store.data)
        data['calendar']={'japanese_holidays':self.japanese.isChecked(),'weekdays':[i for i,c in enumerate(self.weekdays) if c.isChecked()],
            'holidays':[x.strip() for x in self.holidays.toPlainText().splitlines() if x.strip()],
            'workdays':[x.strip() for x in self.workdays.toPlainText().splitlines() if x.strip()]}
        data['consecutive_gap_minutes']=self.gap.value();data['targets']=[]
        for i in range(self.targets.topLevelItemCount()):
            item=self.targets.topLevelItem(i)
            data['targets'].append({'id':item.data(0,Qt.ItemDataRole.UserRole),'label':item.text(0),'path':item.text(1),
                                   'kind':{'ファイル':'file','フォルダー':'folder'}.get(item.text(2),'')})
        return data

    def save(self):
        try:self.store.save(self.candidate())
        except (OSError,ContextOptionsError) as error:
            self.status.setText(f'保存できません。編集中の内容は保持しています。{error}');return False
        self.dirty=False;self.status.setText('保存して反映しました。');self.saved.emit();return True

    def load_topic(self,*_):
        self.topic_loading=True
        pref=self.preferences.preference(self.topic.currentData())
        self.muted.setChecked(pref['muted_date']==datetime.now().astimezone().date().isoformat())
        self.reduced.setChecked(pref['reduced']);self.topic_loading=False

    def save_topic(self,*_):
        if self.topic_loading or not self.topic.currentData():return
        try:self.preferences.update(self.topic.currentData(),muted_date=datetime.now().astimezone().date().isoformat() if self.muted.isChecked() else '',reduced=self.reduced.isChecked())
        except (OSError,ContextOptionsError) as error:
            self.topic_status.setText(f'保存できません。{error}');self.load_topic();return
        self.topic_status.setText('この話題の表示設定を保存して反映しました。')

    def reset_topic(self):
        self.topic_loading=True;self.muted.setChecked(False);self.reduced.setChecked(False);self.topic_loading=False;self.save_topic()

    def closeEvent(self,event):
        if self.dirty:
            answer=QMessageBox.question(self,'未保存の設定','休日・対象・会議の変更を保存しますか？',QMessageBox.StandardButton.Save|QMessageBox.StandardButton.Discard|QMessageBox.StandardButton.Cancel)
            if answer==QMessageBox.StandardButton.Cancel or (answer==QMessageBox.StandardButton.Save and not self.save()):event.ignore();return
            if answer==QMessageBox.StandardButton.Discard:self.revert()
        event.accept()
