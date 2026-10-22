from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
import math
import sqlite3
import sys
import threading
import time

from PySide6.QtCore import QDate, QLocale, QLockFile, QObject, QRectF, QSize, Qt, QTime, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QCalendarWidget, QCheckBox, QComboBox, QFrame, QHeaderView, QHBoxLayout, QLabel, QMainWindow,
    QMenu, QMessageBox, QPushButton, QScrollArea, QSizePolicy, QStackedWidget, QSystemTrayIcon, QTimeEdit,
    QToolButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from .core import CHARACTERS, Engine, Notice, PHRASES, Settings, data_directory, is_quiet, save_json
from .activity import FileHistory, FileTracker, opened_file_snapshot
from .motion import Motion
from .outlook import read_calendar
from .metadata import APP_DISPLAY_NAME, VERSION

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
QComboBox, QTimeEdit, QDateEdit { border: 1px solid #d6ded8; background: white; border-radius: 6px; padding: 8px; min-height: 18px; }
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
QWidget#speechChoiceRow { background: transparent; }
QPushButton#speechChoice { background: transparent; border: 1px solid #dce5da; border-radius: 7px; padding: 7px 10px; color: #41634d; font-size: 12px; font-weight: 500; text-align: left; }
QPushButton#speechChoice:hover, QPushButton#speechChoice:focus { background: #edf4e9; border-color: #7a9a81; }
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


def box(parent=None, margins=0, spacing=10):
    layout = QVBoxLayout(parent)
    layout.setContentsMargins(margins, margins, margins, margins)
    layout.setSpacing(spacing)
    return layout


@lru_cache(maxsize=4)
def character_pixmap(character):
    path = Path(__file__).parent / "assets" / "characters" / f"{character.lower()}.png"
    pixmap = QPixmap(str(path))
    if pixmap.isNull():
        raise RuntimeError(f"キャラクター画像を読み込めません: {path.name}")
    return pixmap


@lru_cache(maxsize=4)
def character_frames(character):
    path = Path(__file__).parent / "assets" / "characters" / f"{character.lower()}_motion.png"
    sheet = QPixmap(str(path))
    if sheet.isNull():
        raise RuntimeError(f"アニメーション画像を読み込めません: {path.name}")
    width, height = sheet.width() // 3, sheet.height() // 2
    return tuple(sheet.copy((i % 3) * width, (i // 3) * height, width, height) for i in range(6))


class Mascot(QWidget):
    """A transparent, smoothly scaled approved character asset."""

    def __init__(self, size=90, parent=None, character="A"):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(size, size)
        self.frame_index = None
        self.flipped = False
        self.bob = 0.0
        self.set_character(character)

    def set_character(self, character):
        self.character = character if character in CHARACTERS else "A"
        self.pixmap = character_pixmap(self.character)
        self.setAccessibleName(CHARACTERS[self.character])
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        pixmap = self.pixmap if self.frame_index is None else character_frames(self.character)[self.frame_index]
        if self.flipped:
            p.translate(self.width(), 0)
            p.scale(-1, 1)
        p.translate(0, self.bob)
        size = pixmap.size().scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio)
        target = QRectF((self.width() - size.width()) / 2,
                        self.height() - size.height(), size.width(), size.height())
        p.drawPixmap(target, pixmap, QRectF(pixmap.rect()))
        p.end()


class Panel(QMainWindow):
    changed = Signal(str)
    connect_requested = Signal()
    sample_requested = Signal()
    pause_requested = Signal()
    hide_requested = Signal()
    clear_history_requested = Signal()

    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.setWindowTitle("余白 — デスクトップの小さな同僚")
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
        brand = label("余白")
        brand.setStyleSheet("font-size: 30px; font-weight: 600; letter-spacing: 5px;")
        left.addWidget(brand)
        left.addWidget(label("Y O H A K U", "eyebrow"))
        left.addSpacing(43)
        self.tabs = []
        self.pages = QStackedWidget()
        for index, title in enumerate(("今日の余白", "キャラと通知")):
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
        self.personality_badge = label(self.settings.personality, "badge")
        words.addWidget(self.personality_badge, alignment=Qt.AlignmentFlag.AlignLeft)
        quote = label("ひと息どうぞ。\nキーボードは逃げません。", wrap=True)
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
        row = QHBoxLayout()
        row.setSpacing(8)
        self.character_buttons = {}
        self.character_group = QButtonGroup(self)
        self.character_group.setExclusive(True)
        for key, name in CHARACTERS.items():
            choice = QToolButton()
            choice.setObjectName("character")
            choice.setText(f"{key}  {name}")
            choice.setIcon(QIcon(character_pixmap(key)))
            choice.setIconSize(QSize(68, 68))
            choice.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            choice.setCheckable(True)
            choice.setChecked(key == self.settings.character)
            choice.setMinimumHeight(108)
            choice.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            choice.setCursor(Qt.CursorShape.PointingHandCursor)
            choice.setAccessibleName(f"キャラクター {key} {name}")
            choice.clicked.connect(lambda checked=False, k=key: self.update_setting("character", k))
            self.character_group.addButton(choice)
            self.character_buttons[key] = choice
            row.addWidget(choice)
        chooser.addLayout(row)
        self.animation_check = QCheckBox("表情・まばたきのアニメーション")
        self.animation_check.setChecked(self.settings.animation)
        self.animation_check.toggled.connect(lambda v: self.update_setting("animation", v))
        chooser.addWidget(self.animation_check)
        self.walking_check = QCheckBox("ときどき、画面下を歩く")
        self.walking_check.setChecked(self.settings.walking)
        self.walking_check.setEnabled(self.settings.animation)
        self.walking_check.toggled.connect(lambda v: self.update_setting("walking", v))
        chooser.addWidget(self.walking_check)
        chooser.addWidget(label("吹き出しを操作中は立ち止まります。静かな時間・おやすみ中は動きません。", "muted", True))
        layout.addWidget(card)
        card = QFrame(objectName="card")
        form = box(card, 18, 11)
        row = QHBoxLayout()
        row.addWidget(label("余白の性格", "section"))
        row.addStretch()
        personality = QComboBox()
        personality.addItems(PHRASES.keys())
        personality.setCurrentText(self.settings.personality)
        personality.setAccessibleName("余白の性格")
        personality.currentTextChanged.connect(lambda v: self.update_setting("personality", v))
        row.addWidget(personality)
        form.addLayout(row)
        chat = QCheckBox("ときどき、ひとこと話しかける")
        chat.setChecked(self.settings.chatter)
        chat.toggled.connect(lambda v: self.update_setting("chatter", v))
        form.addWidget(chat)
        row = QHBoxLayout()
        row.addWidget(label("雑談の間隔"))
        row.addStretch()
        interval = QComboBox()
        for value in (60, 90, 120):
            interval.addItem(f"{value}分に1回まで", value)
        interval.setCurrentIndex((60, 90, 120).index(self.settings.interval))
        interval.setAccessibleName("雑談の間隔")
        interval.currentIndexChanged.connect(lambda i: self.update_setting("interval", interval.itemData(i)))
        row.addWidget(interval)
        form.addLayout(row)
        form.addWidget(label("雑談の間隔は起動後の経過時間で決まります。入力内容は収集しません。", "muted", True))
        layout.addWidget(card)
        activity = QFrame(objectName="card")
        activity_box = box(activity, 18, 10)
        activity_box.addWidget(label("開いたファイルの履歴", "section"))
        self.logging_check = QCheckBox("開いたファイルの履歴を記録する（7日間）")
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
        quiet.addWidget(label("この時間帯は、予定通知も雑談もおやすみします。", "muted", True))
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
        self.personality_badge.setText(self.settings.personality)
        if key == "character":
            self.rail_mascot.set_character(value)
            self.hero_mascot.set_character(value)
            self.character_buttons[value].setChecked(True)
            self.character_caption.setText(CHARACTERS[value] + " · セリフの表示例")
        if key == "animation":
            self.walking_check.setEnabled(value)
        self.changed.emit(key)

    def closeEvent(self, event):
        event.ignore()
        self.hide()


class Resident(Mascot):
    clicked = Signal()
    context_requested = Signal(object)

    def __init__(self, character="A"):
        super().__init__(82, character=character)
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("余白 · クリックで用事を選ぶ／右クリックで設定")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.context_requested.emit(event.globalPosition().toPoint())
        elif event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()


class Bubble(QFrame):
    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setObjectName("card")
        self.setFixedWidth(322)
        self.tail_x = 270
        layout = box(self, 18, 10)
        layout.setContentsMargins(18, 14, 18, 30)
        row = QHBoxLayout()
        self.heading = label("余白から、ひとこと", "muted")
        row.addWidget(self.heading, 1)
        close = button("×", self.hide, "link")
        close.setAccessibleName("吹き出しを閉じる")
        close.setFixedSize(24, 24)
        row.addWidget(close)
        layout.addLayout(row)
        self.text = label("", wrap=True)
        self.text.setStyleSheet("font-size: 14px;")
        layout.addWidget(self.text)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor("#ffffff"))
        painter.setPen(QPen(QColor("#dce5dc"), 1))
        shape = QPainterPath()
        shape.addRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -12.5), 13, 13)
        tail = QPainterPath()
        tail.moveTo(self.tail_x - 10, self.height() - 14)
        tail.lineTo(self.tail_x + 10, self.height() - 14)
        tail.lineTo(self.tail_x, self.height() - 1)
        tail.closeSubpath()
        painter.drawPath(shape.united(tail))

    def display(self, notice):
        self.heading.setText(notice.heading)
        self.text.setText(notice.text)
        self.adjustSize()
        self.show()
        self.timer.start(14000 if notice.important else 10000)


