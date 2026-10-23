"""Render a design sheet from the actual Qt widgets (no Outlook access)."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path
from PySide6.QtCore import QPoint, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from companion.core import CHARACTERS, Notice, Settings
from companion.ui import Bubble, Mascot, Panel, create_application


def main():
    app = create_application()
    destination = Path(__file__).parent / "docs"
    destination.mkdir(exist_ok=True)
    panel = Panel(Settings())
    panel.show()
    app.processEvents()
    panel.grab().save(str(destination / "panel.png"))
    panel.set_page(1)
    app.processEvents()
    panel.grab().save(str(destination / "settings.png"))
    panel.set_page(0)
    app.processEvents()

    board = QPixmap(1440, 1060)
    board.fill(QColor("#e5ebe4"))
    painter = QPainter(board)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    def text(x, y, value, size=14, color="#3f5547", bold=False):
        font = QFont(app.font())
        font.setPixelSize(size)
        font.setBold(bold)
        painter.setFont(font)
        painter.setPen(QColor(color))
        painter.drawText(x, y, value)

    text(56, 55, "Y O H A K U   /   DESKTOP COMPANION", 12, "#677c6b", True)
    text(56, 104, "仕事のそばに、小さな余白。", 30, "#2c4536", True)
    text(56, 136, "Windows常駐アプリ  ·  表情と歩行  ·  音声なし  ·  外部AIなし", 14)
    # The panel is drawn with its real dimensions, 920 × 740 logical pixels.
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(45, 66, 47, 14))
    painter.drawRoundedRect(QRectF(62, 193, 920, 740), 8, 8)
    painter.drawPixmap(56, 184, panel.grab())
    text(1024, 209, "01   ふだんは、小さく。", 17, "#2c4536", True)
    text(1024, 240, "82pxの小さなキャラ。ドラッグで配置。", 13)
    painter.setBrush(QColor("#f2f5ef"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(QRectF(1024, 263, 360, 150), 14, 14)
    mascot = Mascot(82)
    mascot.show()
    app.processEvents()
    painter.drawPixmap(1280, 307, mascot.grab())
    text(1046, 297, "デスクトップの好きな場所に", 11, "#697b6c")
    text(1024, 475, "02   お知らせは、そっと。", 17, "#2c4536", True)
    text(1024, 506, "件名を隠して、開始前だけ通知。", 13)
    bubble = Bubble()
    bubble.display(Notice("予定まで あと10分 · 表示例", "そろそろ会議です。\n余白も、持ち物にどうぞ。", True))
    app.processEvents()
    painter.drawPixmap(1024, 533, bubble.grab())
    text(1024, 709, "03   必要なときは、静かに。", 17, "#2c4536", True)
    text(1024, 741, "1時間おやすみ / 画面共有モード", 13)
    text(1024, 771, "吹き出しは約1分で閉じます。", 13)
    text(56, 986, "実装画面によるデザインプレビュー", 13, "#617566")
    text(56, 1016, "予定表は未接続の表示です。Windows / 従来版Outlookでの実機検証は別途必要です。", 12, "#617566")
    text(1168, 1016, "PROTOTYPE  /  0.13.0", 12, "#617566", True)
    painter.end()
    board.save(str(destination / "design-preview.png"))
    panel.set_page(1)
    app.processEvents()
    # Present the actual selector beside all four actual runtime assets.
    sheet = QPixmap(1480, 1030)
    sheet.fill(QColor("#e5ebe4"))
    painter = QPainter(sheet)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    text(44, 48, "Y O H A K U   /   v0.13.0", 12, "#677c6b", True)
    text(44, 99, "今日はいっしょに、誰と働く？", 30, "#2c4536", True)
    text(44, 133, "A・B・E・Fを設定から切り替え。見た目と性格は、それぞれ選べます。", 15)
    painter.drawPixmap(44, 171, panel.grab())
    for i, (key, name) in enumerate(CHARACTERS.items()):
        x = 1004 + (i % 2) * 218
        y = 186 + (i // 2) * 320
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#fafbf7"))
        painter.drawRoundedRect(QRectF(x, y, 202, 288), 14, 14)
        text(x + 15, y + 33, key + "  " + name, 14, "#2c4536", True)
        illustration = Mascot(174, character=key)
        illustration.show()
        app.processEvents()
        painter.drawPixmap(x + 14, y + 52, illustration.grab())
        illustration.hide()
        text(x + 15, y + 262, "表情と歩行 · 音声なし", 11, "#697b6c")
    text(1004, 877, "切り替えは、その場で反映。", 16, "#2c4536", True)
    text(1004, 908, "選んだキャラは次回も引き継ぎます。", 13)
    text(44, 983, "実装画面のプレビュー / Windows・従来版Outlookの実機検証は別途必要です。", 12, "#617566")
    painter.end()
    sheet.save(str(destination / "character-switching.png"))
    bubble.hide()
    panel.hide()
    mascot.hide()
    print("Rendered design-preview.png, panel.png, settings.png, character-switching.png")


if __name__ == "__main__":
    main()
