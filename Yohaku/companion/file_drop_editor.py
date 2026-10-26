"""Structured editor for the finite file-drop action catalog."""
from copy import deepcopy

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
                              QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QScrollArea, QWidget)

from .file_drop import ACTIONS, FileDropError, defaults


class FileDropEditor(QDialog):
    saved = Signal()

    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.store = store; self.loading = False; self.dirty = False
        self.draft = deepcopy(store.data)
        self.setWindowTitle('Yohaku — ドロップしたファイルの処理')
        self.resize(650, 560)
        outer = QVBoxLayout(self); content = QWidget(); layout = QVBoxLayout(content)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setWidget(content); outer.addWidget(scroll)
        intro = QLabel('拡張子ごとの移動先と処理を登録します。処理は選択後に実行します。')
        intro.setWordWrap(True); layout.addWidget(intro)
        self.enabled = QCheckBox('キャラへのファイルのドロップを受け付ける')
        self.enabled.setChecked(self.draft['enabled']); layout.addWidget(self.enabled)
        self.selector = QComboBox(); self.selector.setAccessibleName('ファイル処理のルール')
        layout.addWidget(self.selector)
        self.name = QLineEdit(); self.extensions = QLineEdit(); self.folder = QLineEdit(); self.password = QLineEdit()
        self.name.setMaxLength(60); self.extensions.setMaxLength(600); self.folder.setMaxLength(2048); self.password.setMaxLength(256)
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.extensions.setPlaceholderText('.pdf または .zip, .拡張子 ／ フォルダーは <folder> ／ その他は *')
        self.folder.setPlaceholderText('移動先フォルダー（移動・解凍には必須）')
        self.password.setPlaceholderText('ZIP用。例：固定部分{month} ／ 空欄はパスワードなし')
        form = QFormLayout()
        form.addRow('表示名', self.name); form.addRow('拡張子', self.extensions)
        directory = QHBoxLayout(); directory.addWidget(self.folder)
        browse = QPushButton('参照'); browse.clicked.connect(self.browse); directory.addWidget(browse)
        form.addRow('移動先', directory); form.addRow('パスワードのひな形', self.password)
        for widget, title in ((self.name, 'ファイルルールの表示名'), (self.extensions, '対象の拡張子'),
                              (self.folder, '移動先フォルダー'), (self.password, 'ZIPのパスワードひな形')):
            widget.setAccessibleName(title)
        layout.addLayout(form)
        self.show_password = QCheckBox('パスワードを表示する')
        self.show_password.toggled.connect(lambda show: self.password.setEchoMode(QLineEdit.EchoMode.Normal if show else QLineEdit.EchoMode.Password))
        layout.addWidget(self.show_password)
        note = QLabel('{month}＝01〜12、{month1}＝1〜12、{year}＝西暦。処理を実行する時点の値を使います。\nひな形は、このPCのfile_drop_settings.jsonと保存時のバックアップに保存します。')
        note.setWordWrap(True); layout.addWidget(note)
        self.actions = {}
        action_form = QFormLayout()
        for key, title in ACTIONS.items():
            check = QCheckBox(title); name = QLineEdit(title); name.setMaxLength(60)
            name.setAccessibleName(title+'のボタン表示名')
            action_form.addRow(check, name); self.actions[key] = (check, name)
            check.toggled.connect(self.update_rule); name.textChanged.connect(self.update_rule)
        layout.addLayout(action_form)
        row = QHBoxLayout()
        add = QPushButton('ルールを追加'); add.clicked.connect(self.add_rule); row.addWidget(add)
        remove = QPushButton('このルールを削除'); remove.clicked.connect(self.remove_rule); row.addWidget(remove)
        layout.addLayout(row)
        self.status = QLabel(store.error); self.status.setWordWrap(True); self.status.setTextFormat(Qt.TextFormat.PlainText)
        outer.addWidget(self.status)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Close)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText('保存して反映')
        buttons.button(QDialogButtonBox.StandardButton.Close).setText('閉じる')
        buttons.accepted.connect(self.save); buttons.rejected.connect(self.close); outer.addWidget(buttons)
        for field in (self.name, self.extensions, self.folder, self.password):
            field.textChanged.connect(self.update_rule)
        self.enabled.toggled.connect(self.update_enabled)
        self.selector.currentIndexChanged.connect(self.load_rule)
        self.populate()

    def populate(self, index=0):
        self.loading = True; self.selector.clear()
        for row in self.draft['rules']:
            self.selector.addItem(row['label'], row['id'])
        self.selector.setCurrentIndex(max(0, min(index, self.selector.count()-1)))
        self.loading = False; self.load_rule()

    def load_rule(self, *_):
        if self.loading or self.selector.currentIndex() < 0:
            return
        self.loading = True
        row = self.draft['rules'][self.selector.currentIndex()]
        self.name.setText(row['label']); self.extensions.setText(', '.join(row['extensions']))
        self.folder.setText(row['destination']); self.password.setText(row['password_template'])
        for key, (check, name) in self.actions.items():
            found = next((action for action in row['actions'] if action['action'] == key), None)
            check.setChecked(found is not None); name.setText(found['label'] if found else ACTIONS[key])
        self.loading = False

    def update_rule(self, *_):
        if self.loading or self.selector.currentIndex() < 0:
            return
        index = self.selector.currentIndex(); row = self.draft['rules'][index]
        row.update(label=self.name.text().strip(), extensions=[part.strip().lower() for part in self.extensions.text().replace('、', ',').split(',') if part.strip()],
                   destination=self.folder.text().strip(), password_template=self.password.text(),
                   actions=[{'action': key, 'label': name.text().strip()} for key, (check, name) in self.actions.items() if check.isChecked()])
        self.selector.setItemText(index, row['label']); self.dirty = True

    def update_enabled(self, enabled):
        if self.loading:
            return
        self.draft['enabled'] = enabled; self.dirty = True

    def reload(self):
        self.store.__init__(self.store.path); self.draft = deepcopy(self.store.data)
        self.loading = True; self.enabled.setChecked(self.draft['enabled']); self.loading = False
        self.populate(); self.status.setText(self.store.error); self.dirty = False

    def browse(self):
        folder = QFileDialog.getExistingDirectory(self, '移動先フォルダー', self.folder.text())
        if folder:
            self.folder.setText(folder)

    def add_rule(self):
        if len(self.draft['rules']) >= 30:
            self.status.setText('ルールは30件までです。'); return
        key = next(f'custom_{i}' for i in range(1, 100) if all(row['id'] != f'custom_{i}' for row in self.draft['rules']))
        row = deepcopy(defaults()['rules'][2]); row.update(id=key, label='新しいルール', extensions=['.txt'])
        self.draft['rules'].append(row); self.dirty = True; self.populate(len(self.draft['rules'])-1)

    def remove_rule(self):
        if len(self.draft['rules']) <= 1:
            self.status.setText('ルールを1件以上残してください。'); return
        index = self.selector.currentIndex(); self.draft['rules'].pop(index)
        self.dirty = True; self.populate(index)

    def save(self):
        try:
            self.store.save(self.draft)
        except FileDropError as error:
            self.status.setText(str(error))
            return
        except OSError:
            self.status.setText('保存できません。保存先の権限を確認してください。')
            return
        self.dirty = False; self.status.setText('保存しました。'); self.saved.emit()
