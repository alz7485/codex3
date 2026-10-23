"""Local departure reminder text and Windows boot-time estimate."""
import ctypes
from datetime import timedelta
import math
import sys
from urllib.parse import urlsplit

DEFAULT_MESSAGE = 'そろそろ退勤の時間です。勤怠の入力を確認しましょう。'


def attendance_url(value):
    value = value.strip()
    if not value:
        return ''
    try:
        parsed = urlsplit(value)
        if (parsed.scheme not in ('http', 'https') or not parsed.hostname
                or any(character.isspace() for character in value) or len(value) > 2048):
            raise ValueError
        parsed.port  # Validate the optional port.
    except ValueError:
        raise ValueError('勤怠サイトは http:// または https:// で始まるURLを入力してください。') from None
    return value


def system_uptime_seconds():
    if sys.platform != 'win32':
        return None
    try:
        clock = ctypes.windll.kernel32.GetTickCount64
        clock.restype = ctypes.c_ulonglong
        return clock() / 1000
    except Exception:
        return None


def departure_body(message, now, uptime_seconds):
    body = message.strip() or DEFAULT_MESSAGE
    if type(uptime_seconds) not in (int, float) or not math.isfinite(uptime_seconds) or not 0 <= uptime_seconds < 10**10:
        return body + '\n\nPCの起動時間を取得できませんでした。'
    boot = now - timedelta(seconds=uptime_seconds)
    minutes = int(uptime_seconds // 60)
    return body + f'\n\nPC起動：{boot:%m/%d %H:%M}\n起動から：{minutes // 60}時間{minutes % 60}分'
