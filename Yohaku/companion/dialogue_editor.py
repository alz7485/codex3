"""Structured editor for the same JSON document used by the conversation engine."""
from copy import deepcopy
import json

from PySide6.QtCore import Qt, QTime, Signal
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QFormLayout, QHBoxLayout,
    QLineEdit, QListWidget, QDoubleSpinBox, QMainWindow, QMessageBox, QPlainTextEdit, QScrollArea, QSpinBox, QTimeEdit,
    QSplitter, QTabWidget, QVBoxLayout, QWidget)

from .dialogue import DialogueError, KINDS, VOICE_NAMES, defaults, read_document, validate
from .motion import EXPRESSION_FRAMES
from .metrics import METRICS
from .ui import box, button, label

EXPRESSION_LABELS = dict(zip(EXPRESSION_FRAMES, ('通常', 'まばたき', '笑顔', 'お知らせ', '考え中', '眠そう',
    '得意げ', '気遣い', 'ウインク', '大笑い', '首かしげ', 'くつろぎ', 'うなずき', '発話', '挨拶', '伸び',
    '正面', '正面・まばたき', '正面・困る', '正面・怒る')))


def spin(minimum, maximum, suffix=''):
    result = QSpinBox()
    result.setRange(minimum, maximum)
    result.setSuffix(suffix)
    return result


