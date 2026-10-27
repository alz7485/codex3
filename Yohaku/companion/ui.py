from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
import math
import json
import sqlite3
import sys
import threading
import time

from PySide6.QtCore import QDate, QEvent, QLocale, QLockFile, QObject, QPoint, QRect, QRectF, QSize, Qt, QTime, QTimer, QUrl, Signal
from PySide6.QtGui import QAction, QColor, QCursor, QDesktopServices, QFont, QIcon, QPainter, QPainterPath, QPen, QPixmap, QTransform
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QCalendarWidget, QCheckBox, QComboBox, QFrame, QGridLayout, QHeaderView, QHBoxLayout, QLabel, QMainWindow,
    QMenu, QMessageBox, QPushButton, QScrollArea, QSizePolicy, QStackedWidget, QSystemTrayIcon, QTimeEdit, QDateEdit,
    QToolButton, QSpinBox, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget, QWidgetAction, QLineEdit, QPlainTextEdit, QListWidget, QListWidgetItem,
)

from .core import CHARACTERS, Engine, Notice, PHRASES, Settings, data_directory, is_quiet, save_json
from .activity import FileHistory, FileTracker, opened_file_snapshot
from .motion import Motion
from .dialogue import AUTO_PERSONALITY, BUBBLE_MS, PROFILES, DialogueError, DialogueStore, voice_for
from .characters import profile_for
from .message_format_ui import MessageEditor, MessageLabel
from .outlook import read_calendar
from .metadata import APP_DISPLAY_NAME, VERSION
from .context import ResourceSampler, UsageLedger, input_idle_seconds, desktop_file_count, office_file_count, work_metrics, system_power_metrics
from .advanced_context import ConditionTimeline, meeting_metrics, remaining_meeting_metrics
from .mail import OutlookMailWatcher
from .preferences import PRESETS, snapped_y
from .departure import attendance_url, system_uptime_seconds

STYLE = """
QWidget { color: #263b43; font-size: 13px; }
QMainWindow, QWidget#panel, QWidget#page { background: #fafbf9; }
QWidget#rail { background: #edf1ee; border-right: 1px solid #dfe6e0; }
QLabel { background: transparent; }
QLabel#muted { color: #65736a; font-size: 11px; }
QLabel#eyebrow { color: #69796f; font-size: 10px; font-weight: 600; letter-spacing: 2px; }
QScrollArea { background: #fafbf9; border: none; }
QScrollBar:vertical { width: 8px; background: #f0f3ef; }
QScrollBar::handle:vertical { background: #bac9bb; border-radius: 4px; min-height: 30px; }
QLabel#heading { font-size: 26px; font-weight: 600; color: #263c35; }
QLabel#section { font-size: 14px; font-weight: 600; }
QLabel#badge { color: #557565; background: #e9f1e9; border-radius: 10px; padding: 4px 10px; font-size: 11px; }
QFrame#card { background: #ffffff; border: 1px solid #e1e7e1; border-radius: 14px; }
QFrame#hero { background: #eaf0e9; border: 1px solid #e0e7df; border-radius: 16px; }
QPushButton { background: #ffffff; border: 1px solid #d6ded8; border-radius: 7px; padding: 9px 14px; font-weight: 500; }
QPushButton:hover { background: #f0f4ef; border-color: #a9bcae; }
QPushButton:pressed { background: #e0e9df; }
QPushButton:focus { border: 2px solid #5c7b68; }
QPushButton:disabled { color: #9ba59d; background: #f0f3ef; }
QPushButton#primary { color: white; background: #385c4a; border-color: #385c4a; }
QPushButton#primary:hover { background: #2b4d3c; }
QPushButton#nav { border: none; background: transparent; color: #738079; text-align: left; padding: 12px 16px; }
QPushButton#nav:checked { color: #2f503e; background: #dfe8dd; font-weight: 600; }
QPushButton#nav:hover { background: #e4ebe1; }
QPushButton#link { background: transparent; border: none; color: #52745e; padding: 6px; font-size: 12px; }
QComboBox, QTimeEdit, QDateEdit, QSpinBox, QDoubleSpinBox, QLineEdit { border: 1px solid #d6ded8; background: white; border-radius: 6px; padding: 8px; min-height: 18px; }
QComboBox::drop-down { border: none; width: 23px; }
QCheckBox { spacing: 10px; }
QCheckBox::indicator { width: 18px; height: 18px; border: 1px solid #b9c7bc; border-radius: 5px; background: white; }
QCheckBox::indicator:checked { background: #41664f; border-color: #41664f; image: none; }
QCheckBox::indicator:checked:hover { background: #2f503e; }
QMenu { background: #fafbf9; padding: 6px; border: 1px solid #d6ded8; }
QMenu::item { padding: 8px 22px; border-radius: 4px; }
QMenu::item:selected { background: #e0e9df; }
QToolTip { background: #263c35; color: white; border: none; padding: 5px; }
QToolButton#character { background: #fafbf9; border: 1px solid #dce4dd; border-radius: 10px; padding: 8px 4px; font-size: 11px; }
QToolButton#character:hover { background: #eef3ec; border-color: #8ca994; }
QToolButton#character:checked { background: #e5eee1; border: 2px solid #41664f; color: #2d513b; }
QToolButton#character:focus { border: 2px solid #41664f; }
QCalendarWidget QWidget#qt_calendar_navigationbar { background: #edf1ee; }
QCalendarWidget QToolButton { background: #edf1ee; color: #263b43; border: none; padding: 4px; }
QCalendarWidget QAbstractItemView:enabled { selection-background-color: #385c4a; selection-color: white; }
QPlainTextEdit { background: white; border: 1px solid #d6ded8; border-radius: 7px; padding: 8px; }
QListWidget { background: white; border: 1px solid #dce4dd; border-radius: 7px; outline: none; }
QListWidget::item { padding: 6px 9px; }
QListWidget::item:selected { background: #e5eee1; color: #263b43; }
QTabWidget::pane { border: 1px solid #dce4dd; background: #fafbf9; }
QTabBar::tab { background: #edf1ee; padding: 9px 17px; color: #65736a; }
QTabBar::tab:selected { background: #fafbf9; color: #385c4a; border-top: 2px solid #385c4a; }
QWidget#speechChoiceRow { background: transparent; }
QPushButton#speechChoice { background: #e8f0e6; color: #385b43; border: 1px solid #afc4b2; border-radius: 7px; padding: 7px 10px; font-size: 12px; font-weight: 500; text-align: left; }
QPushButton#speechChoice:hover { background: #d9e8d6; border-color: #7e9e84; }
QPushButton#speechChoice:pressed { background: #c7dcc3; border-color: #5e8166; }
QPushButton#speechChoice:focus { border: 2px solid #52765c; padding: 6px 9px; }
QTreeWidget { background: white; border: 1px solid #e1e7e1; border-radius: 10px; outline: none; }
QTreeWidget::item { padding: 9px 5px; }
QTreeWidget::item:selected { background: #e5eee1; color: #263b43; }
QHeaderView::section { background: #edf1ee; border: none; padding: 9px 5px; color: #5c7262; }
"""


def label(text, name=None, wrap=False):
    result = QLabel(text)
    result.setTextFormat(Qt.TextFormat.PlainText)
    if name:
        result.setObjectName(name)
    result.setWordWrap(wrap)
    return result


def button(text, callback=None, name=None):
    result = QPushButton(text)
    result.setCursor(Qt.CursorShape.PointingHandCursor)
    if callback:
        result.clicked.connect(callback)
    if name:
        result.setObjectName(name)
    return result


@lru_cache(maxsize=5)
def speech_action_icon(action):
    """Small matching line icons, without relying on emoji fonts or external files."""
    icon = QIcon()
    for scale in (1, 2, 3):
        pixmap = QPixmap(20 * scale, 20 * scale)
        pixmap.setDevicePixelRatio(scale)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor('#385b43'), 1.5, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        path = QPainterPath()
        if action == 'calendar':
            painter.drawRoundedRect(QRectF(3, 4, 14, 13), 2, 2)
            painter.drawLine(3, 8, 17, 8)
            painter.drawLine(6, 2, 6, 6)
            painter.drawLine(14, 2, 14, 6)
            painter.drawLine(6, 11, 8, 11)
            painter.drawLine(12, 11, 14, 11)
            painter.drawLine(6, 14, 8, 14)
        elif action == 'activity':
            path.moveTo(2, 6)
            path.lineTo(2, 4)
            path.lineTo(8, 4)
            path.lineTo(10, 6)
            path.lineTo(17, 6)
            path.lineTo(17, 9)
            path.moveTo(2, 6)
            path.lineTo(2, 16)
            path.lineTo(16, 16)
            path.lineTo(19, 9)
            path.lineTo(5, 9)
            path.lineTo(2, 16)
        elif action == 'settings':
            for index in range(32):
                angle = index * math.tau / 32
                radius = 8 if index % 4 in (1, 2) else 6.4
                x, y = 10 + radius * math.cos(angle), 10 + radius * math.sin(angle)
                path.moveTo(x, y) if index == 0 else path.lineTo(x, y)
            path.closeSubpath()
            painter.drawEllipse(QRectF(7, 7, 6, 6))
        elif action == 'hide':
            path.moveTo(2, 10)
            path.cubicTo(6, 3, 14, 3, 18, 10)
            path.cubicTo(14, 17, 6, 17, 2, 10)
            painter.drawEllipse(QRectF(7, 7, 6, 6))
            painter.drawLine(3, 17, 17, 3)
        elif action == 'one_shot':
            path.moveTo(4, 14)
            path.lineTo(5, 12)
            path.lineTo(5, 8)
            path.cubicTo(5, 2, 15, 2, 15, 8)
            path.lineTo(15, 12)
            path.lineTo(16, 14)
            path.closeSubpath()
            painter.drawLine(8, 17, 12, 17)
            painter.drawLine(10, 1, 10, 3)
        painter.drawPath(path)
        painter.end()
        icon.addPixmap(pixmap)
    return icon


def box(parent=None, margins=0, spacing=10):
    layout = QVBoxLayout(parent)
    layout.setContentsMargins(margins, margins, margins, margins)
    layout.setSpacing(spacing)
    return layout


@lru_cache(maxsize=3)
def character_pixmap(character):
    # Reuse the front artwork for thumbnails and the static pose as well.
    # Separate large still-image PNGs are no longer needed in the bundle.
    return character_frames(character)[24]


