"""A short celebration drawn inside the existing mascot window."""
import math
import time

from PySide6.QtCore import QObject,QRectF,QSize,QTimer,Qt
from PySide6.QtGui import QColor,QPainterPath,QPen

DURATION=2.8


def smooth(value):
    value=max(0.,min(1.,value))
    return value*value*(3-2*value)


def pose(character,elapsed):
    """Return jump, tilt, squash, stretch, expression and effect opacity."""
    t=max(0.,min(DURATION,elapsed))
    envelope=smooth(t/.24)*smooth((DURATION-t)/.30)
    hops,period,height,tilt={'A':(2,.68,.085,4.),'B':(3,.46,.075,3.),'E':(2,.76,.070,9.)}[character]
    phase=(t-.24)/period
    moving=0<=phase<hops
    local=phase%1 if moving else 0.
    jump=math.sin(math.pi*local)**2 if moving else 0.
    landing=math.cos(math.tau*local)*envelope if moving else 0.
    angle=tilt*math.sin(math.tau*local)*envelope if moving else 0.
    scale=1-.10*envelope
    frame=2 if t<.24+hops*period else 6
    if character=='B' and moving and int(phase)%2:frame=9
    return -height*jump,angle,scale*(1+.055*landing),scale*(1-.055*landing),frame,envelope


class LevelUpAnimation(QObject):
    def __init__(self,mascot,clock=time.monotonic):
        super().__init__(mascot)
        self.mascot=mascot;self.clock=clock;self.started=0.;self.active=False
        self.timer=QTimer(self);self.timer.setInterval(16)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer);self.timer.timeout.connect(self.advance)

    def start(self):
        if not self.mascot.isVisible() or not self.mascot.prop_animation_enabled:return
        if (self.mascot.mail_raised or self.mascot.calendar_checking or self.mascot.taking_notes
                or self.mascot.held_icon is not None or getattr(self.mascot,'dragging',False)):return
        self.started=self.clock();self.active=True;self.timer.start();self.mascot.update()

    def cancel(self):
        was_active=self.active;self.active=False;self.timer.stop()
        if was_active:self.mascot.update()

    def advance(self):
        if (not self.mascot.isVisible() or not self.mascot.prop_animation_enabled
                or self.clock()-self.started>=DURATION):self.cancel();return
        self.mascot.update()

    def draw(self,painter,frames):
        mascot=self.mascot;t=self.clock()-self.started
        y,angle,sx,sy,frame,opacity=pose(mascot.character,t)
        image=frames[frame]
        if mascot.costumes is not None:image=mascot.costumes.compose(image,mascot.character,frame)
        # Match the ordinary canvas and baseline; the native window stays still.
        size=image.size().scaled(QSize(mascot.width()-6,mascot.height()-6),Qt.AspectRatioMode.KeepAspectRatio)
        target=QRectF((mascot.width()-size.width())/2,mascot.height()-size.height()-mascot.bottom_padding,size.width(),size.height())
        painter.save();painter.translate(mascot.width()/2,mascot.height()-mascot.bottom_padding+y*mascot.height())
        painter.rotate(angle);painter.scale(sx,sy);painter.translate(-mascot.width()/2,-mascot.height()+mascot.bottom_padding)
        painter.drawPixmap(target,image,QRectF(image.rect()));painter.restore()
        painter.save();painter.setOpacity(opacity);painter.setPen(QPen(QColor('#bd8c27'),1.2));painter.setBrush(QColor('#ffe8a3'))
        for n in range(5):
            side=-1 if n%2 else 1
            x=mascot.width()*(.5+side*(.30+.04*math.sin(t*3+n)))
            cy=mascot.height()*(.13+.125*n)-math.sin(t*3+n)*2
            radius=2.+1.1*math.sin(t*4+n)**2;path=QPainterPath()
            path.moveTo(x,cy-radius*1.5);path.lineTo(x+radius*.45,cy-radius*.4)
            path.lineTo(x+radius*1.2,cy);path.lineTo(x+radius*.45,cy+radius*.4)
            path.lineTo(x,cy+radius*1.5);path.lineTo(x-radius*.45,cy+radius*.4)
            path.lineTo(x-radius*1.2,cy);path.lineTo(x-radius*.45,cy-radius*.4);path.closeSubpath()
            painter.drawPath(path)
        painter.restore()
