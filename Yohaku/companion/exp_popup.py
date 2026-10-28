"""A short, non-activating, click-through EXP label that follows the mascot."""
from collections import deque
import time

from PySide6.QtCore import QEvent,QPoint,QSize,QTimer,Qt
from PySide6.QtGui import QColor,QFont,QFontMetricsF,QImage,QPainter,QPainterPath,QPen
from PySide6.QtWidgets import QWidget

from .growth_content import number

DURATION=1.6


def visual_state(elapsed,animated=True):
    t=max(0.,min(1.,elapsed/DURATION))
    if not animated:return 0.,1.
    opacity=max(0.,min(1.,elapsed/.20,(DURATION-elapsed)/.50))
    return 28*t,opacity


def exp_text(amount):
    places=6 if amount<.01 else 2
    text=f'{amount:.{places}f}'.rstrip('0').rstrip('.')
    return '+'+text+' EXP'


class ExpPopup(QWidget):
    def __init__(self,mascot,allowed=lambda:True,animated=lambda:True,clock=time.monotonic):
        super().__init__(mascot,Qt.WindowType.Tool|Qt.WindowType.FramelessWindowHint|
            Qt.WindowType.WindowStaysOnTopHint|Qt.WindowType.WindowDoesNotAcceptFocus|Qt.WindowType.WindowTransparentForInput)
        self.mascot=mascot;self.allowed=allowed;self.animated=animated;self.clock=clock
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus);self.setFixedSize(184,44)
        self.amount=0.;self.started=0.;self.pending=deque(maxlen=1);self.head_signature=None;self.start_offset=-8.
        self.timer=QTimer(self);self.timer.setInterval(33);self.timer.timeout.connect(self.advance)
        mascot.installEventFilter(self)

    def show_gain(self,amount):
        if not number(amount,0,1e15) or amount<=0 or not self.allowed():return
        if self.timer.isActive():
            if self.pending:self.pending[0]+=amount
            else:self.pending.append(amount)
            return
        self.amount=amount;self.started=self.clock();self.reposition()
        self.show();self.update();self.timer.start()

    def reposition(self):
        rise,_=visual_state(self.clock()-self.started,self.animated())
        signature=(self.mascot.pixmap.cacheKey(),self.mascot.width(),self.mascot.height(),self.mascot.bottom_padding)
        if signature!=self.head_signature:
            self.head_signature=signature
            reference=self.mascot.pixmap.toImage().convertToFormat(QImage.Format.Format_RGBA8888)
            data=bytes(reference.constBits());stride=reference.bytesPerLine();top=0
            for y in range(reference.height()):
                if any(data[y*stride+x*4+3]>=160 for x in range(reference.width())):top=y;break
            size=reference.size().scaled(QSize(self.mascot.width()-6,self.mascot.height()-6),Qt.AspectRatioMode.KeepAspectRatio)
            head=self.mascot.height()-size.height()-self.mascot.bottom_padding+top*size.height()/reference.height()
            # Text baseline is y=30. Start with its lower edge just above the
            # actual head, independent of sprite-sheet transparent margins.
            self.start_offset=head-32
        anchor=self.mascot.frameGeometry();area=self.mascot.screen().availableGeometry()
        x=anchor.center().x()-self.width()//2;y=round(anchor.top()+self.start_offset-rise)
        self.move(max(area.left(),min(x,area.right()-self.width()+1)),max(area.top(),y))

    def advance(self):
        if not self.allowed():self.cancel();return
        if self.clock()-self.started>=DURATION:
            self.timer.stop();self.hide()
            if self.pending:self.show_gain(self.pending.popleft())
            return
        self.reposition();self.update()

    def cancel(self):self.timer.stop();self.pending.clear();self.hide()

    def eventFilter(self,watched,event):
        if watched is self.mascot and event.type()==QEvent.Type.Hide:self.cancel()
        return super().eventFilter(watched,event)

    def paintEvent(self,event):
        _,opacity=visual_state(self.clock()-self.started,self.animated())
        painter=QPainter(self);painter.setRenderHint(QPainter.RenderHint.Antialiasing);painter.setOpacity(opacity)
        font=QFont(self.font());font.setPointSizeF(15);font.setWeight(QFont.Weight.Bold)
        text=exp_text(self.amount);metrics=QFontMetricsF(font)
        if metrics.horizontalAdvance(text)>self.width()-12:
            font.setPointSizeF(15*(self.width()-12)/metrics.horizontalAdvance(text));metrics=QFontMetricsF(font)
        path=QPainterPath();path.addText((self.width()-metrics.horizontalAdvance(text))/2,30,font,text)
        painter.strokePath(path,QPen(QColor('#ffffff'),3.5));painter.fillPath(path,QColor('#28744f'));painter.end()