class Bridge(QObject):
    result = Signal(int, object, str)


class InteractionBubble(Bubble):
    """The usual speech bubble, with four actions on separate rows."""
    selected = Signal(str)

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
        self.content_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.content_scroll.setStyleSheet("QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; }")
        self.content_scroll.setWidget(self.text)
        self.text.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.content_scroll)
        self.choice_row = QWidget(objectName="speechChoiceRow")
        choices = QVBoxLayout(self.choice_row)
        choices.setContentsMargins(0, 0, 0, 0)
        choices.setSpacing(6)
        self.buttons = {}
        for key, title in (("calendar", "予定を聞く"), ("activity", "ファイル起動履歴を見る"), ("settings", "設定を開く"), ("message", "一言を聞く")):
            choice = button(title, lambda checked=False, k=key: self.selected.emit(k), "speechChoice")
            self.buttons[key] = choice
            choices.addWidget(choice)
        layout.addWidget(self.choice_row)
        self.choice_row.hide()
        self.resize_text()

    def resize_text(self):
        height = self.text.heightForWidth(self.width() - 44)
        self.content_scroll.setFixedHeight(max(32, min(200, height + 5)))
        self.adjustSize()

    def open_choices(self, text="お呼びですか？", name="余白"):
        self.timer.stop()
        self.current = None
        self.interactive = True
        self.heading.setText(name)
        self.text.setText(text)
        self.choice_row.show()
        self.resize_text()
        self.show()
        self.raise_()
        self.activateWindow()
        self.buttons["calendar"].setFocus()

    def content(self, key, heading, text):
        self.timer.stop()
        self.current = key
        self.interactive = True
        self.heading.setText(heading)
        self.text.setText(text)
        self.choice_row.show()
        self.resize_text()

    def display(self, notice):
        self.current = None
        self.interactive = False
        self.choice_row.hide()
        self.heading.setText(notice.heading)
        self.text.setText(notice.text)
        self.resize_text()
        self.show()  # WA_ShowWithoutActivating keeps automatic notices passive.
        self.timer.start(14000 if notice.important else 10000)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(event)


