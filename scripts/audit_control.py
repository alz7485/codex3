"""Read-only configuration/plan/target helper; does not launch agents or tests."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]


def load(root: Path = ROOT):
    with (root / '.codex/audit.toml').open('rb') as stream:
        workflow = tomllib.load(stream)
    with (root / '.codex/config.toml').open('rb') as stream:
        config = tomllib.load(stream)
    agents = {}
    for path in sorted((root / '.codex/agents').glob('*.toml')):
        with path.open('rb') as stream:
            role = tomllib.load(stream)
        name = role.get('name')
        if not isinstance(name, str) or not name:
            raise ValueError(f'{path}: name is required')
        if name in agents:
            raise ValueError(f'duplicate agent name: {name}')
        agents[name] = {**role, 'file': str(path.relative_to(root))}
    return workflow, config, agents


def check(root: Path = ROOT):
    workflow, config, agents = load(root)
    if workflow.get('schema_version') != 1:
        raise ValueError('unsupported audit schema_version')
    groups = workflow.get('groups', [])
    if len(groups) != 6 or len({g['id'] for g in groups}) != 6:
        raise ValueError('six unique normal audit groups are required')
    specialists = [name for group in groups for name in group['roles']]
    if len(specialists) != 12 or len(set(specialists)) != 12:
        raise ValueError('the normal groups must cover 12 distinct specialisms exactly once')
    required = [*specialists, workflow['coordinator']]
    if len(set(required)) != 13:
        raise ValueError('coordinator must be independent of the 12 specialists')
    for name in required:
        role = agents.get(name)
        if not role or not all(isinstance(role.get(key), str) and role[key].strip()
                               for key in ('name', 'description', 'developer_instructions')):
            raise ValueError(f'{name}: missing official agent fields')
        if any(key in role for key in ('sandbox_mode', 'approval_policy', 'model_provider', 'mcp_servers')):
            raise ValueError(f'{name}: cannot override inherited session permissions/provider')
    for mode in ('normal', 'complete', 'postfix'):
        if not workflow.get('modes', {}).get(mode, {}).get('trigger'):
            raise ValueError(f'missing mode: {mode}')
    agent_settings = config.get('agents', {})
    if agent_settings.get('enabled') is not True:
        raise ValueError('agents.enabled must be true for this framework')
    capacity = agent_settings.get('max_concurrent_threads_per_session', agent_settings.get('max_threads'))
    if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity < 1:
        raise ValueError('positive agent concurrency required')
    for path in ('AGENTS.md', 'docs/audit/PROTOCOL.md', 'docs/audit/REPORT_TEMPLATE.md'):
        if not (root / path).is_file():
            raise ValueError(f'missing instructions: {path}')
    return {'status': 'ok', 'groups': 6, 'specialists': 12, 'coordinator': workflow['coordinator'],
            'configured_parallel_subagents': capacity, 'modes': workflow['modes'],
            'product_audit_executed': False}


def plan(mode: str, capacity: int = 6, changed=(), root: Path = ROOT):
    check(root)
    workflow, config, agents = load(root)
    if mode not in workflow['modes']:
        raise ValueError('unknown mode')
    if isinstance(capacity, bool) or capacity < 1:
        raise ValueError('capacity must be positive')
    limit = min(capacity, workflow['max_parallel_specialists'],
                config['agents'].get('max_concurrent_threads_per_session', config['agents'].get('max_threads', 6)))
    if mode == 'complete':
        names = [name for group in workflow['groups'] for name in group['roles']]
        names.sort(key=lambda name: int(agents[name]['description'].split('.', 1)[0]))
        jobs = [{'id': name, 'roles': [name], 'role_files': [agents[name]['file']]} for name in names]
    else:
        # Post-fix selection is deliberately conservative; the parent refines with evidence.
        jobs = [{'id': group['id'], 'group': group['name'], 'roles': group['roles'],
                 'role_files': [agents[name]['file'] for name in group['roles']]}
                for group in workflow['groups']]
    return {'mode': mode, 'trigger': workflow['modes'][mode]['trigger'], 'capacity': limit,
            'specialist_waves': [jobs[i:i + limit] for i in range(0, len(jobs), limit)],
            'coordinator_after_all_reports': workflow['coordinator'],
            'coordinator_file': agents[workflow['coordinator']]['file'],
            'changes': list(changed),
            'postfix_baseline_required': mode == 'postfix',
            'postfix_scope': '変更/依存/副作用へ絞る前の保守的6グループ。基準版と影響根拠を親が確定する。' if mode == 'postfix' else None,
            'spawn_agents': False, 'modify_product': False}


def resolve(root: Path = ROOT, explicit: str | None = None):
    workflow, _, _ = load(root)
    if explicit:
        target = Path(explicit).expanduser()
        if not target.is_absolute():
            target = root / target
        target = target.resolve()
        if not target.exists():
            raise ValueError('explicit target does not exist')
    else:
        direct = [p for p in (root, root / 'AttendSync')
                  if (p / 'main.py').is_file() and (p / 'engine.py').is_file()]
        if direct:
            target = direct[0]
        else:
            candidates = []
            for path in root.glob(workflow['archive_glob']):
                match = re.fullmatch(r'AttendSync_Trial(\d+)_.+_Complete\.zip', path.name)
                if match:
                    candidates.append((int(match[1]), path))
            if not candidates:
                raise ValueError('AttendSync source/full release not found; supply --target')
            version = max(n for n, _ in candidates)
            newest = [path for n, path in candidates if n == version]
            if len(newest) != 1:
                raise ValueError('multiple full archives share the newest Trial; supply --target')
            target = newest[0]
    if target.is_dir():
        if not ((target / 'main.py').is_file() and (target / 'engine.py').is_file()):
            raise ValueError('target directory is not an AttendSync source root')
        return {'target': str(target), 'kind': 'source',
                'fingerprint': '親がユーザーデータを除いたソースの相対パス/SHA256一覧を固定する',
                'extracted': False, 'executed': False}
    if target.suffix.lower() != '.zip':
        raise ValueError('target must be an AttendSync source root or ZIP')
    return {'target': str(target), 'kind': 'archive',
            'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
            'extracted': False, 'executed': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('check')
    planner = commands.add_parser('plan')
    planner.add_argument('--mode', choices=('normal', 'complete', 'postfix'), required=True)
    planner.add_argument('--capacity', type=int, default=6)
    planner.add_argument('--changed', nargs='*', default=[])
    target = commands.add_parser('resolve')
    target.add_argument('--target')
    args = parser.parse_args(argv)
    try:
        if args.command == 'check':
            result = check()
        elif args.command == 'plan':
            result = plan(args.mode, args.capacity, args.changed)
        else:
            result = resolve(explicit=args.target)
    except (ValueError, KeyError, OSError, tomllib.TOMLDecodeError) as error:
        print(json.dumps({'status': 'error', 'error': str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
