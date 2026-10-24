"""Local, once-only reminders, separate from recurring notification rules."""
from copy import deepcopy
from datetime import datetime
import re
from uuid import uuid4

from .context_options import ContextOptionsStore


class OneShotError(ValueError):
    pass


class OneShotStore(ContextOptionsStore):
    @staticmethod
    def validate(document):
        if (not isinstance(document, dict) or type(document.get('schema_version')) is not int
                or document['schema_version'] != 1 or not isinstance(document.get('notifications'), list)
                or len(document['notifications']) > 100):
            raise OneShotError('単発通知は100件まで登録できます。')
        seen = set()
        for row in document['notifications']:
            if not isinstance(row, dict):
                raise OneShotError('単発通知の形式が不正です。')
            identifier = row.get('id')
            if not isinstance(identifier, str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}', identifier) or identifier in seen:
                raise OneShotError('単発通知のIDが不正です。')
            seen.add(identifier)
            value = row.get('at')
            try:
                if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}', value):
                    raise ValueError()
                if datetime.fromisoformat(value).isoformat(timespec='minutes') != value:
                    raise ValueError()
            except ValueError:
                raise OneShotError('通知の日付・時刻が不正です。') from None
            message = row.get('message')
            if not isinstance(message, str) or not message.strip() or len(message) > 1000:
                raise OneShotError('通知内容は1〜1000文字で入力してください。')
        return deepcopy(document)

    def __init__(self, path):
        super().__init__(path)
        if not self.path.exists() or self.error:
            self.data = {'schema_version': 1, 'notifications': []}
        if self.error:
            self.error = '単発通知を読み込めません。元のファイルは保持しています。'

    def add(self, when, message, now):
        if self.error:
            raise OneShotError(self.error)
        when = when.replace(tzinfo=None, second=0, microsecond=0)
        if when <= now.replace(tzinfo=None):
            raise OneShotError('現在より後の日付・時刻を選んでください。')
        candidate = deepcopy(self.data)
        candidate['notifications'].append({'id': uuid4().hex, 'at': when.isoformat(timespec='minutes'),
                                            'message': message.strip()})
        self.save(candidate)

    def take_due(self, now):
        """Commit removal before returning; a failed write leaves it pending."""
        if self.error:
            return None
        for row in sorted(self.data['notifications'], key=lambda row: row['at']):
            if datetime.fromisoformat(row['at']) > now.replace(tzinfo=None):
                break
            candidate = deepcopy(self.data)
            candidate['notifications'] = [item for item in candidate['notifications'] if item['id'] != row['id']]
            self.save(candidate)
            return row['message']
        return None
