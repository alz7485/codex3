from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timedelta
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from companion.activity import FileHistory, FileObservation
from companion.core import Settings, save_json
from companion.dialogue import defaults, read_document, upgrade, validate
from companion.motion import ClickReactions, Motion
from companion.preferences import snapped_y


class ComfortLogicTests(unittest.TestCase):
    def test_same_stage_has_cooldown_but_escalation_is_immediate(self):
        clicks, options = ClickReactions(), defaults()['options']
        results = [clicks.click(i / 10, options) for i in range(7)]
        self.assertEqual(results, [None, None, None, 'click_concern', None, None, 'click_angry'])
        self.assertTrue(all(clicks.click(11 + i / 10, options) is None for i in range(7)))
        # Resetting the short burst must not erase the 30-second cooldown.
        self.assertEqual([clicks.click(31 + i / 10, options) for i in range(4)][-1], 'click_concern')

    def test_walk_looks_and_leans_before_moving_then_rests_facing_side(self):
        motion = Motion(uniform=lambda a, b: a)
        motion.wait, motion.distance = 0, 8
        x, first_move, phases = 100.0, None, set()
        for step in range(300):
            old_x = x
            x = motion.advance(.02, x, 0, 200, True)
            phases.add(motion.phase)
            if x != old_x and first_move is None:
                first_move = (step + 1) * .02
            if motion.phase in ('look', 'lean'):
                self.assertEqual(x, 100)
                self.assertEqual(motion.frame(), 0)
            if first_move is not None and motion.phase == 'idle':
                break  # Inspect the first settled trip before another short walk.
        self.assertGreaterEqual(first_move, .30)
        self.assertLessEqual(first_move, .4)
        self.assertTrue({'look', 'lean', 'walk', 'settle', 'idle'} <= phases)
        self.assertEqual(motion.frame(), 0)
        self.assertEqual(motion.facing, -1)
        self.assertAlmostEqual(x, 92, delta=.1)

    def test_interaction_cancels_walk_preparation_without_movement(self):
        motion = Motion()
        motion.wait = 0
        self.assertEqual(motion.advance(.1, 90, 0, 200, True), 90)
        self.assertEqual(motion.phase, 'look')
        self.assertEqual(motion.advance(.1, 90, 0, 200, False), 90)
        self.assertEqual(motion.phase, 'idle')
        self.assertGreaterEqual(motion.wait, .6)

    def test_snap_threshold_is_inclusive_and_can_be_disabled(self):
        self.assertEqual(snapped_y(884, 900, True, 16), 900)
        self.assertEqual(snapped_y(883, 900, True, 16), 883)
        self.assertEqual(snapped_y(884, 900, False, 16), 884)
        self.assertEqual(snapped_y(-116, -100, True, 16), -100)

    def test_anonymous_mail_upgrade_preserves_other_user_edits(self):
        old = defaults()
        old.pop('anonymous_mail_version')
        old['options'].pop('click_repeat_seconds')
        old['options']['interval_minutes'] = 23
        for bank in old['phrases'].values():
            bank['mail_received'] = ['山田さんからメールが来ました。', '{mail_from}メールが来ました。']
            bank['chat'][0] = '自分で編集した会話'
        result = validate(upgrade(old))
        self.assertEqual(result['options']['interval_minutes'], 23)
        self.assertEqual(result['options']['click_repeat_seconds'], 30)
        for voice, bank in result['phrases'].items():
            self.assertEqual(bank['mail_received'], defaults()['phrases'][voice]['mail_received'])
            self.assertTrue(all('山田' not in line and '{mail_from}' not in line for line in bank['mail_received']))
            self.assertEqual(bank['chat'][0], '自分で編集した会話')
        self.assertIn('山田', old['phrases']['控えめな皮肉屋']['mail_received'][0])
        self.assertEqual(upgrade(result), result)

    def test_legacy_sender_setting_cannot_enable_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'settings.json'
            save_json(path, {'mail_show_senders': True, 'walking': False, 'snap_distance': 999})
            settings = Settings.load(path)
            self.assertFalse(settings.mail_show_senders)
            self.assertFalse(settings.walking)
            self.assertEqual(settings.comfort_preset, 'custom')
            self.assertEqual(settings.snap_distance, 16)


