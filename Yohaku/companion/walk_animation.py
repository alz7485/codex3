"""Opposite leg phases built from each mascot's existing neutral artwork."""
import math
from PySide6.QtCore import QRect,Qt
from PySide6.QtGui import QPainter,QPixmap,QRegion

# Coordinates in the original 256px neutral cell: body cutoff and two feet.
# Place hips close together in the three-quarter view so either foot can lead.
RIGS={
    'A':dict(cut=212,feet=((109,210,43,39),(165,210,43,39)),hip=3,stride=20,angle=10,lift=10),
    'B':dict(cut=226,feet=((103,224,47,26),(160,224,48,26)),hip=3,stride=22,angle=10,lift=9),
    'E':dict(cut=233,feet=((103,231,54,20),(158,231,59,20)),hip=3,stride=28,angle=8,lift=8),
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
    painter.translate(center+(-rig['hip'] if leg==0 else rig['hip'])+rig['stride']*forward,rig['cut'])
    painter.rotate(-rig['angle']*forward)
    painter.drawPixmap(-foot.width()//2,-2,foot);painter.end()
    bounds=QRegion(layer.mask()).boundingRect()
    if bounds.isEmpty():raise ValueError('Walking foot artwork is empty')
    result=QPixmap(base.size());result.fill(Qt.GlobalColor.transparent)
    painter=QPainter(result)
    painter.drawPixmap(0,round(ground-rig['lift']*lift)-bounds.bottom(),layer);painter.end()
    return result


def walk_frames(base,character,center,ground,neutral_center):
    rig=RIGS[character];result=[]
    for index in range(8):
        phase=index/8
        frame=QPixmap(base.size());frame.fill(Qt.GlobalColor.transparent)
        painter=QPainter(frame)
        # Back leg, near leg, then the unchanged body conceal the hip joins.
        for leg in (1,0):painter.drawPixmap(0,0,foot_layer(base,character,phase,leg,center,ground))
        body=QRect(0,0,base.width(),rig['cut'])
        painter.drawPixmap(body.translated(round(center-neutral_center),0),base,body)
        painter.end();result.append(frame)
    return tuple(result)