@lru_cache(maxsize=3)
def character_frames(character):
    path = Path(__file__).parent / "assets" / "characters" / f"{character.lower()}_motion.png"
    sheet = QPixmap(str(path))
    if sheet.isNull():
        raise RuntimeError(f"アニメーション画像を読み込めません: {path.name}")
    width, height = sheet.width() // 6, sheet.height() // 4
    frames = tuple(sheet.copy((i % 6) * width, (i // 6) * height, width, height) for i in range(24))
    # Recorded content rectangles exclude neighboring-cell fragments, while one
    # shared canvas preserves scale and baseline throughout the animation.
    layout = json.loads((path.parent / "motion_layout.json").read_text())
    content = [QRect(*values) for values in layout[character.lower()]]
    bounds = QRect()
    cleaned = []
    for frame, rect in zip(frames, content):
        clipped = QPixmap(frame.size())
        clipped.fill(Qt.GlobalColor.transparent)
        painter = QPainter(clipped)
        painter.drawPixmap(rect, frame, rect)
        painter.end()
        cleaned.append(clipped)
        bounds = bounds.united(rect)
    # The generated walking cells have different origins. Register them to
    # the shared canvas center and neutral ground line, retaining one scale for all
    # eight poses. Otherwise every frame visibly hops and slides sideways.
    for index in range(16, 24):
        rect = content[index]
        aligned = QPixmap(cleaned[index].size())
        aligned.fill(Qt.GlobalColor.transparent)
        painter = QPainter(aligned)
        painter.drawPixmap(bounds.center().x() - rect.center().x(),
                           content[0].bottom() - rect.bottom(), cleaned[index])
        painter.end()
        cleaned[index] = aligned
    frames = tuple(frame.copy(bounds) for frame in cleaned)
    # Dedicated front-view artwork: rows A/B/E plus a separate cat strip,
    # columns normal/blink/
    # troubled/angry. Keep a shared canvas and the existing neutral baseline
    # so switching between a walk and a front pose does not change size.
    front_name = 'front_reactions.png'
    front = QPixmap(str(path.parent / front_name))
    if front.isNull():
        raise RuntimeError(f'正面向き画像を読み込めません: {front_name}')
    left, top, w, h = {'A': (35, 25, 270, 282), 'B': (40, 315, 270, 294),
                       'E': (45, 620, 264, 300)}[character]
    stride = 300
    target = QSize(bounds.width(), content[0].height())
    front_frames = []
    for column in range(4):
        source = front.copy(left + column * stride, top, w, h)
        source = source.scaled(target, Qt.AspectRatioMode.KeepAspectRatio,
                               Qt.TransformationMode.SmoothTransformation)
        frame = QPixmap(bounds.size())
        frame.fill(Qt.GlobalColor.transparent)
        painter = QPainter(frame)
        painter.drawPixmap((bounds.width() - source.width()) // 2,
                           content[0].bottom() - bounds.top() + 1 - source.height(), source)
        painter.end()
        front_frames.append(frame)
    return frames + tuple(front_frames)



def blend_frames(previous, current, progress):
    """Interpolate premultiplied pixels before drawing onto the desktop.

    Two source-over draws dim shared opaque pixels to 75% at the midpoint.
    Adding the weighted frames on a transparent surface preserves their alpha.
    """
    weighted = []
    for source, opacity in ((previous, 1 - progress), (current, progress)):
        frame = QPixmap(source.size())
        frame.fill(Qt.GlobalColor.transparent)
        painter = QPainter(frame)
        painter.setOpacity(opacity)
        painter.drawPixmap(0, 0, source)
        painter.end()
        weighted.append(frame)
    # Apply Plus at full painter opacity; Qt's constant-opacity fast path can
    # otherwise fall back to source-over for opaque source pixmaps.
    result = weighted[0]
    painter = QPainter(result)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
    painter.drawPixmap(0, 0, weighted[1])
    painter.end()
    return result


class Mascot(QWidget):
    """A transparent, smoothly scaled approved character asset."""

    def __init__(self, size=90, parent=None, character="A"):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(size, size)
        self.frame_index = None
        self.flipped = False
        self.bob = 0.0
        self.sway = 0.0
        self.scale_x = self.scale_y = 1.0
        self.subpixel = 0.0
        self.bottom_padding = 3
        self.previous_frame = None
        self.previous_flipped = False
        self.frame_changed_at = 0.0
        self.held_icon = None; self.held_frame = None; self.mail_frame = None; self.mail_raised = False
        self.calendar_frame = None; self.calendar_checking = False
        self.mail_timer = QTimer(self); self.mail_timer.setSingleShot(True)
        self.mail_timer.timeout.connect(self.lower_mail)
        self.calendar_timer = QTimer(self); self.calendar_timer.setSingleShot(True)
        self.calendar_timer.timeout.connect(self.lower_calendar)
        self.prop_animation_enabled = True; self.prop_from = None; self.prop_target = None
        self.prop_started = 0.0
        self.prop_timer = QTimer(self); self.prop_timer.setInterval(16)
        self.prop_timer.timeout.connect(self.advance_prop)
        self.set_character(character)

    def transition_prop(self, previous, target):
        self.prop_timer.stop()
        self.prop_from = previous; self.prop_target = target
        self.prop_started = time.monotonic()
        if self.prop_animation_enabled:
            self.prop_timer.start()
        self.update()

    def advance_prop(self):
        if time.monotonic()-self.prop_started >= .20:
            self.prop_timer.stop(); self.prop_from = self.prop_target = None
        self.update()

    def visible_prop(self):
        return (self.mail_frame if self.mail_raised else self.calendar_frame if self.calendar_checking else self.held_frame) or character_pixmap(self.character)

    def check_calendar(self):
        from .props import prop_frame
        previous = self.visible_prop()
        self.calendar_frame = prop_frame(self.character, character_pixmap(self.character), 'calendar')
        self.calendar_checking = True; self.calendar_timer.start(3500)
        self.transition_prop(previous, self.visible_prop())

    def lower_calendar(self):
        previous = self.visible_prop()
        self.calendar_checking = False
        self.transition_prop(previous, self.visible_prop())

    def clear_props(self):
        self.prop_timer.stop(); self.prop_from = self.prop_target = None
        self.held_icon = None; self.held_frame = None; self.mail_frame = None
        self.mail_timer.stop(); self.mail_raised = False
        self.calendar_timer.stop(); self.calendar_checking = False; self.calendar_frame = None
        self.update()

    def hold_item(self, path):
        from .props import item_icon, prop_frame
        previous = self.visible_prop()
        self.held_icon = item_icon(path)
        self.held_frame = prop_frame(self.character, character_pixmap(self.character), 'file', self.held_icon)
        self.transition_prop(previous, self.visible_prop())

    def raise_mail(self):
        previous = self.visible_prop()
        from .props import prop_frame
        self.mail_frame = prop_frame(self.character, character_pixmap(self.character), 'mail')
        self.mail_raised = True; self.mail_timer.start(2600)
        self.transition_prop(previous, self.visible_prop())

    def lower_mail(self):
        previous = self.visible_prop()
        self.mail_raised = False
        self.transition_prop(previous, self.visible_prop())

    def set_character(self, character):
        self.character = character if character in CHARACTERS else "A"
        self.pixmap = character_pixmap(self.character)
        self.previous_frame = None
        self.prop_timer.stop(); self.prop_from = self.prop_target = None
        if self.calendar_checking:
            from .props import prop_frame
            self.calendar_frame = prop_frame(self.character, self.pixmap, 'calendar')
        if self.held_icon is not None:
            from .props import prop_frame
            self.held_frame = prop_frame(self.character, self.pixmap, 'file', self.held_icon)
        if self.mail_raised:
            from .props import prop_frame
            self.mail_frame = prop_frame(self.character, self.pixmap, 'mail')
        self.setAccessibleName(CHARACTERS[self.character])
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        prop = self.mail_frame if self.mail_raised else self.calendar_frame if self.calendar_checking else self.held_frame
        if self.prop_timer.isActive() and self.prop_from is not None:
            progress = min(1., max(0., (time.monotonic()-self.prop_started)/.20))
            progress = progress*progress*(3-2*progress)
            prop = blend_frames(self.prop_from, self.prop_target, progress)
        if prop is not None:
            size = prop.size().scaled(QSize(self.width()-6, self.height()-6), Qt.AspectRatioMode.KeepAspectRatio)
            target = QRectF((self.width()-size.width())/2, self.height()-size.height()-self.bottom_padding, size.width(), size.height())
            p.drawPixmap(target, prop, QRectF(prop.rect())); p.end(); return
        p.translate(self.subpixel, self.bob)
        p.translate(self.width() / 2, self.height() - 4)
        p.rotate(self.sway)
        p.scale(self.scale_x, self.scale_y)
        p.translate(-self.width() / 2, -self.height() + 4)
        frames = character_frames(self.character)
        pixmap = self.pixmap if self.frame_index is None else frames[self.frame_index]
        if self.flipped and (self.frame_index is None or self.frame_index < 24):
            pixmap = pixmap.transformed(QTransform().scale(-1, 1))
        blend = min(1.0, max(0.0, (time.monotonic() - self.frame_changed_at) / 0.085))
        if self.previous_frame is not None and self.frame_index is not None and blend < 1:
            previous = frames[self.previous_frame]
            if self.previous_flipped and self.previous_frame < 24:
                previous = previous.transformed(QTransform().scale(-1, 1))
            pixmap = blend_frames(previous, pixmap, blend)
        size = pixmap.size().scaled(QSize(self.width() - 6, self.height() - 6), Qt.AspectRatioMode.KeepAspectRatio)
        target = QRectF((self.width() - size.width()) / 2,
                       self.height() - size.height() - self.bottom_padding, size.width(), size.height())
        p.drawPixmap(target, pixmap, QRectF(pixmap.rect()))
        p.end()



class Panel(QMainWindow):
    changed = Signal(str)
    preset_requested = Signal(str)
    preview_requested = Signal()
    connect_requested = Signal()
    sample_requested = Signal()
    pause_requested = Signal()
    hide_requested = Signal()
    clear_history_requested = Signal()
    dialogue_requested = Signal()
    reminders_requested = Signal()
    clear_usage_requested = Signal()
    context_options_requested = Signal()
    file_drop_requested = Signal()

    def __init__(self, settings, dialogue=None):
        super().__init__()
        self.settings = settings
        self.dialogue = dialogue
        self.setWindowTitle("Yohaku — デスクトップの小さな同僚")
        self.setMinimumSize(880, 680)
        self.resize(920, 740)
        root = QWidget(objectName="panel")
        self.setCentralWidget(root)
        horizontal = QHBoxLayout(root)
        horizontal.setContentsMargins(0, 0, 0, 0)
        horizontal.setSpacing(0)
        rail = QWidget(objectName="rail")
        rail.setFixedWidth(190)
        left = box(rail, 22, 9)
        left.addSpacing(10)
        brand = label("Yohaku")
        brand.setStyleSheet("font-size: 28px; font-weight: 600; letter-spacing: 1px;")
        left.addWidget(brand)
        left.addWidget(label("DESKTOP COMPANION", "eyebrow"))
        left.addSpacing(43)
        self.tabs = []
        self.pages = QStackedWidget()
        for index, title in enumerate(("今日のようす", "キャラと通知")):
            tab = button(title, lambda checked=False, i=index: self.set_page(i), "nav")
            tab.setCheckable(True)
            left.addWidget(tab)
            self.tabs.append(tab)
        left.addStretch()
        self.rail_mascot = Mascot(78, character=settings.character)
        left.addWidget(self.rail_mascot, alignment=Qt.AlignmentFlag.AlignLeft)
        left.addWidget(label("ちょうどいい距離の、\n小さな同僚。", wrap=True))
        left.addSpacing(10)
        left.addWidget(label(f"LOCAL ONLY  /  v{VERSION}", "eyebrow"))
        horizontal.addWidget(rail)
        horizontal.addWidget(self.pages, 1)
        self.build_today()
        self.build_settings()
        self.set_page(0)

    def profile(self, key):
        if self.dialogue is None:
            return PROFILES[key]
        p = profile_for(self.dialogue.data['profiles'], key)
        return p['voice'], p['description'], p['tagline']

    def voice(self):
        return voice_for(self.settings, self.dialogue.data if self.dialogue else None)

    def quote(self):
        if self.settings.personality == AUTO_PERSONALITY:
            return self.profile(self.settings.character)[2]
        bank = self.dialogue.data['phrases'] if self.dialogue else PHRASES
        return bank[self.voice()]['chat'][0]

    def refresh_dialogue(self):
        self.personality_badge.setText(self.voice())
        p = self.profile(self.settings.character)
        self.profile_description.setText(p[1])
        self.hero_quote.setText(self.quote())
        self.interval_spin.blockSignals(True)
        self.interval_spin.setValue(self.settings.interval)
        self.interval_spin.blockSignals(False)

    def set_page(self, index):
        self.pages.setCurrentIndex(index)
        for i, tab in enumerate(self.tabs):
            tab.setChecked(i == index)

    def page(self, eyebrow, title, subtitle):
        page = QWidget(objectName="page")
        layout = box(page, 30, 15)
        layout.addWidget(label(eyebrow, "eyebrow"))
        layout.addWidget(label(title, "heading"))
        layout.addWidget(label(subtitle, "muted", True))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(page)
        self.pages.addWidget(scroll)
        return layout

    def build_today(self):
        layout = self.page("YOUR QUIET COMPANY", "お仕事に、ひと呼吸。", "予定はそっと。小言はほどほどに。")
        layout.addSpacing(3)
        hero = QFrame(objectName="hero")
        h = QHBoxLayout(hero)
        h.setContentsMargins(20, 18, 24, 18)
        h.setSpacing(22)
        self.hero_mascot = Mascot(108, character=self.settings.character)
        h.addWidget(self.hero_mascot)
        words = box(spacing=9)
        self.personality_badge = label(self.voice(), "badge")
        words.addWidget(self.personality_badge, alignment=Qt.AlignmentFlag.AlignLeft)
        self.hero_quote = quote = label(self.quote(), wrap=True)
        quote.setStyleSheet("font-size: 18px; line-height: 1.6;")
        words.addWidget(quote)
        self.character_caption = label(CHARACTERS[self.settings.character] + " · セリフの表示例", "muted")
        words.addWidget(self.character_caption)
        h.addLayout(words, 1)
        layout.addWidget(hero)
        row = QHBoxLayout()
        row.addWidget(label("予定のお知らせ", "section"))
        row.addStretch()
        row.addWidget(label("開始10分前に、ひとこと", "muted"))
        layout.addLayout(row)
        calendar = QFrame(objectName="card")
        content = box(calendar, 18, 8)
        connection_row = QHBoxLayout()
        self.status_label = label("○  Outlookは未接続")
        self.status_label.setStyleSheet("font-weight: 600;")
        connection_row.addWidget(self.status_label)
        connection_row.addStretch()
        self.connect_button = button("Outlookに接続", self.connect_requested.emit, "primary")
        connection_row.addWidget(self.connect_button)
        content.addLayout(connection_row)
        self.calendar_detail = label("従来版Outlookを開いてから接続してください。", "muted", True)
        content.addWidget(self.calendar_detail)
        self.event_summary = label("予定の件名は、初期設定では表示しません。", wrap=True)
        self.event_summary.setStyleSheet("font-size: 12px; color: #65766b; padding-top: 5px;")
        content.addWidget(self.event_summary)
        layout.addWidget(calendar)
        row = QHBoxLayout()
        row.addWidget(label("今は、静かに。", "section"))
        row.addStretch()
        self.mode_label = label("通常モード", "muted")
        row.addWidget(self.mode_label)
        layout.addLayout(row)
        controls = QHBoxLayout()
        self.pause_button = button("1時間おやすみ", self.pause_requested.emit)
        self.share_button = button("画面共有モード", self.hide_requested.emit)
        self.share_button.setToolTip("すべての表示と通知を停止します。トレイから解除できます。")
        controls.addWidget(self.pause_button)
        controls.addWidget(self.share_button)
        layout.addLayout(controls)
        layout.addWidget(label("おやすみ中は予定通知も停止。画面共有モードはトレイから解除できます。", "muted", True))
        layout.addStretch()
        footer = QHBoxLayout()
        footer.addWidget(label("外部AIなし · 予定と設定はこのPCの中に", "muted"))
        footer.addStretch()
        footer.addWidget(button("通知を試す  ↗", self.sample_requested.emit, "link"))
        layout.addLayout(footer)

    def build_settings(self):
        layout = self.page("MAKE YOURSELF COMFORTABLE", "ちょうどいい距離感に。", "声をかける頻度も、ちょっとした性格も。")
        layout.setSpacing(12)
        card = QFrame(objectName="card")
        chooser = box(card, 18, 10)
        chooser.addWidget(label("いっしょに働くキャラクター", "section"))
        chooser.addWidget(label("選ぶとすぐに切り替わります。性格は下で別々に選べます。", "muted", True))
        self.preset_combo = QComboBox()
        for key, (title, _, _) in PRESETS.items():
            self.preset_combo.addItem(title, key)
        self.preset_combo.addItem('カスタム', 'custom')
        self.preset_combo.setCurrentIndex(self.preset_combo.findData(self.settings.comfort_preset))
        self.preset_combo.setAccessibleName('会話と動きのプリセット')
        self.preset_combo.currentIndexChanged.connect(lambda _: self.preset_requested.emit(self.preset_combo.currentData()))
        chooser.addWidget(label('会話と動きのプリセット', 'section'))
        chooser.addWidget(self.preset_combo)
        chooser.addWidget(label('標準：10分ごと・歩行あり／控えめ：30分ごと・歩行なし／通知だけ：自動雑談と動きを停止。手動の一言は使えます。', 'muted', True))
        row = QGridLayout()
        row.setSpacing(8)
        self.character_buttons = {}
        self.character_group = QButtonGroup(self)
        self.character_group.setExclusive(True)
        for index, (key, name) in enumerate(CHARACTERS.items()):
            choice = QToolButton()
            choice.setObjectName("character")
            choice.setText(name)
            choice.setIcon(QIcon(character_pixmap(key)))
            choice.setIconSize(QSize(68, 68))
            choice.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            choice.setCheckable(True)
            choice.setChecked(key == self.settings.character)
            choice.setMinimumHeight(108)
            choice.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            choice.setCursor(Qt.CursorShape.PointingHandCursor)
            choice.setAccessibleName(f"キャラクター {name}")
            choice.clicked.connect(lambda checked=False, k=key: self.update_setting("character", k))
            self.character_group.addButton(choice)
            self.character_buttons[key] = choice
            row.addWidget(choice, index // 3, index % 3)
        chooser.addLayout(row)
        self.profile_description = label(self.profile(self.settings.character)[1], "muted", True)
        chooser.addWidget(self.profile_description)
        chooser.addWidget(button('ドロップしたファイルの処理を設定', self.file_drop_requested.emit))
        chooser.addWidget(label('ファイルやフォルダーを渡すと移動先を選べます。PDFはA4・A3・用紙に合わせる印刷も選べます。', 'muted', True))
        self.animation_check = QCheckBox("表情・まばたきのアニメーション")
        self.animation_check.setChecked(self.settings.animation)
        self.animation_check.toggled.connect(lambda v: self.update_setting("animation", v))
        chooser.addWidget(self.animation_check)
        self.walking_check = QCheckBox("こまめに、置いた高さを歩く")
        self.walking_check.setChecked(self.settings.walking)
        self.walking_check.setEnabled(self.settings.animation)
        self.walking_check.toggled.connect(lambda v: self.update_setting("walking", v))
        chooser.addWidget(self.walking_check)
        self.snap_check = QCheckBox('下端近くで離すとタスクバー直上にそろえる')
        self.snap_check.setChecked(self.settings.snap_to_taskbar)
        self.snap_check.toggled.connect(lambda value: self.update_setting('snap_to_taskbar', value))
        chooser.addWidget(self.snap_check)
        self.snap_spin = QSpinBox()
        self.snap_spin.setRange(4, 48)
        self.snap_spin.setSuffix(' px以内で吸着')
        self.snap_spin.setValue(self.settings.snap_distance)
        self.snap_spin.setAccessibleName('タスクバーに吸着する距離')
        self.snap_spin.valueChanged.connect(lambda value: self.update_setting('snap_distance', value))
        chooser.addWidget(self.snap_spin)
        chooser.addWidget(button('表情・通知のプレビュー', self.preview_requested.emit))
        chooser.addWidget(label("静かな時間や別の設定画面を開いている間も歩きます。呼び出し・吹き出しの操作・連打への反応中と、おやすみ中は止まります。", "muted", True))
        layout.addWidget(card)
        card = QFrame(objectName="card")
        form = box(card, 18, 11)
        row = QHBoxLayout()
        row.addWidget(label("キャラの性格", "section"))
        row.addStretch()
        personality = QComboBox()
        personality.addItems([AUTO_PERSONALITY, *PHRASES])
        personality.setCurrentText(self.settings.personality)
        personality.setAccessibleName("キャラの性格")
        personality.currentTextChanged.connect(lambda v: self.update_setting("personality", v))
        row.addWidget(personality)
        form.addLayout(row)
        chat = QCheckBox("ときどき、ひとこと話しかける")
        self.chatter_check = chat
        chat.setChecked(self.settings.chatter)
        chat.toggled.connect(lambda v: self.update_setting("chatter", v))
        form.addWidget(chat)
        row = QHBoxLayout()
        row.addWidget(label("雑談の間隔"))
        row.addStretch()
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 1440)
        self.interval_spin.setSuffix(' 分')
        self.interval_spin.setValue(self.settings.interval)
        self.interval_spin.setAccessibleName('雑談の間隔')
        self.interval_spin.valueChanged.connect(lambda value: self.update_setting('interval', value))
        row.addWidget(self.interval_spin)
        form.addLayout(row)
        form.addWidget(label("初期設定は約10分ごと。通常メッセージは20秒、メール・予定などの通知は1分表示します。会議中・非表示中は自動会話を休みます。", "muted", True))
        form.addWidget(button("会話文・発生ルールを編集", self.dialogue_requested.emit))
        layout.addWidget(card)
        monitor = QFrame(objectName='card')
        monitor_box = box(monitor, 18, 10)
        monitor_box.addWidget(label('PCの状態と受信通知', 'section'))
        self.context_check = QCheckBox('操作時間・ファイル件数・CPUとメモリ使用率を会話に使う')
        self.context_check.setChecked(self.settings.context_enabled)
        self.context_check.toggled.connect(lambda value: self.update_setting('context_enabled', value))
        monitor_box.addWidget(self.context_check)
        monitor_box.addWidget(label('入力内容は記録せず、最後の操作からの秒数で推定します。Office文書数・デスクトップ件数・PC全体のCPUとメモリ使用率も使います。使用率はアプリ起動中だけ確認し、保存しません。', 'muted', True))
        self.context_status = label('集計を準備しています。', 'muted', True)
        monitor_box.addWidget(self.context_status)
        monitor_box.addWidget(button('休日・対象ファイル・話題の表示を設定',self.context_options_requested.emit))
        self.advanced_context_status=label('', 'muted', True)
        monitor_box.addWidget(self.advanced_context_status)
        monitor_box.addWidget(button('操作時間・アプリ使用日の集計を削除', self.clear_usage_requested.emit))
        self.mail_check = QCheckBox('Outlook接続中、新着メール・会議依頼をすぐ知らせる')
        self.mail_check.setChecked(self.settings.mail_enabled)
        self.mail_check.toggled.connect(lambda value: self.update_setting('mail_enabled', value))
        monitor_box.addWidget(self.mail_check)
        monitor_box.addWidget(label('新着は「メールが届きました」と通知します。送信者名・新着件数は表示せず、送信者・件名・本文は読みません。直後の連続受信は同じ通知にまとめます。未読がたまると通常会話で件数をお知らせします。', 'muted', True))
        self.mail_status = label('受信通知はOutlook接続後に開始します。', 'muted', True)
        monitor_box.addWidget(self.mail_status)
        layout.addWidget(monitor)
        departure = QFrame(objectName='card')
        departure_box = box(departure, 18, 10)
        departure_box.addWidget(label('退勤前のお知らせ', 'section'))
        self.departure_check = QCheckBox('指定した時刻に知らせる')
        self.departure_check.setChecked(self.settings.departure_enabled)
        departure_box.addWidget(self.departure_check)
        self.departure_weekdays = QCheckBox('営業日だけ（祝日・会社休日を除く）')
        self.departure_weekdays.setChecked(self.settings.departure_weekdays)
        departure_box.addWidget(self.departure_weekdays)
        self.departure_time = QTimeEdit(QTime.fromString(self.settings.departure_time, 'HH:mm'))
        self.departure_time.setDisplayFormat('HH:mm')
        self.departure_time.setAccessibleName('退勤前に知らせる時刻')
        departure_box.addWidget(self.departure_time)
        departure_box.addWidget(label('メッセージ'))
        self.departure_message = QPlainTextEdit(self.settings.departure_message)
        self.departure_message.setMaximumHeight(85)
        self.departure_message.setAccessibleName('退勤前のメッセージ')
        departure_box.addWidget(self.departure_message)
        departure_box.addWidget(label('勤怠入力サイトのURL'))
        self.attendance_url = QLineEdit(self.settings.attendance_url)
        self.attendance_url.setMaxLength(2048)
        self.attendance_url.setPlaceholderText('https:// （利用者が入力）')
        self.attendance_url.setAccessibleName('勤怠入力サイトのURL')
        departure_box.addWidget(self.attendance_url)
        departure_box.addWidget(label('1日1回、指定時刻から10分以内に表示します。Windowsの起動時刻と経過時間を添え、サイトを開くか選べます。サイトの入力・送信は行いません。', 'muted', True))
        departure_box.addWidget(button('退勤前通知の設定を保存', self.save_departure_fields))
        self.departure_status = label('', 'muted', True)
        departure_box.addWidget(self.departure_status)
        layout.addWidget(departure)
        reminders = QFrame(objectName='card')
        reminders_box = box(reminders, 18, 10)
        reminders_box.addWidget(label('自分で登録する通知', 'section'))
        reminders_box.addWidget(label('月末や毎月の締め日を指定できます。「営業日」は祝日・会社休日を除外します。次回の対象日も確認できます。', 'muted', True))
        reminders_box.addWidget(button('通知を登録・編集', self.reminders_requested.emit))
        self.reminders_status = label('', 'muted', True)
        reminders_box.addWidget(self.reminders_status)
        layout.addWidget(reminders)
        activity = QFrame(objectName="card")
        activity_box = box(activity, 18, 10)
        activity_box.addWidget(label("開いたファイルの履歴", "section"))
        self.logging_check = QCheckBox("開いたファイルの履歴を記録する（3か月・最大15,000件）")
        self.logging_check.setChecked(self.settings.file_logging)
        self.logging_check.toggled.connect(lambda v: self.update_setting("file_logging", v))
        activity_box.addWidget(self.logging_check)
        activity_box.addWidget(label("ファイル名・保存先・確認した時刻を、このPCだけに保存します。Excel等のOfficeとWindowsの最近使ったファイルを確認し、文書の内容は読みません。", "muted", True))
        activity_box.addWidget(label("5秒間隔の確認です。すべてのファイルを漏れなく記録する機能ではありません。", "muted", True))
        activity_box.addWidget(label("表示時刻は初回確認・最近使ったファイルの更新時刻の目安です。", "muted", True))
        self.activity_status = label("記録オフ", "muted", True)
        activity_box.addWidget(self.activity_status)
        activity_box.addWidget(button("保存した履歴をすべて削除", self.clear_history_requested.emit), alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(activity)
        card = QFrame(objectName="card")
        quiet = box(card, 18, 9)
        quiet.addWidget(label("静かな時間", "section"))
        quiet.addWidget(label("この時間帯は、予定通知も雑談もおやすみします。キャラの歩行・表情は続きます。", "muted", True))
        row = QHBoxLayout()
        for index, key in enumerate(("quiet_start", "quiet_end")):
            edit = QTimeEdit(QTime.fromString(getattr(self.settings, key), "HH:mm"))
            edit.setDisplayFormat("HH:mm")
            edit.setAccessibleName("静かな時間の" + ("開始" if index == 0 else "終了"))
            edit.timeChanged.connect(lambda value, k=key: self.update_setting(k, value.toString("HH:mm")))
            row.addWidget(edit, 1)
            if index == 0:
                row.addWidget(label("〜"))
        quiet.addLayout(row)
        quiet.addWidget(label("毎日適用 · 開始と終了を同じ時刻にすると、時間帯指定を解除します。", "muted", True))
        layout.addWidget(card)
        titles = QCheckBox("通知とこの画面に予定の件名を表示する")
        titles.setChecked(self.settings.show_titles)
        titles.toggled.connect(lambda v: self.update_setting("show_titles", v))
        layout.addWidget(titles)
        layout.addWidget(label("初期設定は非表示。会議の時刻だけでも、お知らせできます。", "muted", True))
        layout.addStretch()
        self.saved_label = label("設定は自動でこのPCに保存されます。音声・効果音はありません。", "muted", True)
        layout.addWidget(self.saved_label)

    def update_setting(self, key, value):
        setattr(self.settings, key, value)
        if key in ('animation', 'walking', 'chatter', 'interval'):
            self.settings.comfort_preset = 'custom'
            self.sync_behavior()
        self.personality_badge.setText(self.voice())
        if key == "character":
            self.rail_mascot.set_character(value)
            self.hero_mascot.set_character(value)
            self.character_buttons[value].setChecked(True)
            self.character_caption.setText(CHARACTERS[value] + " · セリフの表示例")
            self.profile_description.setText(self.profile(value)[1])
        if key in ('character', 'personality'):
            self.hero_quote.setText(self.quote())
        if key == "animation":
            self.walking_check.setEnabled(value)
        self.changed.emit(key)

    def sync_behavior(self):
        for widget, value in ((self.animation_check, self.settings.animation),
                              (self.walking_check, self.settings.walking),
                              (self.chatter_check, self.settings.chatter)):
            widget.blockSignals(True)
            widget.setChecked(value)
            widget.blockSignals(False)
        self.walking_check.setEnabled(self.settings.animation)
        self.preset_combo.blockSignals(True)
        self.preset_combo.setCurrentIndex(self.preset_combo.findData(self.settings.comfort_preset))
        self.preset_combo.blockSignals(False)
        self.refresh_dialogue()

    def save_departure_fields(self):
        try:
            url = attendance_url(self.attendance_url.text())
            message = self.departure_message.toPlainText().strip()
            if not message or len(message) > 1000:
                raise ValueError('メッセージは1〜1,000文字で入力してください。')
        except ValueError as error:
            self.departure_status.setText(str(error))
            return
        self.settings.departure_enabled = self.departure_check.isChecked()
        self.settings.departure_weekdays = self.departure_weekdays.isChecked()
        self.settings.departure_time = self.departure_time.time().toString('HH:mm')
        self.settings.departure_message = message
        self.settings.attendance_url = url
        self.departure_status.setText('退勤前通知の設定を反映しました。')
        self.changed.emit('departure')

    def closeEvent(self, event):
        event.ignore()
        self.hide()


class Resident(Mascot):
    clicked = Signal()
    context_requested = Signal(object)
    dragged = Signal(object)
    drag_finished = Signal()
    file_dropped = Signal(str)

    def __init__(self, character="A"):
        super().__init__(82, character=character)
        self.bottom_padding = 0
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Yohaku · 左クリックで一言／右クリックで呼び出し／ドラッグで移動")
        self.press_position = None
        self.press_origin = None
        self.dragging = False
        self.drop_hover = False
        self.drop_allowed = lambda: True
        self.setAcceptDrops(True)

    @staticmethod
    def dropped_path(event):
        urls = event.mimeData().urls() if event.mimeData().hasUrls() else []
        path = urls[0].toLocalFile() if len(urls) == 1 and urls[0].isLocalFile() else ''
        return path if path and Path(path).is_absolute() else ''

    def dragEnterEvent(self, event):
        if self.drop_allowed() and self.dropped_path(event) and event.possibleActions() & Qt.DropAction.CopyAction:
            self.drop_hover = True
            event.setDropAction(Qt.DropAction.CopyAction); event.accept()
        else:
            self.drop_hover = False
            event.ignore()

    def dragMoveEvent(self, event):
        self.dragEnterEvent(event)

    def dragLeaveEvent(self, event):
        self.drop_hover = False; event.accept()

    def dropEvent(self, event):
        self.drop_hover = False
        path = self.dropped_path(event)
        if self.drop_allowed() and path and event.possibleActions() & Qt.DropAction.CopyAction:
            event.setDropAction(Qt.DropAction.CopyAction); event.accept()
            self.file_dropped.emit(path)
        else:
            event.ignore()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.context_requested.emit(event.globalPosition().toPoint())
        elif event.button() == Qt.MouseButton.LeftButton:
            self.press_position = event.globalPosition().toPoint()
            self.press_origin = self.pos()
            self.dragging = False
        event.accept()

    def mouseMoveEvent(self, event):
        if self.press_position is not None and event.buttons() & Qt.MouseButton.LeftButton:
            delta = event.globalPosition().toPoint() - self.press_position
            if self.dragging or delta.manhattanLength() >= QApplication.startDragDistance():
                self.dragging = True
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
                self.dragged.emit(self.press_origin + delta)
        event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.press_position is not None:
            was_dragging = self.dragging
            self.press_position = None
            self.dragging = False
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            if was_dragging:
                self.drag_finished.emit()
            elif self.rect().contains(event.position().toPoint()):
                self.clicked.emit()
        event.accept()

    def hideEvent(self, event):
        # Hiding while the button is down may prevent delivery of its release.
        # Do not carry that press into the next visible session.
        self.press_position = self.press_origin = None
        self.dragging = False
        self.drop_hover = False
        self.clear_props()
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        super().hideEvent(event)


class Bubble(QFrame):
    call_requested = Signal()
    calendar_presented = Signal()
    content_changing = Signal()
    dismissed = Signal()
    hidden = Signal()

    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setObjectName("card")
        self.setFixedWidth(322)
        self.duration_ms = BUBBLE_MS
        self.kind = "message"
        self.notice = None
        self.tail_x = 270
        self.tail_above = False
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(lambda _: self.call_requested.emit())
        layout = box(self, 18, 10)
        layout.setContentsMargins(18, 14, 18, 30)
        # Retain notice metadata for previews; no header or close button is laid out.
        self.heading = label('', 'muted')
        self.heading.setParent(self)
        self.heading.hide()
        self.text = MessageLabel()
        self.text.setTextFormat(Qt.TextFormat.PlainText)
        self.text.setStyleSheet("font-size: 14px;")
        layout.addWidget(self.text)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide)
        for widget in (self, self.text):
            widget.installEventFilter(self)

    def eventFilter(self, watched, event):
        if (event.type() == QEvent.Type.MouseButtonRelease
                and event.button() == Qt.MouseButton.LeftButton
                and not getattr(self, 'interactive', False)):
            self.dismiss()
            return True
        return super().eventFilter(watched, event)

    def dismiss(self):
        self.timer.stop()
        self.hide()
        self.dismissed.emit()

    def hideEvent(self, event):
        super().hideEvent(event)
        self.hidden.emit()

    def set_tail_above(self, above):
        self.tail_above = above
        vertical = 10
        self.layout().setContentsMargins(18, vertical + (12 if above else 0),
                                        18, vertical + (0 if above else 12))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        fill, stroke = {'message': ('#ffffff', '#dce5dc'), 'menu': ('#f2f6ef', '#b6c9b2'),
                        'calendar': ('#fff3d4', '#cfb16c'), 'notification': ('#e7f1ff', '#8caed1'),
                        'reminder': ('#e7f1ff', '#8caed1'),
                        'departure': ('#fff0dd', '#cf9a61')}[self.kind]
        painter.setBrush(QColor(fill))
        painter.setPen(QPen(QColor(stroke), 1))
        shape = QPainterPath()
        shape.addRoundedRect(QRectF(self.rect()).adjusted(0.5, 12.5 if self.tail_above else 0.5,
                                                       -0.5, -0.5 if self.tail_above else -12.5), 13, 13)
        tail = QPainterPath()
        base, tip = (14, 1) if self.tail_above else (self.height() - 14, self.height() - 1)
        tail.moveTo(self.tail_x - 10, base)
        tail.lineTo(self.tail_x + 10, base)
        tail.lineTo(self.tail_x, tip)
        tail.closeSubpath()
        painter.drawPath(shape.united(tail))

    def set_kind(self, kind):
        self.kind = kind if kind in ('message', 'menu', 'calendar', 'notification', 'departure', 'reminder') else 'message'
        self.heading.hide()
        self.text.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction if self.kind == 'message'
                                         else Qt.TextInteractionFlag.TextSelectableByMouse)
        self.set_tail_above(self.tail_above)
        self.update()

    def display(self, notice):
        self.content_changing.emit()
        self.notice = notice
        self.set_kind('calendar' if notice.important and notice.kind == 'message' else notice.kind)
        self.heading.setText(notice.heading)
        if notice.important or notice.kind in ('calendar','notification','reminder','departure'):
            self.text.set_message(notice.text, styles=notice.styles)
        else:
            self.text.setText(notice.text)
        self.layout().activate()
        self.resize(self.width(), self.layout().sizeHint().height())
        self.show()
        self.timer.start(self.display_duration_ms())

    def display_duration_ms(self):
        notice = self.notice
        return 60000 if notice is not None and (notice.important or notice.kind in ('notification', 'reminder', 'departure')) else self.duration_ms


class Bridge(QObject):
    result = Signal(int, object, str)


class PopupDateEdit(QDateEdit):
    """Open a calendar from the whole date field, including its text area."""
    opening = Signal()
    chosen = Signal()
    def __init__(self, day):
        super().__init__(day)
        self.setCalendarPopup(True)
        self.date_popup = QMenu(self)
        self.popup_calendar = QCalendarWidget()
        action = QWidgetAction(self.date_popup);action.setDefaultWidget(self.popup_calendar)
        self.date_popup.addAction(action)
        self.popup_calendar.clicked.connect(self.choose_date)
        self.popup_calendar.activated.connect(self.choose_date)
        self.lineEdit().installEventFilter(self)

    def choose_date(self, day):
        if self.minimumDate() <= day <= self.maximumDate():
            self.setDate(day);self.date_popup.hide()
            self.chosen.emit()

    def show_calendar(self):
        self.opening.emit()
        self.popup_calendar.setDateRange(self.minimumDate(), self.maximumDate())
        self.popup_calendar.setSelectedDate(self.date())
        self.date_popup.popup(self.mapToGlobal(QPoint(0, self.height())))
        self.popup_calendar.setFocus()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.show_calendar();event.accept()
        else:
            super().mousePressEvent(event)

    def eventFilter(self, watched, event):
        if watched is self.lineEdit() and event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            self.show_calendar();return True
        return super().eventFilter(watched, event)

    def hideEvent(self, event):
        self.date_popup.hide()
        super().hideEvent(event)


class ReminderTimeEdit(QLineEdit):
    """Edit the whole HH:mm value without QTimeEdit's section replacement."""
    def __init__(self, clock):
        super().__init__()
        self._minimum = QTime(0, 0)
        self.setInputMask('00:00;_')
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setToolTip('24時間表記で入力します（例：09:05、17:30）。時刻全体の貼り付けもできます。')
        self.setTime(clock)

    def time(self):
        return QTime.fromString(self.text(), 'HH:mm')

    def setTime(self, clock):
        self.setText(clock.toString('HH:mm'))

    def setMinimumTime(self, clock):
        self._minimum = clock

    def minimumTime(self):
        return self._minimum


class InteractionBubble(Bubble):
    """The usual speech bubble with five actions and passive left-click remarks."""
    selected = Signal(str)
    attendance_requested = Signal()
    file_requested = Signal(str)
    one_shot_requested = Signal()
    file_action_requested = Signal(str)
    file_settings_requested = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowFlag(Qt.WindowType.WindowDoesNotAcceptFocus, False)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.current = None
        self.interactive = False
        layout = self.layout()
        layout.removeWidget(self.text)
        self.content_scroll = QScrollArea()
        self.content_scroll.setWidgetResizable(True)
        self.content_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.content_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.content_scroll.setStyleSheet("QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; }")
        self.content_scroll.setWidget(self.text)
        self.available_height = None
        self.text.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.content_scroll)
        self.file_links=QListWidget()
        self.file_links.setAccessibleName('今日開いたファイルのリンク。クリックすると開きます')
        self.file_links.setCursor(Qt.CursorShape.PointingHandCursor)
        self.file_links.setStyleSheet('QListWidget { background: transparent; border: none; } QListWidget::item { padding: 2px 2px; }')
        self.file_links.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.file_links.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.file_links.itemClicked.connect(lambda item:self.file_requested.emit(item.data(Qt.ItemDataRole.UserRole)))
        layout.addWidget(self.file_links);self.file_links.hide()
        self.choice_row = QWidget(objectName="speechChoiceRow")
        choices = QVBoxLayout(self.choice_row)
        choices.setContentsMargins(0, 0, 0, 0)
        choices.setSpacing(6)
        self.buttons = {}
        for key, title in (("calendar", "予定を聞く"), ("activity", "ファイル起動履歴を見る"), ("settings", "設定を開く"), ("one_shot", "通知を設定する"), ("hide", "非表示にする")):
            choice = button(title, lambda checked=False, k=key: self.selected.emit(k), "speechChoice")
            choice.setIcon(speech_action_icon(key))
            choice.setIconSize(QSize(18, 18))
            self.buttons[key] = choice
            choices.addWidget(choice)
        layout.addWidget(self.choice_row)
        self.choice_row.hide()
        self.drop_row = QWidget(objectName='speechChoiceRow')
        drop_layout = QVBoxLayout(self.drop_row); drop_layout.setContentsMargins(0, 0, 0, 0); drop_layout.setSpacing(6)
        self.drop_notice = MessageLabel(); self.drop_notice.setTextFormat(Qt.TextFormat.PlainText)
        drop_layout.addWidget(self.drop_notice); self.drop_notice.hide()
        self.drop_buttons = {}
        for key in ('move', 'print_pdf', 'move_extract'):
            choice = button('', lambda checked=False, action=key: self.file_action_requested.emit(action), 'speechChoice')
            self.drop_buttons[key] = choice; drop_layout.addWidget(choice)
        self.drop_settings_button = button('移動先・パスワードなどを設定', self.file_settings_requested.emit, 'speechChoice')
        drop_layout.addWidget(self.drop_settings_button)
        self.drop_targets = QWidget()
        self.drop_targets_layout = QVBoxLayout(self.drop_targets);self.drop_targets_layout.setContentsMargins(0,0,0,0);self.drop_targets_layout.setSpacing(6)
        self.drop_targets_scroll=QScrollArea();self.drop_targets_scroll.setWidgetResizable(True);self.drop_targets_scroll.setWidget(self.drop_targets)
        self.drop_targets_scroll.setFrameShape(QFrame.Shape.NoFrame);self.drop_targets_scroll.setFixedHeight(180)
        drop_layout.insertWidget(1,self.drop_targets_scroll);self.drop_targets_scroll.hide()
        self.drop_extra_buttons={}
        self.drop_cancel = button('キャンセル', self.dismiss, 'speechChoice'); drop_layout.addWidget(self.drop_cancel)
        layout.addWidget(self.drop_row); self.drop_row.hide()
        self.departure_row = QWidget()
        actions = QHBoxLayout(self.departure_row)
        actions.setContentsMargins(0, 0, 0, 0)
        self.attendance_button = button('勤怠サイトを開く', self.attendance_requested.emit)
        actions.addWidget(self.attendance_button)
        actions.addWidget(button('あとで', self.hide))
        layout.addWidget(self.departure_row)
        self.departure_row.hide()
        self.detail_action=button('管理画面を開く',lambda:self.selected.emit('outlook_calendar' if self.kind=='calendar' else 'activity_manager'),'speechChoice')
        layout.addWidget(self.detail_action);self.detail_action.hide()
        self.one_shot_form = QWidget()
        form = QVBoxLayout(self.one_shot_form)
        form.setContentsMargins(0, 0, 0, 0);form.setSpacing(7)
        date_time = QHBoxLayout()
        self.reminder_date = PopupDateEdit(QDate.currentDate())
        self.reminder_date.setDisplayFormat('yyyy/MM/dd');self.reminder_date.setCalendarPopup(True)
        self.reminder_date.setAccessibleName('通知する日付');self.reminder_date.setToolTip('カレンダーから日付を選択できます')
        self.reminder_time = ReminderTimeEdit(QTime.currentTime())
        self.reminder_time.setAccessibleName('通知する時刻（24時間表記、HH:mm）')
        date_time.addWidget(self.reminder_date, 3);date_time.addWidget(self.reminder_time, 2)
        form.addLayout(date_time)
        self.reminder_message = MessageEditor()
        self.reminder_message.setPlaceholderText('通知内容（1000文字まで）')
        self.reminder_message.setAccessibleName('通知内容');self.reminder_message.setFixedHeight(76)
        form.addWidget(self.reminder_message.toolbar())
        form.addWidget(self.reminder_message)
        self.reminder_status = label('', 'muted', True);form.addWidget(self.reminder_status)
        self.inline_mail = MessageLabel()
        self.inline_mail.setStyleSheet('background: #e7f1ff; color: #315878; border-radius: 5px; padding: 6px;')
        form.addWidget(self.inline_mail);self.inline_mail.hide()
        form_actions = QHBoxLayout()
        self.reminder_ok = button('OK', self.one_shot_requested.emit, 'primary')
        self.reminder_cancel = button('キャンセル', self.dismiss)
        form_actions.addWidget(self.reminder_ok);form_actions.addWidget(self.reminder_cancel)
        form.addLayout(form_actions)
        layout.addWidget(self.one_shot_form);self.one_shot_form.hide()
        self._time_error = ''
        self._adjusting_reminder_bounds = False
        self._reminder_date_recheck = False
        self.reminder_bounds_timer = QTimer(self)
        self.reminder_bounds_timer.setInterval(1000)
        self.reminder_bounds_timer.timeout.connect(self.refresh_one_shot_bounds)
        self.reminder_date.dateChanged.connect(self.confirm_reminder_date)
        self.reminder_date.chosen.connect(self.confirm_reminder_date)
        self.reminder_date.opening.connect(self.refresh_one_shot_bounds)
        self.reminder_time.textChanged.connect(lambda: self.refresh_one_shot_bounds())
        self.reminder_time.textEdited.connect(self.confirm_reminder_date)
        self.resize_text()
        for widget in [self, *self.findChildren(QWidget)]:
            widget.installEventFilter(self)

    def eventFilter(self, watched, event):
        if (event.type()==QEvent.Type.KeyPress and watched is getattr(self,'file_links',None)
                and event.key() in (Qt.Key.Key_Return,Qt.Key.Key_Enter)):
            item=self.file_links.currentItem()
            if item:self.file_requested.emit(item.data(Qt.ItemDataRole.UserRole))
            return True
        if (event.type()==QEvent.Type.MouseButtonRelease and event.button()==Qt.MouseButton.LeftButton
                and (getattr(self,'current',None) in ('activity','calendar') or getattr(self,'kind',None)=='menu' and getattr(self,'current',None)!='one_shot')
                and watched in (self,self.text,self.content_scroll,self.content_scroll.viewport(),getattr(self,'choice_row',None))):
            self.dismiss();return True
        if (event.type()==QEvent.Type.MouseButtonRelease and event.button()==Qt.MouseButton.LeftButton
                and getattr(self,'kind',None)=='calendar' and watched is self.text):
            self.dismiss();return True
        if event.type() == QEvent.Type.ContextMenu:
            return True  # Right-button press already toggled the call window.
        if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.RightButton:
            self.call_requested.emit()
            return True
        if (event.type() == QEvent.Type.MouseButtonRelease
                and watched is self.content_scroll.verticalScrollBar()):
            return False  # Reading a long message must not dismiss it while scrolling.
        return super().eventFilter(watched, event)

    def resize_text(self, available_height=None):
        if available_height is not None:
            self.available_height = max(1, available_height)
        screen = self.screen() or QApplication.primaryScreen()
        maximum = self.available_height or (screen.availableGeometry().height() - 16 if screen else 600)
        # Measure the fixed chrome/choices separately from the scrollable body.
        # A temporary 1px viewport must not introduce a scrollbar that narrows
        # the label and keeps an otherwise unnecessary extra line alive.
        self.content_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.text.setMinimumHeight(0)
        self.content_scroll.setFixedHeight(1)
        has_links = self.file_links.isVisible()
        if has_links:
            row_height = max(1, self.file_links.sizeHintForRow(0)) if self.file_links.count() else 1
            list_height = max(1, self.file_links.count()*row_height+2*self.file_links.frameWidth())
            self.file_links.setFixedHeight(1)
        self.layout().invalidate()
        self.layout().activate()
        chrome = self.layout().sizeHint().height() - 1 - (1 if has_links else 0)
        budget = max(1, maximum - chrome)
        cap = budget
        margins = self.layout().contentsMargins()
        width = max(1, self.contentsRect().width() - margins.left() - margins.right())
        height = max(1, self.text.heightForWidth(width))
        if has_links:
            # Share the usable screen height between the introduction and the
            # file list, retaining the management button and other controls.
            cap = min(height, max(1, budget//3))
        if height > cap:
            width = max(1, width - self.content_scroll.verticalScrollBar().sizeHint().width())
            height = max(1, self.text.heightForWidth(width))
        self.text.setMinimumHeight(height)
        body_height = min(height, cap)
        self.content_scroll.setFixedHeight(body_height)
        if has_links:
            self.file_links.setFixedHeight(min(list_height, max(1, budget-body_height)))
        self.layout().invalidate()
        self.layout().activate()
        # QWidget.adjustSize() can impose a 100px minimum on a top-level window.
        self.resize(self.width(), self.layout().sizeHint().height())
        self.content_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

    def open_choices(self, text="お呼びですか？", name="Yohaku"):
        self.content_changing.emit()
        self.drop_row.hide()
        self.reminder_bounds_timer.stop()
        self.notice = None
        self.one_shot_form.hide()
        self.departure_row.hide()
        self.file_links.hide();self.file_links.clear();self.detail_action.hide()
        self.set_kind("menu")
        self.timer.start(self.display_duration_ms())
        self.current = None
        self.interactive = True
        self.heading.setText(name)
        self.text.setText(text)
        self.choice_row.show()
        self.resize_text()
        self.content_scroll.verticalScrollBar().setValue(0)
        self.show()
        self.raise_()
        self.activateWindow()
        self.buttons["calendar"].setFocus()

    def content(self, key, heading, text):
        self.display(Notice(heading, text, kind="calendar" if key == "calendar" else "message"))
        self.current = key

    def display(self, notice):
        self.content_changing.emit()
        self.drop_row.hide()
        self.reminder_bounds_timer.stop()
        self.one_shot_form.hide()
        self.notice = notice
        self.departure_row.hide()
        self.file_links.hide();self.file_links.clear();self.detail_action.hide();self.detail_action.setEnabled(True)
        self.set_kind("calendar" if notice.important and notice.kind == "message" else notice.kind)
        self.current = None
        self.interactive = False
        self.choice_row.hide()
        self.heading.setText(notice.heading)
        if notice.important or notice.kind in ('calendar','notification','reminder','departure'):
            self.text.set_message(notice.text, styles=notice.styles)
        else:
            self.text.setText(notice.text)
        if self.kind=='calendar':
            self.interactive=True
            self.detail_action.setText('Outlookの予定を開く');self.detail_action.show()
        self.resize_text()
        self.content_scroll.verticalScrollBar().setValue(0)
        self.show()  # WA_ShowWithoutActivating keeps automatic notices passive.
        self.timer.start(self.display_duration_ms())
        if self.kind in ('calendar', 'reminder', 'departure'):
            self.calendar_presented.emit()

    def show_drop_stage(self, path, stage, destinations=(), error=''):
        prompts={'action':'どう処理しましょう？','destination':'どこに移動しましょう？','paper':'どの用紙で印刷しましょう？'}
        text=path.name+'\n'+prompts[stage]
        if error:text+='\n\n'+error
        self.display(Notice('',text));self.current='file_drop';self.interactive=True;self.set_kind('menu');self.timer.stop()
        self.drop_notice.clear();self.drop_notice.hide()
        for choice in self.drop_buttons.values():choice.hide();choice.setEnabled(True)
        for choice in self.drop_extra_buttons.values():
            self.drop_targets_layout.removeWidget(choice);choice.hide();choice.deleteLater()
        self.drop_extra_buttons={};self.drop_targets_scroll.hide();self.drop_settings_button.hide()
        self.drop_cancel.setEnabled(True)
        if stage=='action':
            choices={'move':'移動する'}
            if not path.is_dir() and path.suffix.lower()=='.pdf':choices['print_pdf']='印刷する'
            for key,title in choices.items():
                choice=self.drop_buttons[key];choice.setText(title);choice.setEnabled(not error);choice.show()
                choice.setIcon(speech_action_icon('activity'))
        else:
            choices=([(f'destination:{row["id"]}',row['name'],row['path']) for row in destinations] if stage=='destination'
                     else [('paper:a4','A4で印刷する',''),('paper:a3','A3で印刷する',''),('paper:auto','用紙サイズに合わせる','')])
            for key,title,tooltip in choices:
                choice=button(title,lambda checked=False,action=key:self.file_action_requested.emit(action),'speechChoice')
                choice.setToolTip(tooltip);choice.setEnabled(not error);self.drop_targets_layout.addWidget(choice);self.drop_extra_buttons[key]=choice
            self.drop_targets_scroll.setFixedHeight(min(250,max(42,len(choices)*42)))
            self.drop_targets_scroll.show()
            if stage=='destination':
                self.drop_settings_button.setText('移動先を編集する');self.drop_settings_button.setEnabled(True);self.drop_settings_button.show()
                if not destinations and not error:self.drop_notice.setText('移動先が未登録です。「移動先を編集する」から登録してください。');self.drop_notice.show()
        self.drop_row.show();self.resize_text();self.activateWindow()

    def show_drop_choices(self,path,rule=None,error=''):
        self.show_drop_stage(path,'action',error=error)

    def show_one_shot_form(self):
        self.display(Notice('', 'いつ、何をお知らせしましょう？'))
        self.current = 'one_shot';self.interactive = True
        self.set_kind('menu')
        earliest = datetime.now().astimezone().replace(second=0, microsecond=0) + timedelta(minutes=1)
        day = QDate(earliest.year, earliest.month, earliest.day)
        self.reminder_date.setMinimumDate(day)
        self.reminder_date.setDate(day)
        self.reminder_time.setTime(QTime(earliest.hour, earliest.minute))
        self.reminder_message.clear();self.reminder_status.clear();self.reminder_status.hide();self.inline_mail.hide()
        self._reminder_date_recheck = False
        self.refresh_one_shot_bounds()
        self.reminder_bounds_timer.start()
        self.one_shot_form.show();self.timer.stop();self.resize_text()
        self.activateWindow();self.reminder_message.setFocus()

    def confirm_reminder_date(self, *_):
        if not self._adjusting_reminder_bounds:
            self._reminder_date_recheck = False
            self.refresh_one_shot_bounds()

    def refresh_one_shot_bounds(self, now=None):
        if self.current != 'one_shot':
            return
        now = now or datetime.now().astimezone()
        earliest = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
        minimum_day = QDate(earliest.year, earliest.month, earliest.day)
        if self.reminder_date.minimumDate() != minimum_day:
            if self.reminder_date.date() < minimum_day and self.one_shot_form.isVisible():
                self._reminder_date_recheck = True
            self._adjusting_reminder_bounds = True
            try:
                self.reminder_date.setMinimumDate(minimum_day)
            finally:
                self._adjusting_reminder_bounds = False
        self.reminder_date.popup_calendar.setMinimumDate(minimum_day)
        minimum_time = QTime(earliest.hour, earliest.minute) if self.reminder_date.date() == minimum_day else QTime(0, 0)
        self.reminder_time.setMinimumTime(minimum_time)
        clock = self.reminder_time.time()
        error = ('選択できる日付が変わりました。日付か時刻を選び直してください。' if self._reminder_date_recheck
                 else '時刻は24時間表記のHH:mmで入力してください。' if not clock.isValid()
                 else f'選択した日の時刻は{minimum_time.toString("HH:mm")}以降を指定してください。' if clock < minimum_time else '')
        self.reminder_ok.setEnabled(not error)
        if error:
            self.reminder_status.setText(error);self.reminder_status.show()
        elif self._time_error and self.reminder_status.text() == self._time_error:
            self.reminder_status.clear();self.reminder_status.hide()
        changed = self._time_error != error
        self._time_error = error
        if changed and self.one_shot_form.isVisible():
            self.resize_text()

    def hideEvent(self, event):
        self.reminder_bounds_timer.stop()
        super().hideEvent(event)

    def show_file_history(self,text,rows):
        self.display(Notice('',text))
        self.current='activity';self.interactive=True
        for name,path in rows:
            item=QListWidgetItem(name);item.setData(Qt.ItemDataRole.UserRole,path);item.setToolTip(path)
            font=item.font();font.setUnderline(True);item.setFont(font);item.setForeground(QColor('#2e628b'))
            self.file_links.addItem(item)
        self.file_links.setVisible(bool(rows))
        self.detail_action.setText('管理画面を開く');self.detail_action.show()
        self.resize_text();self.file_links.scrollToTop()

    def show_departure(self, notice, has_url):
        self.display(notice)
        self.interactive = True
        self.attendance_button.setText('勤怠サイトを開く' if has_url else 'URLを設定する')
        self.departure_row.show()
        self.resize_text()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.dismiss()
        else:
            super().keyPressEvent(event)


class HistoryCalendar(QCalendarWidget):
    """Blue selection, amber today; retain both cues when today is selected."""
    def paintCell(self, painter, rect, date):
        super().paintCell(painter, rect, date)
        selected, today = date == self.selectedDate(), date == QDate.currentDate()
        if not (selected or today):
            return
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor('#1d4ed8' if selected else '#fde68a'))
        painter.setPen(QPen(QColor('#d97706'), 2) if today else Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(rect).adjusted(2, 2, -2, -2), 5, 5)
        font = painter.font()
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor('#ffffff' if selected else '#713f12'))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(date.day()))
        painter.restore()


