"""The bundle smoke mode must not open or collect normal application data."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from companion.self_check import run


class BundleCheckTests(unittest.TestCase):
    def test_cli_renders_assets_without_creating_user_data(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            report = root/'smoke-report.json'
            env = os.environ.copy()
            env.update(LOCALAPPDATA=str(root/'user-data'), QT_QPA_PLATFORM='offscreen',
                       PYTHONDONTWRITEBYTECODE='1')
            main = Path(__file__).resolve().parents[1]/'main.py'
            process = subprocess.run([sys.executable, str(main), '--self-check', str(report)],
                                     env=env, capture_output=True, timeout=30)
            self.assertEqual(process.returncode, 0, process.stderr.decode('utf-8', errors='replace'))
            result = json.loads(report.read_text(encoding='utf-8'))
            self.assertTrue(result['success'])
            self.assertEqual(result['character_frames_rendered'], 12)
            self.assertEqual(result['prop_poses_rendered'], 9)
            self.assertEqual(result['pickup_poses_rendered'],3)
            self.assertEqual(result['note_poses_rendered'],6)
            self.assertEqual(result['topics'], 76)
            self.assertEqual(result['voices'], 7)
            self.assertFalse((root/'user-data').exists())

    def test_failure_report_omits_exception_details_and_has_failing_exit_status(self):
        with tempfile.TemporaryDirectory() as temporary:
            report = Path(temporary)/'smoke-report.json'
            with patch('companion.self_check.check_bundle', side_effect=ValueError('PRIVATE DOCUMENT NAME')):
                self.assertEqual(run(report), 1)
            self.assertNotIn('PRIVATE', report.read_text())
            self.assertEqual(json.loads(report.read_text())['error_type'], 'ValueError')

    def test_unwritable_report_is_not_reported_as_success(self):
        with tempfile.TemporaryDirectory() as temporary, \
             patch('companion.self_check.check_bundle', return_value={'success': True}):
            self.assertEqual(run(Path(temporary)/'missing'/'smoke-report.json'), 2)


if __name__ == '__main__':
    unittest.main()
