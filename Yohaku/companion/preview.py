"""An isolated preview: no history, notification state or click counters are changed."""
import time
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QComboBox, QMainWindow, QWidget
from .core import CHARACTERS, Notice
from .dialogue import voice_for
from .motion import Motion
from .ui import InteractionBubble, Mascot, box, button, label


class PreviewWindow(QMainWindow):
    def __init__(self, settings, dialogue):
        super().__init__()
        self.settings, self.dialogue = settings, dialogue
        self.setWindowTitle('表情・通知のプレビュー — 余白')
        self.resize(540, 640)
        root = QWidget(objectName='panel')
        self.setCentralWidget(root)
        layout = box(root, 24, 12)
        layout.addWidget(label('表情と吹き出しを試す', 'section'))
        layout.addWidget(label('表示例です。実際の通知・履歴・連打の判定には影響しません。', 'muted', True))
        self.selector = QComboBox()
        for key, title in (('normal', '通常の一言'), ('click_concern', '困る'),
                           ('click_angry', '怒る'), ('mail_received', '新着メール'),
                           ('calendar', '予定'), ('call', '呼び出し')):
            self.selector.addItem(title, key)
        self.selector.setAccessibleName('試す表情・通知')
        layout.addWidget(self.selector)
        layout.addWidget(button('もう一度表示', self.play))
        self.bubble = InteractionBubble()
        self.bubble.setWindowFlags(Qt.WindowType.Widget)
        for key in ('activity', 'settings'):
            self.bubble.buttons[key].setEnabled(False)
            self.bubble.buttons[key].setToolTip('プレビューではこの操作は行いません')
        layout.addWidget(self.bubble, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.mascot = Mascot(100, character=settings.character)
        layout.addWidget(self.mascot, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch()
        self.motion = Motion()
        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self.animate)
        self.last_time = time.monotonic()
        self.selector.currentIndexChanged.connect(self.play)
        self.bubble.selected.connect(self.selected)
        self.bubble.call_requested.connect(self.toggle_choices)

    def selected(self, key):
        if key in ('dismiss', 'hide'):
            self.bubble.dismiss()
            if key == 'hide':
                self.mascot.hide()
        elif key == 'calendar':
            self.selector.setCurrentIndex(self.selector.findData('calendar'))

    def toggle_choices(self):
        if self.bubble.isVisible() and self.bubble.kind == 'menu':
            self.bubble.hide()
        else:
            self.selector.setCurrentIndex(self.selector.findData('call'))
            self.play()

    def play(self, *_):
        self.mascot.set_character(self.settings.character)
        self.mascot.show()
        key = self.selector.currentData()
        bank = self.dialogue.data['phrases'][voice_for(self.settings, self.dialogue.data)]
        topic = {'normal': 'chat', 'calendar': 'calendar_intro'}.get(key, key)
        text = bank[topic][0]
        expression = self.dialogue.rule(topic)['expression']
        if key == 'calendar':
            text += '\n\n14:00–14:30 予定あり（表示例）'
        if key == 'call':
            self.bubble.open_choices(text, CHARACTERS[self.settings.character])
        else:
            kind = 'notification' if key == 'mail_received' else 'calendar' if key == 'calendar' else 'message'
            self.bubble.display(Notice('', text, expression=expression, kind=kind))
        self.bubble.timer.stop()
        self.bubble.setFixedHeight(self.bubble.layout().sizeHint().height())
        self.motion.react(expression, seconds=float('inf'))
        self.motion.face_front(float('inf') if key in ('normal', 'call') else 0)
        self.mascot.frame_index = self.motion.frame()
        self.mascot.previous_frame = None
        self.mascot.update()

    def animate(self):
        now = time.monotonic()
        self.motion.advance(now - self.last_time, 0, 0, 0, False)
        self.last_time = now
        self.mascot.frame_index = self.motion.frame()
        self.mascot.bob, self.mascot.sway, self.mascot.scale_x, self.mascot.scale_y = self.motion.pose()
        self.mascot.update()

    def showEvent(self, event):
        super().showEvent(event)
        self.last_time = time.monotonic()
        self.timer.start()
        self.play()

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)
