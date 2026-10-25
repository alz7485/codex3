"""Map each sprite's main connected shape for runtime clipping; PNGs stay unchanged."""
import json
from pathlib import Path
from PySide6.QtGui import QImage

ROOT = Path(__file__).resolve().parents[1] / 'companion/assets/characters'


def main_bounds(image):
    alpha = image.convertToFormat(QImage.Format.Format_Alpha8)
    width, height = alpha.width(), alpha.height()
    stride = alpha.bytesPerLine()
    raw = bytes(alpha.constBits())
    active = bytearray(raw[y * stride + x] >= 128 for y in range(height) for x in range(width))
    largest, selected = 0, None
    for start in range(width * height):
        if not active[start]:
            continue
        stack, count = [start], 0
        active[start] = 0
        left = right = start % width
        top = bottom = start // width
        while stack:
            index = stack.pop()
            x, y = index % width, index // width
            count += 1
            left, right = min(left, x), max(right, x)
            top, bottom = min(top, y), max(bottom, y)
            neighbors = []
            if x: neighbors.append(index - 1)
            if x + 1 < width: neighbors.append(index + 1)
            if y: neighbors.append(index - width)
            if y + 1 < height: neighbors.append(index + width)
            for neighbor in neighbors:
                if active[neighbor]:
                    active[neighbor] = 0
                    stack.append(neighbor)
        if count > largest:
            largest = count
            selected = (max(0, left - 2), max(0, top - 2), min(width, right + 3), min(height, bottom + 3))
    if selected is None:
        raise RuntimeError('Empty sprite cell')
    left, top, right, bottom = selected
    return [left, top, right - left, bottom - top]


def main():
    result = {}
    for key in 'abe':
        sheet = QImage(str(ROOT / f'{key}_motion.png'))
        width, height = sheet.width() // 6, sheet.height() // 4
        result[key] = [main_bounds(sheet.copy((i % 6) * width, (i // 6) * height, width, height)) for i in range(24)]
    (ROOT / 'motion_layout.json').write_text(json.dumps(result, indent=2) + '\n')
    print('Mapped 72 sprite cells; PNGs unchanged.')


if __name__ == '__main__':
    main()
