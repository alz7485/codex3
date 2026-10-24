from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import random
import re
from typing import Callable

from .dialogue import AUTO_PERSONALITY, PHRASES, DialogueStore, matches, voice_for
from .departure import DEFAULT_MESSAGE, attendance_url, departure_body
from .motion import ClickReactions
from .reminders import ReminderStore, due_time
from .one_shot import OneShotStore


CHARACTERS = {
    "A": "つづり",
    "B": "ビット",
    "E": "ペギー",
    "F": "きなこ",
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
    position_set: bool = False
    position_x: int = 0
    position_y: int = 0
    file_logging: bool = False
    context_enabled: bool = True
    mail_enabled: bool = True
    mail_show_senders: bool = False  # Legacy key, always ignored by the watcher.
    snap_to_taskbar: bool = True
    snap_distance: int = 16
    comfort_preset: str = 'standard'
    personality: str = AUTO_PERSONALITY
    interval: int = 10
    conversation_version: int = 2
    quiet_start: str = "18:00"
    quiet_end: str = "09:00"
    departure_enabled: bool = False
    departure_weekdays: bool = True
    departure_time: str = '17:00'
    departure_message: str = DEFAULT_MESSAGE
    attendance_url: str = ''

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
        if not 1 <= settings.interval <= 1440:
            settings.interval = 10
        # Adopt the requested ten-minute rhythm when upgrading older installs.
        # Existing custom voice overrides are preserved.
        if raw and (type(raw.get("conversation_version")) is not int or raw["conversation_version"] < 2):
            settings.interval = 10
        settings.conversation_version = 2
        settings.mail_show_senders = False
        if settings.comfort_preset not in ('standard', 'restrained', 'notifications', 'custom'):
            settings.comfort_preset = 'custom'
        if not 4 <= settings.snap_distance <= 48:
            settings.snap_distance = 16
        for name in ("quiet_start", "quiet_end", 'departure_time'):
            try:
                datetime.strptime(getattr(settings, name), "%H:%M")
            except ValueError:
                setattr(settings, name, getattr(cls(), name))
        try:
            settings.attendance_url = attendance_url(settings.attendance_url)
        except ValueError:
            settings.attendance_url = ''
        if not settings.departure_message.strip() or len(settings.departure_message) > 1000:
            settings.departure_message = DEFAULT_MESSAGE
        if 'comfort_preset' not in raw:
            settings.comfort_preset = ('standard' if all(getattr(settings, key) == getattr(cls(), key)
                                                       for key in ('chatter', 'animation', 'walking', 'interval')) else 'custom')
        return settings


@dataclass(frozen=True)
class Event:
    key: str
    start: datetime
    end: datetime
    title: str = ""
    response: str = ""
    legacy_key: str = ""


@dataclass(frozen=True)
class Notice:
    heading: str
    text: str
    important: bool = False
    expression: str = "happy"
    kind: str = "message"



def is_quiet(now: datetime, settings: Settings) -> bool:
    current = now.strftime("%H:%M")
    start, end = settings.quiet_start, settings.quiet_end
    if start == end:
        return False  # Equal endpoints explicitly disable quiet hours.
    return (current >= start or current < end) if start > end else start <= current < end


class Engine:
    """Notice history contains opaque keys, phrase indices, and delivery dates."""

    def __init__(self, settings: Settings, history_path: Path,
                 choose: Callable = random.choice, dialogue: DialogueStore | None = None):
        self.settings = settings
        self.history_path = history_path
        self.dialogue = dialogue or DialogueStore(history_path.parent / "dialogue.json", settings.interval)
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
        self.context = {}
        from .context_options import ContextOptionsStore, TopicPreferences
        self.context_options=ContextOptionsStore(history_path.parent/'context_options.json')
        self.topic_preferences=TopicPreferences(history_path.parent/'topic_preferences.json')
        self.consumed_events={}
        self.click_reactions = ClickReactions()
        raw = self.state.get("notified", {})
        self.notified = raw if isinstance(raw, dict) else {}
        self.departure_date = self.state.get('departure_date', '')
        self.reminders = ReminderStore(history_path.parent / 'reminders.json')
        self.one_shots = OneShotStore(history_path.parent / 'one_shot_notifications.json')
        raw = self.state.get('custom_notified', {})
        self.custom_notified = ({key: value for key, value in raw.items()
                                 if isinstance(key, str) and isinstance(value, str)} if isinstance(raw, dict) else {})

    def phrase(self, category: str, replacements=None) -> str:
        voice = voice_for(self.settings, self.dialogue.data)
        rule = self.dialogue.rule(category)
        if rule is None or not rule["enabled"]:
            return ""
        phrases = self.dialogue.data["phrases"][voice][category]
        keys = [f"{voice}/{category}/{i}" for i in range(len(phrases))]
        # Cycle through nearly the entire category before reusing a remark.
        recent = [key for key in self.recent if key.startswith(f"{voice}/{category}/")]
        count = min(self.dialogue.data["options"]["repeat_window"], len(phrases) - 1)
        window = recent[-count:] if count else []
        candidates = [i for i, key in enumerate(keys) if key not in window]
        index = self.choose(candidates or list(range(len(phrases))))
        self.recent = (self.recent + [keys[index]])[-64:]
        values = {key: str(round(value)) if type(value) in (int, float) else str(value)[:120]
                  for key, value in self.context.items() if value is not None}
        end = self.context.get('until_work_end_minutes')
        if type(end) in (int, float):
            hours, minutes = divmod(int(round(max(0, end))), 60)
            values['hours_to_end'] = (f'{hours}時間' if hours else '') + (f'{minutes}分' if minutes or not hours else '')
        values['work_start'] = self.dialogue.data['options']['work_start']
        values['work_end'] = self.dialogue.data['options']['work_end']
        values.update(replacements or {})
        template = re.sub(r'\{hours_to_end\}\s*時間', '{hours_to_end}', phrases[index])
        if category == 'mail_received':
            values['mail_from'] = ''
        return re.sub(r'\{([a-z_]+)\}', lambda match: values.get(match.group(1), match.group(0)), template)

    def click_reaction(self, monotonic_time):
        category = self.click_reactions.click(monotonic_time, self.dialogue.data['options'])
        if category:
            text = self.phrase(category)
            if text:
                return Notice('', text, expression=self.dialogue.rule(category)['expression'])
        return None

    def conversation(self, now: datetime, events: list[Event] = (), connected=False, manual=True) -> Notice | None:
        """Evaluate validated declarative JSON rules; no expressions or code execution."""
        options = self.dialogue.data['options']
        self.context['business_day']=None if self.context_options.error else int(self.context_options.calendar().is_business_day(now.date()))
        self.context['_consumed_events']=self.consumed_events
        if self.topic_preferences.error:return None
        candidates = [r for r in self.dialogue.data['rules'] if r['trigger'] == 'auto' and r['enabled']
                      and matches(r, now, self.started, self.session_spoken, events, connected, self.context)]
        candidates=[r for r in candidates if self.topic_preferences.preference(r['id'])['muted_date']!=now.date().isoformat()
                    and (not self.topic_preferences.preference(r['id'])['reduced'] or r['id'] not in self.category_last
                         or (now-self.category_last[r['id']]).total_seconds()>=max(1,r['cooldown_minutes'])*120)]
        if not candidates:
            return None
        first = [r for r in candidates if r['condition']['kind'] == 'session_range'
                 and r['condition']['first_only']]
        if first:
            pool = first
        else:
            rotating = [r for r in candidates if not options['avoid_consecutive_topic'] or r['id'] != self.last_category]
            rotating = rotating or candidates
            eligible = [r for r in rotating if r['id'] not in self.category_last or
                        (now - self.category_last[r['id']]).total_seconds() >= r['cooldown_minutes'] * 60]
            if not eligible and not manual:
                return None
            pool = eligible or rotating or candidates
            if eligible and options['selection_policy'] == 'least_recent':
                oldest = min(self.category_last[r['id']].timestamp() if r['id'] in self.category_last else float('-inf') for r in eligible)
                pool = [r for r in eligible if (self.category_last[r['id']].timestamp() if r['id'] in self.category_last else float('-inf')) == oldest]
                # A small number of extra tickets can bring a priority topic
                # back before every other eligible topic has had a turn.
                pool += [r for r in eligible for _ in range(r.get('priority', 0))]
        category = self.choose([r['id'] for r in pool for _ in range(r['weight'])])
        self.session_spoken = True
        self.last_category = category
        self.category_last[category] = now
        from .advanced_context import condition_key, EVENT_KINDS
        def matched_conditions(condition):
            if not matches({'condition':condition},now,self.started,self.session_spoken,events,connected,self.context):return
            yield condition
            for child in condition.get('conditions',()):yield from matched_conditions(child)
        matched=list(matched_conditions(self.dialogue.rule(category)['condition']))
        for condition in matched:
            key=condition_key(condition)
            if condition['kind'] in EVENT_KINDS and self.context.get('_temporal',{}).get(key,{}).get('active'):
                self.consumed_events[key]=self.context['_temporal'][key]['event']
        replacements={}
        for condition in matched:
            if condition['kind']=='watched_file':
                target=next((t for t in self.context_options.data['targets'] if t['id']==condition['target_id']),None)
                if target:
                    replacements={'target_name':target['label'],'target_open_count':str(self.context.get('_target_counts',{}).get(target['id'],0))}
                    break
        return Notice("",
                      self.phrase(category,replacements), expression=self.dialogue.rule(category)['expression'])

    def persist(self, now: datetime) -> None:
        # Keys are removed one day after the occurrence ends; cap corrupted files too.
        self.notified = {k: v for k, v in self.notified.items()
                         if isinstance(v, (int, float)) and v > now.timestamp()} 
        self.notified = dict(list(self.notified.items())[-512:])
        current_ids = {rule['id'] for rule in self.reminders.data['notifications']}
        self.custom_notified = {key: value for key, value in self.custom_notified.items() if key in current_ids}
        save_json(self.history_path, {"recent": self.recent, "notified": self.notified,
                                     'departure_date': self.departure_date, 'custom_notified': self.custom_notified})

    def custom_notice(self, now, hidden=False):
        if (hidden or is_quiet(now, self.settings)
                or (self.paused_until and now < self.paused_until)):
            return None
        for rule in sorted(self.reminders.data['notifications'], key=lambda rule: rule['time']):
            if self.context_options.error and rule['condition']['kind'] in ('month_end_business_day','monthly_business_day_before'):continue
            due = due_time(rule, now, self.context_options.calendar())
            if due is None or self.custom_notified.get(rule['id']) == due.date().isoformat():
                continue
            previous = self.custom_notified.get(rule['id'])
            last_display = self.last_display
            self.custom_notified[rule['id']] = due.date().isoformat()
            self.last_display = now
            try:
                self.persist(now)
            except OSError:
                if previous is None:
                    self.custom_notified.pop(rule['id'], None)
                else:
                    self.custom_notified[rule['id']] = previous
                self.last_display = last_display
                raise
            return Notice('', rule['message'], True, 'notice', 'reminder')
        return None

    def departure_notice(self, now, hidden=False, uptime_provider=lambda: None):
        if (not self.settings.departure_enabled or hidden or is_quiet(now, self.settings)
                or (self.paused_until and now < self.paused_until)
                or (self.settings.departure_weekdays and (self.context_options.error or not self.context_options.calendar().is_business_day(now.date())))
                or self.departure_date == now.date().isoformat()):
            return None
        hour, minute = map(int, self.settings.departure_time.split(':'))
        due = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if not 0 <= (now - due).total_seconds() < 600:
            return None
        self.departure_date = now.date().isoformat()
        self.last_display = now
        return Notice('退勤前のお知らせ', departure_body(self.settings.departure_message, now, uptime_provider()),
                      True, 'notice', 'departure')

    def next_notice(self, now: datetime, events: list[Event], hidden: bool = False,
                    connected: bool = False, allow_chatter: bool = True, allow_reminders: bool = True) -> Notice | None:
        if hidden or is_quiet(now, self.settings) or (self.paused_until and now < self.paused_until):
            return None
        options = self.dialogue.data["options"]
        reminder = self.dialogue.rule("meeting")
        for event in sorted(events, key=lambda e: e.start):
            delta = (event.start - now).total_seconds()
            if (connected and reminder["enabled"] and 0 < delta <= options["meeting_lead_minutes"] * 60
                    and event.key not in self.notified and event.legacy_key not in self.notified):
                previous_display = self.last_display
                self.notified[event.key] = (event.end + timedelta(days=1)).timestamp()
                minutes = max(1, int((delta + 59) // 60))
                text = self.phrase("meeting")
                state = f'（{event.response}）' if event.response else ''
                text = f'予定まであと{minutes}分です。{state}\n' + text
                if self.settings.show_titles and event.title:
                    text = event.title[:60] + "\n" + text
                self.last_display = now
                try:
                    self.persist(now)
                except OSError:
                    # No notice reached the UI. Retry after storage recovers.
                    self.notified.pop(event.key, None)
                    self.last_display = previous_display
                    raise
                status = f" · {event.response}" if event.response else ""
                return Notice(f"予定まで あと{minutes}分{status}", text, True, reminder["expression"], "calendar")
        if allow_reminders:
            message = self.one_shots.take_due(now)
            if message is not None:
                self.last_display = now
                return Notice('', message, True, 'notice', 'reminder')
            notice = self.custom_notice(now)
            if notice:
                return notice
        elapsed = (now - self.last_display).total_seconds()
        if options["suppress_during_meetings"] and connected and any(event.start <= now < event.end for event in events):
            return None  # Keep casual remarks out of calendar meeting time.
        if allow_chatter and self.settings.chatter and elapsed >= options["interval_minutes"] * 60:
            previous=(self.last_display,self.session_spoken,self.last_category,dict(self.category_last),
                      list(self.recent),dict(self.consumed_events))
            notice = self.conversation(now, events, connected, manual=False)
            if notice:
                self.last_display = now
                try:self.persist(now)
                except OSError:
                    (self.last_display,self.session_spoken,self.last_category,self.category_last,
                     self.recent,self.consumed_events)=previous
                    raise
            return notice
        return None
