"""Small, cached poses with a native dropped-item icon between the hands."""
from functools import lru_cache
from pathlib import Path
from PySide6.QtCore import QFileInfo, QRectF, QSize, Qt
from PySide6.QtGui import QIcon, QImage, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QFileIconProvider, QStyle


@lru_cache(maxsize=9)
def pose_art(character, kind):
    name = {'mail': 'mail_poses.png', 'calendar': 'calendar_poses.png', 'file': 'holding_poses.png'}[kind]
    sheet = QPixmap(str(Path(__file__).parent/'assets/characters'/name))
    if sheet.isNull():
        raise RuntimeError('小道具のポーズ画像を読み込めません。')
    column = 'ABE'.index(character)
    # Generated sprites can use unequal whitespace. Find transparent gutters
    # near thirds so a raised envelope is never cut or borrowed by its neighbor.
    full = sheet.toImage().convertToFormat(QImage.Format.Format_RGBA8888)
    pixels = bytes(full.constBits()); stride = full.bytesPerLine(); counts = [0]*full.width()
    for y in range(full.height()):
        row = pixels[y*stride:y*stride+full.width()*4]
        for x in range(full.width()):
            if row[x*4+3] >= 160:
                counts[x] += 1
    edges = [0]
    for fraction in (1/3, 2/3):
        low = int(full.width()*(fraction-.09)); high = int(full.width()*(fraction+.09))
        gaps = []; begin = None
        for x in range(low, high+1):
            if counts[x] < 5 and begin is None:
                begin = x
            elif counts[x] >= 5 and begin is not None:
                gaps.append((x-begin, (begin+x)//2)); begin = None
        if begin is not None:
            gaps.append((high+1-begin, (begin+high)//2))
        edges.append(max(gaps)[1] if gaps else int(full.width()*fraction))
    edges.append(full.width())
    source = sheet.copy(edges[column], 0, edges[column+1]-edges[column], sheet.height())
    # Alpha bounds keep generated transparent margins out of scale calculation.
    image = source.toImage()
    # Use scanlines via an RGBA view rather than iterating millions of QColors.
    image = image.convertToFormat(QImage.Format.Format_RGBA8888)
    data = bytes(image.constBits()); stride = image.bytesPerLine()
    left, top, right, bottom = image.width(), image.height(), -1, -1
    for y in range(image.height()):
        row = data[y*stride:y*stride+image.width()*4]
        xs = [x for x in range(image.width()) if row[x*4+3] >= 160]
        if xs:
            left = min(left, xs[0]); right = max(right, xs[-1]); top = min(top, y); bottom = y
    if right < left:
        raise RuntimeError('小道具のポーズ画像が空です。')
    return source.copy(left, top, right-left+1, bottom-top+1)


def item_icon(path):
    provider = QFileIconProvider()
    provider.setOptions(QFileIconProvider.Option.DontUseCustomDirectoryIcons)
    icon = provider.icon(QFileInfo(str(path)))
    if icon.isNull():
        icon = QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon if Path(path).is_dir() else QStyle.StandardPixmap.SP_FileIcon)
    return QIcon(icon)


def prop_frame(character, canvas, kind, icon=None):
    artwork = pose_art(character, kind)
    # Match the neutral front pose's occupied height and ground line.
    reference = canvas.toImage(); occupied = []
    for y in range(reference.height()):
        if any(reference.pixelColor(x, y).alpha() >= 160 for x in range(reference.width())):
            occupied.append(y)
    top, bottom = (occupied[0], occupied[-1]) if occupied else (0, canvas.height()-1)
    size = artwork.size().scaled(QSize(canvas.width(), bottom-top+1), Qt.AspectRatioMode.KeepAspectRatio)
    output = QPixmap(canvas.size()); output.fill(Qt.GlobalColor.transparent)
    p = QPainter(output); p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    target = QRectF((canvas.width()-size.width())/2, bottom+1-size.height(), size.width(), size.height())
    p.drawPixmap(target, artwork, QRectF(artwork.rect()))
    if kind == 'file' and icon is not None:
        # Draw the icon above the torso, then restore the two mitten/flipper
        # regions above its side edges. No extra synthetic arms are drawn.
        area = QRectF(artwork.width()*.27, artwork.height()*.56, artwork.width()*.48, artwork.height()*.33)
        rect = QRectF(target.x()+area.x()*target.width()/artwork.width(), target.y()+area.y()*target.height()/artwork.height(), area.width()*target.width()/artwork.width(), area.height()*target.height()/artwork.height())
        pixmap = icon.pixmap(QSize(96, 96))
        icon_size = pixmap.size().scaled(rect.size().toSize(), Qt.AspectRatioMode.KeepAspectRatio)
        p.drawPixmap(QRectF(rect.center().x()-icon_size.width()/2, rect.center().y()-icon_size.height()/2, icon_size.width(), icon_size.height()), pixmap, QRectF(pixmap.rect()))
        for hand in (QRectF(0, .55, .39, .23), QRectF(.67, .55, .33, .23)):
            source = QRectF(hand.x()*artwork.width(), hand.y()*artwork.height(), hand.width()*artwork.width(), hand.height()*artwork.height())
            dest = QRectF(target.x()+hand.x()*target.width(), target.y()+hand.y()*target.height(), hand.width()*target.width(), hand.height()*target.height())
            p.drawPixmap(dest, artwork, source)
    p.end(); return output
