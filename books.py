"""Infer book volumes from the last numeric run in each directory name."""
from safety import is_link, confined, destination_exists, move_no_replace, recovery_folder, write_recovery
from dataclasses import dataclass
from pathlib import Path
import re
from core import normalize_punctuation
from work import checkpoint


def volume_name(title, original):
    title = normalize_punctuation(title)
    generated = re.fullmatch(re.escape(title) + r' 第([0-9]+)巻(相当)?', original)
    if generated:
        number = int(generated.group(1))
        if number < 1:
            return None
        return f'{title} 第{number:0{2 if number < 100 else 3}d}巻' + (generated.group(2) or '')
    numbers = list(re.finditer(r'[0-9]+', original))
    if not numbers:
        return None
    match = numbers[-1]
    number = int(match.group())
    if number < 1:
        return None
    equivalent = original[match.end():match.end() + 1] == 's'
    width = 2 if number < 100 else 3
    return f'{title} 第{number:0{width}d}巻' + ('相当' if equivalent else '')


@dataclass(frozen=True)
class BookFolder:
    source: Path
    suggested: str | None

    @property
    def inferred_range(self):
        numbers = list(re.finditer(r'[0-9]+', self.source.name))
        if not numbers:
            return None
        match = numbers[-1]
        end = match.end() + (self.source.name[match.end():match.end()+1] == 's')
        return match.start(), end


def discover_books(root):
    root = Path(root).resolve()
    result = []
    for title in sorted(root.iterdir()):
        checkpoint(f'本フォルダを確認: {title.name}')
        if not title.is_dir() or is_link(title) or title.name.casefold() == '.folder-tool-trash':
            continue
        for book in sorted(title.iterdir()):
            if book.is_dir() and not is_link(book) and book.name.casefold() != '.folder-tool-trash':
                result.append(BookFolder(book, volume_name(title.name, book.name)))
    return result
