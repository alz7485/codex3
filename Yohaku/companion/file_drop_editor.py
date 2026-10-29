"""General drop acceptance setting and entry point to named destinations."""
from copy import deepcopy
from PySide6.QtCore import Qt,Signal
from PySide6.QtWidgets import QCheckBox,QDialog,QDialogButtonBox,QLabel,QPushButton,QVBoxLayout
from .file_drop import FileDropError


class FileDropEditor(QDialog):
    saved=Signal();destinations_requested=Signal()
    def __init__(self,store,parent=None):
        super().__init__(parent);self.store=store;self.dirty=False
        self.setWindowTitle('Yohaku — ドロップしたファイルの処理');self.resize(560,300)
        layout=QVBoxLayout(self)
        intro=QLabel('複数項目も渡せます。PDFだけなら印刷、ZIP・7zだけなら解凍も選べます。その他・混在は預ける・移動に対応します。')
        intro.setWordWrap(True);layout.addWidget(intro)
        self.enabled=QCheckBox('キャラへのファイル・フォルダーのドロップを受け付ける');layout.addWidget(self.enabled)
        self.enabled.toggled.connect(lambda:setattr(self,'dirty',True))
        edit=QPushButton('移動先の一覧を編集');edit.clicked.connect(self.destinations_requested.emit);layout.addWidget(edit)
        note=QLabel('PDFはWindowsの既定プリンターへ印刷します。A4・A3・用紙サイズに合わせる、から選択します。')
        note.setWordWrap(True);layout.addWidget(note);layout.addStretch()
        self.status=QLabel();self.status.setTextFormat(Qt.TextFormat.PlainText);self.status.setWordWrap(True);layout.addWidget(self.status)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Close)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText('保存して反映');buttons.button(QDialogButtonBox.StandardButton.Close).setText('閉じる')
        buttons.accepted.connect(self.save);buttons.rejected.connect(self.close);layout.addWidget(buttons);self.reload()
    def reload(self):
        self.store.__init__(self.store.path);self.enabled.setChecked(self.store.data['enabled']);self.status.setText(self.store.error);self.dirty=False
    def save(self):
        document=deepcopy(self.store.data);document['enabled']=self.enabled.isChecked()
        try:self.store.save(document)
        except (FileDropError,OSError) as error:
            self.status.setText(str(error) if isinstance(error,FileDropError) else '保存できません。');return
        self.dirty=False;self.status.setText('保存しました。');self.saved.emit()