class FullHistorySearchTests(unittest.TestCase):
    def test_search_spans_dates_matches_path_and_treats_sql_symbols_literally(self):
        with tempfile.TemporaryDirectory() as tmp:
            history = FileHistory(Path(tmp) / 'files.sqlite3')
            now = datetime.now().astimezone()
            observations = [
                FileObservation('C:/営業/予算.xlsx', '予算.xlsx', 'Excel', now - timedelta(days=10)),
                FileObservation('C:/経理/予算.xlsx', '予算.xlsx', 'Excel', now - timedelta(days=1)),
                FileObservation('C:/work/100%_done.xlsx', '100%_done.xlsx', 'Excel', now),
                FileObservation('C:/work/Straße.xlsx', 'Straße.xlsx', 'Excel', now),
            ]
            history.append(observations, now)
            self.assertEqual(len(history.search('予算', now)), 2)
            self.assertEqual(history.search('営業', now)[0][1], observations[0].path)
            self.assertEqual(len(history.search('%_', now)), 1)
            self.assertEqual(len(history.search('STRASSE', now)), 1)
            self.assertEqual(history.search("' OR 1=1 --", now), [])
            self.assertEqual(history.search('', now), [])

    def test_search_is_not_limited_to_the_2000_row_daily_view(self):
        with tempfile.TemporaryDirectory() as tmp:
            history = FileHistory(Path(tmp) / 'files.sqlite3')
            now = datetime.now().astimezone()
            history.append([FileObservation(f'C:/work/{i}.xlsx', f'資料{i}.xlsx', 'Excel', now)
                            for i in range(2105)], now)
            self.assertEqual(len(history.for_day(now.date(), now)), 2000)
            self.assertEqual(len(history.search('資料', now)), 2105)

    def test_search_obeys_retention_and_does_not_create_a_database_when_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'files.sqlite3'
            history = FileHistory(path)
            now = datetime.now().astimezone()
            self.assertEqual(history.search('資料', now), [])
            self.assertFalse(path.exists())
            history.append([FileObservation('C:/old.xlsx', '資料.xlsx', 'Excel', now - timedelta(days=120)),
                            FileObservation('C:/new.xlsx', '資料.xlsx', 'Excel', now)], now)
            self.assertEqual([row[1] for row in history.search('資料', now)], ['C:/new.xlsx'])


class ComfortInterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from companion.ui import create_application
        cls.app = create_application()

    def setUp(self):
        from companion.ui import Controller
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {'LOCALAPPDATA': self.temp.name})
        self.env.start()
        root = Path(self.temp.name) / 'Yohaku'
        save_json(root / 'settings.json', asdict(Settings(context_enabled=False, mail_enabled=False,
                                                       animation=False, quiet_start='00:00', quiet_end='00:00')))
        self.c = Controller(self.app,data_path=Path(os.environ["LOCALAPPDATA"])/"Yohaku")
        self.c.panel.hide()

    def tearDown(self):
        c = self.c
        for timer in (c.tick_timer, c.poll_timer, c.animation_timer, c.activity_timer, c.context_timer):
            timer.stop()
        c.shutdown()
        for widget in (c.panel, c.resident, c.bubble, c.history_window): widget.hide()
        c.tray.hide()
        self.app.processEvents()
        c.deleteLater()
        self.env.stop()
        self.temp.cleanup()

    def test_stationary_hover_resumes_walking_but_new_pointer_motion_and_press_pause_it(self):
        from PySide6.QtCore import QPoint
        c = self.c
        c.settings.animation = True
        c.settings.walking = True
        c.motion.wait = 0
        c.motion_x = 200.0
        c.resident.press_position = None
        clock = 100.0
        with patch.object(c.resident, 'underMouse', return_value=True), patch('companion.ui.QCursor.pos', return_value=QPoint(220, 500)) as cursor:
            for step in range(100):
                clock = 100 + step * .05
                c.last_motion_time = clock - .05
                with patch('companion.ui.time.monotonic', return_value=clock):
                    c.animate()
                if step < 4:
                    self.assertEqual(c.motion_x, 200)
                if step == 20:
                    self.assertNotEqual(c.motion_x, 200)
            self.assertNotEqual(c.motion_x, 200)
            position = c.motion_x
            cursor.return_value = QPoint(224, 500)
            c.last_motion_time = clock
            with patch('companion.ui.time.monotonic', return_value=clock + .05):
                c.animate()
            self.assertEqual(c.motion_x, position)
            c.resident.press_position = QPoint(224, 500)
            try:
                for step in range(100):
                    c.last_motion_time = clock + step * .05
                    with patch('companion.ui.time.monotonic', return_value=clock + (step + 1) * .05):
                        c.animate()
                    self.assertEqual(c.motion_x, position)
            finally:
                c.resident.press_position = None

    def test_presets_save_dialogue_and_flags_without_enabling_data_sources(self):
        c = self.c
        c.apply_preset('restrained')
        self.assertEqual((c.settings.chatter, c.settings.walking, c.settings.interval), (True, False, 30))
        self.assertEqual(c.dialogue.data['options']['interval_minutes'], 30)
        c.dialogue_saved()
        self.assertEqual(c.settings.comfort_preset, 'restrained')
        self.assertEqual(Settings.load(c.path / 'settings.json').comfort_preset, 'restrained')
        c.apply_preset('notifications')
        self.assertFalse(c.settings.chatter or c.settings.walking or c.settings.animation)
        self.assertFalse(c.settings.outlook_enabled or c.settings.file_logging or c.settings.context_enabled)
        c.show_message()
        self.assertTrue(c.bubble.isVisible())  # Explicit requests still work.
        c.apply_preset('standard')
        self.assertEqual((c.settings.chatter, c.settings.walking, c.settings.interval), (True, True, 10))
        c.panel.walking_check.click()
        self.assertEqual(c.settings.comfort_preset, 'custom')
        self.assertEqual(c.panel.preset_combo.currentData(), 'custom')

    def test_failed_preset_save_keeps_previous_behavior(self):
        c = self.c
        original = asdict(c.settings)
        document = deepcopy(c.dialogue.data)
        with patch.object(c.dialogue, 'save', side_effect=OSError('synthetic failure')):
            c.apply_preset('standard')
        self.assertEqual(asdict(c.settings), original)
        self.assertEqual(c.dialogue.data, document)
        self.assertIn('保存できません', c.panel.saved_label.text())
        # If the second file fails, the already-written dialogue must roll back.
        settings_bytes = (c.path / 'settings.json').read_bytes()
        with patch('companion.ui.save_json', side_effect=OSError('synthetic settings failure')):
            c.apply_preset('restrained')
        self.assertEqual(asdict(c.settings), original)
        self.assertEqual(read_document(c.dialogue.path), document)
        self.assertEqual((c.path / 'settings.json').read_bytes(), settings_bytes)

    def test_preview_does_not_modify_live_history_settings_or_click_lock(self):
        c = self.c
        settings, document, recent = asdict(c.settings), deepcopy(c.dialogue.data), list(c.engine.recent)
        c.show_preview()
        for key, frame in (('click_concern', 26), ('click_angry', 27), ('mail_received', 3), ('calendar', 4), ('call', 24)):
            c.preview.selector.setCurrentIndex(c.preview.selector.findData(key))
            c.preview.play()
            if key == 'call':
                self.assertIn(c.preview.mascot.frame_index, (24, 25))
            else:
                self.assertEqual(c.preview.mascot.frame_index, frame)
            self.assertFalse(c.preview.bubble.timer.isActive())
        self.assertEqual(asdict(c.settings), settings)
        self.assertEqual(c.dialogue.data, document)
        self.assertEqual(c.engine.recent, recent)
        self.assertIsNone(c.pending_reaction)
        self.assertIsNone(c.engine.click_reactions.last)
        self.assertFalse(c.bubble.isVisible())
        c.preview.hide()
        self.assertFalse(c.preview.timer.isActive())

    def test_drag_release_snaps_and_saves_but_can_be_disabled(self):
        from PySide6.QtCore import QPoint
        c = self.c
        area = c.resident_area()
        floor = area.bottom() + 1 - c.resident.height()
        c.drag_character(QPoint(area.left() + 100, floor - 15))
        c.finish_drag()
        self.assertEqual(c.resident.y(), floor)
        self.assertEqual(Settings.load(c.path / 'settings.json').position_y, floor)
        c.settings.snap_to_taskbar = False
        c.motion_y = floor - 15
        c.finish_drag()
        self.assertEqual(c.resident.y(), floor - 15)

    def test_history_search_ignores_calendar_and_clearing_restores_day_view(self):
        from PySide6.QtCore import QDate, QUrl
        from PySide6.QtGui import QDesktopServices
        c = self.c
        now = datetime.now().astimezone()
        c.activity_history.append([FileObservation('C:/work/昨日.xlsx', '予算.xlsx', 'Excel', now - timedelta(days=1)),
                                   FileObservation('C:/work/今日.xlsx', '予算.xlsx', 'Excel', now)], now)
        c.history_window.calendar.setSelectedDate(QDate.currentDate())
        c.history_window.search_edit.setText('予算')
        c.history_window.run_search()
        self.assertEqual(c.history_window.table.topLevelItemCount(), 2)
        self.assertIn('全履歴', c.history_window.day_label.text())
        self.assertIn('/', c.history_window.table.topLevelItem(0).text(0))
        with patch.object(QDesktopServices, 'openUrl', return_value=True) as opened:
            c.history_window.open_file(c.history_window.table.topLevelItem(1))
            self.assertEqual(opened.call_args.args[0], QUrl.fromLocalFile('C:/work/昨日.xlsx'))
        c.history_window.search_edit.clear()
        c.history_window.run_search()
        self.assertEqual(c.history_window.table.topLevelItemCount(), 1)
        self.assertNotIn('全履歴', c.history_window.day_label.text())


if __name__ == '__main__':
    unittest.main()