class HistoryWindow(QMainWindow):
    """File history is a separate standard window, not part of the character's speech."""
    refresh_requested = Signal()
    settings_requested = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("ファイル履歴 — 余白")
        self.resize(960, 580)
        self.setMinimumSize(800, 500)
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
        body = QHBoxLayout()
        body.setSpacing(20)
        dates = box(spacing=10)
        self.calendar = QCalendarWidget()
        self.calendar.setLocale(QLocale(QLocale.Language.Japanese, QLocale.Country.Japan))
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.calendar.setDateRange(QDate.currentDate().addDays(-7), QDate.currentDate())
        self.calendar.setAccessibleName("ファイル履歴を表示する日付")
        self.calendar.selectionChanged.connect(self.refresh_requested.emit)
        dates.addWidget(self.calendar)
        dates.addWidget(button("今日に戻る", self.today, "link"))
        dates.addWidget(label("過去7日間 · このPC内に保存\nファイルの内容は読みません。", "muted", True))
        dates.addStretch()
        body.addLayout(dates)
        files = box(spacing=10)
        self.day_label = label("", "section")
        files.addWidget(self.day_label)
        self.table = QTreeWidget()
        self.table.setHeaderLabels(["時刻", "ファイル名", "保存先", "取得元"])
        self.table.setRootIsDecorated(False)
        self.table.setUniformRowHeights(True)
        self.table.setColumnWidth(0, 70)
        self.table.setColumnWidth(1, 145)
        self.table.setColumnWidth(3, 80)
        self.table.header().setStretchLastSection(False)
        self.table.header().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setAccessibleName("選択した日に開いたファイル")
        files.addWidget(self.table, 1)
        self.empty = label("この日の記録はありません。", "muted", True)
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        files.addWidget(self.empty, 1)
        body.addLayout(files, 1)
        layout.addLayout(body, 1)
        layout.addWidget(label("時刻は検出・最近使ったファイルの更新時刻の目安です。保存先は行にポインターを置くと全文を確認できます。", "muted", True))
        self.last_rows = None
        self.set_records([], "記録オフ")

    def today(self):
        self.calendar.setDateRange(QDate.currentDate().addDays(-7), QDate.currentDate())
        self.calendar.setSelectedDate(QDate.currentDate())

    def set_records(self, rows, status, error=""):
        self.status.setText(status)
        day = self.calendar.selectedDate()
        self.day_label.setText(self.calendar.locale().toString(day, "yyyy年M月d日（ddd）") + f"  ·  {len(rows)}件")
        self.empty.setText(error or "この日の記録はありません。\n記録をオンにすると、この後に開いたファイルを残します。")
        self.table.setVisible(bool(rows))
        self.empty.setVisible(not rows)
        if rows != self.last_rows:
            self.table.clear()
            for name, path, source, opened in rows:
                item = QTreeWidgetItem([datetime.fromisoformat(opened).astimezone().strftime("%H:%M:%S"), name, path, source])
                item.setToolTip(1, name)
                item.setToolTip(2, path)
                item.setToolTip(3, source)
                self.table.addTopLevelItem(item)
            self.last_rows = list(rows)

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
        self.engine = Engine(self.settings, self.path / "history.json")
        self.panel = Panel(self.settings)
        self.brand_icon = QIcon(str(Path(__file__).parent / "assets/app/yohaku.ico"))
        self.resident = Resident(self.settings.character)
        self.bubble = InteractionBubble()
        self.interaction = self.bubble  # One actual speech window for all modes.
        self.history_window = HistoryWindow()
        self.motion = Motion()
        self.motion_x = None
        self.last_motion_time = time.monotonic()
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
        self.hidden = False
        self.busy = False
        self.generation = 0
        self.connected_at = None
        self.bridge = Bridge()
        self.bridge.result.connect(self.received)
        self.panel.changed.connect(self.save_settings)
        self.panel.connect_requested.connect(self.refresh)
        self.panel.sample_requested.connect(self.sample)
        self.panel.pause_requested.connect(self.pause)
        self.panel.hide_requested.connect(self.share)
        self.panel.clear_history_requested.connect(self.clear_activity)
        self.resident.clicked.connect(self.open_choices)
        self.interaction.selected.connect(self.select_content)
        self.history_window.refresh_requested.connect(self.refresh_history)
        self.history_window.settings_requested.connect(self.show_panel)
        self.menu = QMenu()
        self.menu.addAction("余白を開く", self.show_panel)
        self.pause_action = self.menu.addAction("1時間おやすみ", self.pause)
        self.share_action = self.menu.addAction("画面共有モード", self.share)
        self.menu.addSeparator()
        self.menu.addAction("Outlookから切断", self.disconnect)
        self.menu.addSeparator()
        self.menu.addAction("余白を終了", self.app.quit)
        self.resident.context_requested.connect(self.menu.popup)
        self.tray = QSystemTrayIcon(self)
        self.apply_character()
        self.tray.setToolTip("余白 — デスクトップの小さな同僚")
        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(self.tray_activated)
        self.tray.show()
        self.panel.share_button.setEnabled(QSystemTrayIcon.isSystemTrayAvailable())
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.panel.share_button.setToolTip("画面共有モードにはシステムトレイが必要です。")
            self.share_action.setEnabled(False)
        self.position()
        self.resident.show()
        self.show_panel()
        self.tick_timer = QTimer(self)
        self.tick_timer.timeout.connect(self.tick)
        self.tick_timer.start(15000)
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.poll)
        self.poll_timer.start(120000)
        self.animation_timer = QTimer(self)
        self.animation_timer.setInterval(50)
        self.animation_timer.timeout.connect(self.animate)
        self.activity_timer = QTimer(self)
        self.activity_timer.setInterval(5000)
        self.activity_timer.timeout.connect(self.poll_activity)
        self.configure_activity()
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
            self.show_panel()

    def show_panel(self):
        self.panel.show()
        self.panel.raise_()
        self.panel.activateWindow()

    def position(self, *args):
        area = self.app.primaryScreen().availableGeometry()
        lower = area.left() + 12
        upper = max(lower, area.right() - self.resident.width() - 20)
        if self.motion_x is None:
            self.motion_x = float(upper)
        self.motion_x = min(upper, max(lower, self.motion_x))
        self.resident.move(round(self.motion_x), area.bottom() - self.resident.height() - 12)
        for bubble in (self.bubble,):
            x = self.resident.x() + self.resident.width() / 2 - bubble.width() / 2
            x = max(area.left() + 8, min(area.right() - bubble.width() - 8, x))
            y = max(area.top() + 8, self.resident.y() - bubble.height() - 8)
            bubble.move(round(x), round(y))
            bubble.tail_x = max(24, min(bubble.width() - 24, self.resident.x() + self.resident.width() / 2 - x))
            bubble.update()

    def update_animation_policy(self):
        now = datetime.now().astimezone()
        enabled = self.settings.animation and not self.hidden and not is_quiet(now, self.settings)
        enabled = enabled and not (self.engine.paused_until and now < self.engine.paused_until)
        if enabled:
            if not self.animation_timer.isActive():
                self.last_motion_time = time.monotonic()
                self.animation_timer.start()
        else:
            self.animation_timer.stop()
            self.resident.frame_index = None
            self.resident.flipped = False
            self.resident.bob = 0
            self.resident.update()

    def animate(self):
        if is_quiet(datetime.now().astimezone(), self.settings):
            self.update_animation_policy()
            return
        now = time.monotonic()
        dt, self.last_motion_time = now - self.last_motion_time, now
        area = self.app.primaryScreen().availableGeometry()
        lower = area.left() + 12
        upper = max(lower, area.right() - self.resident.width() - 20)
        blocked = self.bubble.isVisible() or self.panel.isVisible() or self.history_window.isVisible() or self.resident.underMouse()
        self.motion_x = self.motion.advance(dt, self.motion_x if self.motion_x is not None else upper,
                                          lower, upper, self.settings.walking and not blocked)
        state = (self.motion.frame(), self.motion.direction < 0 and self.motion.walking,
                 -abs(math.sin(self.motion.elapsed * 10)) * 1.5 if self.motion.walking else 0)
        if state != (self.resident.frame_index, self.resident.flipped, self.resident.bob):
            self.resident.frame_index, self.resident.flipped, self.resident.bob = state
            self.resident.update()
        self.position()

    def open_choices(self):
        if self.hidden:
            return
        self.motion.react("happy")
        self.interaction.open_choices(self.engine.phrase("call"), CHARACTERS[self.settings.character])
        self.position()

    def select_content(self, key):
        if self.hidden:
            return
        now = datetime.now().astimezone()
        if key == "calendar":
            fresh = self.connected_at is not None and (now - self.connected_at).total_seconds() < 300
            if not self.connected or not fresh:
                text = "予定は未接続、または更新待ちです。\n設定画面からOutlookに接続してください。"
            else:
                upcoming = [event for event in self.events if event.end > now]
                text = "\n\n".join(f"{e.start:%H:%M}–{e.end:%H:%M}  " +
                                   (e.title[:80] if self.settings.show_titles and e.title else "予定あり（件名は非表示）")
                                   for e in upcoming[:10]) or "このあとの時間指定の予定はありません。"
            self.interaction.content(key, CHARACTERS[self.settings.character], "このあとの予定をお知らせします。\n\n" + text)
        elif key == "activity":
            self.interaction.content(key, CHARACTERS[self.settings.character], "履歴を開きました。\n日付を選んで、振り返ってみましょう。")
            self.history_window.calendar.setDateRange(QDate.currentDate().addDays(-7), QDate.currentDate())
            self.refresh_history()
            self.history_window.show()
            self.history_window.raise_()
            self.history_window.activateWindow()
        elif key == "message":
            self.motion.react("happy")
            self.interaction.content(key, CHARACTERS[self.settings.character], self.engine.phrase("chat"))
        elif key == "settings":
            self.interaction.content(key, CHARACTERS[self.settings.character], "設定を開きますね。")
            self.show_panel()
        self.position()

    def refresh_history(self):
        now = datetime.now().astimezone()
        status = ("記録オン" if self.settings.file_logging else "記録オフ") + " · 過去7日間 / 最大1,000件 · 1日200件まで表示"
        if self.activity_error:
            status += "\n" + self.activity_error
        try:
            day = self.history_window.calendar.selectedDate().toPython()
            rows = self.activity_history.for_day(day, now)
            self.history_window.set_records(rows, status)
        except (OSError, ValueError, sqlite3.Error):
            self.history_window.set_records([], status, "履歴を読み込めません。保存先の権限をご確認ください。")

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
            except Exception:
                self.activity_error = "履歴を保存できません。保存先の権限をご確認ください。"
        self.panel.activity_status.setText(self.activity_error or "記録中 · 5秒ごとに確認 · 保存は7日間 / 最大1,000件")
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

    def save_settings(self, key="show_titles"):
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
        except OSError:
            self.panel.saved_label.setText("設定を保存できません。保存先の書き込み権限をご確認ください。")
        # Appearance/personality/frequency changes must not interrupt Outlook or
        # dismiss an already-visible reminder. Only privacy/source changes do.
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
        self.busy = True
        generation = self.generation
        titles = self.settings.show_titles
        self.panel.connect_button.setEnabled(False)
        self.panel.status_label.setText("○  Outlookを確認中…")

        def worker():
            try:
                events = read_calendar(titles)
                self.bridge.result.emit(generation, events, "")
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
        self.events = events
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
        self.panel.calendar_detail.setText("今日の予定を読み取りました · " + datetime.now().strftime("%H:%M更新"))
        now = datetime.now().astimezone()
        future = [event for event in events if event.start > now]
        if future:
            event = future[0]
            title = event.title if self.settings.show_titles else "予定あり（件名は非表示）"
            self.panel.event_summary.setText(f"次の予定  {event.start:%H:%M}  {title[:80]}")
        else:
            self.panel.event_summary.setText("このあとの時間指定の予定はありません。")
        self.tick()
        if self.interaction.isVisible() and self.interaction.current == "calendar":
            self.select_content("calendar")

    def disconnect(self):
        self.settings.outlook_enabled = False
        self.save_settings("outlook_enabled")
        self.panel.calendar_detail.setText("切断しました。再接続するまで予定を取得しません。")
        self.panel.connect_button.setText("Outlookに接続")

    def poll(self):
        if self.settings.outlook_enabled:
            self.refresh()

    def tick(self):
        now = datetime.now().astimezone()
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
        if self.interaction.isVisible() and self.interaction.current == "calendar":
            self.select_content("calendar")
        fresh = self.connected_at is not None and (now - self.connected_at).total_seconds() < 300
        try:
            notice = self.engine.next_notice(now, self.events, self.hidden, self.connected and fresh,
                                             allow_chatter=not self.interaction.isVisible())
        except OSError:
            self.panel.calendar_detail.setText("通知履歴を保存できません。保存先の権限をご確認ください。")
            return
        if notice:
            self.motion.react("notice" if notice.important else "happy")
            self.bubble.display(notice)
            self.position()

    def sample(self):
        if self.hidden:
            self.panel.mode_label.setText("画面共有モード中は通知を表示しません")
            return
        self.bubble.display(Notice("通知のプレビュー · 実際の予定ではありません", self.engine.phrase("meeting"), True))
        self.motion.react("notice")
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
        self.panel.mode_label.setText("画面共有モード" if self.hidden else (f"{paused:%H:%M}までおやすみ" if paused else "通常モード"))

    def share(self):
        self.hidden = not self.hidden
        self.bubble.hide()
        self.interaction.hide()
        self.history_window.hide()
        self.resident.setVisible(not self.hidden)
        if self.hidden:
            self.panel.hide()
        self.share_action.setText("画面共有モードを解除" if self.hidden else "画面共有モード")
        self.panel.share_button.setText("画面共有モードを解除" if self.hidden else "画面共有モード")
        self.tray.setToolTip("余白 — 画面共有モード中" if self.hidden else "余白 — デスクトップの小さな同僚")
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
        QMessageBox.critical(None, "余白", "設定の保存先を作成できません。ユーザーフォルダーの権限をご確認ください。")
        return
    lock = QLockFile(str(path / "instance.lock"))
    if not lock.tryLock(0):
        QMessageBox.information(None, "余白", "余白はすでに起動しているか、保存先を使用できません。タスクトレイをご確認ください。")
        return
    controller = Controller(app)
    app.aboutToQuit.connect(controller.bubble.hide)
    app.aboutToQuit.connect(controller.history_window.hide)
    sys.exit(app.exec())
