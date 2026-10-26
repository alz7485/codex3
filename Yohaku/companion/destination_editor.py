"""Add named full paths with a plus button; no file operation on Save."""
from copy import deepcopy
from uuid import uuid4
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QDialog,QDialogButtonBox,QFileDialog,QHBoxLayout,QLabel,
    QLineEdit,QPushButton,QScrollArea,QVBoxLayout,QWidget)
from .file_drop import FileDropError


class DestinationEditor(QDialog):
    saved=Signal()
    def __init__(self,store,parent=None):
        super().__init__(parent);self.store=store;self.dirty=False;self.rows=[]
        self.setWindowTitle('Yohaku — 移動先を編集');self.resize(700,470)
        layout=QVBoxLayout(self)
        layout.addWidget(QLabel('選択肢に表示する名前と、移動先フォルダーのフルパスを登録します。'))
        scroll=QScrollArea();scroll.setWidgetResizable(True);content=QWidget();self.entries=QVBoxLayout(content)
        self.entries.setAlignment(Qt.AlignmentFlag.AlignTop);scroll.setWidget(content);layout.addWidget(scroll,1)
        self.add_button=QPushButton('＋ 移動先を追加');self.add_button.setAccessibleName('移動先を追加')
        self.add_button.clicked.connect(lambda:self.add_row());layout.addWidget(self.add_button)
        self.status=QLabel();self.status.setWordWrap(True);self.status.setTextFormat(Qt.TextFormat.PlainText);layout.addWidget(self.status)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Close)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText('保存して反映')
        buttons.button(QDialogButtonBox.StandardButton.Close).setText('閉じる')
        buttons.accepted.connect(self.save);buttons.rejected.connect(self.close);layout.addWidget(buttons)
        self.reload()

    def reload(self):
        for row in self.rows:
            self.entries.removeWidget(row['widget']);row['widget'].hide();row['widget'].deleteLater()
        self.rows=[]
        for entry in self.store.data['destinations']:self.add_row(entry)
        self.status.setText(self.store.error or '保存するまでファイルの移動は行いません。');self.dirty=False

    def add_row(self,entry=None):
        if len(self.rows)>=100:self.status.setText('移動先は100件までです。');return
        entry=deepcopy(entry) if entry else dict(id=uuid4().hex,name='',path='')
        widget=QWidget();layout=QVBoxLayout(widget);layout.setContentsMargins(0,4,0,8)
        top=QHBoxLayout();name=QLineEdit(entry['name']);name.setMaxLength(60);name.setPlaceholderText('表示名（例：提出用、保管用）');name.setAccessibleName('移動先の表示名')
        remove=QPushButton('削除');top.addWidget(name,1);top.addWidget(remove);layout.addLayout(top)
        bottom=QHBoxLayout();path=QLineEdit(entry['path']);path.setMaxLength(2048);path.setPlaceholderText('フォルダーのフルパス');path.setAccessibleName('移動先のフルパス')
        browse=QPushButton('参照');bottom.addWidget(path,1);bottom.addWidget(browse);layout.addLayout(bottom)
        row=dict(id=entry['id'],name=name,path=path,widget=widget);self.rows.append(row);self.entries.addWidget(widget)
        name.textChanged.connect(self.changed);path.textChanged.connect(self.changed)
        remove.clicked.connect(lambda:self.remove_row(row));browse.clicked.connect(lambda:self.browse(path))
        self.dirty=True

    def changed(self):self.dirty=True
    def remove_row(self,row):
        self.rows.remove(row);self.entries.removeWidget(row['widget']);row['widget'].deleteLater();self.dirty=True
    def browse(self,field):
        path=QFileDialog.getExistingDirectory(self,'移動先フォルダー',field.text())
        if path:field.setText(path)
    def save(self):
        document=dict(schema_version=1,destinations=[dict(id=row['id'],name=row['name'].text().strip(),path=row['path'].text().strip()) for row in self.rows])
        try:self.store.save(document)
        except (FileDropError,OSError) as error:
            self.status.setText(str(error) if isinstance(error,FileDropError) else '保存できません。保存先の権限を確認してください。');return
        self.dirty=False;self.status.setText('保存しました。');self.saved.emit()
