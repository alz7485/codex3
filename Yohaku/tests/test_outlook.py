"""Synthetic COM checks for tentative appointments and Inbox meeting requests."""
from datetime import datetime, timedelta, timezone
import hashlib
import sys
import types
import unittest
from unittest.mock import patch
from companion.outlook import APPOINTMENT, MEETING, read_calendar

NOW = datetime(2026, 10, 23, 9, 0, tzinfo=timezone.utc)
START = NOW + timedelta(minutes=10)
END = START + timedelta(minutes=30)


class FrozenDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return NOW.astimezone(tz) if tz else NOW.replace(tzinfo=None)


class Items:
    def __init__(self, values, reject_jet=False):
        self.values = values
        self.reject_jet = reject_jet
        self.filters = []
        self.offset = 0
        self.IncludeRecurrences = False
    def Sort(self, *_): pass
    def Restrict(self, value):
        self.filters.append(value)
        if self.reject_jet and not value.startswith('@SQL='):
            raise RuntimeError('regional date rejected')
        return self
    def GetFirst(self):
        self.offset = 0
        return self.values[0] if self.values else None
    def GetNext(self):
        self.offset += 1
        return self.values[self.offset] if self.offset < len(self.values) else None


class OutlookReadTests(unittest.TestCase):
    def appointment(self, gid='AABB', response=3, status=3, identity='appointment', start=START):
        return types.SimpleNamespace(EntryID=identity, GlobalAppointmentID=gid, AllDayEvent=False,
                                     MeetingStatus=status, ResponseStatus=response, StartUTC=start,
                                     EndUTC=start+timedelta(minutes=30), Subject='会議の件名')

    def request(self, gid='AABB', start=START, response=5, cancelled=False, missing=False, extra=None):
        properties = {
            f'{APPOINTMENT}/820D0040': start,
            f'{APPOINTMENT}/820E0040': start + timedelta(minutes=30),
            f'{APPOINTMENT}/8215000B': False,
            f'{APPOINTMENT}/82180003': response,
            f'{MEETING}/00030102': bytes.fromhex(gid),
        }
        properties.update(extra or {})
        def get_property(uri):
            key = uri.split('/id/')[1]
            if missing or key not in properties: raise RuntimeError('not available')
            return properties[key]
        class Request:
            EntryID = 'request-' + gid
            MessageClass = 'IPM.Schedule.Meeting.Canceled' if cancelled else 'IPM.Schedule.Meeting.Request'
            PropertyAccessor = types.SimpleNamespace(GetProperty=get_property)
            MeetingRequestType = 0
            subject_reads = 0
            @property
            def Subject(self):
                self.subject_reads += 1
                return '未承諾の件名'
            @property
            def Body(self): raise AssertionError('Do not read bodies')
            @property
            def UnRead(self): raise AssertionError('Do not read or change read flags')
            def GetAssociatedAppointment(self, *_): raise AssertionError('Do not create/associate appointments')
            def Save(self): raise AssertionError('Read-only')
            def Respond(self, *_): raise AssertionError('Never respond')
        return Request()

    def read(self, appointments=(), requests=(), show_titles=False, reject_jet=False, calendar_fails=False, inbox_fails=False, whole_week=False):
        calendar, inbox = Items(list(appointments), reject_jet), Items(list(requests))
        def folder(kind):
            if kind == 9:
                if calendar_fails: raise RuntimeError('calendar inaccessible')
                return types.SimpleNamespace(Items=calendar)
            if inbox_fails: raise RuntimeError('inbox inaccessible')
            return types.SimpleNamespace(Items=inbox)
        app = types.SimpleNamespace(GetNamespace=lambda _: types.SimpleNamespace(GetDefaultFolder=folder))
        package, client = types.ModuleType('win32com'), types.ModuleType('win32com.client')
        package.client = client
        client.GetActiveObject = lambda _: app
        com = types.ModuleType('pythoncom')
        com.CoInitialize = lambda: None
        com.CoUninitialize = lambda: None
        api = types.ModuleType('win32api')
        api.GetDateFormat = lambda *args: '10/23/2026'
        api.GetTimeFormat = lambda *args: '09:00 AM'
        with patch.dict(sys.modules, {'pythoncom':com, 'win32api':api, 'win32com':package, 'win32com.client':client}), patch('companion.outlook.sys.platform', 'win32'), patch('companion.outlook.datetime', FrozenDateTime):
            result = read_calendar(show_titles, whole_week)
        return result, calendar, inbox

    def test_prior_day_ongoing_calendar_and_pending_request_reach_remaining_schedule(self):
        from companion.advanced_context import remaining_meeting_metrics
        lower = NOW.replace(hour=0, minute=0)
        start = lower - timedelta(hours=1)
        end = NOW + timedelta(minutes=30)
        appointment = self.appointment(start=start)
        appointment.EndUTC = end
        request = self.request(start=start, extra={f'{APPOINTMENT}/820E0040': end})
        for appointments, requests in (([appointment], []), ([], [request])):
            with self.subTest(source='calendar' if appointments else 'pending'):
                result, _, _ = self.read(appointments, requests)
                self.assertTrue(result.complete)
                values = remaining_meeting_metrics(result, NOW)
                self.assertEqual(values['remaining_meetings'], 1)
                self.assertEqual(values['remaining_meeting_minutes'], 30)
                self.assertEqual(values['overlapping_meetings'], 1)

        # Reproduce the original late-day false "all finished" path through
        # the actual Controller metric merge and conversation engine.
        import tempfile
        from pathlib import Path
        from unittest.mock import Mock
        from companion import core, dialogue, ui
        from companion.advanced_context import ConditionTimeline
        now = NOW.replace(hour=16, minute=30)
        appointment.EndUTC = now + timedelta(minutes=30)
        finished = self.appointment('CCDD', start=lower+timedelta(hours=9))
        finished.EndUTC = lower+timedelta(hours=10)
        with patch(__name__ + '.NOW', now):
            events, _, _ = self.read([appointment, finished])
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            store = dialogue.DialogueStore(folder/'dialogue.json')
            for row in store.data['rules']:
                row['enabled'] = row['trigger'] != 'auto' or row['id'] == 'meeting_day_finished'
            settings = core.Settings(context_enabled=False, quiet_start='00:00', quiet_end='00:00')
            engine = core.Engine(settings, folder/'history.json', dialogue=store)
            engine.started = now-timedelta(hours=2)
            engine.last_display = now-timedelta(minutes=11)
            engine.session_spoken = True
            fake = types.SimpleNamespace(dialogue=store, settings=settings, engine=engine, usage=None,
                connected=True, connected_at=now, weekly_events=0, daily_events=len(events), events=events,
                condition_timeline=ConditionTimeline(), panel=types.SimpleNamespace(advanced_context_status=Mock()))
            ui.Controller.refresh_context_metrics(fake, now)
            self.assertEqual(engine.context['remaining_meetings'], 1)
            self.assertEqual(engine.context['completed_meetings'], 1)
            self.assertEqual(engine.context['remaining_meeting_minutes'], 30)
            self.assertIsNone(engine.next_notice(now, events, connected=True))

    def test_calendar_day_boundaries_exclude_ended_at_midnight_and_starting_tomorrow(self):
        lower = NOW.replace(hour=0, minute=0)
        ended = self.appointment('AAAA', start=lower-timedelta(hours=1))
        ended.EndUTC = lower
        tomorrow = self.appointment('BBBB', start=lower+timedelta(days=1))
        finished = self.appointment('CCCC', start=lower-timedelta(hours=2))
        finished.EndUTC = lower+timedelta(hours=1)
        result, _, _ = self.read([ended, tomorrow, finished])
        self.assertEqual([e.end for e in result], [finished.EndUTC])

    def test_unaccepted_and_tentative_calendar_items_are_included(self):
        result, calendar, _ = self.read([self.appointment('AABB', response=5), self.appointment('CCDD', response=2)])
        self.assertEqual([e.response for e in result], ['未承諾', '仮承諾'])
        self.assertTrue(calendar.IncludeRecurrences)
        self.assertTrue(result.complete)

    def test_unprocessed_request_is_read_without_adding_or_responding_or_subject_reads(self):
        request = self.request()
        result, _, inbox = self.read(requests=[request])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].response, '未承諾')
        self.assertEqual(result[0].start, START)
        self.assertEqual(result[0].title, '')
        self.assertEqual(request.subject_reads, 0)
        self.assertIn('[MessageClass]', inbox.filters[0])

    def test_same_meeting_in_calendar_and_inbox_is_deduplicated_and_keeps_its_key_after_acceptance(self):
        pending, _, _ = self.read(requests=[self.request()])
        accepted, _, _ = self.read([self.appointment()], [self.request()])
        self.assertEqual(len(accepted), 1)
        self.assertEqual(pending[0].key, accepted[0].key)
        self.assertEqual(accepted[0].response, '')

    def test_declined_cancelled_and_outdated_requests_do_not_return(self):
        result, _, _ = self.read([self.appointment(response=4)], [self.request()])
        self.assertEqual(result, [])
        result, _, _ = self.read(requests=[self.request(cancelled=True), self.request()])
        self.assertEqual(result, [])
        result, _, _ = self.read([self.appointment()], [self.request(cancelled=True), self.request()])
        self.assertEqual(result, [])
        result, _, _ = self.read(requests=[self.request(), self.request(cancelled=True)])
        self.assertEqual(len(result), 1)  # An older cancellation must not erase a newer request.
        request = self.request()
        request.MeetingRequestType = 524288
        result, _, _ = self.read(requests=[request])
        self.assertEqual(result, [])
        result, _, _ = self.read([self.appointment(status=7)], [self.request()])
        self.assertEqual(result, [])

    def test_bad_item_and_inaccessible_source_preserve_other_events_and_explain_partial_results(self):
        result, _, _ = self.read([object(), self.appointment()], [self.request(missing=True)])
        self.assertEqual(len(result), 1)
        self.assertFalse(result.complete)
        self.assertTrue(result.warnings)
        result, _, _ = self.read(requests=[self.request()], calendar_fails=True)
        self.assertEqual(len(result), 1)
        self.assertFalse(result.complete)
        with self.assertRaises(RuntimeError):
            self.read(calendar_fails=True, inbox_fails=True)

    def test_date_filter_falls_back_to_utc_dasl_and_subject_is_opt_in(self):
        request = self.request('CCDD')
        result, calendar, _ = self.read([self.appointment()], [request], show_titles=True, reject_jet=True)
        self.assertEqual(len(calendar.filters), 2)
        self.assertTrue(calendar.filters[1].startswith('@SQL='))
        self.assertEqual({e.title for e in result}, {'会議の件名', '未承諾の件名'})
        self.assertEqual(request.subject_reads, 1)

    def test_date_range_recurrences_and_legacy_notification_key_are_kept(self):
        tomorrow = START + timedelta(days=1)
        result, _, _ = self.read([self.appointment(start=START), self.appointment(start=tomorrow)], [self.request(start=tomorrow)])
        self.assertEqual(len(result), 1)
        week, _, _ = self.read([self.appointment(start=START), self.appointment(start=tomorrow)], [self.request(start=tomorrow)], whole_week=True)
        self.assertEqual(len(week), 2)
        legacy = hashlib.sha256(f'appointment/{START.astimezone().isoformat()}'.encode()).hexdigest()
        self.assertEqual(result[0].legacy_key, legacy)

    def test_rescheduled_requests_and_calendar_do_not_keep_old_start(self):
        moved = START + timedelta(hours=1)
        requests = [self.request(start=moved), self.request()]
        for appointments in ([], [self.appointment(start=moved)]):
            result, _, _ = self.read(appointments, requests)
            self.assertEqual([e.start for e in result], [moved])

    def test_latest_move_outside_day_suppresses_old_in_range_request(self):
        tomorrow = START + timedelta(days=1)
        requests = [self.request(start=tomorrow), self.request()]
        result, _, _ = self.read(requests=requests)
        self.assertEqual(result, [])
        result, _, _ = self.read(requests=requests, whole_week=True)
        self.assertEqual([e.start for e in result], [tomorrow])
        all_day_update = self.request(extra={f'{APPOINTMENT}/8215000B': True})
        result, _, _ = self.read(requests=[all_day_update, self.request()])
        self.assertEqual(result, [])

    def test_latest_cancellation_after_move_suppresses_all_old_versions(self):
        moved = START + timedelta(hours=1)
        result, _, _ = self.read([self.appointment()], [self.request(start=moved, cancelled=True), self.request()])
        self.assertEqual(result, [])
        result, _, _ = self.read(requests=[self.request(start=moved), self.request(cancelled=True)])
        self.assertEqual([e.start for e in result], [moved])

    def test_recurring_moved_exception_matches_original_date_and_keeps_other_days(self):
        tomorrow = START + timedelta(days=1)
        moved = START + timedelta(hours=1)
        occurrence = {f'{APPOINTMENT}/8223000B': True, f'{APPOINTMENT}/82280040': START}
        next_occurrence = {f'{APPOINTMENT}/8223000B': True, f'{APPOINTMENT}/82280040': tomorrow}
        result, _, _ = self.read(requests=[self.request(start=moved, extra=occurrence), self.request(extra=occurrence),
                                          self.request(start=tomorrow, extra=next_occurrence)], whole_week=True)
        self.assertEqual([e.start for e in result], [moved, tomorrow])
        result, _, _ = self.read(requests=[self.request(start=moved, cancelled=True, extra=occurrence),
                                          self.request(extra=occurrence), self.request(start=tomorrow, extra=next_occurrence)], whole_week=True)
        self.assertEqual([e.start for e in result], [tomorrow])

    def test_global_object_id_occurrence_date_matches_clean_calendar_identity(self):
        clean = '040000008200E00074C5B7101A82E008' + '00000000' + 'AABBCCDD'
        instance = clean[:32] + '07EA0A17' + clean[40:]  # 2026-10-23 original instance
        appointment = self.appointment(gid=clean, start=START + timedelta(hours=1))
        appointment.IsRecurring = True
        result, _, _ = self.read([appointment], [self.request(gid=instance)])
        self.assertEqual([e.start for e in result], [appointment.StartUTC])

    def test_comparable_revision_uses_newer_update_and_ignores_stale_cancel(self):
        appointment = self.appointment()
        appointment.PropertyAccessor = types.SimpleNamespace(GetProperty=lambda uri: 2 if uri.endswith('/82010003') else None)
        moved = START + timedelta(days=1)
        update = self.request(start=moved, extra={f'{APPOINTMENT}/82010003': 3})
        result, _, _ = self.read([appointment], [update, self.request()])
        self.assertEqual(result, [])  # The latest revision moved out of today's view.
        old_cancel = self.request(cancelled=True, extra={f'{APPOINTMENT}/82010003': 1})
        result, _, _ = self.read([appointment], [old_cancel])
        self.assertEqual([e.start for e in result], [START])
        appointment.IsRecurring = True
        old_cancel = self.request(cancelled=True, extra={f'{APPOINTMENT}/82010003': 1, f'{APPOINTMENT}/8223000B': True})
        result, _, _ = self.read([appointment], [old_cancel])
        self.assertEqual([e.start for e in result], [START])

    def test_recurring_series_cancel_keeps_only_a_later_reinvited_occurrence(self):
        tomorrow = START + timedelta(days=1)
        cancellation = self.request(cancelled=True, extra={f'{APPOINTMENT}/8223000B': True})
        occurrence = {f'{APPOINTMENT}/8223000B': True, f'{APPOINTMENT}/82280040': tomorrow}
        invitation = self.request(start=tomorrow, extra=occurrence)
        result, _, _ = self.read(requests=[cancellation, invitation], whole_week=True)
        self.assertEqual(result, [])
        result, _, _ = self.read(requests=[invitation, cancellation], whole_week=True)
        self.assertEqual([e.start for e in result], [tomorrow])


if __name__ == '__main__': unittest.main()
