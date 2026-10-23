"""Render the actual registered-notification editor using synthetic local data."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import tempfile

from companion.reminders import ReminderStore, new_rule
from companion.reminder_editor import ReminderEditor
from companion.ui import create_application


def main():
    app = create_application()
    with tempfile.TemporaryDirectory() as temporary:
        store = ReminderStore(Path(temporary) / 'reminders.json')
        month_end = new_rule()
        month_end.update(name='月末の確認', time='16:30', message='月末の確認をお願いします。')
        cutoff = new_rule()
        cutoff.update(name='15日締めの確認', time='15:00', message='締め日です。申請を確認してください。',
                      condition={'kind': 'monthly_weekday_before', 'day': 15})
        store.save({'schema_version': 1, 'notifications': [month_end, cutoff]})
        editor = ReminderEditor(store)
        editor.rules.setCurrentRow(1)
        editor.show()
        app.processEvents()
        destination = Path(__file__).parent / 'docs/registered-notifications.png'
        editor.grab().save(str(destination))
        editor.hide()
        print('Rendered', destination.name)


if __name__ == '__main__': main()
