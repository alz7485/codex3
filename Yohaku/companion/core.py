from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import random
from typing import Callable


CHARACTERS = {
    "A": "余白ノート",
    "B": "事務ロボ",
    "E": "まじめなペンギン",
    "F": "お茶ねこ",
}


def data_directory() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local" / "share"))
    return base / "Yohaku"


def save_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def load_json(path: Path) -> dict:
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
        return result if isinstance(result, dict) else {}
    except (OSError, ValueError):
        return {}


@dataclass
class Settings:
    outlook_enabled: bool = False
    show_titles: bool = False
    chatter: bool = True
    character: str = "A"
    animation: bool = True
    walking: bool = True
    file_logging: bool = False
    personality: str = "控えめな皮肉屋"
    interval: int = 90
    quiet_start: str = "18:00"
    quiet_end: str = "09:00"

    @classmethod
    def load(cls, path: Path) -> "Settings":
        raw = load_json(path)
        settings = cls()
        for key, value in raw.items():
            if key in asdict(settings) and type(value) is type(getattr(settings, key)):
                setattr(settings, key, value)
        if settings.personality not in PHRASES:
            settings.personality = cls.personality
        if settings.character not in CHARACTERS:
            settings.character = "A"
        if settings.interval not in (60, 90, 120):
            settings.interval = 90
        for name in ("quiet_start", "quiet_end"):
            try:
                datetime.strptime(getattr(settings, name), "%H:%M")
            except ValueError:
                setattr(settings, name, getattr(cls(), name))
        return settings


@dataclass(frozen=True)
class Event:
    key: str
    start: datetime
    end: datetime
    title: str = ""


@dataclass(frozen=True)
class Notice:
    heading: str
    text: str
    important: bool = False


PHRASES = {
    "控えめな皮肉屋": {
        "call": ["お呼びですか？", "用事は何でしょう？", "何？", "何かありました？"],
        "meeting": ["そろそろ会議です。余白も、持ち物にどうぞ。", "会議まであと少し。お茶の準備も議題のうちです。", "もうすぐ会議。結論にも、出番があるといいですね。"],
        "chat": ["ひと息どうぞ。考えごとは、席を外すと進むことも。", "肩の力を抜きましょう。キーボードは逃げません。", "少し遠くを見ませんか。画面とは、長い付き合いですし。", "予定の隙間も予定のうち。少しだけ、ひと休み。"],
    },
    "元気な応援係": {
        "call": ["呼びました？", "何をしましょうか？", "今日は何のお手伝い？", "お呼びですか？"],
        "meeting": ["もうすぐ会議です。ひと呼吸して、いってらっしゃい！", "会議が近づいています。準備した分、きっと大丈夫。", "あと少しで会議。飲み物もお忘れなく！"],
        "chat": ["ここまでお疲れさまです。少し背伸びをどうぞ！", "ひと息ついて、また一歩ずついきましょう。", "水分補給の時間です。今日もいいペースで！", "小さな休憩も、次の集中の味方です。"],
    },
    "冷静な案内役": {
        "call": ["ご用件は何でしょうか？", "お呼びでしょうか？", "何を確認しますか？", "用事は何でしょう？"],
        "meeting": ["まもなく予定の開始時刻です。準備をご確認ください。", "予定の開始が近づいています。移動時間もご確認ください。", "開始前のお知らせです。必要な資料をご確認ください。"],
        "chat": ["短い休憩をおすすめします。", "目を休める時間を取りましょう。", "姿勢と水分補給をご確認ください。", "ひと区切りついたら、肩を動かしてみましょう。"],
    },
    "のんびりした同僚": {
        "call": ["ん、呼びました？", "何？", "どうしました？", "何か用ですか？"],
        "meeting": ["そろそろ会議みたいです。ゆっくり、準備しましょう。", "予定が近づいています。お茶をひと口、どうぞ。", "もうすぐ会議ですね。ひと呼吸してからで。"],
        "chat": ["ちょっと、ひと息つきませんか。", "窓の外を眺める時間も、あっていいですよね。", "背伸びでもしましょう。私も、気持ちだけ。", "少し休んでから、続きにしましょう。"],
    },
}


def is_quiet(now: datetime, settings: Settings) -> bool:
    current = now.strftime("%H:%M")
    start, end = settings.quiet_start, settings.quiet_end
    if start == end:
        return False  # Equal endpoints explicitly disable quiet hours.
    return (current >= start or current < end) if start > end else start <= current < end


class Engine:
    """Only opaque appointment keys and phrase indices are persisted."""

    def __init__(self, settings: Settings, history_path: Path,
                 choose: Callable = random.choice):
        self.settings = settings
        self.history_path = history_path
        self.state = load_json(history_path)
        self.choose = choose
        self.paused_until: datetime | None = None
        self.started = datetime.now().astimezone()
        self.last_display = self.started
        self.recent = self.state.get("recent", [])
        if not isinstance(self.recent, list):
            self.recent = []
        self.recent = [v for v in self.recent if isinstance(v, str)][-16:]
        raw = self.state.get("notified", {})
        self.notified = raw if isinstance(raw, dict) else {}

    def phrase(self, category: str) -> str:
        phrases = PHRASES[self.settings.personality][category]
        keys = [f"{self.settings.personality}/{category}/{i}" for i in range(len(phrases))]
        candidates = [i for i, key in enumerate(keys) if key not in self.recent[-2:]]
        index = self.choose(candidates or list(range(len(phrases))))
        self.recent = (self.recent + [keys[index]])[-16:]
        return phrases[index]

    def persist(self, now: datetime) -> None:
        # Keys are removed one day after the occurrence ends; cap corrupted files too.
        self.notified = {k: v for k, v in self.notified.items()
                         if isinstance(v, (int, float)) and v > now.timestamp()} 
        self.notified = dict(list(self.notified.items())[-512:])
        save_json(self.history_path, {"recent": self.recent, "notified": self.notified})

    def next_notice(self, now: datetime, events: list[Event], hidden: bool = False,
                    connected: bool = False, allow_chatter: bool = True) -> Notice | None:
        if hidden or is_quiet(now, self.settings) or (self.paused_until and now < self.paused_until):
            return None
        for event in sorted(events, key=lambda e: e.start):
            delta = (event.start - now).total_seconds()
            if connected and 0 < delta <= 600 and event.key not in self.notified:
                self.notified[event.key] = (event.end + timedelta(days=1)).timestamp()
                minutes = max(1, int((delta + 59) // 60))
                text = self.phrase("meeting")
                if self.settings.show_titles and event.title:
                    text = event.title[:60] + "\n" + text
                self.last_display = now
                self.persist(now)
                return Notice(f"予定まで あと{minutes}分", text, True)
        elapsed = (now - self.last_display).total_seconds()
        if connected and any(event.start <= now < event.end for event in events):
            return None  # Keep casual remarks out of calendar meeting time.
        if allow_chatter and self.settings.chatter and elapsed >= self.settings.interval * 60:
            self.last_display = now
            text = self.phrase("chat")
            self.persist(now)
            return Notice("余白から、ひとこと", text)
        return None