class HistoryWindow(QMainWindow):
    """File history is a separate standard window, not part of the character's speech."""
    refresh_requested = Signal()
    settings_requested = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("ファイル履歴 — Yohaku")
        self.resize(1180, 620)
        self.setMinimumSize(1000, 500)
        root = QWidget(objectName="panel")
        self.setCentralWidget(root)
        layout = box(root, 24, 16)
        layout.addWidget(label("FILE HISTORY", "eyebrow"))
        top = QHBoxLayout()
        top.addWidget(label("開いたファイルの履歴", "heading"))
        top.addStretch()
        top.addWidget(button("記録の設定", self.settings_requested.emit, "link"))
        layout.addLayout(top)
        self.status = label("記録オフ", "muted", True)
        layout.addWidget(self.status)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText('ファイル名・保存先を全履歴から検索')
        self.search_edit.setAccessibleName('保存済みの全ファイル履歴を検索')
        self.search_edit.setClearButtonEnabled(True)
        layout.addWidget(self.search_edit)
        layout.addWidget(label('検索中は、選択した日付にかかわらず保存済みの全履歴が対象です。検索を消すと日付別に戻ります。', 'muted', True))
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(180)
        self.search_timer.timeout.connect(self.refresh_requested.emit)
        self.search_edit.textChanged.connect(lambda _: self.search_timer.start())
        self.search_edit.returnPressed.connect(self.run_search)
        body = QHBoxLayout()
        body.setSpacing(20)
        dates = box(spacing=10)
        self.calendar = HistoryCalendar()
        self.calendar.setMaximumWidth(310)
        self.calendar.setLocale(QLocale(QLocale.Language.Japanese, QLocale.Country.Japan))
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.calendar.setMinimumHeight(self.calendar.sizeHint().height())
        self.calendar.setDateRange(QDate.currentDate().addMonths(-3), QDate.currentDate())
        self.calendar.setAccessibleName("ファイル履歴を表示する日付")
        self.calendar.selectionChanged.connect(self.refresh_requested.emit)
        dates.addWidget(self.calendar)
        dates.addWidget(button("今日に戻る", self.today, "link"))
        dates.addWidget(label("青：選択した日　黄：今日\n過去3か月 · このPC内に保存\nファイルの内容は読みません。", "muted", True))
        dates.addStretch()
        body.addLayout(dates)
        files = box(spacing=10)
        self.day_label = label("", "section")
        files.addWidget(self.day_label)
        self.table = QTreeWidget()
        self.table.setStyleSheet("QTreeWidget::item { padding: 3px 5px; }")
        self.table.setHeaderLabels(["時刻", "ファイル名", "保存先"])
        self.table.setRootIsDecorated(False)
        self.table.setUniformRowHeights(True)
        self.table.setColumnWidth(0, 70)
        self.table.setColumnWidth(1, 340)
        self.table.header().setStretchLastSection(False)
        self.table.header().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setAccessibleName("選択した日に開いたファイル")
        self.table.itemDoubleClicked.connect(self.open_file)
        files.addWidget(self.table, 1)
        self.empty = label("この日の記録はありません。", "muted", True)
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        files.addWidget(self.empty, 1)
        body.addLayout(files, 1)
        layout.addLayout(body, 1)
        self.open_status = label("ダブルクリックでファイルを開きます。保存先はポインターを置くと全文を確認できます。時刻は検出時の目安です。", "muted", True)
        layout.addWidget(self.open_status)
        self.last_rows = None
        self.set_records([], "記録オフ")

    def today(self):
        self.search_edit.clear()
        self.calendar.setDateRange(QDate.currentDate().addMonths(-3), QDate.currentDate())
        self.calendar.setSelectedDate(QDate.currentDate())

    def run_search(self):
        self.search_timer.stop()
        self.refresh_requested.emit()

    def open_file(self, item, column=0):
        path = item.data(0, Qt.ItemDataRole.UserRole)
        if path and not QDesktopServices.openUrl(QUrl.fromLocalFile(path)):
            self.open_status.setText('ファイルを開けませんでした。移動・削除されていないか、保存先や関連付けを確認してください。')

    def set_records(self, rows, status, error="", query=""):
        self.status.setText(status)
        day = self.calendar.selectedDate()
        self.day_label.setText((f'全履歴の検索結果「{query}」' if query else self.calendar.locale().toString(day, "yyyy年M月d日（ddd）")) + f"  ·  {len(rows)}件")
        self.empty.setText(error or ('一致する履歴はありません。' if query else "この日の記録はありません。\n記録をオンにすると、この後に開いたファイルを残します。"))
        self.table.setHeaderLabels(['日時' if query else '時刻', 'ファイル名', '保存先'])
        self.table.setColumnWidth(0, 150 if query else 70)
        self.table.setVisible(bool(rows))
        self.empty.setVisible(not rows)
        if (rows, bool(query)) != self.last_rows:
            self.table.clear()
            for name, path, source, opened in rows:
                item = QTreeWidgetItem([datetime.fromisoformat(opened).astimezone().strftime("%Y/%m/%d %H:%M" if query else "%H:%M:%S"), name, path])
                item.setData(0, Qt.ItemDataRole.UserRole, path)
                item.setToolTip(1, name)
                item.setToolTip(2, path)
                self.table.addTopLevelItem(item)
            self.last_rows = (list(rows), bool(query))
        # An explicit 500px minimum otherwise overrides Qt's layout minimum
        # and lets the calendar overlap the controls below it.
        self.ensurePolished()
        self.setMinimumSize(self.minimumSize().expandedTo(self.minimumSizeHint()))

    def closeEvent(self, event):
        event.ignore()
        self.hide()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(event)


