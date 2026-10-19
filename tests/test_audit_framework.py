"""Audit routing and preservation checks; no product tests or agents are launched."""
from __future__ import annotations
import hashlib
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import audit_control as audit


class AuditFrameworkTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        shutil.copytree(ROOT / '.codex', self.root / '.codex')
        shutil.copytree(ROOT / 'docs/audit', self.root / 'docs/audit')
        shutil.copy2(ROOT / 'AGENTS.md', self.root / 'AGENTS.md')

    def test_all_thirteen_roles_and_modes_exist(self):
        result = audit.check(self.root)
        self.assertEqual((result['groups'], result['specialists']), (6, 12))
        self.assertEqual(set(result['modes']), {'normal', 'complete', 'postfix'})
        self.assertFalse(result['product_audit_executed'])

    def test_normal_is_six_parallel_groups_covering_twelve_roles(self):
        result = audit.plan('normal', root=self.root)
        self.assertEqual([len(wave) for wave in result['specialist_waves']], [6])
        roles = [name for job in result['specialist_waves'][0] for name in job['roles']]
        self.assertEqual(len(set(roles)), 12)
        self.assertNotIn(result['coordinator_after_all_reports'], roles)

    def test_complete_uses_twelve_distinct_jobs_in_two_waves(self):
        result = audit.plan('complete', root=self.root)
        self.assertEqual([len(wave) for wave in result['specialist_waves']], [6, 6])
        jobs = [job for wave in result['specialist_waves'] for job in wave]
        self.assertTrue(all(len(job['roles']) == 1 for job in jobs))
        self.assertEqual(len({job['id'] for job in jobs}), 12)

    def test_lower_host_capacity_is_respected(self):
        result = audit.plan('complete', capacity=2, root=self.root)
        self.assertEqual([len(wave) for wave in result['specialist_waves']], [2] * 6)

    def test_postfix_requires_baseline_and_preserves_changed_paths(self):
        result = audit.plan('postfix', changed=['outlook_mail.py'], root=self.root)
        self.assertTrue(result['postfix_baseline_required'])
        self.assertEqual(result['changes'], ['outlook_mail.py'])
        self.assertIn('audit_skeptic', [r for wave in result['specialist_waves'] for job in wave for r in job['roles']])
        self.assertFalse(result['modify_product'])

    def test_zero_capacity_is_rejected(self):
        with self.assertRaises(ValueError):
            audit.plan('normal', capacity=0, root=self.root)

    def test_duplicate_specialism_cannot_silently_reduce_coverage(self):
        path = self.root / '.codex/audit.toml'
        path.write_text(path.read_text().replace('audit_architecture', 'audit_specification'))
        with self.assertRaises(ValueError):
            audit.check(self.root)

    def test_missing_role_is_an_error(self):
        (self.root / '.codex/agents/audit_skeptic.toml').unlink()
        with self.assertRaises(ValueError):
            audit.check(self.root)

    def test_unsupported_per_role_sandbox_is_not_claimed(self):
        path = self.root / '.codex/agents/audit_security.toml'
        path.write_text(path.read_text() + '\nsandbox_mode = "read-only"\n')
        with self.assertRaises(ValueError):
            audit.check(self.root)

    def test_inspection_does_not_change_existing_config_or_extensions(self):
        path = self.root / '.codex/config.toml'
        path.write_text(path.read_text() + '\n[existing_extension]\nkeep = "preserved"\n')
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        audit.check(self.root)
        audit.plan('normal', root=self.root)
        after = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before, after)

    def release(self, name):
        folder = self.root / 'downloads/AttendSync'
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / name
        path.write_bytes(name.encode())
        return path

    def test_latest_numeric_trial_not_lexicographic_order(self):
        self.release('AttendSync_Trial9_Old_Complete.zip')
        expected = self.release('AttendSync_Trial10_New_Complete.zip')
        self.release('AttendSync_Trial99_Essentials.zip')
        result = audit.resolve(self.root)
        self.assertEqual(Path(result['target']), expected)
        self.assertEqual(result['sha256'], hashlib.sha256(expected.read_bytes()).hexdigest())
        self.assertFalse(result['executed'])
        self.assertFalse(result['extracted'])

    def test_ambiguous_latest_release_requires_explicit_target(self):
        self.release('AttendSync_Trial10_First_Complete.zip')
        self.release('AttendSync_Trial10_Second_Complete.zip')
        with self.assertRaises(ValueError):
            audit.resolve(self.root)

    def test_direct_source_precedes_archived_release(self):
        self.release('AttendSync_Trial10_Old_Complete.zip')
        (self.root / 'main.py').write_text('# source')
        (self.root / 'engine.py').write_text('# source')
        self.assertEqual(audit.resolve(self.root)['kind'], 'source')

    def test_unrelated_repository_root_is_not_mistaken_for_attendsync(self):
        (self.root / 'app.py').write_text('# different product')
        with self.assertRaises(ValueError):
            audit.resolve(self.root)

    def test_explicit_target_must_exist(self):
        with self.assertRaises(ValueError):
            audit.resolve(self.root, explicit='missing.zip')


if __name__ == '__main__':
    unittest.main(verbosity=2)
