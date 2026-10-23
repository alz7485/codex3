"""Render actual runtime widgets to a motion GIF and expression contact sheet."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import shutil
import subprocess
import tempfile
from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from companion.core import CHARACTERS
from companion.dialogue import PROFILES
from companion.motion import Motion
from companion.ui import Mascot, create_application

LABELS = ('通常', 'まばたき', '笑顔', 'お知らせ', '考え中', '眠そう', '得意げ', '気遣い',
          'ウインク', '大笑い', '首かしげ', 'くつろぎ', 'うなずき', '発話', '挨拶', '伸び', '正面', '正面まばたき', '困る', '怒る')
FRAMES = tuple(range(16)) + (24, 25, 26, 27)


def main():
    app = create_application()
    destination = Path(__file__).parent / 'docs'
    mascots = [Mascot(130, character=key) for key in CHARACTERS]
    for mascot in mascots:
        mascot.show()
    app.processEvents()

    def text(painter, x, y, value, size=14, bold=False):
        font = QFont(app.font())
        font.setPixelSize(size)
        font.setBold(bold)
        painter.setFont(font)
        painter.setPen(QColor('#344f3f'))
        painter.drawText(x, y, value)

    board = QPixmap(2000, 960)
    board.fill(QColor('#e7ede6'))
    painter = QPainter(board)
    text(painter, 40, 45, 'Yohaku  /  v0.14.6', 14, True)
    text(painter, 40, 95, '4つの性格。20の表情としぐさ。', 32, True)
    for row, (key, name) in enumerate(CHARACTERS.items()):
        y = 150 + row * 190
        text(painter, 40, y, f'{name} / {PROFILES[key][0]}', 17, True)
        mascot = mascots[row]
        mascot.setFixedSize(88, 118)
        for index, caption in enumerate(LABELS):
            x = 40 + index * 96
            mascot.frame_index = FRAMES[index]
            mascot.previous_frame = None
            painter.drawPixmap(x, y + 9, mascot.grab())
            text(painter, x + 4, y + 151, caption, 11)
    text(painter, 40, 945, '実装ウィジェットの描画 / 各キャラに歩行8コマも同梱 / Windows実機の動作は未検証', 13)
    painter.end()
    board.save(str(destination / 'expression-preview.png'))
    if shutil.which('ffmpeg'):
        motions = [Motion(uniform=lambda a, b: a) for _ in mascots]
        for motion in motions:
            motion.wait = 0
            motion.direction = 1
        for mascot in mascots:
            mascot.setFixedSize(138, 160)
            mascot.bottom_padding = 0
        with tempfile.TemporaryDirectory(prefix='yohaku-motion-') as temporary:
            xs = [0.0] * 4
            for frame in range(240):
                canvas = QPixmap(1200, 640)
                canvas.fill(QColor('#e7ede6'))
                p = QPainter(canvas)
                text(p, 32, 38, 'Yohaku  /  v0.14.6', 13, True)
                text(p, 32, 81, '小休止を挟んで、ちょこちょこ歩く。', 29, True)
                text(p, 32, 112, '小休止2〜5秒・1回24〜56px / タスクバー直上を歩く / 下段は20種の表情', 14)
                for column, ((key, name), mascot, motion) in enumerate(zip(CHARACTERS.items(), mascots, motions)):
                    left = 24 + column * 294
                    text(p, left + 8, 160, name, 16, True)
                    text(p, left + 8, 187, PROFILES[key][0], 12)
                    p.setPen(QColor('#c9d5c7'))
                    p.fillRect(left + 8, 367, 256, 18, QColor('#d3ddd2'))
                    p.drawLine(left + 8, 367, left + 264, 367)
                    xs[column] = motion.advance(1 / 30, xs[column], 0, 150, True)
                    mascot.frame_index = motion.frame()
                    mascot.flipped = motion.facing < 0
                    mascot.bob, mascot.sway, mascot.scale_x, mascot.scale_y = motion.pose()
                    mascot.previous_frame = None
                    p.drawPixmap(left + 8 + round(xs[column]), 207, mascot.grab())
                    expression = frame // 12
                    mascot.frame_index = FRAMES[expression]
                    mascot.bob = mascot.sway = 0
                    mascot.scale_x = mascot.scale_y = 1
                    p.drawPixmap(left + 64, 410, mascot.grab())
                    text(p, left + 88, 590, LABELS[expression], 13)
                text(p, 32, 625, '実装ウィジェットのプレビュー / GIFは30fps / Windows実機は未検証', 12)
                p.end()
                if frame == 30:
                    canvas.save(str(destination / 'walk-ground.png'))
                canvas.save(str(Path(temporary) / f'{frame:04d}.png'))
            subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', '30',
                            '-i', str(Path(temporary) / '%04d.png'), '-filter_complex',
                            '[0:v]split[a][b];[a]palettegen=max_colors=128[p];[b][p]paletteuse=dither=bayer',
                            str(destination / 'motion-preview.gif')], check=True)
    for mascot in mascots:
        mascot.hide()
    print('Rendered expression-preview.png and motion-preview.gif')


if __name__ == '__main__':
    main()