class Controller(QObject):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.path = data_directory()
        self.settings = Settings.load(self.path / "settings.json")
        self.dialogue = DialogueStore(self.path / "dialogue.json", self.settings.interval)
        self.settings.interval = self.dialogue.data["options"]["interval_minutes"]
        preset = PRESETS.get(self.settings.comfort_preset)
        if preset and (any(getattr(self.settings, key) != value for key, value in preset[1].items())
                       or preset[2] is not None and self.settings.interval != preset[2]):
            self.settings.comfort_preset = 'custom'
        self.engine = Engine(self.settings, self.path / "history.json", dialogue=self.dialogue)
        self.editor = None
        self.reminder_editor = None
        self.context_editor = None
        self.condition_timeline = ConditionTimeline()
        self.preview = None
        self.panel = Panel(self.settings, self.dialogue)
        self.brand_icon = QIcon(str(Path(__file__).parent / "assets/app/yohaku.ico"))
        self.resident = Resident(self.settings.character)
        self.bubble = InteractionBubble()
        self.bubble.duration_ms = self.dialogue.data["options"]["bubble_seconds"] * 1000
        self.interaction = self.bubble  # One actual speech window for all modes.
        self.pending_reaction = None
        self.bubble.dismissed.connect(self.bubble_dismissed)
        self.bubble.hidden.connect(self.bubble_hidden)
        self.bubble.hidden.connect(self.resident.clear_props)
        self.bubble.content_changing.connect(self.resident.clear_props)
        self.bubble.calendar_presented.connect(self.resident.check_calendar)
        self.history_window = HistoryWindow()
        self.motion = Motion()
        self.static_pose_timer = QTimer(self)
        self.static_pose_timer.setSingleShot(True)
        self.static_pose_timer.timeout.connect(self.reset_static_pose)
        self.motion_x = float(self.settings.position_x) if self.settings.position_set else None
        self.motion_y = self.settings.position_y if self.settings.position_set else None
        self.last_motion_time = time.monotonic()
        self.hover_point = None
        self.hover_until = 0.0
        self.activity_history = FileHistory(self.path / "files.sqlite3")
        self.activity_tracker = FileTracker(self.activity_history)
        self.activity_busy = False
        self.activity_generation = 0
        self.activity_error = ""
        self.next_retention = datetime.now().astimezone()
        self.activity_bridge = Bridge()
        self.activity_bridge.result.connect(self.activity_received)
        self.events = []
        self.connected = False
        self.weekly_events = None
        self.daily_events = None
        self.usage = None
        self.context_values = {}
        self.context_at = None
        self.context_busy = False
        self.context_generation = 0
        self.last_usage_time = time.monotonic()
        self.next_usage_save = time.monotonic() + 60
        self.next_context_scan = 0
        self.context_bridge = Bridge()
        self.context_bridge.result.connect(self.context_received)
        self.mail_bridge = Bridge()
        self.mail_bridge.result.connect(self.mail_result)
        self.mail_generation = 0
        self.mail_watcher = None
        self.mail_configuration = None
        self.mail_burst_last = None
        self.mail_burst_notice = None
        self.unread_count = None
        self.unread_at = None
        self.hidden = False
        self.user_hidden = False
        self.busy = False
        self.generation = 0
        self.connected_at = None
        self.bridge = Bridge()
        self.bridge.result.connect(self.received)
        self.panel.changed.connect(self.save_settings)
        self.panel.dialogue_requested.connect(self.show_dialogue_editor)
        self.panel.context_options_requested.connect(self.show_context_options)
        self.panel.reminders_requested.connect(self.show_reminder_editor)
        self.refresh_reminder_status()
        self.panel.clear_usage_requested.connect(self.clear_usage)
        self.panel.connect_requested.connect(self.refresh)
        self.panel.sample_requested.connect(self.sample)
        self.panel.preview_requested.connect(self.show_preview)
        self.panel.preset_requested.connect(self.apply_preset)
        self.panel.pause_requested.connect(self.pause)
        self.panel.hide_requested.connect(self.share)
        self.panel.clear_history_requested.connect(self.clear_activity)
        self.resident.clicked.connect(self.show_message)
        self.resident.dragged.connect(self.drag_character)
        self.resident.drag_finished.connect(self.finish_drag)
        self.interaction.selected.connect(self.select_content)
        self.interaction.one_shot_requested.connect(self.save_one_shot)
        self.history_window.refresh_requested.connect(self.refresh_history)
        self.history_window.settings_requested.connect(self.show_panel)
        self.menu = QMenu()
        self.visibility_action = self.menu.addAction("キャラを非表示", self.toggle_visibility)
        self.menu.addAction("設定を開く", self.show_panel)
        self.menu.addAction("会話を編集", self.show_dialogue_editor)
        self.menu.addAction("通知を登録・編集", self.show_reminder_editor)
        self.menu.addAction('休日・対象ファイル・話題の表示',self.show_context_options)
        self.topic_menu=self.menu.addMenu('直前の話題')
        self.topic_menu.addAction('今日はこの話題を休む',lambda:self.change_topic_preference('mute'))
        self.topic_menu.addAction('この話題を減らす',lambda:self.change_topic_preference('reduce'))
        self.topic_menu.addAction('この話題の表示設定を戻す',lambda:self.change_topic_preference('reset'))
        self.menu.aboutToShow.connect(self.refresh_topic_menu)
        self.pause_action = self.menu.addAction("1時間おやすみ", self.pause)
        self.share_action = self.menu.addAction("画面共有モード", self.share)
        self.menu.addSeparator()
        self.menu.addAction("Outlookから切断", self.disconnect)
        self.menu.addSeparator()
        self.menu.addAction("Yohakuを終了", self.request_quit)
        self.resident.context_requested.connect(lambda _: self.open_choices())
        self.bubble.call_requested.connect(self.open_choices)
        self.bubble.attendance_requested.connect(self.open_attendance)
        self.bubble.file_requested.connect(self.open_history_file)
        self.navigation_bridge=Bridge();self.navigation_bridge.result.connect(self.outlook_opened)
        self.outlook_open_busy=False;self.outlook_open_notice=None
        self.tray = QSystemTrayIcon(self)
        self.apply_character()
        self.tray.setToolTip("Yohaku — 左クリックで表示切り替え / 右クリックでメニュー")
        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(self.tray_activated)
        self.tray.show()
        from .file_drop_ui import FileDropController
        self.file_drop_service = FileDropController(self)
        self.panel.share_button.setEnabled(QSystemTrayIcon.isSystemTrayAvailable())
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.panel.share_button.setToolTip("画面共有モードにはシステムトレイが必要です。")
            self.share_action.setEnabled(False)
        self.position()
        self.resident.show()
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.show_panel()
        self.tick_timer = QTimer(self)
        self.tick_timer.timeout.connect(self.tick)
        self.tick_timer.start(15000)
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.poll)
        self.poll_timer.start(120000)
        self.animation_timer = QTimer(self)
        self.animation_timer.setInterval(16)
        self.animation_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.animation_timer.timeout.connect(self.animate)
        self.activity_timer = QTimer(self)
        self.activity_timer.setInterval(5000)
        self.activity_timer.timeout.connect(self.poll_activity)
        self.context_timer = QTimer(self)
        self.context_timer.setInterval(5000)
        self.context_timer.timeout.connect(self.sample_context)
        self.configure_activity()
        self.configure_context()
        self.configure_mail()
        self.app.aboutToQuit.connect(self.shutdown)
        if self.dialogue.error:
            self.panel.saved_label.setText(self.dialogue.error)
        self.update_animation_policy()
        for screen in self.app.screens():
            screen.availableGeometryChanged.connect(self.position)
        self.app.primaryScreenChanged.connect(self.position)
        self.app.screenAdded.connect(self.position)
        self.app.screenRemoved.connect(self.position)
        if self.settings.outlook_enabled:
            QTimer.singleShot(700, self.refresh)

    def tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle_visibility()

    def hide_character(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.show_panel()
            self.panel.mode_label.setText("通知領域が使えないため、キャラの非表示はできません")
            return
        self.user_hidden = True
        self.apply_visibility()

    def toggle_visibility(self):
        if self.hidden:
            self.share()  # A tray click is an explicit request to leave sharing mode.
        elif self.user_hidden:
            self.user_hidden = False
            self.engine.last_display = datetime.now().astimezone()
            self.apply_visibility()
        else:
            self.hide_character()

    def apply_visibility(self):
        visible = not self.hidden and not self.user_hidden
        self.resident.setVisible(visible)
        if not visible:
            if self.file_drop_service.print_dialog:
                self.file_drop_service.print_dialog.reject()
            self.file_drop_service.hide_editors()
            self.bubble.hide()
            self.history_window.hide()
            self.panel.hide()
            if self.context_editor: self.context_editor.hide()
            if self.editor:
                self.editor.hide()
            if self.preview:
                self.preview.hide()
            if self.reminder_editor:
                self.reminder_editor.hide()
        self.visibility_action.setText("キャラを非表示" if visible else "キャラを表示")
        self.tray.setToolTip("Yohaku — " + ("画面共有モード中" if self.hidden else "非表示 · 左クリックで表示" if self.user_hidden else "左クリックで非表示 / 右クリックでメニュー"))
        self.update_mode()
        self.update_animation_policy()
        if visible:
            self.resume_reaction()

    def show_panel(self):
        self.panel.show()
        self.panel.raise_()
        self.panel.activateWindow()

    def open_attendance(self):
        if not self.settings.attendance_url:
            self.bubble.hide()
            self.panel.set_page(1)
            self.show_panel()
            self.panel.attendance_url.setFocus()
            for scroll in self.panel.findChildren(QScrollArea):
                if scroll.isAncestorOf(self.panel.attendance_url):
                    scroll.ensureWidgetVisible(self.panel.attendance_url, 20, 40)
            return
        try:
            url = attendance_url(self.settings.attendance_url)
        except ValueError:
            self.bubble.text.setText('勤怠サイトのURLを設定で確認してください。')
            self.bubble.resize_text()
            return
        if QDesktopServices.openUrl(QUrl(url)):
            self.bubble.hide()
        else:
            self.bubble.text.setText(self.bubble.text.text() + '\n\nサイトを開けませんでした。設定のURLをご確認ください。')
            self.bubble.resize_text()

    def request_quit(self):
        if self.file_drop_service.busy:
            self.panel.saved_label.setText('ファイルの処理中です。完了してから終了してください。')
            self.show_panel()
            return
        if self.context_editor is not None and not self.context_editor.close(): return
        if self.editor is not None and self.editor.dirty:
            self.editor.show()
            self.editor.raise_()
            if not self.editor.close():
                return
        if self.reminder_editor is not None and self.reminder_editor.dirty:
            self.reminder_editor.show()
            self.reminder_editor.raise_()
            if not self.reminder_editor.close():
                return
        self.app.quit()

    def refresh_reminder_status(self):
        store = self.engine.reminders
        enabled = sum(rule['enabled'] for rule in store.data['notifications'])
        self.panel.reminders_status.setText(store.error or f'登録{len(store.data["notifications"])}件 · 有効{enabled}件 · 平日は月〜金 / 営業日は休日設定を参照')

    def show_reminder_editor(self):
        if self.reminder_editor is None:
            from .reminder_editor import ReminderEditor
            self.reminder_editor = ReminderEditor(self.engine.reminders,self.engine.context_options)
            self.reminder_editor.setWindowIcon(self.brand_icon)
            self.reminder_editor.saved.connect(self.refresh_reminder_status)
        elif not self.reminder_editor.dirty:
            self.reminder_editor.revert()
        self.reminder_editor.show()
        self.reminder_editor.raise_()
        self.reminder_editor.activateWindow()

    def show_dialogue_editor(self):
        if self.editor is None:
            from .dialogue_editor import DialogueEditor
            self.editor = DialogueEditor(self.dialogue,self.engine.context_options)
            self.editor.setWindowIcon(self.brand_icon)
            self.editor.saved.connect(self.dialogue_saved)
        elif not self.editor.dirty:
            self.editor.revert()
        self.editor.show()
        self.editor.raise_()
        self.editor.activateWindow()

    def refresh_topic_menu(self):
        rule=self.dialogue.rule(self.engine.last_category)
        self.topic_menu.setEnabled(rule is not None and rule['trigger']=='auto')
        self.topic_menu.setTitle('直前の話題：'+rule['label'] if rule else '直前の話題（まだありません）')

    def change_topic_preference(self,action):
        key=self.engine.last_category
        rule=self.dialogue.rule(key)
        if not rule or rule['trigger']!='auto': return
        previous=self.engine.topic_preferences.preference(key)
        try:
            self.engine.topic_preferences.update(key,muted_date=datetime.now().astimezone().date().isoformat() if action=='mute' else previous['muted_date'] if action=='reduce' else '',
                                                reduced=True if action=='reduce' else previous['reduced'] if action=='mute' else False)
        except (OSError,ValueError) as error:
            self.panel.saved_label.setText(f'話題の設定を保存できません。{error}'); return
        if self.bubble.kind=='message' and self.pending_reaction is None: self.bubble.hide()
        if self.context_editor: self.context_editor.load_topic()

    def show_context_options(self):
        if self.context_editor is None:
            from .context_editor import ContextOptionsEditor
            self.context_editor=ContextOptionsEditor(self.engine.context_options,self.engine.topic_preferences,self.dialogue)
            self.context_editor.setWindowIcon(self.brand_icon)
            self.context_editor.saved.connect(self.context_options_saved)
        elif not self.context_editor.dirty: self.context_editor.revert()
        self.context_editor.show(); self.context_editor.raise_(); self.context_editor.activateWindow()

    def context_options_saved(self):
        self.condition_timeline=ConditionTimeline()
        self.engine.consumed_events.clear()
        self.refresh_context_metrics(datetime.now().astimezone())
        if self.editor: self.editor.refresh_targets()
        if self.reminder_editor and not self.reminder_editor.dirty: self.reminder_editor.revert()

    def show_preview(self):
        if self.hidden or self.user_hidden:
            self.panel.mode_label.setText('非表示中はプレビューも表示しません')
            return
        if self.preview is None:
            from .preview import PreviewWindow
            self.preview = PreviewWindow(self.settings, self.dialogue)
            self.preview.setWindowIcon(self.brand_icon)
        self.preview.show()
        self.preview.raise_()
        self.preview.activateWindow()

    def apply_preset(self, name):
        if name == 'custom':
            self.settings.comfort_preset = name
            self.save_settings('preset')
            return
        if name not in PRESETS:
            return
        from copy import deepcopy
        _, flags, interval = PRESETS[name]
        original = deepcopy(self.dialogue.data)
        candidate = deepcopy(original)
        if interval is not None:
            candidate['options']['interval_minutes'] = interval
        values = asdict(self.settings)
        values.update(flags, comfort_preset=name, interval=candidate['options']['interval_minutes'])
        try:
            self.dialogue.save(candidate)
            save_json(self.path / 'settings.json', values)
        except (OSError, DialogueError) as error:
            try:
                self.dialogue.save(original)
            except (OSError, DialogueError):
                self.dialogue.data = original
            self.panel.sync_behavior()
            self.panel.saved_label.setText(f'プリセットを保存できませんでした。{error}')
            return
        for key, value in values.items():
            setattr(self.settings, key, value)
        self.panel.sync_behavior()
        if self.editor is not None and not self.editor.dirty:
            self.editor.revert()
        self.engine.last_display = datetime.now().astimezone()
        self.update_animation_policy()
        self.panel.saved_label.setText('会話と動きのプリセットを保存しました。')

    def dialogue_saved(self):
        self.settings.interval = self.dialogue.data['options']['interval_minutes']
        preset = PRESETS.get(self.settings.comfort_preset)
        if preset and preset[2] is not None and self.settings.interval != preset[2]:
            self.settings.comfort_preset = 'custom'
        self.panel.sync_behavior()
        self.panel.refresh_dialogue()
        self.bubble.duration_ms = self.dialogue.data['options']['bubble_seconds'] * 1000
        if self.bubble.current in ('one_shot', 'file_drop') or self.pending_reaction is not None and self.bubble.notice is self.pending_reaction:
            self.bubble.timer.stop()
        elif self.bubble.isVisible():
            self.bubble.timer.start(self.bubble.display_duration_ms())
        self.engine.category_last.clear()
        self.engine.last_category = None
        self.engine.recent = []  # Old indices may refer to deleted/reordered lines.
        self.engine.last_display = datetime.now().astimezone()
        self.engine.click_reactions.reset()

    def resident_area(self):
        if self.motion_x is None or self.motion_y is None:
            return self.app.primaryScreen().availableGeometry()
        center = QPoint(round(self.motion_x + self.resident.width() / 2),
                        round(self.motion_y + self.resident.height() / 2))
        screen = self.app.screenAt(center)
        if screen is None:
            # A monitor can be unplugged, or a saved position can be off-screen.
            screen = min(self.app.screens(), key=lambda s: (
                center - s.availableGeometry().center()).manhattanLength())
        return screen.availableGeometry()

    def drag_character(self, point):
        self.motion_x, self.motion_y = float(point.x()), point.y()
        self.position()
        self.resident.repaint()

    def finish_drag(self):
        area = self.resident_area()
        floor = max(area.top() + 8, area.bottom() + 1 - self.resident.height())
        self.motion_y = snapped_y(self.motion_y, floor, self.settings.snap_to_taskbar, self.settings.snap_distance)
        self.position()
        self.motion.start_soon()
        self.motion.distance = self.motion.speed = 0
        self.motion.walking = False
        self.last_motion_time = time.monotonic()
        self.settings.position_set = True
        self.settings.position_x = self.resident.x()
        self.settings.position_y = self.resident.y()
        try:
            save_json(self.path / "settings.json", asdict(self.settings))
        except OSError:
            self.panel.saved_label.setText("移動しましたが、位置を保存できませんでした。")

    def position(self, *args):
        area = self.resident_area()
        lower = area.left() + 12
        upper = max(lower, area.right() - self.resident.width() - 20)
        if self.motion_x is None:
            self.motion_x = float(upper)
        if self.motion_y is None:
            self.motion_y = area.bottom() + 1 - self.resident.height()
        self.motion_x = min(upper, max(lower, self.motion_x))
        self.motion_y = min(max(area.top() + 8, area.bottom() + 1 - self.resident.height()),
                            max(area.top() + 8, self.motion_y))
        self.resident.subpixel = self.motion_x - math.floor(self.motion_x)
        point = QPoint(math.floor(self.motion_x), self.motion_y)
        if point != self.resident.pos():
            self.resident.move(point)
        for bubble in (self.bubble,):
            if bubble.available_height != area.height() - 16:
                bubble.resize_text(area.height() - 16)
            x = self.resident.x() + self.resident.width() / 2 - bubble.width() / 2
            x = max(area.left() + 8, min(area.right() - bubble.width() - 8, x))
            above = self.resident.y() - bubble.height() - 8
            tail_above = above < area.top() + 8
            y = self.resident.y() + self.resident.height() + 8 if tail_above else above
            y = max(area.top() + 8, min(area.bottom() - bubble.height() - 8, y))
            if bubble.tail_above != tail_above:
                bubble.set_tail_above(tail_above)
            point = QPoint(round(x), round(y))
            if point != bubble.pos():
                bubble.move(point)
            tail_x = max(24, min(bubble.width() - 24, self.resident.x() + self.resident.width() / 2 - x))
            if tail_x != bubble.tail_x:
                bubble.tail_x = tail_x
                if bubble.isVisible():
                    bubble.update()

    def update_animation_policy(self):
        self.resident.prop_animation_enabled = self.settings.animation
        now = datetime.now().astimezone()
        enabled = self.settings.animation and not self.hidden and not self.user_hidden
        enabled = enabled and not (self.engine.paused_until and now < self.engine.paused_until)
        if enabled:
            if not self.animation_timer.isActive():
                self.motion.start_soon()
                self.last_motion_time = time.monotonic()
                self.animation_timer.start()
        else:
            self.animation_timer.stop()
            # Keep unread reactions pinned. Ordinary static poses use their
            # wall-clock timer to restore the neutral front pose.
            if self.pending_reaction is not None and self.bubble.notice is self.pending_reaction:
                self.resident.frame_index = self.motion.frame()
            elif not self.static_pose_timer.isActive() or self.motion.walking:
                self.motion.react('front', seconds=0)
                self.motion.face_front(0)
                self.resident.frame_index = 24
            self.resident.flipped = False
            self.resident.bob = self.resident.sway = 0
            self.resident.scale_x = self.resident.scale_y = 1.0
            self.resident.previous_frame = None
            self.resident.update()

    def animate(self):
        now_wall = datetime.now().astimezone()
        if (not self.settings.animation or self.hidden or self.user_hidden
                or self.engine.paused_until and now_wall < self.engine.paused_until):
            self.update_animation_policy()
            return
        now = time.monotonic()
        dt, self.last_motion_time = now - self.last_motion_time, now
        if self.resident.press_position is not None:
            return  # Keep both the native window and its pose still under the pointer.
        area = self.resident_area()
        lower = area.left() + 12
        upper = max(lower, area.right() - self.resident.width() - 20)
        hovered = self.resident.underMouse()
        if hovered:
            point = QCursor.pos()
            if self.hover_point is None or (point - self.hover_point).manhattanLength() >= 3:
                self.hover_point = point
                self.hover_until = now + 0.2
        else:
            self.hover_point = None
        # Give a moving pointer time to click, without pinning the character
        # forever beneath an untouched pointer. This transient position is not logged.
        hover_pause = hovered and now < self.hover_until
        blocked = self.pending_reaction is not None or (self.bubble.isVisible() and self.bubble.interactive) or hover_pause or self.resident.drop_hover or self.resident.mail_raised or self.resident.calendar_checking
        self.motion_x = self.motion.advance(dt, self.motion_x if self.motion_x is not None else upper,
                                          lower, upper, self.settings.walking and not blocked)
        frame = self.motion.frame()
        if frame != self.resident.frame_index:
            self.resident.previous_frame = self.resident.frame_index
            self.resident.previous_flipped = self.resident.flipped
            self.resident.frame_changed_at = now
            self.resident.frame_index = frame
        self.resident.flipped = frame < 24 and self.motion.facing < 0
        (self.resident.bob, self.resident.sway,
         self.resident.scale_x, self.resident.scale_y) = self.motion.pose()
        self.position()
        # Present the pose immediately after the native window move, as one tick.
        self.resident.repaint()

    def configure_context(self):
        self.context_generation += 1
        self.condition_timeline=ConditionTimeline()
        self.engine.consumed_events.clear()
        self.resource_sampler = ResourceSampler()
        self.resource_values = {}
        self.resource_at = None
        self.context_values = {}
        self.context_at = None
        self.last_usage_time = time.monotonic()
        self.usage = UsageLedger(self.path / 'usage.json', datetime.now().astimezone())
        if self.settings.context_enabled:
            try:
                self.usage.persist()
            except OSError:
                self.panel.context_status.setText('操作時間の保存ができません。今回の起動中だけ集計します。')
            self.context_timer.start()
            self.next_context_scan = 0
            self.sample_context()
        else:
            self.context_timer.stop()
            try:
                self.usage.persist()
            except OSError:
                pass
            self.panel.context_status.setText('PC状態の集計はオフです。保存済み集計は削除ボタンで消せます。')
        self.refresh_context_metrics(datetime.now().astimezone())

    def sample_context(self):
        if not self.settings.context_enabled or self.usage is None:
            return
        now = datetime.now().astimezone()
        clock = time.monotonic()
        dt, self.last_usage_time = clock - self.last_usage_time, clock
        self.resource_values = self.resource_sampler.sample(clock)
        try: self.resource_values.update(system_power_metrics())
        except Exception: pass
        self.resource_at = now
        try:
            idle = input_idle_seconds()
        except Exception:
            idle = None
        self.usage.sample(now, dt, idle, self.dialogue.data['options']['active_threshold_seconds'])
        if clock >= self.next_usage_save:
            self.next_usage_save = clock + 60
            try:
                self.usage.persist()
            except OSError:
                self.panel.context_status.setText('集計を保存できません。現在の起動中だけ集計しています。')
        if clock >= self.next_context_scan and not self.context_busy:
            self.next_context_scan = clock + 60
            self.context_busy = True
            generation = self.context_generation
            def worker():
                values = {}
                for key, provider in (('open_office_files', office_file_count), ('desktop_files', desktop_file_count)):
                    try:
                        values[key] = provider()
                    except Exception:
                        values[key] = None
                self.context_bridge.result.emit(generation, values, '')
            threading.Thread(target=worker, daemon=True).start()
        self.refresh_context_metrics(now)
        metrics = self.engine.context
        active, idle = metrics.get('daily_active_minutes'), metrics.get('idle_minutes')
        self.panel.context_status.setText('操作あり 約{}分 / 操作なし経過 約{}分 · アプリ起動中の推定値'.format(
            round(active) if active is not None else '取得不可', round(idle) if idle is not None else '取得不可'))
        cpu, memory = metrics.get('cpu_percent'), metrics.get('memory_percent')
        self.panel.context_status.setText(self.panel.context_status.text() + '\nCPU {} / メモリ {}'.format(
            f'{cpu:.0f}%' if cpu is not None else '計測中・取得不可',
            f'{memory:.0f}%' if memory is not None else '取得不可'))

    def context_received(self, generation, values, error):
        self.context_busy = False
        if generation != self.context_generation or not self.settings.context_enabled:
            return
        self.context_values = values if not error else {}
        self.context_at = datetime.now().astimezone()
        self.refresh_context_metrics(self.context_at)

    def refresh_context_metrics(self, now):
        options = self.dialogue.data['options']
        values = work_metrics(now, options['work_start'], options['work_end'])
        values['business_day']=None if self.engine.context_options.error else int(self.engine.context_options.calendar().is_business_day(now.date()))
        if self.usage is not None:
            app_usage = self.usage.metrics(now)
            values.update({key: app_usage[key] for key in ('missed_yesterday', 'days_since_last_use')})
        if self.settings.context_enabled and self.usage is not None:
            values.update(self.usage.metrics(now))
            if self.resource_at and 0 <= (now - self.resource_at).total_seconds() < 15:
                values.update(self.resource_values)
            if self.context_at and 0 <= (now - self.context_at).total_seconds() < 180:
                values.update(self.context_values)
        fresh = self.connected and self.connected_at and 0 <= (now - self.connected_at).total_seconds() < 300
        if fresh:
            values['weekly_events'] = self.weekly_events
            values['daily_events'] = self.daily_events
            if self.daily_events is not None:
                values.update(meeting_metrics(self.events,now,self.engine.context_options.data['consecutive_gap_minutes']))
                values.update(remaining_meeting_metrics(self.events,now))
            upcoming = [event for event in self.events if event.start > now]
            if upcoming:
                values['next_event_minutes'] = min((event.start - now).total_seconds() / 60 for event in upcoming)
        if self.settings.file_logging:
            try:
                values.update(self.activity_history.repeat_summary(now) or {})
                if not self.activity_error and self.activity_tracker.baselined:
                    values['_target_counts']=self.activity_history.target_counts(self.engine.context_options.data['targets'],now)
            except (OSError, sqlite3.Error):
                pass
        if (self.settings.outlook_enabled and self.settings.mail_enabled and self.unread_at
                and 0 <= (now - self.unread_at).total_seconds() < 90):
            values['unread_mail_count'] = self.unread_count
        values['_temporal']=self.condition_timeline.update(time.monotonic(),values,self.dialogue.data['rules'])
        self.engine.consumed_events={k:v for k,v in self.engine.consumed_events.items() if k in values['_temporal']}
        self.engine.context = values
        self.panel.advanced_context_status.setText(self.engine.context_options.error or self.engine.topic_preferences.error or
            f'営業日・休日を参照 · 対象{len(self.engine.context_options.data["targets"])}件 · 話題の表示を個別設定できます')

    def clear_usage(self):
        try:
            (self.path / 'usage.json').unlink(missing_ok=True)
            self.configure_context()
            self.panel.context_status.setText('操作時間とアプリ使用日の保存集計を削除しました。' + ('集計は再開しています。' if self.settings.context_enabled else ''))
        except OSError:
            self.panel.context_status.setText('集計を削除できません。保存先の権限をご確認ください。')

    def configure_mail(self):
        self.settings.mail_show_senders = False
        configuration = (self.settings.outlook_enabled, self.settings.mail_enabled)
        if configuration == self.mail_configuration:
            return
        self.mail_configuration = configuration
        self.unread_count = self.unread_at = None
        self.mail_burst_last = self.mail_burst_notice = None
        self.mail_generation += 1
        if self.mail_watcher:
            self.mail_watcher.stop()
            self.mail_watcher = None
        if not (self.settings.outlook_enabled and self.settings.mail_enabled):
            self.panel.mail_status.setText('受信通知は停止中です。Outlook接続と新着通知の設定を確認してください。')
            return
        generation = self.mail_generation
        self.mail_watcher = OutlookMailWatcher(
            lambda payload: self.mail_bridge.result.emit(generation, payload, ''),
            lambda status: self.mail_bridge.result.emit(generation, None, status))
        self.mail_watcher.start()

    def mail_result(self, generation, payload, status):
        if generation != self.mail_generation:
            return
        if payload is None:
            self.panel.mail_status.setText(status)
            return
        now = datetime.now().astimezone()
        if 'unread_count' in payload:
            count = payload['unread_count']
            self.unread_count = count if type(count) is int and count >= 0 else None
            self.unread_at = now if self.unread_count is not None else None
            self.refresh_context_metrics(now)
            return  # Counts are conversation context, never an immediate notice.
        if not (self.settings.mail_enabled and self.settings.outlook_enabled) or self.hidden or self.user_hidden or is_quiet(now, self.settings) or (self.engine.paused_until and now < self.engine.paused_until):
            return
        rule = self.dialogue.rule('mail_received')
        if rule is None or not rule['enabled']:
            return
        messages = payload.get('messages', [])
        if not isinstance(messages, list):
            return
        messages = [message for message in messages if isinstance(message, dict)
                    and message.get('kind') in ('mail', 'meeting')]
        if not messages:
            return
        clock = time.monotonic()
        continuing = self.mail_burst_last is not None and 0 <= clock - self.mail_burst_last <= 3
        self.mail_burst_last = clock
        if continuing:
            if self.bubble.isVisible() and self.bubble.notice is self.mail_burst_notice:
                self.bubble.timer.start(self.bubble.display_duration_ms())
            return  # Acknowledge a burst once, without revealing names or counts.
        self.engine.last_display = now
        self.motion.react(rule['expression'], speaking=True)
        self.mail_burst_notice = Notice('', self.engine.phrase('mail_received'), True, rule['expression'], 'notification')
        if self.bubble.isVisible() and self.bubble.current == 'file_drop':
            self.bubble.drop_notice.set_message(self.mail_burst_notice.text)
            self.bubble.drop_notice.show(); self.bubble.resize_text(); self.position()
            self.resident.raise_mail()
            return
        if self.bubble.isVisible() and self.bubble.current == 'one_shot':
            self.bubble.inline_mail.set_message(self.mail_burst_notice.text)
            self.bubble.inline_mail.show();self.bubble.resize_text();self.position()
            self.resident.raise_mail()
            return  # Notify immediately without replacing the unfinished form.
        self.bubble.display(self.mail_burst_notice)
        self.resident.raise_mail()
        self.position()

    def shutdown(self):
        self.file_drop_service.closed = True
        if self.file_drop_service.print_dialog:
            self.file_drop_service.print_dialog.reject()
        self.file_drop_service.hide_editors()
        if self.context_editor: self.context_editor.hide()
        self.pending_reaction = None
        self.static_pose_timer.stop()
        if self.preview:
            self.preview.hide()
        if self.reminder_editor:
            self.reminder_editor.hide()
        if self.mail_watcher:
            self.mail_watcher.stop()
        if self.usage is not None:
            try:
                self.usage.persist()
            except OSError:
                pass

    def show_message(self):
        if self.file_drop_service.busy:
            return
        if self.bubble.isVisible() and self.bubble.current in ('one_shot', 'file_drop'):
            return
        if self.hidden or self.user_hidden or self.pending_reaction is not None:
            return
        now = datetime.now().astimezone()
        self.refresh_context_metrics(now)
        self.engine.last_display = now
        fresh = self.connected and self.connected_at is not None and (now - self.connected_at).total_seconds() < 300
        notice = self.engine.click_reaction(time.monotonic())
        reacting = notice is not None
        if notice is None:
            notice = self.engine.conversation(now, self.events, fresh)
        if notice is None:
            notice = Notice(CHARACTERS[self.settings.character], self.engine.phrase('no_conversation'), expression='think')
        seconds = self.dialogue.data['options']['click_recovery_seconds'] if reacting else 8
        if reacting:
            self.pending_reaction = notice
        self.motion.react(notice.expression, seconds=float('inf') if reacting else seconds, speaking=True)
        self.motion.face_front(seconds if not reacting else 0)
        if not reacting:
            self.motion.start_soon()
        # Show the requested pose immediately, including with animation off.
        frame = self.motion.frame()
        previous = self.resident.frame_index
        self.resident.previous_flipped = self.resident.flipped
        self.resident.frame_index = frame
        self.resident.flipped = False
        self.resident.previous_frame = previous if self.animation_timer.isActive() and previous != frame else None
        self.resident.frame_changed_at = time.monotonic()
        self.resident.update()
        if reacting:
            self.static_pose_timer.stop()
        else:
            self.static_pose_timer.start(seconds * 1000)
        self.bubble.display(notice)
        if reacting:
            self.bubble.timer.stop()  # Read the reaction before another left click.
        self.position()

    def clear_reaction(self):
        self.pending_reaction = None
        self.static_pose_timer.stop()
        self.motion.react('front', seconds=0)
        self.motion.front_until = 0
        self.resident.frame_index = 24
        self.resident.previous_frame = None
        self.resident.flipped = False
        self.resident.update()

    def bubble_dismissed(self):
        if self.pending_reaction is None:
            return
        if self.bubble.notice is self.pending_reaction or self.bubble.kind == 'menu':
            self.clear_reaction()
        else:
            self.resume_reaction()

    def bubble_hidden(self):
        # Immediate mail/calendar notices can temporarily replace a reaction.
        # Return to the unread reaction after that notice closes. Right-click
        # menus can be hidden deliberately without reopening the bubble.
        if self.pending_reaction is not None and self.bubble.kind != 'menu':
            QTimer.singleShot(0, self.resume_reaction)

    def resume_reaction(self):
        if (self.pending_reaction is None or self.hidden or self.user_hidden
                or self.bubble.isVisible() or self.history_window.isVisible() or self.panel.isVisible()):
            return
        self.motion.react(self.pending_reaction.expression, seconds=float('inf'))
        self.motion.face_front(0)
        self.resident.frame_index = self.motion.frame()
        self.resident.previous_frame = None
        self.resident.flipped = False
        self.resident.update()
        self.bubble.display(self.pending_reaction)
        self.bubble.timer.stop()
        self.position()

    def reset_static_pose(self):
        if not self.animation_timer.isActive() and self.pending_reaction is None:
            self.motion.react('front', seconds=0)
            self.motion.front_until = 0
            self.resident.frame_index = 24
            self.resident.previous_frame = None
            self.resident.flipped = False
            self.resident.update()

    def open_choices(self):
        if self.hidden or self.user_hidden:
            return
        if self.bubble.isVisible() and self.bubble.kind == 'menu' and self.bubble.current != 'one_shot':
            self.bubble.timer.stop()
            self.bubble.hide()
            return
        self.motion.react(self.dialogue.rule("call")["expression"])
        self.motion.face_front()
        self.resident.frame_index = 24
        self.resident.flipped = False
        self.resident.update()
        self.engine.last_display = datetime.now().astimezone()
        text = self.engine.phrase("call")
        if self.pending_reaction is not None:
            text = self.pending_reaction.text + '\n\n' + text
        self.interaction.open_choices(text, CHARACTERS[self.settings.character])
        self.position()

    def save_one_shot(self):
        if self.hidden or self.user_hidden or self.bubble.current != 'one_shot' or not self.bubble.isVisible():
            return
        now = datetime.now().astimezone()
        self.bubble.refresh_one_shot_bounds(now)
        if not self.bubble.reminder_ok.isEnabled():
            self.bubble.resize_text();self.position()
            return
        day = self.bubble.reminder_date.date();clock = self.bubble.reminder_time.time()
        when = datetime(day.year(), day.month(), day.day(), clock.hour(), clock.minute())
        try:
            self.engine.one_shots.add(when, self.bubble.reminder_message.toPlainText(), now, self.bubble.reminder_message.styles())
        except ValueError as error:
            self.bubble.reminder_status.setText(str(error))
            self.bubble.reminder_status.show()
        except OSError:
            self.bubble.reminder_status.setText('通知を保存できません。保存先の空き容量・権限をご確認ください。')
            self.bubble.reminder_status.show()
        else:
            self.bubble.display(Notice('', f'{when:%Y/%m/%d %H:%M} に、一度だけお知らせします。'))
        self.bubble.resize_text();self.position()

    def select_content(self, key):
        if self.hidden or self.user_hidden:
            return
        now = datetime.now().astimezone()
        self.engine.last_display = now
        if key in ('calendar', 'activity', 'settings', 'one_shot'):
            self.interaction.timer.stop()
            self.interaction.hide()
            self.interaction.choice_row.hide()
            self.interaction.current = None
            self.interaction.interactive = False
        if key == "calendar":
            self.motion.react(self.dialogue.rule("calendar_intro")["expression"], speaking=True)
            fresh = self.connected_at is not None and (now - self.connected_at).total_seconds() < 300
            if not self.connected or not fresh:
                text = self.engine.phrase("calendar_unavailable")
            else:
                upcoming = [event for event in self.events if event.end > now]
                text = "\n\n".join(f"{e.start:%H:%M}–{e.end:%H:%M}  " + (f"[{e.response}] " if e.response else "") +
                                   (e.title[:80] if self.settings.show_titles and e.title else "予定あり（件名は非表示）")
                                   for e in upcoming[:10]) or self.engine.phrase("calendar_empty")
                if not getattr(self.events, 'complete', True):
                    text += '\n\n一部の予定を確認できていません。設定の接続状態をご確認ください。'
            self.interaction.content(key, CHARACTERS[self.settings.character], self.engine.phrase("calendar_intro") + "\n\n" + text)
        elif key == "activity":
            self.motion.react(self.dialogue.rule("activity_open")["expression"])
            self.show_today_history()
        elif key == 'one_shot':
            self.bubble.show_one_shot_form()
            if self.engine.one_shots.error:
                self.bubble.reminder_status.setText(self.engine.one_shots.error)
                self.bubble.reminder_status.show()
                self.bubble.resize_text()
        elif key=='outlook_calendar':
            self.open_outlook_calendar()
        elif key == 'activity_manager':
            self.bubble.timer.stop();self.bubble.hide()
            self.bubble.current=None
            self.history_window.calendar.setDateRange(QDate.currentDate().addMonths(-3), QDate.currentDate())
            self.refresh_history()
            self.history_window.show()
            self.history_window.raise_()
            self.history_window.activateWindow()
        elif key == "message":
            self.show_message()
        elif key == "hide":
            self.hide_character()
        elif key == "settings":
            self.motion.react(self.dialogue.rule("settings_open")["expression"])
            self.show_panel()
        self.position()

    def show_today_history(self):
        now=datetime.now().astimezone();text=self.engine.phrase('activity_open')
        try:
            rows=self.activity_history.for_day(now.date(),now,15000)
            seen=set();files=[]
            for name,path,_source,_opened in rows:
                key=path.replace('/','\\').casefold()
                if key not in seen:seen.add(key);files.append((name,path))
            if len(files)>50:text+='\n直近50ファイルです。全件は管理画面で確認できます。'
            if not files:text+='\n今日の記録はまだありません。'
            if not self.settings.file_logging:text+='\nファイル履歴の記録はオフです。'
            if self.activity_error:text+='\n一部の記録を確認できていません。管理画面で状態を確認できます。'
        except (OSError,sqlite3.Error):
            files=[];text+='\n履歴を読み込めませんでした。管理画面で状態をご確認ください。'
        self.bubble.show_file_history(text,files[:50])

    def open_history_file(self,path):
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(path)):
            self.bubble.text.setText('ファイルを開けませんでした。移動・削除や関連付けをご確認ください。')
            self.bubble.resize_text();self.position()

    def open_outlook_calendar(self):
        if self.outlook_open_busy:return
        self.outlook_open_busy=True;self.outlook_open_notice=self.bubble.notice
        self.bubble.detail_action.setEnabled(False)
        def worker():
            try:
                from .outlook import show_calendar
                show_calendar();error=''
            except Exception as exception:error=str(exception) if isinstance(exception,RuntimeError) else 'Outlookの予定表を開けませんでした。'
            self.navigation_bridge.result.emit(0,None,error)
        threading.Thread(target=worker,daemon=True).start()

    def outlook_opened(self,_generation,_value,error):
        self.outlook_open_busy=False;self.bubble.detail_action.setEnabled(True)
        if self.bubble.notice is not self.outlook_open_notice:return
        if error:
            self.bubble.text.setText(self.bubble.text.text()+'\n\n'+error)
            self.bubble.resize_text();self.position()
        else:self.bubble.dismiss()

    def refresh_history(self):
        now = datetime.now().astimezone()
        status = ("記録オン" if self.settings.file_logging else "記録オフ") + " · 過去3か月 / 最大15,000件 · 1日2,000件まで表示"
        if self.activity_error:
            status += "\n" + self.activity_error
        try:
            day = self.history_window.calendar.selectedDate().toPython()
            query = self.history_window.search_edit.text().strip()
            rows = self.activity_history.search(query, now) if query else self.activity_history.for_day(day, now)
            self.history_window.set_records(rows, status, query=query)
        except (OSError, ValueError, sqlite3.Error):
            self.history_window.set_records([], status, "履歴を読み込めません。保存先の権限をご確認ください。",
                                            query=self.history_window.search_edit.text().strip())

    def configure_activity(self):
        self.activity_generation += 1
        self.activity_error = ""
        self.activity_tracker.configure(self.settings.file_logging, datetime.now().astimezone())
        if self.settings.file_logging:
            self.panel.activity_status.setText("記録を開始します。最初の確認で既に開いているファイルは除きます。")
            self.activity_timer.start()
            self.poll_activity()
        else:
            self.activity_timer.stop()
            self.panel.activity_status.setText("記録オフ。保存済みの履歴は削除ボタンで消せます。")

    def poll_activity(self):
        if not self.settings.file_logging or self.activity_busy:
            return
        self.activity_busy = True
        generation = self.activity_generation

        def worker():
            try:
                snapshot = opened_file_snapshot()
                self.activity_bridge.result.emit(generation, snapshot, "")
            except Exception:
                self.activity_bridge.result.emit(generation, [], "開いたファイルを確認できません。Windowsの実行環境をご確認ください。")

        threading.Thread(target=worker, daemon=True).start()

    def activity_received(self, generation, snapshot, error):
        self.activity_busy = False
        if generation != self.activity_generation or not self.settings.file_logging:
            if self.settings.file_logging:
                self.poll_activity()
            return
        self.activity_error = error
        if not error:
            try:
                self.activity_tracker.ingest(snapshot, datetime.now().astimezone())
                self.activity_error = '\n'.join(getattr(snapshot, 'warnings', ()))
            except Exception:
                self.activity_error = "履歴を保存できません。保存先の権限をご確認ください。"
        self.panel.activity_status.setText(self.activity_error or "記録中 · 5秒ごとに確認 · 保存は3か月 / 最大15,000件")
        if self.history_window.isVisible():
            self.refresh_history()

    def clear_activity(self):
        try:
            self.activity_history.clear()
            # Discard a scan already in flight so erased entries cannot return.
            self.configure_activity()
            self.panel.activity_status.setText("保存した履歴を削除しました。" + ("記録は継続中です。" if self.settings.file_logging else ""))
            if self.history_window.isVisible():
                self.refresh_history()
        except OSError:
            self.panel.activity_status.setText("履歴を削除できません。保存先の権限をご確認ください。")

    def apply_character(self):
        self.resident.set_character(self.settings.character)
        self.icon = QIcon(character_pixmap(self.settings.character))
        self.panel.setWindowIcon(self.brand_icon)
        self.tray.setIcon(self.icon)
        self.history_window.setWindowIcon(self.brand_icon)
        if self.bubble.interactive:
            self.bubble.heading.setText(CHARACTERS[self.settings.character])
        if self.preview is not None and self.preview.isVisible():
            self.preview.play()

    def save_settings(self, key="show_titles"):
        if key == 'context_enabled':
            self.configure_context()
        if key in ('mail_enabled', 'mail_show_senders'):
            self.configure_mail()
            if self.bubble.kind == 'notification':
                self.bubble.hide()
        if key == 'interval':
            from copy import deepcopy
            candidate = deepcopy(self.dialogue.data)
            candidate['options']['interval_minutes'] = self.settings.interval
            try:
                self.dialogue.save(candidate)
            except (OSError, DialogueError) as error:
                self.settings.interval = self.dialogue.data['options']['interval_minutes']
                self.panel.refresh_dialogue()
                self.panel.saved_label.setText(f'会話の間隔を保存できませんでした。{error}')
                return
            if self.editor is not None and not self.editor.dirty:
                self.editor.revert()
        if key == "character":
            self.apply_character()
        if key in ("animation", "walking", "quiet_start", "quiet_end"):
            self.update_animation_policy()
        if key == "file_logging":
            self.configure_activity()
            if self.history_window.isVisible():
                self.refresh_history()
        try:
            save_json(self.path / "settings.json", asdict(self.settings))
            self.panel.saved_label.setText("設定を保存しました。")
            if key == 'departure':
                self.panel.departure_status.setText('退勤前通知の設定を保存しました。')
        except OSError:
            self.panel.saved_label.setText("設定を保存できません。保存先の書き込み権限をご確認ください。")
            if key == 'departure':
                self.panel.departure_status.setText('保存できませんでした。設定は今回の起動中だけ反映しています。')
        # Appearance/personality/frequency changes must not interrupt Outlook or
        # dismiss an already-visible reminder. Only privacy/source changes do.
        if key == "outlook_enabled":
            self.configure_mail()
        if key not in ("show_titles", "outlook_enabled"):
            return
        # Invalidate an in-flight read when title visibility changes.
        self.generation += 1
        self.events = []
        self.connected = False
        self.bubble.hide()
        if self.interaction.isVisible() and self.interaction.current == "calendar":
            self.interaction.content("calendar", "今日の予定", "予定を更新しています。件名は表示しません。")
        self.panel.event_summary.setText("予定の件名は表示しません。" if not self.settings.show_titles else "予定の件名を表示します。")
        self.panel.status_label.setText("○  予定を再確認します" if self.settings.outlook_enabled else "○  Outlookは未接続")
        if self.settings.outlook_enabled:
            self.poll()

    def refresh(self):
        if self.busy:
            return
        self.settings.outlook_enabled = True
        try:
            save_json(self.path / "settings.json", asdict(self.settings))
        except OSError:
            self.panel.calendar_detail.setText("接続設定を保存できません。今回の起動中のみ接続します。")
        self.configure_mail()
        self.busy = True
        generation = self.generation
        titles = self.settings.show_titles
        self.panel.connect_button.setEnabled(False)
        self.panel.status_label.setText("○  Outlookを確認中…")

        def worker():
            try:
                events = read_calendar(titles)
                try:
                    week = read_calendar(False, whole_week=True)
                    weekly = len(week) if getattr(week, 'complete', True) else None
                except Exception:
                    weekly = None
                self.bridge.result.emit(generation, {'events': events, 'weekly': weekly}, "")
            except Exception as error:
                self.bridge.result.emit(generation, [], str(error) if isinstance(error, RuntimeError) else "予定を取得できませんでした。")

        threading.Thread(target=worker, daemon=True).start()

    def received(self, generation, events, error):
        self.busy = False
        self.panel.connect_button.setEnabled(True)
        self.panel.connect_button.setText("再接続")
        if generation != self.generation:
            if self.settings.outlook_enabled:
                self.refresh()
            return
        if isinstance(events, dict):
            self.weekly_events = events.get('weekly')
            events = events.get('events', [])
        else:
            self.weekly_events = None
        self.events = events
        self.daily_events = len(events) if not error and getattr(events, 'complete', True) else None
        self.connected = not error
        self.connected_at = datetime.now().astimezone() if self.connected else None
        if error:
            self.panel.status_label.setText("○  Outlookは未接続")
            self.panel.calendar_detail.setText(error)
            self.panel.event_summary.setText("予定通知は停止中です。キャラクターと雑談は利用できます。")
            if self.interaction.isVisible() and self.interaction.current == "calendar":
                self.select_content("calendar")
            return
        self.panel.status_label.setText("●  Outlookと接続済み")
        warnings = getattr(events, 'warnings', ())
        if warnings:
            self.panel.status_label.setText('●  Outlookと接続済み · 一部取得')
        self.panel.calendar_detail.setText(("今日の予定・未承諾の会議案内を読み取りました · " + datetime.now().strftime("%H:%M") + "更新")
                                          + ('\n' + '\n'.join(warnings) if warnings else ''))
        now = datetime.now().astimezone()
        future = [event for event in events if event.start > now]
        if future:
            event = future[0]
            title = event.title if self.settings.show_titles else "予定あり（件名は非表示）"
            status = f"[{event.response}] " if event.response else ""
            self.panel.event_summary.setText(f"次の予定  {event.start:%H:%M}  {status}{title[:80]}")
        else:
            self.panel.event_summary.setText("このあとの時間指定の予定はありません。")
        self.tick()
        if self.interaction.isVisible() and self.interaction.current == "calendar":
            self.select_content("calendar")

    def disconnect(self):
        self.settings.outlook_enabled = False
        self.configure_mail()
        self.save_settings("outlook_enabled")
        self.panel.calendar_detail.setText("切断しました。再接続するまで予定を取得しません。")
        self.panel.connect_button.setText("Outlookに接続")

    def poll(self):
        if self.settings.outlook_enabled:
            self.refresh()

    def tick(self):
        now = datetime.now().astimezone()
        if self.usage is not None and not self.settings.context_enabled:
            self.usage.touch(now)
            if time.monotonic() >= self.next_usage_save:
                self.next_usage_save = time.monotonic() + 60
                try:
                    self.usage.persist()
                except OSError:
                    pass
        if now >= self.next_retention:
            self.next_retention = now + timedelta(hours=1)
            try:
                self.activity_history.append([], now)
            except (OSError, sqlite3.Error):
                self.panel.activity_status.setText("保存した履歴の期限切れ整理ができません。保存先をご確認ください。")
        if self.engine.paused_until and now >= self.engine.paused_until:
            self.engine.paused_until = None
            self.update_mode()
        self.update_animation_policy()
        self.refresh_context_metrics(now)
        if self.bubble.isVisible() and self.bubble.current in ('one_shot', 'file_drop'):
            return  # Keep scheduled messages from replacing unfinished input.
        departure = self.engine.departure_notice(now, self.hidden or self.user_hidden, system_uptime_seconds)
        if departure:
            try:
                self.engine.persist(now)
            except OSError:
                self.panel.departure_status.setText('通知履歴を保存できません。再起動すると再通知する場合があります。')
            self.motion.react('notice', speaking=True)
            self.bubble.show_departure(departure, bool(self.settings.attendance_url))
            self.position()
            return
        if self.bubble.isVisible() and self.bubble.kind == 'departure':
            return
        fresh = self.connected_at is not None and (now - self.connected_at).total_seconds() < 300
        try:
            notice = self.engine.next_notice(now, self.events, self.hidden or self.user_hidden, self.connected and fresh,
                                             allow_chatter=not (self.pending_reaction is not None or self.interaction.isVisible() or self.panel.isVisible() or self.history_window.isVisible() or (self.editor is not None and self.editor.isVisible()) or (self.reminder_editor is not None and self.reminder_editor.isVisible()) or (self.context_editor is not None and self.context_editor.isVisible())),
                                             allow_reminders=not (self.pending_reaction is not None or self.bubble.isVisible()))
        except OSError:
            self.panel.calendar_detail.setText("通知履歴を保存できません。保存先の権限をご確認ください。")
            self.panel.reminders_status.setText('通知履歴を保存できません。保存先の権限をご確認ください。')
            return
        if notice:
            self.motion.react(notice.expression, speaking=True)
            self.bubble.display(notice)
            self.position()

    def sample(self):
        if self.hidden or self.user_hidden:
            self.panel.mode_label.setText("非表示中は通知を表示しません")
            return
        self.bubble.display(Notice("通知のプレビュー · 実際の予定ではありません", (self.engine.phrase("meeting") or self.engine.phrase("reminder_disabled")), True))
        self.motion.react(self.dialogue.rule("meeting")["expression"])
        self.position()

    def pause(self):
        self.engine.paused_until = None if self.engine.paused_until else datetime.now().astimezone() + timedelta(hours=1)
        self.bubble.hide()
        self.update_mode()
        self.update_animation_policy()

    def update_mode(self):
        paused = self.engine.paused_until
        text = "おやすみを解除" if paused else "1時間おやすみ"
        self.panel.pause_button.setText(text)
        self.pause_action.setText(text)
        self.panel.mode_label.setText("画面共有モード" if self.hidden else (f"{paused:%H:%M}までおやすみ" if paused else "キャラは非表示" if self.user_hidden else "通常モード"))

    def share(self):
        if self.context_editor: self.context_editor.hide()
        self.hidden = not self.hidden
        self.bubble.hide()
        self.interaction.hide()
        self.history_window.hide()
        if not self.hidden:
            self.user_hidden = False
        self.apply_visibility()
        self.share_action.setText("画面共有モードを解除" if self.hidden else "画面共有モード")
        self.panel.share_button.setText("画面共有モードを解除" if self.hidden else "画面共有モード")
        self.update_mode()
        self.update_animation_policy()


def create_application():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Yohaku")
    app.setApplicationDisplayName(APP_DISPLAY_NAME)
    app.setApplicationVersion(VERSION)
    app.setWindowIcon(QIcon(str(Path(__file__).parent / "assets/app/yohaku.ico")))
    app.setOrganizationName("Yohaku")
    app.setQuitOnLastWindowClosed(False)
    font = QFont("Yu Gothic UI" if sys.platform == "win32" else "Noto Sans CJK JP", 10)
    app.setFont(font)
    app.setStyleSheet(STYLE)
    return app


def run():
    app = create_application()
    path = data_directory()
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError:
        QMessageBox.critical(None, "Yohaku", "設定の保存先を作成できません。ユーザーフォルダーの権限をご確認ください。")
        return
    lock = QLockFile(str(path / "instance.lock"))
    if not lock.tryLock(0):
        QMessageBox.information(None, "Yohaku", "Yohakuはすでに起動しているか、保存先を使用できません。タスクトレイをご確認ください。")
        return
    controller = Controller(app)
    app.aboutToQuit.connect(controller.bubble.hide)
    app.aboutToQuit.connect(controller.history_window.hide)
    sys.exit(app.exec())