class DialogueEditor(QMainWindow):
    saved = Signal()

    def __init__(self, store):
        super().__init__()
        self.store = store
        self.loading = True
        self.dirty = False
        self.draft = deepcopy(store.data)
        self.setWindowTitle('余白 — 会話の編集')
        self.resize(1020, 800)
        self.setMinimumSize(800, 620)
        root = QWidget(objectName='panel')
        self.setCentralWidget(root)
        layout = box(root, 22, 12)
        layout.addWidget(label('言葉も、話しかけるタイミングも。', 'heading'))
        layout.addWidget(label('編集後に「保存して反映」を押すと、このPCの会話にすぐ反映します。', 'muted', True))
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)
        self.build_phrases()
        self.build_rules()
        self.build_options()
        row = QHBoxLayout()
        row.addWidget(button('JSONを読み込む', self.import_json))
        row.addWidget(button('JSONを書き出す', self.export_json))
        row.addWidget(button('初期値へ戻す', self.reset_defaults))
        row.addStretch()
        row.addWidget(button('変更を取り消す', self.revert))
        self.save_button = button('保存して反映', self.save, 'primary')
        row.addWidget(self.save_button)
        layout.addLayout(row)
        self.status = label('', 'muted', True)
        self.status.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.status)
        self.path_label = label(f'保存先：{store.path}', 'muted', True)
        layout.addWidget(self.path_label)
        self.populate()
        self.status.setText(store.error or 'JSON形式で保存します。直前の保存内容は .json.bak に残します。')

    def mark_dirty(self):
        if not self.loading:
            self.dirty = True
            self.status.setText('編集中です。保存すると反映されます。')

    def build_phrases(self):
        page = QWidget()
        outer = box(page, 12, 10)
        row = QHBoxLayout()
        row.addWidget(label('性格'))
        self.voice = QComboBox()
        self.voice.addItems(VOICE_NAMES)
        self.voice.setAccessibleName('編集する性格')
        self.voice.currentIndexChanged.connect(self.load_phrases)
        row.addWidget(self.voice)
        row.addStretch()
        outer.addLayout(row)
        split = QSplitter()
        self.phrase_topics = QListWidget()
        self.phrase_topics.setAccessibleName('会話の話題')
        self.phrase_topics.currentRowChanged.connect(self.load_phrases)
        split.addWidget(self.phrase_topics)
        content = QWidget()
        layout = box(content, 12, 8)
        self.lines = QListWidget()
        self.lines.setAccessibleName('セリフ一覧')
        self.lines.currentRowChanged.connect(self.load_line)
        layout.addWidget(self.lines, 1)
        row = QHBoxLayout()
        row.addWidget(button('セリフを追加', self.add_line))
        self.remove_line_button = button('このセリフを削除', self.remove_line)
        row.addWidget(self.remove_line_button)
        row.addStretch()
        layout.addLayout(row)
        layout.addWidget(label('選択したセリフ（改行も使えます）', 'section'))
        self.line_edit = QPlainTextEdit()
        self.line_edit.setAccessibleName('セリフの本文')
        self.line_edit.setMaximumHeight(150)
        self.line_edit.textChanged.connect(self.update_line)
        layout.addWidget(self.line_edit)
        layout.addWidget(label('1話題1〜200件、1件1〜1000文字。本文に {idle_minutes}・{file_name}・{file_open_count}・{hours_to_end}・{weekly_events} 等の差し込みが使えます。', 'muted', True))
        split.addWidget(content)
        split.setSizes([240, 650])
        outer.addWidget(split)
        self.tabs.addTab(page, '会話文')

    def build_rules(self):
        page = QWidget()
        layout = QHBoxLayout(page)
        left = QWidget()
        left_box = box(left, 0, 8)
        self.rule_list = QListWidget()
        self.rule_list.setAccessibleName('発生ルール一覧')
        self.rule_list.currentRowChanged.connect(self.load_rule)
        left_box.addWidget(self.rule_list)
        row = QHBoxLayout()
        row.addWidget(button('話題を追加', self.add_rule))
        self.remove_rule_button = button('削除', self.remove_rule)
        row.addWidget(self.remove_rule_button)
        left_box.addLayout(row)
        layout.addWidget(left, 1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        fields = QWidget(objectName='page')
        form = QFormLayout(fields)
        self.rule_form = form
        form.setSpacing(12)
        self.rule_label = QLineEdit()
        self.rule_label.setMaxLength(60)
        self.rule_enabled = QCheckBox('この話題を使う')
        self.rule_trigger = label('')
        self.expression = QComboBox()
        for key, text in EXPRESSION_LABELS.items():
            self.expression.addItem(text, key)
        self.weight = spin(1, 100)
        self.priority = spin(0, 5)
        self.priority.setToolTip('0は通常。未発言を優先する選択方式でも、追加の抽選枠を持ちます。')
        self.cooldown = spin(0, 1440, ' 分')
        self.kind = QComboBox()
        for key, text in KINDS.items():
            self.kind.addItem(text, key)
        self.start_time, self.end_time = time_edit(), time_edit()
        self.days = [QCheckBox(day) for day in ('月', '火', '水', '木', '金', '土', '日')]
        self.day_row = day_row = QWidget()
        row = QHBoxLayout(day_row)
        row.setContentsMargins(0, 0, 0, 0)
        for day in self.days:
            row.addWidget(day)
        self.minimum = spin(0, 43200, ' 分')
        self.maximum = spin(0, 43200, ' 分')
        self.no_maximum = QCheckBox('上限なし')
        self.first_only = QCheckBox('起動後、最初の会話だけで使う')
        self.metric_selector = QComboBox()
        for key, title in METRICS.items(): self.metric_selector.addItem(title, key)
        self.metric_minimum, self.metric_maximum = QDoubleSpinBox(), QDoubleSpinBox()
        for field in (self.metric_minimum, self.metric_maximum):
            field.setRange(-43200, 100000)
            field.setDecimals(3)
        self.details = QPlainTextEdit()
        self.details.setMaximumHeight(170)
        self.details.setAccessibleName('AND ORの詳細条件JSON配列')
        for title, widget in [('話題名', self.rule_label), ('有効・無効', self.rule_enabled), ('発生方法', self.rule_trigger),
                              ('表情', self.expression), ('出現しやすさ', self.weight), ('少し優先する（0〜5）', self.priority), ('同じ話題の間隔', self.cooldown),
                              ('発生条件', self.kind), ('集計値', self.metric_selector), ('集計値の下限', self.metric_minimum), ('集計値の上限', self.metric_maximum), ('詳細条件JSON配列', self.details), ('開始時刻', self.start_time), ('終了時刻', self.end_time),
                              ('曜日', day_row), ('経過／開始までの下限', self.minimum), ('上限', self.maximum),
                              ('', self.no_maximum), ('', self.first_only)]:
            widget.setAccessibleName(title or widget.text())
            form.addRow(title, widget)
        form.addRow(label('時間帯は開始を含み終了を含みません。同時刻なら終日。曜日と時刻はPCのローカル設定です。予定の前後はOutlook接続時だけ候補になります。', 'muted', True))
        form.addRow(label('出現しやすさは同じ優先度の候補内で使います。「呼びかけ」と「予定のお知らせ」は個別の操作・通知に対応します。', 'muted', True))
        scroll.setWidget(fields)
        layout.addWidget(scroll, 2)
        self.tabs.addTab(page, '発生ルール')
        self.rule_label.textChanged.connect(self.update_rule)
        for widget in [self.rule_enabled, *self.days, self.no_maximum, self.first_only]:
            widget.toggled.connect(self.update_rule)
        for widget in (self.weight, self.priority, self.cooldown, self.minimum, self.maximum):
            widget.valueChanged.connect(self.update_rule)
        for widget in (self.expression, self.kind):
            widget.currentIndexChanged.connect(self.update_rule)
        self.metric_selector.currentIndexChanged.connect(self.update_rule)
        self.metric_minimum.valueChanged.connect(self.update_rule)
        self.metric_maximum.valueChanged.connect(self.update_rule)
        self.details.textChanged.connect(self.update_rule)
        self.start_time.timeChanged.connect(self.update_rule)
        self.end_time.timeChanged.connect(self.update_rule)

    def build_options(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        page = QWidget(objectName='page')
        form = QFormLayout(page)
        form.setContentsMargins(20, 20, 20, 20)
        form.setSpacing(15)
        self.options = {
            'interval_minutes': spin(1, 1440, ' 分'), 'bubble_seconds': spin(5, 300, ' 秒'),
            'meeting_lead_minutes': spin(1, 120, ' 分前'), 'repeat_window': spin(0, 64, ' 件'),
            'suppress_during_meetings': QCheckBox('予定の開催中は自動雑談をしない'),
            'avoid_consecutive_topic': QCheckBox('同じ話題を続けて選ばない'),
            'selection_policy': QComboBox(),
            'work_start': time_edit(), 'work_end': time_edit(),
            'active_threshold_seconds': spin(5, 600, ' 秒'),
            'click_reactions': QCheckBox('連打されたときに困る・怒る反応をする'),
            'click_window_seconds': spin(1, 30, ' 秒'),
            'click_concern_count': spin(2, 30, ' 回'),
            'click_angry_count': spin(3, 60, ' 回'),
            'click_recovery_seconds': spin(1, 120, ' 秒'),
            'click_repeat_seconds': spin(1, 600, ' 秒'),
        }
        self.options['selection_policy'].addItem('未使用・久しぶりの話題を優先', 'least_recent')
        self.options['selection_policy'].addItem('出現しやすさで抽選', 'weighted')
        titles = ('自動会話の間隔', '吹き出しの表示時間', '予定のお知らせ', '同じセリフを避ける数', '会議中', '連続する話題', '話題の選び方', '始業時刻', '定時（終業時刻）', '操作ありと判定する最終操作からの秒数',
                  'クリックへの反応', '連打を数える期間', '困る反応を始める回数', '怒る反応を始める回数', '最後のクリックから回数をリセットするまで', '同じ段階の反応を繰り返すまで')
        for (key, widget), title in zip(self.options.items(), titles):
            widget.setAccessibleName(title)
            form.addRow(title, widget)
            if isinstance(widget, QSpinBox): widget.valueChanged.connect(self.update_options)
            elif isinstance(widget, QCheckBox): widget.toggled.connect(self.update_options)
            elif isinstance(widget, QTimeEdit): widget.timeChanged.connect(self.update_options)
            else: widget.currentIndexChanged.connect(self.update_options)
        form.addRow(label('静かな時間・おやすみ・非表示中の停止は通常の設定に従います。', 'muted', True))
        self.profile_key = QComboBox()
        self.profile_key.addItems(['A 余白ノート', 'B 事務ロボ', 'E まじめなペンギン', 'F お茶ねこ'])
        self.profile_voice = QComboBox()
        self.profile_voice.addItems(VOICE_NAMES)
        self.description = QLineEdit()
        self.description.setMaxLength(300)
        self.tagline = QPlainTextEdit()
        self.tagline.setMaximumHeight(90)
        form.addRow(label('キャラの性格', 'section'))
        for title, widget in [('キャラ', self.profile_key), ('基本の性格', self.profile_voice), ('性格の説明', self.description), ('代表的な一言', self.tagline)]:
            form.addRow(title, widget)
        self.profile_key.currentIndexChanged.connect(self.load_profile)
        self.profile_voice.currentIndexChanged.connect(self.update_profile)
        self.description.textChanged.connect(self.update_profile)
        self.tagline.textChanged.connect(self.update_profile)
        scroll.setWidget(page)
        self.tabs.addTab(scroll, '全体設定・性格')

    def populate(self):
        self.loading = True
        self.phrase_topics.clear()
        self.rule_list.clear()
        for rule in self.draft['rules']:
            self.phrase_topics.addItem(rule['label'])
            self.rule_list.addItem(rule['label'])
        for key, widget in self.options.items():
            value = self.draft['options'][key]
            if isinstance(widget, QSpinBox): widget.setValue(value)
            elif isinstance(widget, QCheckBox): widget.setChecked(value)
            elif isinstance(widget, QTimeEdit): widget.setTime(QTime.fromString(value, 'HH:mm'))
            else: widget.setCurrentIndex(widget.findData(value))
        self.loading = False
        self.phrase_topics.setCurrentRow(0)
        self.rule_list.setCurrentRow(0)
        self.load_phrases()
        self.load_rule()
        self.load_profile()
        self.dirty = False

    def bank(self):
        row = self.phrase_topics.currentRow()
        if row < 0:
            return None
        key = self.draft['rules'][row]['id']
        return self.draft['phrases'][self.voice.currentText()][key]

    def load_phrases(self, *_):
        if self.loading:
            return
        self.loading = True
        self.lines.clear()
        for line in self.bank() or []:
            self.lines.addItem(line.replace('\n', ' ↵ ')[:70])
        self.loading = False
        self.lines.setCurrentRow(0)
        self.load_line()

    def load_line(self, *_):
        if self.loading:
            return
        self.loading = True
        bank, row = self.bank(), self.lines.currentRow()
        self.line_edit.setPlainText(bank[row] if bank and row >= 0 else '')
        self.line_edit.setEnabled(bool(bank) and row >= 0)
        self.remove_line_button.setEnabled(bool(bank) and len(bank) > 1)
        self.loading = False

    def update_line(self):
        if self.loading:
            return
        bank, row = self.bank(), self.lines.currentRow()
        if bank is not None and row >= 0:
            bank[row] = self.line_edit.toPlainText()
            self.lines.item(row).setText(bank[row].replace('\n', ' ↵ ')[:70] or '（空のセリフ）')
            self.mark_dirty()

    def add_line(self):
        bank = self.bank()
        if bank is not None and len(bank) < 200:
            bank.append('新しいセリフ')
            self.load_phrases()
            self.lines.setCurrentRow(len(bank) - 1)
            self.line_edit.selectAll()
            self.line_edit.setFocus()
            self.mark_dirty()

    def remove_line(self):
        bank, row = self.bank(), self.lines.currentRow()
        if bank and len(bank) > 1 and row >= 0:
            del bank[row]
            self.load_phrases()
            self.lines.setCurrentRow(min(row, len(bank) - 1))
            self.mark_dirty()

    def load_rule(self, *_):
        row = self.rule_list.currentRow()
        if self.loading or row < 0:
            return
        self.loading = True
        r = self.draft['rules'][row]
        self.rule_label.setText(r['label'])
        self.rule_enabled.setChecked(r['enabled'])
        self.rule_trigger.setText({'auto': '自動会話', 'click': 'キャラをクリック', 'reminder': '予定開始前のお知らせ', 'action': '操作に対する返答', 'notification': '受信を検知したら通知'}[r['trigger']])
        self.expression.setCurrentIndex(self.expression.findData(r['expression']))
        self.weight.setValue(r['weight'])
        self.priority.setValue(r.get('priority', 0))
        self.cooldown.setValue(r['cooldown_minutes'])
        c = r['condition']
        self.kind.setCurrentIndex(self.kind.findData(c['kind']))
        self.start_time.setTime(QTime.fromString(c.get('start', '09:00'), 'HH:mm'))
        self.end_time.setTime(QTime.fromString(c.get('end', '18:00'), 'HH:mm'))
        for index, day in enumerate(self.days): day.setChecked(index in c.get('days', []))
        self.minimum.setValue(c.get('minimum_minutes', 0))
        self.maximum.setValue(c.get('maximum_minutes') or 0)
        self.no_maximum.setChecked(c.get('maximum_minutes') is None)
        self.first_only.setChecked(c.get('first_only', False))
        self.metric_selector.setCurrentIndex(max(0, self.metric_selector.findData(c.get('metric', 'idle_minutes'))))
        self.metric_minimum.setValue(c.get('minimum', 0))
        self.metric_maximum.setValue(c.get('maximum') or 0)
        if c['kind'] == 'metric_range': self.no_maximum.setChecked(c.get('maximum') is None)
        children = c.get('conditions', [{'kind': 'metric_range', 'metric': 'idle_minutes', 'minimum': 5, 'maximum': None}])
        self.details.setPlainText(children if isinstance(children, str) else json.dumps(children, ensure_ascii=False, indent=2))
        self.remove_rule_button.setEnabled(r['trigger'] == 'auto' and r['id'] != 'chat')
        self.loading = False
        self.enable_condition_fields()

    def enable_condition_fields(self):
        r = self.draft['rules'][self.rule_list.currentRow()]
        automatic = r['trigger'] == 'auto'
        kind = self.kind.currentData()
        self.kind.setEnabled(automatic)
        self.weight.setEnabled(automatic)
        self.priority.setEnabled(automatic)
        self.cooldown.setEnabled(automatic)
        self.start_time.setEnabled(automatic and kind == 'time_range')
        self.end_time.setEnabled(automatic and kind == 'time_range')
        for day in self.days: day.setEnabled(automatic and kind == 'weekday')
        ranged = automatic and kind in ('session_range', 'before_meeting', 'after_meeting')
        self.minimum.setEnabled(ranged)
        self.maximum.setEnabled(ranged and (kind != 'session_range' or not self.no_maximum.isChecked()))
        self.no_maximum.setEnabled(automatic and kind in ('session_range', 'metric_range'))
        self.metric_maximum.setEnabled(not self.no_maximum.isChecked())
        self.first_only.setEnabled(automatic and kind == 'session_range')
        for widget, visible in [(self.weight, automatic), (self.priority, automatic), (self.cooldown, automatic), (self.kind, automatic),
                (self.start_time, automatic and kind == 'time_range'), (self.end_time, automatic and kind == 'time_range'),
                (self.day_row, automatic and kind == 'weekday'), (self.minimum, ranged), (self.maximum, ranged),
                (self.no_maximum, automatic and kind in ('session_range', 'metric_range')),
                (self.metric_selector, automatic and kind == 'metric_range'), (self.metric_minimum, automatic and kind == 'metric_range'),
                (self.metric_maximum, automatic and kind == 'metric_range'), (self.details, automatic and kind in ('all', 'any')), (self.first_only, automatic and kind == 'session_range')]:
            self.rule_form.setRowVisible(widget, visible)

    def update_rule(self, *_):
        row = self.rule_list.currentRow()
        if self.loading or row < 0:
            return
        r = self.draft['rules'][row]
        c = {'kind': self.kind.currentData()}
        if c['kind'] == 'metric_range':
            c.update(metric=self.metric_selector.currentData(), minimum=self.metric_minimum.value(),
                     maximum=None if self.no_maximum.isChecked() else self.metric_maximum.value())
        elif c['kind'] in ('all', 'any'):
            text = self.details.toPlainText()
            try:
                c['conditions'] = json.loads(text)
            except (json.JSONDecodeError, RecursionError):
                c['conditions'] = text  # Preserve the draft; validation blocks saving it.
        elif c['kind'] == 'time_range':
            c.update(start=self.start_time.time().toString('HH:mm'), end=self.end_time.time().toString('HH:mm'))
        elif c['kind'] == 'weekday':
            c['days'] = [i for i, day in enumerate(self.days) if day.isChecked()]
        elif c['kind'] in ('session_range', 'before_meeting', 'after_meeting'):
            c.update(minimum_minutes=self.minimum.value(), maximum_minutes=None if c['kind'] == 'session_range' and self.no_maximum.isChecked() else self.maximum.value())
            if c['kind'] == 'session_range': c['first_only'] = self.first_only.isChecked()
        r.update(label=self.rule_label.text(), enabled=self.rule_enabled.isChecked(), expression=self.expression.currentData(),
                 weight=self.weight.value(), priority=self.priority.value(), cooldown_minutes=self.cooldown.value(), condition=c)
        self.rule_list.item(row).setText(r['label'] or '（話題名なし）')
        self.phrase_topics.item(row).setText(r['label'] or '（話題名なし）')
        self.enable_condition_fields()
        self.mark_dirty()

    def add_rule(self):
        if len(self.draft['rules']) >= 200:
            return
        keys = {r['id'] for r in self.draft['rules']}
        key = next(f'custom_{i}' for i in range(1, 201) if f'custom_{i}' not in keys)
        self.draft['rules'].append(dict(id=key, label='新しい話題', enabled=True, trigger='auto',
            condition={'kind': 'always'}, expression='happy', weight=1, cooldown_minutes=60))
        for bank in self.draft['phrases'].values(): bank[key] = ['ひと息つきませんか。']
        self.populate()
        self.rule_list.setCurrentRow(len(self.draft['rules']) - 1)
        self.phrase_topics.setCurrentRow(len(self.draft['rules']) - 1)
        self.mark_dirty()

    def remove_rule(self):
        row = self.rule_list.currentRow()
        if row >= 0 and self.draft['rules'][row]['trigger'] == 'auto' and self.draft['rules'][row]['id'] != 'chat':
            key = self.draft['rules'].pop(row)['id']
            for bank in self.draft['phrases'].values(): del bank[key]
            self.populate()
            self.mark_dirty()

    def load_profile(self, *_):
        if self.loading:
            return
        self.loading = True
        profile = self.draft['profiles']['ABEF'[self.profile_key.currentIndex()]]
        self.profile_voice.setCurrentText(profile['voice'])
        self.description.setText(profile['description'])
        self.tagline.setPlainText(profile['tagline'])
        self.loading = False

    def update_profile(self, *_):
        if not self.loading:
            self.draft['profiles']['ABEF'[self.profile_key.currentIndex()]] = dict(voice=self.profile_voice.currentText(),
                description=self.description.text(), tagline=self.tagline.toPlainText())
            self.mark_dirty()

    def update_options(self, *_):
        if self.loading:
            return
        for key, widget in self.options.items():
            self.draft['options'][key] = widget.value() if isinstance(widget, QSpinBox) else widget.isChecked() if isinstance(widget, QCheckBox) else widget.time().toString('HH:mm') if isinstance(widget, QTimeEdit) else widget.currentData()
        self.mark_dirty()

    def save(self):
        try:
            self.store.save(self.draft)
        except (OSError, DialogueError) as error:
            self.status.setText(f'保存できませんでした。変更は反映していません。{error}')
            return False
        self.dirty = False
        self.status.setText('JSONに保存し、会話へ反映しました。')
        self.saved.emit()
        return True

    def revert(self):
        self.draft = deepcopy(self.store.data)
        self.populate()
        self.status.setText('保存済みの内容に戻しました。')

    def reset_defaults(self):
        self.draft = defaults()
        self.populate()
        self.mark_dirty()
        self.status.setText('初期値を編集中です。「保存して反映」で確定します。')

    def import_json(self):
        path, _ = QFileDialog.getOpenFileName(self, '会話JSONを読み込む', '', '会話JSON (*.json *.json.bak);;すべてのファイル (*)')
        if not path:
            return
        try:
            candidate = read_document(path)
        except (OSError, DialogueError) as error:
            self.status.setText(f'読み込めません。編集中の内容は変更していません。{error}')
            return
        self.draft = candidate
        self.populate()
        self.mark_dirty()
        self.status.setText('JSONを読み込みました。「保存して反映」でこのPCの会話に使います。')

    def export_json(self):
        try:
            candidate = validate(self.draft)
        except DialogueError as error:
            self.status.setText(str(error))
            return
        path, _ = QFileDialog.getSaveFileName(self, '会話JSONを書き出す', 'Yohaku-conversation.json', 'JSON (*.json)')
        if path:
            try:
                from pathlib import Path
                target = Path(path)
                if target.resolve() == self.store.path.resolve():
                    self.status.setText('使用中のJSONには「保存して反映」で保存してください。')
                    return
                target.write_text(json.dumps(candidate, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
                self.status.setText('JSONを書き出しました。現在の会話への反映は「保存して反映」で行います。')
            except OSError as error:
                self.status.setText(f'書き出せませんでした。{error}')

    def closeEvent(self, event):
        if self.dirty:
            result = QMessageBox.question(self, '会話の編集', '編集内容を保存しますか？',
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel)
            if result == QMessageBox.StandardButton.Cancel or (result == QMessageBox.StandardButton.Save and not self.save()):
                event.ignore()
                return
            if result == QMessageBox.StandardButton.Discard:
                self.revert()
        event.accept()


def time_edit():
    result = QTimeEdit()
    result.setDisplayFormat('HH:mm')
    return result
