"""Small visual pickers shared by the content editor and growth screen."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox,QDialog,QDialogButtonBox,QGridLayout,QHBoxLayout,
    QLabel,QLineEdit,QListWidget,QListWidgetItem,QPushButton,QTabWidget,QVBoxLayout,QWidget)

FRAME_NAMES=('通常','まばたき','うれしい','気づく','考える','眠そう','得意げ','気づかう',
             'ウィンク','笑う','興味','くつろぐ','うなずく','話す','あいさつ','伸び')


def frame_caption(frame):
    name=FRAME_NAMES[frame] if frame<16 else f'歩行 {frame-15}/8' if frame<24 else ('正面','正面まばたき','困る','怒る')[frame-24]
    return f'{frame}: {name}'


class FramePicker(QDialog):
    def __init__(self,selected=(),parent=None):
        super().__init__(parent);self.setWindowTitle('衣装を重ねるフレーム');self.resize(650,340)
        outer=QVBoxLayout(self);outer.addWidget(QLabel('画像に対応するコマを選んでください。未選択の動作では衣装を表示しません。'))
        tabs=QTabWidget();outer.addWidget(tabs);self.checks={}
        for title,frames in (('通常・表情',range(16)),('歩行',range(16,24)),('正面',range(24,28))):
            page=QWidget();grid=QGridLayout(page)
            for n,frame in enumerate(frames):
                check=QCheckBox(frame_caption(frame));check.setChecked(frame in selected)
                self.checks[frame]=check;grid.addWidget(check,n//4,n%4)
            tabs.addTab(page,title)
        row=QHBoxLayout();outer.addLayout(row)
        for title,values in (('歩行をまとめて選択',range(16,24)),('正面をまとめて選択',range(24,28)),('すべて解除',())):
            button=QPushButton(title);button.clicked.connect(lambda _,v=values:self.set_selected(v));row.addWidget(button)
        self.status=QLabel();outer.addWidget(self.status)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept);buttons.rejected.connect(self.reject);outer.addWidget(buttons)

    def selected(self):return [n for n,check in self.checks.items() if check.isChecked()]

    def set_selected(self,values):
        for frame,check in self.checks.items():check.setChecked(frame in values)

    def accept(self):
        if not self.selected():self.status.setText('1つ以上のフレームを選んでください。');return
        super().accept()


class RewardPicker(QDialog):
    def __init__(self,options,selected=(),parent=None):
        super().__init__(parent);self.setWindowTitle('解放するものを選ぶ');self.resize(700,480)
        outer=QVBoxLayout(self);self.search=QLineEdit();self.search.setPlaceholderText('名前・IDで絞り込み');outer.addWidget(self.search)
        self.items=QListWidget();outer.addWidget(self.items,1)
        all_options=dict(options)
        for key in selected:all_options.setdefault(key,'参照先がないID（解除するか、パックを追加してください）')
        for key,title in sorted(all_options.items()):
            row=QListWidgetItem(title+'\n'+key);row.setData(Qt.ItemDataRole.UserRole,key)
            row.setFlags(row.flags()|Qt.ItemFlag.ItemIsUserCheckable)
            row.setCheckState(Qt.CheckState.Checked if key in selected else Qt.CheckState.Unchecked);self.items.addItem(row)
        self.search.textChanged.connect(self.filter)
        self.status=QLabel('1〜30件を選べます。');outer.addWidget(self.status)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept);buttons.rejected.connect(self.reject);outer.addWidget(buttons)

    def filter(self,text):
        for n in range(self.items.count()):
            row=self.items.item(n);row.setHidden(text.casefold() not in row.text().casefold())

    def selected(self):
        return [self.items.item(n).data(Qt.ItemDataRole.UserRole) for n in range(self.items.count())
                if self.items.item(n).checkState()==Qt.CheckState.Checked]

    def accept(self):
        if not 1<=len(self.selected())<=30:self.status.setText('1〜30件を選んでください。');return
        super().accept()
