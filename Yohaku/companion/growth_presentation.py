"""Native styling and quiet, static decorations for the growth window."""
from PySide6.QtCore import QRectF,Qt
from PySide6.QtGui import QColor,QLinearGradient,QPainter,QPainterPath,QPen
from PySide6.QtWidgets import QComboBox,QFrame,QLabel,QVBoxLayout,QWidget

GROWTH_STYLE='''
QWidget { color:#2d4338; font-size:13px; }
QWidget#growthRoot { background:#f2f5f1; }
QLabel { background:transparent; border:none; }
QLabel#growthTitle { font-size:22px; font-weight:600; color:#284d3c; }
QLabel#growthSubtitle, QLabel#growthMuted { color:#607366; font-size:12px; }
QLabel#growthName { font-size:27px; font-weight:600; color:#284d3c; }
QLabel#growthLevel { background:#edf4eb; color:#446d4d; border-radius:9px; padding:7px 13px; font-size:19px; font-weight:600; }
QLabel#growthSection { font-size:15px; font-weight:600; color:#345643; }
QLabel#growthNext { color:#446952; font-size:14px; font-weight:600; }
QLabel#growthMetricValue { color:#294c3b; font-size:22px; font-weight:600; }
QLabel#growthRewardLevel { background:#f8f0dd; color:#86662b; border-radius:6px; padding:4px 10px; font-weight:600; }
QLabel#growthError { background:#fff4df; color:#795625; border:1px solid #e9d6ad; border-radius:9px; padding:8px 12px; }
QFrame#growthCard { background:#ffffff; border:1px solid #dfe7dd; border-radius:15px; }
QFrame#growthHero { background:#ffffff; border:1px solid #dfe7dd; border-radius:18px; }
QComboBox, QLineEdit { background:#ffffff; border:1px solid #d7e1d5; border-radius:8px; padding:8px 11px; min-height:18px; selection-background-color:#dcead8; }
QComboBox:hover, QLineEdit:hover { border-color:#a9c0a2; }
QComboBox:focus, QLineEdit:focus { border:1px solid #648b66; }
QComboBox::drop-down { border:none; width:25px; }
QComboBox::down-arrow { image:none; }
QComboBox QAbstractItemView { background:#ffffff; color:#2d4338; selection-background-color:#dfeedd; selection-color:#284d3c; border:1px solid #d7e1d5; padding:4px; }
QPushButton { background:#ffffff; color:#42634c; border:1px solid #d6e0d2; border-radius:8px; padding:8px 14px; min-height:18px; }
QPushButton:hover { background:#edf4e9; border-color:#adc4a3; }
QPushButton:pressed { background:#dcead6; }
QPushButton:focus { border:2px solid #648b66; padding:7px 13px; }
QPushButton#growthPrimary { background:#466e50; color:#ffffff; border-color:#466e50; font-weight:600; }
QPushButton#growthPrimary:hover { background:#365c40; border-color:#365c40; }
QPushButton:disabled { background:#eff2ed; color:#8b978c; border-color:#e0e5dc; }
QPushButton#growthPrimary:disabled { background:#e5ece1; color:#8b978c; border-color:#e0e5dc; }
QTabWidget::pane { border:none; background:transparent; }
QTabBar::tab { color:#607366; background:transparent; padding:10px 17px; margin:0 4px 9px 0; border-radius:8px; }
QTabBar::tab:selected { background:#466e50; color:#ffffff; font-weight:600; }
QTabBar::tab:!selected:hover { background:#e4ecdf; color:#345643; }
QTabBar::tab:focus { border:1px solid #466e50; }
QProgressBar { background:#e9eee5; border:none; border-radius:5px; min-height:10px; max-height:10px; }
QProgressBar::chunk { background:#799c6b; border-radius:5px; }
QTreeWidget, QPlainTextEdit { background:#ffffff; border:1px solid #dfe7dd; border-radius:9px; selection-background-color:#e3eddd; selection-color:#294c3b; padding:6px; }
QTreeWidget::item { padding:6px 4px; border:none; }
QTreeWidget::item:selected { background:#e3eddd; color:#294c3b; }
QTreeWidget::item:hover:!selected { background:#f3f6f0; }
QHeaderView::section { background:#edf2e9; color:#617461; padding:8px 6px; border:none; border-bottom:1px solid #dfe7dd; font-weight:600; }
QScrollArea, QScrollArea > QWidget > QWidget { background:transparent; border:none; }
QSplitter::handle { background:transparent; width:8px; height:8px; }
QScrollBar:vertical { background:transparent; width:10px; margin:0; }
QScrollBar::handle:vertical { background:#c7d4c0; border-radius:4px; min-height:28px; margin:1px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background:transparent; }
'''


def text_label(text='',name='growthMuted'):
    label=QLabel(text);label.setObjectName(name);label.setWordWrap(True)
    label.setTextFormat(Qt.TextFormat.PlainText)
    return label


def card(name='growthCard',margins=18):
    frame=QFrame();frame.setObjectName(name)
    layout=QVBoxLayout(frame);layout.setContentsMargins(margins,margins,margins,margins);layout.setSpacing(10)
    return frame,layout


class MetricCard(QFrame):
    def __init__(self,title):
        super().__init__();self.setObjectName('growthCard')
        layout=QVBoxLayout(self);layout.setContentsMargins(15,13,15,13);layout.setSpacing(5)
        layout.addWidget(text_label(title));self.value=text_label('—','growthMetricValue');layout.addWidget(self.value)
        self.hint=text_label();layout.addWidget(self.hint)


class PortraitStage(QWidget):
    def __init__(self):
        super().__init__();self.character='A';self.setFixedSize(166,166)
        self.content=QVBoxLayout(self);self.content.setContentsMargins(12,12,12,12)

    def set_character(self,character):
        if self.character!=character:self.character=character;self.update()

    def paintEvent(self,event):
        painter=QPainter(self);painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        gradient=QLinearGradient(20,10,145,155)
        gradient.setColorAt(0,QColor({'A':'#f6eedb','B':'#e5f0f6','E':'#e2efec'}.get(self.character,'#edf3e8')))
        gradient.setColorAt(1,QColor('#f8faf5'));painter.setPen(Qt.PenStyle.NoPen);painter.setBrush(gradient)
        painter.drawEllipse(QRectF(9,7,148,148));painter.setBrush(QColor('#e3e6d9'));painter.drawEllipse(QRectF(47,143,72,9))
        painter.setBrush(QColor('#c8b17a'))
        for x,y,radius in ((29,31,4),(139,62,3),(133,21,2)):
            path=QPainterPath();path.moveTo(x,y-radius);path.lineTo(x+radius*.35,y-radius*.35)
            path.lineTo(x+radius,y);path.lineTo(x+radius*.35,y+radius*.35);path.lineTo(x,y+radius)
            path.lineTo(x-radius*.35,y+radius*.35);path.lineTo(x-radius,y);path.lineTo(x-radius*.35,y-radius*.35);path.closeSubpath();painter.drawPath(path)
        painter.end()


class GrowthCombo(QComboBox):
    """Keep a visible native-control affordance under the scoped stylesheet."""
    def paintEvent(self,event):
        super().paintEvent(event)
        painter=QPainter(self);painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor('#6f886f' if self.isEnabled() else '#adb8a8'),1.5,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap,Qt.PenJoinStyle.RoundJoin))
        x=self.width()-17;y=self.height()/2
        path=QPainterPath();path.moveTo(x-3,y-1.5);path.lineTo(x,y+1.5);path.lineTo(x+3,y-1.5);painter.drawPath(path);painter.end()
