from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import random
from typing import Callable

from .dialogue import AUTO_PERSONALITY, EXPRESSIONS, INTERVALS, PHRASES, PROFILES, voice_for


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
    personality: str = AUTO_PERSONALITY
    interval: int = 10
    conversation_version: int = 2
    quiet_start: str = "18:00"
    quiet_end: str = "09:00"

    @classmethod
    def load(cls, path: Path) -> "Settings":
        raw = load_json(path)
        settings = cls()
        for key, value in raw.items():
            if key in asdict(settings) and type(value) is type(getattr(settings, key)):
                setattr(settings, key, value)
        if settings.personality not in (*PHRASES, AUTO_PERSONALITY):
            settings.personality = cls.personality
        if settings.character not in CHARACTERS:
            settings.character = "A"
        if settings.interval not in INTERVALS:
            settings.interval = 10
        # Adopt the requested ten-minute rhythm when upgrading older installs.
        # Existing custom voice overrides are preserved.
        if raw and (type(raw.get("conversation_version")) is not int or raw["conversation_version"] < 2):
            settings.interval = 10
        settings.conversation_version = 2
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
    expression: str = "happy"



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
        self.recent = [v for v in self.recent if isinstance(v, str)][-64:]
        self.category_last: dict[str, datetime] = {}
        self.last_category = None
        self.session_spoken = False
        raw = self.state.get("notified", {})
        self.notified = raw if isinstance(raw, dict) else {}

    def phrase(self, category: str) -> str:
        voice = voice_for(self.settings)
        phrases = PHRASES[voice][category]
        keys = [f"{voice}/{category}/{i}" for i in range(len(phrases))]
        # Cycle through nearly the entire category before reusing a remark.
        recent = [key for key in self.recent if key.startswith(f"{voice}/{category}/")]
        window = recent[-min(12, len(phrases) - 1):]
        candidates = [i for i, key in enumerate(keys) if key not in window]
        index = self.choose(candidates or list(range(len(phrases))))
        self.recent = (self.recent + [keys[index]])[-64:]
        return phrases[index]

    def conversation(self, now: datetime, events: list[Event] = (), connected=False) -> Notice:
        """Choose authored lines from time/calendar context, never observed user input."""
        session_minutes = (now - self.started).total_seconds() / 60
        if not self.session_spoken and 0 <= session_minutes <= 30:
            category = "startup"
        else:
            hour = now.hour
            time_category = ("morning" if 5 <= hour < 11 else "lunch" if 11 <= hour < 14
                             else "afternoon" if 14 <= hour < 17 else "evening")
            candidates = ["chat", "focus", "encourage", "smalltalk", "water", "eyes", "posture", time_category]
            if now.weekday() == 0:
                candidates.append("monday")
            elif now.weekday() == 4:
                candidates.append("friday")
            elif now.weekday() >= 5:
                candidates.append("weekend")
            if session_minutes >= 60:
                candidates.append("long_session")
            if connected:
                if any(600 < (e.start - now).total_seconds() <= 1800 for e in events):
                    candidates.extend(["before_meeting"] * 2)
                if any(0 <= (now - e.end).total_seconds() <= 1200 for e in events):
                    candidates.extend(["after_meeting"] * 2)
            eligible = [c for c in candidates if c != self.last_category and
                        (c not in self.category_last or
                         (now - self.category_last[c]).total_seconds() >= (1200 if c == "chat" else 3600))]
            # Rapid manual requests still rotate topics; automatic remarks respect cooldowns.
            if eligible:
                # Prefer topics not yet used this session, then the oldest topic.
                # This keeps long working days varied even with unlucky random draws.
                oldest = min(self.category_last[c].timestamp() if c in self.category_last else float("-inf") for c in eligible)
                pool = [c for c in eligible if (self.category_last[c].timestamp() if c in self.category_last else float("-inf")) == oldest]
            else:
                pool = [c for c in candidates if c != self.last_category] or candidates
            category = self.choose(pool)
        self.session_spoken = True
        self.last_category = category
        self.category_last[category] = now
        return Notice(f"{CHARACTERS[self.settings.character]}から、ひとこと",
                      self.phrase(category), expression=EXPRESSIONS[category])

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
                return Notice(f"予定まで あと{minutes}分", text, True, "notice")
        elapsed = (now - self.last_display).total_seconds()
        if connected and any(event.start <= now < event.end for event in events):
            return None  # Keep casual remarks out of calendar meeting time.
        if allow_chatter and self.settings.chatter and elapsed >= self.settings.interval * 60:
            self.last_display = now
            notice = self.conversation(now, events, connected)
            self.persist(now)
            return notice
        return None
