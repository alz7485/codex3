"""Load the additional characters' transparent, shared-scale animation atlases."""
import json
from pathlib import Path

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QPainter, QPixmap


def atlas_frames(character):
    root = Path(__file__).parent / 'assets/characters'
    sheet = QPixmap(str(root / f'{character.lower()}_atlas.png'))
    if sheet.isNull():
        raise RuntimeError('キャラクターのアニメーション画像を読み込めません。')
    layout = json.loads((root / 'atlas_layout.json').read_text(encoding='utf-8'))[character]
    rectangles = [QRect(*values) for values in layout]
    if len(rectangles) != 28 or any(r.isEmpty() or not sheet.rect().contains(r) for r in rectangles):
        raise RuntimeError('キャラクターのアニメーション配置が不正です。')
    # All poses keep one source scale. Only translation registers their feet
    # and silhouette center; per-frame resizing would visibly pulse while walking.
    size = QSize(max(r.width() for r in rectangles), max(r.height() for r in rectangles))
    frames = []
    for rect in rectangles:
        frame = QPixmap(size)
        frame.fill(Qt.GlobalColor.transparent)
        painter = QPainter(frame)
        painter.drawPixmap((size.width() - rect.width()) // 2, size.height() - rect.height(),
                           sheet.copy(rect))
        painter.end()
        frames.append(frame)
    return tuple(frames)
