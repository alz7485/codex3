"""Structured registration UI for local, recurring notification JSON."""
from copy import deepcopy
from datetime import datetime

from PySide6.QtCore import Qt, QTime, Signal
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFormLayout, QHBoxLayout, QLineEdit,
    QListWidget, QMainWindow, QMessageBox, QPlainTextEdit, QSpinBox, QSplitter, QTimeEdit, QWidget)

from .reminders import KINDS, WEEKDAYS, ReminderError, new_rule, next_occurrence
from .ui import box, button, label


class ReminderEditor(QMainWindow):
    saved = Signal()

    def __init__(self, store, context_options=None):
        super().__init__()
        self.context_options=context_options
        self.store = store
        self.draft = deepcopy(store.data)
        self.loading = False
        self.dirty = False
        self.setWindowTitle('Yohaku — 通知の登録')
        self.resize(860, 730)
        self.setMinimumSize(760, 680)
        root = QWidget(objectName='panel')
        self.setCentralWidget(root)
        layout = box(root, 22, 12)
        layout.addWidget(label('忘れたくないことを、決まった日に。', 'heading'))
        layout.addWidget(label('月末や毎月の締め日を条件にして、時刻とメッセージを登録できます。', 'muted', True))
        split = QSplitter()
        list_page = QWidget()
        list_layout = box(list_page, 0, 10)
        self.rules = QListWidget()
        self.rules.setAccessibleName('登録した通知')
        self.rules.currentRowChanged.connect(self.load_rule)
        list_layout.addWidget(self.rules, 1)
        actions = QHBoxLayout()
        actions.addWidget(button('追加', self.add_rule))
        actions.addWidget(button('削除', self.remove_rule))
        list_layout.addLayout(actions)
        split.addWidget(list_page)
        self.fields = QWidget()
        fields = box(self.fields, 14, 12)
        self.enabled = QCheckBox('この通知を有効にする')
        self.enabled.toggled.connect(self.edit_rule)
        fields.addWidget(self.enabled)
        form = QFormLayout()
        self.form = form
        self.name = QLineEdit()
        self.name.setMaxLength(80)
        self.name.setAccessibleName('通知の管理用の名前')
        self.name.textChanged.connect(self.edit_rule)
        form.addRow('管理用の名前', self.name)
        self.kind = QComboBox()
        for key, title in KINDS.items():
            self.kind.addItem(title, key)
        self.kind.setAccessibleName('通知条件')
        self.kind.currentIndexChanged.connect(self.edit_rule)
        form.addRow('条件', self.kind)
        self.day = QSpinBox()
        self.day.setRange(1, 31)
        self.day.setValue(15)
        self.day.setSuffix(' 日')
        self.day.setAccessibleName('毎月の基準日')
        self.day.valueChanged.connect(self.edit_rule)
        form.addRow('基準日', self.day)
        self.weekday_row = QWidget()
        days_layout = QHBoxLayout(self.weekday_row)
        days_layout.setContentsMargins(0, 0, 0, 0)
        self.weekdays = []
        for i, title in enumerate(WEEKDAYS):
            check = QCheckBox(title)
            check.setChecked(i < 5)
            check.setAccessibleName(title + '曜日に通知')
            check.toggled.connect(self.edit_rule)
            self.weekdays.append(check)
            days_layout.addWidget(check)
        form.addRow('曜日', self.weekday_row)
        self.time = QTimeEdit(QTime(17, 0))
        self.time.setDisplayFormat('HH:mm')
        self.time.setAccessibleName('登録通知の時刻')
        self.time.timeChanged.connect(self.edit_rule)
        form.addRow('時刻', self.time)
        fields.addLayout(form)
        fields.addWidget(label('吹き出しに表示するメッセージ'))
        self.message = QPlainTextEdit()
        self.message.setAccessibleName('登録通知のメッセージ')
        self.message.setMaximumHeight(140)
        self.message.textChanged.connect(self.edit_rule)
        fields.addWidget(self.message)
        self.description = label('', 'muted', True)
        fields.addWidget(self.description)
        self.next_date = label('', 'section', True)
        fields.addWidget(self.next_date)
        fields.addStretch()
        split.addWidget(self.fields)
        split.setSizes([260, 540])
        layout.addWidget(split, 1)
        layout.addWidget(label('「平日」は月〜金、「営業日」は祝日・会社休日も除外します。通知は指定時刻から10分以内に1回。アプリ停止中・非表示・画面共有・おやすみ・静かな時間中は表示しません。', 'muted', True))
        row = QHBoxLayout()
        row.addWidget(button('変更を取り消す', self.revert))
        row.addStretch()
        row.addWidget(button('保存して反映', self.save, 'primary'))
        layout.addLayout(row)
        self.status = label(store.error or '「追加」から作成し、「保存して反映」で通知に反映します。', 'muted', True)
        layout.addWidget(self.status)
        path = label(f'JSONの保存先：{store.path}', 'muted', True)
        path.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(path)
        self.populate()

    def row_text(self, rule):
        return f"{'●' if rule['enabled'] else '○'} {rule['name']}\n{rule['time']} · {KINDS[rule['condition']['kind']]}"

    def populate(self, selected=0):
        self.loading = True
        self.rules.clear()
        for rule in self.draft['notifications']:
            self.rules.addItem(self.row_text(rule))
        self.loading = False
        self.rules.setCurrentRow(min(selected, self.rules.count() - 1))
        self.load_rule()

    def load_rule(self, *_):
        if self.loading:
            return
        index = self.rules.currentRow()
        self.fields.setEnabled(index >= 0)
        if index < 0:
            self.next_date.setText('通知を追加してください。')
            return
        self.loading = True
        rule = self.draft['notifications'][index]
        self.enabled.setChecked(rule['enabled'])
        self.name.setText(rule['name'])
        self.kind.setCurrentIndex(self.kind.findData(rule['condition']['kind']))
        self.day.setValue(rule['condition'].get('day', 15))
        for i, check in enumerate(self.weekdays):
            check.setChecked(i in rule['condition'].get('weekdays', [0, 1, 2, 3, 4]))
        self.time.setTime(QTime.fromString(rule['time'], 'HH:mm'))
        self.message.setPlainText(rule['message'])
        self.loading = False
        self.update_preview(rule)

    def edit_rule(self, *_):
        index = self.rules.currentRow()
        if self.loading or index < 0:
            return
        kind = self.kind.currentData()
        condition = {'kind': kind}
        if kind in ('monthly_day', 'monthly_weekday_before','monthly_business_day_before'):
            condition['day'] = self.day.value()
        if kind == 'weekly':
            condition['weekdays'] = [i for i, check in enumerate(self.weekdays) if check.isChecked()]
        rule = self.draft['notifications'][index]
        rule.update(name=self.name.text(), enabled=self.enabled.isChecked(),
                    time=self.time.time().toString('HH:mm'), message=self.message.toPlainText(), condition=condition)
        self.rules.item(index).setText(self.row_text(rule))
        self.dirty = True
        self.status.setText('編集中です。「保存して反映」で通知に反映します。')
        self.update_preview(rule)

    def update_preview(self, rule):
        kind = rule['condition']['kind']
        self.day.setEnabled(kind in ('monthly_day', 'monthly_weekday_before','monthly_business_day_before'))
        self.weekday_row.setEnabled(kind == 'weekly')
        self.form.setRowVisible(self.day, kind in ('monthly_day', 'monthly_weekday_before','monthly_business_day_before'))
        self.form.setRowVisible(self.weekday_row, kind == 'weekly')
        descriptions = {
            'month_end_business_day':'日本の祝日・会社休日・営業曜日を使い、月末から営業日まで繰り上げます。設定は「休日・対象ファイル・話題の表示」で変更できます。',
            'monthly_business_day_before':'基準日を含め、それ以前の最後の営業日に通知します。祝日・会社休日も除外し、前月に繰り上がる場合があります。',
            'daily': '毎日、指定した時刻に通知します。',
            'weekly': '選択した曜日ごとに、指定した時刻に通知します。',
            'monthly_day': 'その月に指定日がない場合は月末日に通知します。土日も対象です。',
            'month_end_weekday': '月末が土曜なら前日の金曜、日曜なら2日前の金曜に通知します。',
            'monthly_weekday_before': '基準日が平日ならその日、土日なら直前の金曜に通知します。その月にない日は月末を基準にします。1日が土日なら前月に繰り上がります。',
        }
        self.description.setText(descriptions[kind])
        if kind in ('month_end_business_day','monthly_business_day_before') and self.context_options and self.context_options.error:
            self.next_date.setText('営業日設定を読み込めないため、次回日付を計算できません。');return
        upcoming = next_occurrence(rule, datetime.now().astimezone(),self.context_options.calendar() if self.context_options else None)
        if upcoming:
            suffix = '（現在は無効）' if not rule['enabled'] else ''
            self.next_date.setText(f'次回対象日：{upcoming:%Y/%m/%d}（{WEEKDAYS[upcoming.weekday()]}）{rule["time"]} {suffix}')
        else:
            self.next_date.setText('曜日を1つ以上選んでください。')

    def add_rule(self):
        if len(self.draft['notifications']) >= 100:
            self.status.setText('通知は100件まで登録できます。')
            return
        self.draft['notifications'].append(new_rule())
        self.dirty = True
        self.populate(len(self.draft['notifications']) - 1)
        self.status.setText('通知を追加しました。条件を編集し「保存して反映」を押してください。')

    def remove_rule(self):
        index = self.rules.currentRow()
        if index >= 0:
            del self.draft['notifications'][index]
            self.dirty = True
            self.populate(max(0, index - 1))
            self.status.setText('編集中の一覧から削除しました。「保存して反映」で確定します。')

    def revert(self):
        self.draft = deepcopy(self.store.data)
        self.dirty = False
        self.populate()
        self.status.setText(self.store.error or '保存済みの通知に戻しました。')

    def save(self):
        try:
            self.store.save(self.draft)
        except (ReminderError, OSError) as error:
            self.status.setText(f'保存できません。通知は変更していません。{error}')
            return False
        self.draft = deepcopy(self.store.data)
        self.dirty = False
        self.status.setText('保存して反映しました。管理用の名前は吹き出しには表示しません。')
        self.saved.emit()
        return True

    def closeEvent(self, event):
        if self.dirty:
            result = QMessageBox.question(self, '通知の登録', '編集内容を保存しますか？',
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel)
            if result == QMessageBox.StandardButton.Cancel or (result == QMessageBox.StandardButton.Save and not self.save()):
                event.ignore()
                return
            if result == QMessageBox.StandardButton.Discard:
                self.revert()
        event.accept()
