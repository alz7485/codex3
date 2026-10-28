"""Cached PNG layers in the exact existing animation-frame coordinate space."""
from collections import OrderedDict
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QPainter, QPixmap


class CostumeRenderer:
    def __init__(self):
        self.items = []; self.images = {}; self.cache = OrderedDict()

    def configure(self, catalog, progress, character):
        self.items = []; self.images.clear(); self.cache.clear()
        for key in progress.get('equipped', {}).values():
            item = catalog.items['costumes'].get(key)
            if item and key in progress.get('unlocked', []) and character in item['characters']:
                self.items.append(item)
        for item in self.items:
            for v in item['variants']:
                if v['character'] == character:
                    image = QPixmap(str(item['root']/v['image']))
                    if not image.isNull(): self.images[(item['key'], v['image'])] = image

    def compose(self, base, character, frame):
        # Prop poses, carrying and pickup have different canvases and deliberately
        # hide all costumes. Unknown frames never borrow an unrelated overlay.
        if not self.items or frame not in range(28): return base
        cache_key = (character, frame, base.cacheKey())
        if cache_key in self.cache:
            self.cache.move_to_end(cache_key); return self.cache[cache_key]
        layers = []
        for item in self.items:
            v = next((v for v in item['variants'] if v['character'] == character and frame in v['frames']), None)
            if v and (item['key'],v['image']) in self.images: layers.append((item,v))
        if not layers: return base
        result = QPixmap(base.size()); result.fill(Qt.GlobalColor.transparent)
        painter = QPainter(result); painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        def draw(item,v):
            image = self.images[(item['key'],v['image'])]
            painter.drawPixmap(QRectF(v['x'],v['y'],image.width()*v['scale'],image.height()*v['scale']), image, QRectF(image.rect()))
        for item,v in layers:
            if item['layer'] == 'back': draw(item,v)
        painter.drawPixmap(0,0,base)
        for layer in ('front','accessory'):
            for item,v in layers:
                if item['layer'] == layer: draw(item,v)
        painter.end(); self.cache[cache_key] = result
        if len(self.cache) > 128: self.cache.popitem(last=False)
        return result
