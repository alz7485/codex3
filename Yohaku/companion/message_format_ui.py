"""Native selection-based bold/colour editor with JSON-compatible ranges."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton, QTextEdit, QWidget
from .message_format import message_html, validate_styles


class MessageLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent); self.raw_text = ''; self.rich_html = ''
        self.setWordWrap(True)

    def clear(self):
        self.setText('')

    def setText(self, text):
        self.raw_text = text; self.rich_html = ''
        self.setTextFormat(Qt.TextFormat.PlainText); super().setText(text)

    def text(self):
        return self.raw_text

    def set_message(self, text, automatic=True, styles=()):
        self.raw_text = text
        self.rich_html = message_html(text, automatic, styles)
        self.setTextFormat(Qt.TextFormat.RichText); super().setText(self.rich_html)


class MessageEditor(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptRichText(False)  # Pasted HTML is never a source of styles.

    def clear(self):
        self.set_message('')

    def set_message(self, text, styles=()):
        self.setPlainText(text)
        cursor = QTextCursor(self.document()); cursor.select(QTextCursor.SelectionType.Document)
        cursor.setCharFormat(QTextCharFormat())
        for row in validate_styles(text, list(styles)):
            cursor.setPosition(len(text[:row['start']].encode('utf-16-le'))//2)
            cursor.setPosition(len(text[:row['start']+row['length']].encode('utf-16-le'))//2, QTextCursor.MoveMode.KeepAnchor)
            value = QTextCharFormat(); value.setFontWeight(QFont.Weight.Bold if row['bold'] else QFont.Weight.Normal)
            if row['color']:value.setForeground(QColor(row['color']))
            cursor.setCharFormat(value)
        cursor = self.textCursor(); cursor.clearSelection(); self.setTextCursor(cursor)

    def styles(self):
        text = self.toPlainText(); cursor = QTextCursor(self.document()); position=0; result=[]
        for index, character in enumerate(text):
            count=len(character.encode('utf-16-le'))//2
            cursor.setPosition(position);cursor.setPosition(position+count,QTextCursor.MoveMode.KeepAnchor)
            value=cursor.charFormat();bold=value.fontWeight() >= QFont.Weight.DemiBold
            color=value.foreground().color().name() if value.foreground().style()!=Qt.BrushStyle.NoBrush else ''
            if bold or color:
                if result and result[-1]['start']+result[-1]['length']==index and (result[-1]['bold'],result[-1]['color'])==(bold,color):
                    result[-1]['length']+=1
                else:result.append(dict(start=index,length=1,bold=bold,color=color))
            position+=count
        return result

    def apply_format(self, bold=None, color=None, reset=False):
        cursor=self.textCursor()
        if not cursor.hasSelection():cursor.select(QTextCursor.SelectionType.Document)
        value=QTextCharFormat()
        if reset:cursor.setCharFormat(value)
        else:
            if bold is not None:value.setFontWeight(QFont.Weight.Bold if bold else QFont.Weight.Normal)
            if color is not None:value.setForeground(QColor(color))
            cursor.mergeCharFormat(value)
        self.setTextCursor(cursor);self.setFocus()

    def toolbar(self):
        row=QWidget();layout=QHBoxLayout(row);layout.setContentsMargins(0,0,0,0);layout.setSpacing(4)
        self.bold_button=QPushButton('太字');self.bold_button.setCheckable(True)
        self.bold_button.setAccessibleName('選択した文字を太字にする')
        self.bold_button.clicked.connect(lambda checked:self.apply_format(bold=checked));layout.addWidget(self.bold_button)
        self.color_box=QComboBox();self.color_box.setAccessibleName('選択した文字の色')
        for title,color in [('色を選択',None),('青','#245ca6'),('緑','#28744f'),('赤','#b0443a'),('紫','#7650a3'),('橙','#9c570c'),('黒','#263b43')]:
            self.color_box.addItem(title,color)
        self.color_box.activated.connect(lambda index:self.apply_format(color=self.color_box.itemData(index)) if self.color_box.itemData(index) else None)
        layout.addWidget(self.color_box)
        reset=QPushButton('標準');reset.clicked.connect(lambda:self.apply_format(reset=True));layout.addWidget(reset)
        layout.addStretch();row.setToolTip('文字を選んで装飾します。未選択の場合は本文全体に適用します。')
        def synchronize():
            self.bold_button.setChecked(self.currentCharFormat().fontWeight() >= QFont.Weight.DemiBold)
        self.cursorPositionChanged.connect(synchronize);self.selectionChanged.connect(synchronize)
        synchronize()
        return row
