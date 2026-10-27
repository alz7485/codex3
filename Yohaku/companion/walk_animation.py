"""Opposite leg phases built from each mascot's existing neutral artwork."""
import math
from PySide6.QtCore import QRect,Qt,QPointF
from PySide6.QtGui import QPainter,QPixmap,QRegion,QPainterPath,QPen,QColor,QLinearGradient,QBrush

# Coordinates in the original 256px neutral cell: body cutoff and two feet.
# Foot textures exclude the body; stems join fixed hips to the moving shoes.
RIGS={
    'A':dict(cut=212,feet=((111,226,38,21),(164,226,39,21)),hip=22,stride=9,angle=7,lift=7,stem=17,speed=16),
    'B':dict(cut=226,feet=((104,228,44,20),(162,228,45,20)),hip=23,stride=10,angle=7,lift=6,stem=14,speed=20),
    'E':dict(cut=233,feet=((106,235,51,14),(162,235,53,14)),hip=28,stride=8,angle=5,lift=6,stem=7,speed=18),
}
WALK_BLEND_SECONDS=.055


def leg_phase(phase,leg):
    value=(phase+(.5 if leg else 0))%1
    # Linear backward stance cancels the body's forward travel on the ground.
    if value<=.5:return 1-4*value,0.
    angle=(value-.5)*math.tau
    return -math.cos(angle),math.sin(angle)


def foot_layer(base,character,phase,leg,center,ground):
    rig=RIGS[character];rect=QRect(*rig['feet'][leg]);foot=base.copy(rect)
    forward,lift=leg_phase(phase,leg)
    layer=QPixmap(base.size());layer.fill(Qt.GlobalColor.transparent)
    painter=QPainter(layer);painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    hip_x=center+(-rig['hip'] if leg==0 else rig['hip'])
    painter.translate(hip_x+rig['stride']*forward,rig['cut'])
    painter.rotate(-rig['angle']*forward)
    painter.drawPixmap(-foot.width()//2,-2,foot);painter.end()
    bounds=QRegion(layer.mask()).boundingRect()
    if bounds.isEmpty():raise ValueError('Walking foot artwork is empty')
    result=QPixmap(base.size());result.fill(Qt.GlobalColor.transparent)
    painter=QPainter(result)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    dy=round(ground-rig['lift']*lift)-bounds.bottom()
    ankle=QPointF(bounds.center().x(),bounds.top()+dy+3)
    bob=-round(1.5*abs(math.sin(math.tau*phase)))
    hip=QPointF(hip_x,rig['cut']-4+bob)
    path=QPainterPath(hip)
    path.quadTo(QPointF(hip_x+rig['stride']*forward*.35,(hip.y()+ankle.y())/2),ankle)
    gradient=QLinearGradient(hip_x-rig['stem']/2,0,hip_x+rig['stem']/2,0)
    gradient.setColorAt(0,QColor('#655f58' if character!='E' else '#293341'))
    gradient.setColorAt(1,QColor('#403b36' if character!='E' else '#1c2530'))
    painter.setPen(QPen(QBrush(gradient),rig['stem'],Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap))
    painter.drawPath(path)
    painter.drawPixmap(0,dy,layer);painter.end()
    return result


def walk_frames(base,character,center,ground,neutral_center):
    rig=RIGS[character];result=[]
    for index in range(8):
        phase=index/8
        frame=QPixmap(base.size());frame.fill(Qt.GlobalColor.transparent)
        painter=QPainter(frame)
        # Back leg, near leg, then the body conceal the anchored hip joins.
        for leg in (1,0):painter.drawPixmap(0,0,foot_layer(base,character,phase,leg,center,ground))
        body=QRect(0,0,base.width(),rig['cut'])
        bob=-round(1.5*abs(math.sin(math.tau*phase)))
        painter.drawPixmap(body.translated(round(center-neutral_center),bob),base,body)
        painter.end();result.append(frame)
    return tuple(result)
