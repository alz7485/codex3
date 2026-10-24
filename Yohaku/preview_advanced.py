"""Render real advanced condition/settings widgets using synthetic local data."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import datetime
from companion.ui import create_application
from companion.context_options import ContextOptionsStore,TopicPreferences
from companion.context_editor import ContextOptionsEditor
from companion.dialogue import DialogueStore
from companion.dialogue_editor import DialogueEditor
from companion.reminders import ReminderStore
from companion.reminder_editor import ReminderEditor


def main():
    app=create_application();destination=Path(__file__).parent/'docs'
    with TemporaryDirectory(prefix='yohaku-advanced-preview-') as temporary:
        root=Path(temporary);options=ContextOptionsStore(root/'context_options.json');prefs=TopicPreferences(root/'topic_preferences.json');dialogue=DialogueStore(root/'dialogue.json')
        options.data['calendar']['holidays']=['2026-10-30','2026-12-29','2026-12-30','2026-12-31']
        options.data['calendar']['workdays']=['2026-10-24']
        options.data['targets']=[{'id':'daily','label':'日報','path':'C:/work/日報.xlsx','kind':'file'},
            {'id':'project','label':'進行中の案件','path':'C:/work/案件','kind':'folder'}]
        prefs.update('cpu_high',muted_date=datetime.now().astimezone().date().isoformat())
        editor=ContextOptionsEditor(options,prefs,dialogue);editor.show()
        for index,name in enumerate(('advanced-calendar','advanced-targets','advanced-meetings','advanced-topics')):
            editor.tabs.setCurrentIndex(index)
            if index==3:editor.topic.setCurrentIndex(editor.topic.findData('cpu_high'))
            app.processEvents();editor.grab().save(str(destination/(name+'.png')))
        editor.hide()
        conditions=DialogueEditor(dialogue,options);conditions.resize(1040,1060);conditions.show()
        conditions.path_label.setText(r'保存先：%LOCALAPPDATA%\Yohaku\dialogue.json')
        conditions.rule_list.setCurrentRow(next(i for i,r in enumerate(conditions.draft['rules']) if r['id']=='cpu_recovered'))
        conditions.tabs.setCurrentIndex(1);app.processEvents();conditions.rule_list.scrollToItem(conditions.rule_list.currentItem());app.processEvents()
        conditions.grab().save(str(destination/'advanced-conditions.png'));conditions.hide()
        reminders=ReminderEditor(ReminderStore(root/'reminders.json'),options);reminders.add_rule()
        reminders.kind.setCurrentIndex(reminders.kind.findData('month_end_business_day'));reminders.name.setText('月末の確認')
        reminders.show();app.processEvents();reminders.grab().save(str(destination/'registered-business-days.png'))
        reminders.dirty=False;reminders.hide()
    print('Rendered advanced settings, conditions and business-day notifications (synthetic data)')


if __name__=='__main__':main()
