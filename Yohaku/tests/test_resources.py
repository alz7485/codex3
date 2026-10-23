"""Windows API boundaries, averaging, unknown values and editable resource topics."""
from copy import deepcopy
import ctypes
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, patch

from companion.context import ResourceSampler, system_cpu_times, physical_memory_percent
from companion.core import Engine, Settings
from companion.dialogue import RESOURCE_RULE_IDS, defaults, read_document, matches, validate


class ResourceTests(unittest.TestCase):
    def test_native_api_reads_64_bit_counters_and_physical_memory_without_sleep(self):
        def times(idle, kernel, user):
            for pointer, low in ((idle, 40), (kernel, 80), (user, 20)):
                pointer._obj.low, pointer._obj.high = low, 1
            return 1
        def memory(pointer):
            self.assertEqual(pointer._obj.length, 64)
            self.assertEqual(ctypes.sizeof(pointer._obj), 64)
            pointer._obj.total_phys = 16 * 1024 ** 3
            pointer._obj.available_phys = 4 * 1024 ** 3
            return 1
        kernel = SimpleNamespace(GetSystemTimes=times, GlobalMemoryStatusEx=memory)
        with patch('companion.context.sys.platform', 'win32'), patch.object(ctypes, 'windll', SimpleNamespace(kernel32=kernel), create=True):
            self.assertEqual(system_cpu_times(), tuple(2**32 + n for n in (40, 80, 20)))
            self.assertEqual(physical_memory_percent(), 75)

    def test_native_failures_and_unsupported_platform_return_unknown(self):
        kernel = SimpleNamespace(GetSystemTimes=Mock(return_value=0), GlobalMemoryStatusEx=Mock(return_value=0))
        with patch.object(ctypes, 'windll', SimpleNamespace(kernel32=kernel), create=True):
            with patch('companion.context.sys.platform', 'win32'):
                self.assertIsNone(system_cpu_times())
                self.assertIsNone(physical_memory_percent())
            kernel.GetSystemTimes.reset_mock()
            with patch('companion.context.sys.platform', 'linux'):
                self.assertIsNone(system_cpu_times())
                self.assertIsNone(physical_memory_percent())
            kernel.GetSystemTimes.assert_not_called()

    def test_cpu_subtracts_idle_from_kernel_plus_user_and_waits_for_warmup(self):
        cpu = Mock(side_effect=[(100, 200, 100), (140, 250, 150), (160, 300, 200)])
        sampler = ResourceSampler(cpu, lambda: 75)
        self.assertEqual(sampler.sample(0), {'cpu_percent':None, 'memory_percent':75})
        self.assertIsNone(sampler.sample(5)['cpu_percent'])
        self.assertEqual(sampler.sample(10)['cpu_percent'], 70)

    def test_cpu_old_load_expires_from_rolling_average(self):
        counters = [0, 0, 0]
        sampler = ResourceSampler(lambda: tuple(counters), lambda: 40)
        sampler.sample(0)
        for second in range(5, 76, 5):
            counters[1] += 100
            if second > 10:
                counters[0] += 100
            result = sampler.sample(second)
        self.assertEqual(result['cpu_percent'], 0)
        self.assertLessEqual(len(sampler.samples), 12)

    def test_sleep_counter_reset_and_zero_interval_do_not_reuse_old_load(self):
        for time_value, counters in ((100, (200, 400, 300)), (10, (200, 400, 300)),
                                     (15, (0, 0, 0)), (15, (400, 310, 210)), (15, (160, 300, 200))):
            with self.subTest(time=time_value, counters=counters):
                provider = Mock(side_effect=[(100, 200, 100), (140, 250, 150), (160, 300, 200), counters])
                sampler = ResourceSampler(provider, lambda: 85)
                for second in (0, 5, 10): sampler.sample(second)
                self.assertIsNone(sampler.sample(time_value)['cpu_percent'])

    def test_provider_error_clears_cpu_baseline_and_keeps_memory_independent(self):
        provider = Mock(side_effect=[(0, 0, 0), (50, 100, 0), (100, 200, 0), OSError('unavailable'),
                                     (200, 400, 0), (250, 500, 0), (300, 600, 0)])
        sampler = ResourceSampler(provider, lambda: 90)
        values = [sampler.sample(second) for second in range(0, 35, 5)]
        self.assertEqual([v['cpu_percent'] for v in values], [None, None, 50, None, None, None, 50])
        self.assertTrue(all(v['memory_percent'] == 90 for v in values))
        for invalid in (None, float('nan'), float('inf'), -1, 101, True):
            self.assertIsNone(ResourceSampler(lambda: None, lambda: invalid).sample(0)['memory_percent'])

    def test_resource_threshold_boundaries_unknown_values_and_normal_conversation(self):
        document = defaults()
        now = datetime(2026, 10, 23, 10, tzinfo=timezone.utc)
        for key, boundary, outside in (('cpu_high',80,79.9), ('cpu_low',20,20.1),
                                       ('memory_high',85,84.9), ('memory_low',50,50.1)):
            rule = next(r for r in document['rules'] if r['id'] == key)
            metric = rule['condition']['metric']
            args = (now, now, True, [], False)
            self.assertTrue(matches(rule, *args, {metric:boundary}))
            for unknown in (outside, None, float('nan'), float('inf'), True):
                self.assertFalse(matches(rule, *args, {metric:unknown}))
        with tempfile.TemporaryDirectory() as temporary:
            engine = Engine(Settings(quiet_start='00:00', quiet_end='00:00'), Path(temporary)/'history.json', choose=lambda xs:xs[0])
            for rule in engine.dialogue.data['rules']: rule['enabled'] = rule['id'] == 'cpu_high'
            engine.context = {'cpu_percent':87}
            notice = engine.conversation(now, manual=False)
            self.assertEqual(notice.kind, 'message')
            self.assertFalse(notice.important)
            self.assertIn('87%', notice.text)
            self.assertIsNone(engine.conversation(now + timedelta(minutes=10), manual=False))
            self.assertIsNotNone(engine.conversation(now + timedelta(hours=1), manual=False))

    def test_old_json_gains_topics_once_and_preserves_edits_and_deletions(self):
        old = defaults()
        old.pop('resource_context_version')
        old['rules'] = [r for r in old['rules'] if r['id'] not in RESOURCE_RULE_IDS]
        for bank in old['phrases'].values():
            for key in RESOURCE_RULE_IDS: bank.pop(key)
        old['phrases']['控えめな皮肉屋']['chat'] = ['利用者の編集した文章']
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)/'dialogue.json'
            path.write_text(json.dumps(old, ensure_ascii=False))
            before = path.read_bytes()
            upgraded = read_document(path)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(upgraded['phrases']['控えめな皮肉屋']['chat'], ['利用者の編集した文章'])
            self.assertTrue(set(RESOURCE_RULE_IDS) <= {r['id'] for r in upgraded['rules']})
            upgraded['rules'] = [r for r in upgraded['rules'] if r['id'] != 'cpu_low']
            next(r for r in upgraded['rules'] if r['id'] == 'cpu_high')['condition']['minimum'] = 90
            for bank in upgraded['phrases'].values(): bank.pop('cpu_low')
            path.write_text(json.dumps(upgraded, ensure_ascii=False))
            self.assertEqual(read_document(path), upgraded)

    def test_upgrade_does_not_overflow_a_full_custom_rule_document(self):
        document = defaults()
        document.pop('resource_context_version')
        document['rules'] = [r for r in document['rules'] if r['id'] not in RESOURCE_RULE_IDS]
        for bank in document['phrases'].values():
            for key in RESOURCE_RULE_IDS: bank.pop(key)
        template = next(r for r in document['rules'] if r['id'] == 'chat')
        while len(document['rules']) < 200:
            rule = deepcopy(template); rule['id'] = f'custom_{len(document["rules"])}'
            document['rules'].append(rule)
            for bank in document['phrases'].values(): bank[rule['id']] = ['独自の会話']
        from companion.dialogue import upgrade
        migrated = validate(upgrade(document))
        self.assertEqual(len(migrated['rules']), 200)
        self.assertEqual(migrated['phrases'], document['phrases'])
