#!/usr/bin/env python3
"""Plan, install, or verify repository-owned engineering skills. No Git writes.

Ownership: portable-engineering-skills/v1
Run --verify from a fresh clone without an AIOS checkout. --source defaults to
the repository containing this script. No bundled executable is ever run.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

OWNER = 'portable-engineering-skills/v1'
GUIDE_MARKER = '<!-- portable-engineering-skills:v1 -->'
START = '<!-- portable-engineering-skills:start -->'
END = '<!-- portable-engineering-skills:end -->'
BLOCK = (START + '\n## Agent engineering skills\n\n'
         'Before coding work, read '
         '[docs/agent-engineering.md](docs/agent-engineering.md). '
         'Use the repository-local versions and namespaced pstack entries; '
         'existing task, authorization, and release rules still govern.\n'
         '@docs/agent-engineering.md\n' + END)
EXCLUDES = {'/.agents/skills/pstack-*', '/.claude/skills/pstack-*'}
OLD_COMMENT = '# AIOS local pstack discovery links; source versioned in ai-life-os.'


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(['git', '-C', str(repo), *args], text=True,
                            capture_output=True)
    if result.returncode:
        raise ValueError(result.stderr.strip() or 'Git inspection failed')
    return result.stdout.strip()


def inside(path: Path, root: Path) -> bool:
    return path.resolve().is_relative_to(root.resolve())


def exists(path: Path) -> bool:
    return os.path.lexists(path)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_parent(path: Path, repo: Path) -> None:
    if not inside(path.parent, repo):
        raise ValueError(f'Parent escapes repository: {path}')
    for ancestor in (path.parent, *path.parent.parents):
        if ancestor == repo.parent:
            break
        if exists(ancestor) and not ancestor.is_dir():
            raise ValueError(f'Parent is not a directory: {ancestor}')


def closure(directory: Path) -> None:
    """A copied bundle must not depend on absolute or external symlinks."""
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError(f'Bundle is not a physical directory: {directory}')
    for path in directory.rglob('*'):
        if path.is_symlink():
            if os.path.isabs(os.readlink(path)) or not inside(path, directory):
                raise ValueError(f'Nonportable bundle symlink: {path}')
            if not path.exists():
                raise ValueError(f'Broken bundle symlink: {path}')


def pstack_check(package: Path) -> dict:
    closure(package)
    manifest = json.loads((package / 'SOURCE.json').read_text())
    hashes = manifest['source_sha256']
    upstream = package / 'upstream'
    actual = {p.relative_to(upstream).as_posix()
              for p in upstream.rglob('*') if p.is_file() or p.is_symlink()}
    if actual != set(hashes):
        raise ValueError(f'Pinned source file set differs: {package}')
    for rel, expected in hashes.items():
        file = upstream / rel
        if not inside(file, upstream) or digest(file) != expected:
            raise ValueError(f'Pinned upstream hash mismatch: {file}')
    skills = manifest['skills']
    names = {s['installed_name'] for s in skills}
    found = {p.parent.name for p in (package / 'entrypoints').glob('*/SKILL.md')}
    if len(names) != manifest['main_skill_count'] or found != names:
        raise ValueError('Pstack entrypoint inventory differs from SOURCE.json')
    for item in skills:
        name, original = item['installed_name'], item['upstream_name']
        if name != 'pstack-' + original or Path(original).name != original:
            raise ValueError(f'Unexpected pstack namespace: {name}')
        folder = package / 'entrypoints' / name
        text = (folder / 'SKILL.md').read_text()
        policy = (folder / 'agents/openai.yaml').read_text()
        if f'\nname: {name}\n' not in text or 'disable-model-invocation: true' not in text:
            raise ValueError(f'Unsafe entrypoint metadata: {folder}')
        if 'allow_implicit_invocation: false' not in policy:
            raise ValueError(f'Unsafe implicit invocation policy: {folder}')
        for relative in ('../../AIOS-ADAPTER.md',
                         f'../../upstream/skills/{original}/SKILL.md'):
            if not (folder / relative).is_file():
                raise ValueError(f'Broken source reference: {folder / relative}')
    return manifest


def skill_name(folder: Path) -> str:
    file = folder / 'SKILL.md'
    if not file.is_file():
        raise ValueError(f'Existing skill has no SKILL.md: {folder}')
    text = file.read_text()
    if not text.startswith('---\n'):
        raise ValueError(f'Existing skill lacks frontmatter: {folder}')
    for line in text.split('---', 2)[1].splitlines():
        if line.startswith('name:'):
            return line.partition(':')[2].strip().strip('\"\'')
    raise ValueError(f'Existing skill lacks a name: {folder}')


def matt_inventory(directory: Path) -> dict:
    result = {}
    for file in sorted(directory.rglob('SKILL.md')):
        name = skill_name(file.parent)
        if not name or name in ('.', '..') or '/' in name or '\\' in name:
            raise ValueError(f'Unsafe Matt skill name: {name}')
        if name in result:
            raise ValueError(f'Duplicate Matt skill name: {name}')
        result[name] = file.parent.relative_to(directory)
    if not result:
        raise ValueError(f'No Matt Pocock skills found: {directory}')
    return result


def routing_block(physical: Path, repo: Path) -> str:
    relative = Path(os.path.relpath(repo / 'docs/agent-engineering.md', physical.parent)).as_posix()
    return BLOCK.replace('docs/agent-engineering.md', relative)


def support_check(repo: Path) -> None:
    for relative, marker in (('docs/agent-engineering.md', GUIDE_MARKER),
                             ('scripts/install_portable_engineering_skills.py', OWNER)):
        path = repo / relative
        if path.is_symlink() or not path.is_file() or not inside(path, repo):
            raise ValueError(f'Portable support is not a local physical file: {path}')
        if marker not in path.read_text():
            raise ValueError(f'Portable support ownership missing: {path}')
    guide = repo / 'docs/agent-engineering.md'
    for link in re.findall(r'\]\(([^)]+)\)', guide.read_text()):
        target = link.split('#', 1)[0]
        if not target or re.match(r'[A-Za-z][A-Za-z0-9+.-]*:', target):
            continue
        if target.startswith('/') or not inside(guide.parent / target, repo) or not (guide.parent / target).exists():
            raise ValueError(f'Nonportable guide dependency: {link}')
    for target in re.findall(r'^@([^\s]+)', guide.read_text(), re.MULTILINE):
        if target.startswith('/') or not inside(guide.parent / target, repo) or not (guide.parent / target).exists():
            raise ValueError(f'Nonportable guide import: {target}')


def tree_equal(left: Path, right: Path) -> bool:
    def files(root: Path) -> dict:
        return {p.relative_to(root).as_posix(): digest(p)
                for p in root.rglob('*') if p.is_file()}
    return files(left) == files(right)


def plan(repo: Path, source: Path) -> dict:
    if Path(git(repo, 'rev-parse', '--show-toplevel')).resolve() != repo:
        raise ValueError('--repo must identify an explicit repository root')
    canonical = source / 'skills/pstack'
    manifest = pstack_check(canonical)
    copies, links, writes, preserved = [], [], [], []
    target = repo / 'skills/pstack'
    safe_parent(target, repo)
    if exists(target):
        current = pstack_check(target)
        if current['upstream_commit'] != manifest['upstream_commit']:
            raise ValueError(f'Existing pstack snapshot differs; preserve it: {target}')
        if target != canonical and not tree_equal(target, canonical):
            raise ValueError(f'Existing pstack package differs; refusing overwrite: {target}')
    else:
        copies.append((canonical, target))
    matt = repo / 'skills/mattpocock'
    safe_parent(matt, repo)
    matt_source = matt if exists(matt) else source / 'skills/mattpocock'
    closure(matt_source)
    matt_skills = matt_inventory(matt_source)
    if not exists(matt):
        copies.append((matt_source, matt))
    else:
        preserved.append({'path': 'skills/mattpocock', 'reason': 'existing snapshot'})

    # Introducing a Claude root in a worktree can hide unrelated main-checkout
    # skills. Fail before mutation rather than copying or shadowing that history.
    main = next((Path(line[9:]).resolve()
                 for line in git(repo, 'worktree', 'list', '--porcelain').splitlines()
                 if line.startswith('worktree ')), repo)
    if main != repo and not exists(repo / '.claude/skills'):
        inherited = main / '.claude/skills'
        if inherited.is_dir() and any(inherited.iterdir()):
            expected = {item['installed_name']: canonical / 'entrypoints' / item['installed_name']
                        for item in manifest['skills']}
            entries = list(inherited.iterdir())
            owned_only = all(entry.name in expected and entry.is_symlink()
                             and entry.resolve() == expected[entry.name].resolve()
                             for entry in entries)
            if not owned_only:
                raise ValueError('Claude inherits another checkout; installing a new root '
                                 'would shadow it. Localize that inherited set explicitly first.')

    migrated = 0
    for directory in (repo / '.agents/skills', repo / '.claude/skills'):
        safe_parent(directory / '_entry', repo)
        if exists(directory) and not directory.is_dir():
            raise ValueError(f'Discovery root is not a directory: {directory}')
        for item in manifest['skills']:
            name = item['installed_name']
            alias = directory / name
            destination = target / 'entrypoints' / name
            old = canonical / 'entrypoints' / name
            state = 'create'
            if exists(alias):
                if not alias.is_symlink():
                    raise ValueError(f'Unknown pstack collision: {alias}')
                if alias.resolve() == destination.resolve():
                    state = 'replace' if os.path.isabs(os.readlink(alias)) else 'keep'
                elif alias.resolve() == old.resolve() and old != destination:
                    state = 'replace'
                    migrated += 1
                else:
                    raise ValueError(f'Unowned pstack symlink: {alias}')
            links.append((alias, destination, state, os.readlink(alias) if state == 'replace' else None))
        for name in matt_skills:
            alias = directory / name
            destination = matt / matt_skills[name]
            if exists(alias):
                if not inside(alias, repo) or skill_name(alias) != name:
                    raise ValueError(f'Unknown or external Matt skill collision: {alias}')
                preserved.append({'path': alias.relative_to(repo).as_posix(),
                                  'source': alias.resolve().relative_to(repo).as_posix(),
                                  'reason': 'existing local skill retained byte-for-byte'})
                if alias.is_symlink() and os.path.isabs(os.readlink(alias)):
                    links.append((alias, alias.resolve(), 'replace', os.readlink(alias)))
                continue
            links.append((alias, destination, 'create', 'mattpocock'))

    guide = source / 'docs/agent-engineering.md'
    installer = Path(__file__).resolve()
    for src, dst, marker in ((guide, repo / 'docs/agent-engineering.md', GUIDE_MARKER),
                             (installer, repo / 'scripts' / installer.name, OWNER)):
        safe_parent(dst, repo)
        if not src.is_file() or marker not in src.read_text():
            raise ValueError(f'Owned portable support source missing: {src}')
        if exists(dst):
            if dst.is_symlink() or not dst.is_file():
                raise ValueError(f'Unknown support collision: {dst}')
            if src.read_bytes() == dst.read_bytes():
                continue
            if marker not in dst.read_text():
                raise ValueError(f'Unowned support file: {dst}')
        copies.append((src, dst))
    seen = set()
    for name in ('AGENTS.md', 'CLAUDE.md'):
        path = repo / name
        if not inside(path, repo):
            raise ValueError(f'Startup file escapes repository: {path}')
        physical = path.resolve()
        if physical in seen:
            continue
        seen.add(physical)
        text = path.read_text() if path.exists() else ''
        if text.count(START) != text.count(END) or text.count(START) > 1:
            raise ValueError(f'Malformed owned routing block: {path}')
        if START in text:
            before, rest = text.split(START, 1)
            _, after = rest.split(END, 1)
            updated = before + routing_block(physical, repo) + after
        else:
            updated = text + ('\n\n' if text and not text.endswith('\n\n') else '') + routing_block(physical, repo) + '\n'
        if updated != text:
            writes.append((physical, updated))

    common = Path(git(repo, 'rev-parse', '--git-common-dir'))
    common = common if common.is_absolute() else repo / common
    exclude = common.resolve() / 'info/exclude'
    cleanup = None
    # Retain the shared ignore rule while other in-progress worktrees still use
    # old external aliases. The caller may force-stage the new tracked aliases.
    other_old = False
    if migrated:
        for line in git(repo, 'worktree', 'list', '--porcelain').splitlines():
            if not line.startswith('worktree '):
                continue
            checkout = Path(line[9:]).resolve()
            if checkout == repo:
                continue
            for root in ('.agents/skills', '.claude/skills'):
                for item in manifest['skills']:
                    alias = checkout / root / item['installed_name']
                    old = canonical / 'entrypoints' / item['installed_name']
                    if alias.is_symlink() and alias.resolve() == old.resolve():
                        other_old = True
        if exclude.is_file() and not other_old:
            old_text = exclude.read_text()
            if OLD_COMMENT in old_text.splitlines():
                new_text = '\n'.join(line for line in old_text.splitlines()
                                     if line not in EXCLUDES and line != OLD_COMMENT) + '\n'
                if new_text != old_text:
                    cleanup = (exclude, new_text)
    return {'manifest': manifest, 'copies': copies, 'links': links, 'writes': writes,
            'preserved': preserved, 'exclude_cleanup': cleanup,
            'shared_excludes_retained': other_old, 'migrated_links': migrated}


def apply_plan(data: dict) -> None:
    for src, dst in data['copies']:
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            if exists(dst):
                raise ValueError(f'Concurrent bundle appeared: {dst}')
            with tempfile.TemporaryDirectory(prefix='.engineering-', dir=dst.parent) as temp:
                staged = Path(temp) / 'bundle'
                shutil.copytree(src, staged, symlinks=True)
                staged.rename(dst)
        else:
            shutil.copy2(src, dst)
    for alias, destination, state, previous in data['links']:
        if state == 'keep':
            continue
        alias.parent.mkdir(parents=True, exist_ok=True)
        if state == 'replace':
            if not alias.is_symlink() or os.readlink(alias) != previous:
                raise ValueError(f'Concurrent discovery collision: {alias}')
            alias.unlink()
        elif exists(alias):
            raise ValueError(f'Concurrent discovery collision: {alias}')
        alias.symlink_to(os.path.relpath(destination.resolve(), alias.parent.resolve()),
                         target_is_directory=True)
    for path, text in data['writes']:
        path.write_text(text)
    if data['exclude_cleanup']:
        path, text = data['exclude_cleanup']
        path.write_text(text)


def verify(repo: Path) -> dict:
    if Path(git(repo, 'rev-parse', '--show-toplevel')).resolve() != repo:
        raise ValueError('--repo must identify an explicit repository root')
    manifest = pstack_check(repo / 'skills/pstack')
    closure(repo / 'skills/mattpocock')
    links = 0
    for root in ('.agents/skills', '.claude/skills'):
        safe_parent(repo / root / '_entry', repo)
        for item in manifest['skills']:
            alias = repo / root / item['installed_name']
            expected = repo / 'skills/pstack/entrypoints' / item['installed_name']
            if (not alias.is_symlink() or os.path.isabs(os.readlink(alias))
                    or alias.resolve() != expected.resolve() or not inside(alias, repo)):
                raise ValueError(f'Pstack discovery is not repository-local: {alias}')
            links += 1
        for name in matt_inventory(repo / 'skills/mattpocock'):
            alias = repo / root / name
            if (not inside(alias, repo) or not alias.is_dir()
                    or skill_name(alias) != name
                    or (alias.is_symlink() and os.path.isabs(os.readlink(alias)))):
                raise ValueError(f'Matt discovery is not repository-local: {alias}')
            links += 1
    for relative in ('AGENTS.md', 'CLAUDE.md'):
        path = repo / relative
        if not inside(path, repo) or routing_block(path.resolve(), repo) not in path.read_text():
            raise ValueError(f'Portable routing missing: {path}')
    support_check(repo)
    return {'source_files_verified': len(manifest['source_sha256']),
            'pstack_skills': len(manifest['skills']), 'discovery_entries_checked': links}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--source', type=Path, default=Path(__file__).resolve().parents[1])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--apply', action='store_true')
    mode.add_argument('--verify', action='store_true')
    parser.add_argument('--receipt', type=Path)
    args = parser.parse_args()
    repo, source = args.repo.resolve(), args.source.resolve()
    report = {'observed_at': dt.datetime.now(dt.timezone.utc).isoformat(),
              'mode': 'verify' if args.verify else 'apply' if args.apply else 'plan',
              'repo': str(repo), 'errors': []}
    try:
        if args.verify:
            report.update(verify(repo))
        else:
            data = plan(repo, source)
            report.update({'upstream_commit': data['manifest']['upstream_commit'],
                           'copies': [str(dst.relative_to(repo)) for _, dst in data['copies']],
                           'routing_files': [str(p.relative_to(repo)) for p, _ in data['writes']],
                           'links_to_create': sum(s == 'create' for _, _, s, _ in data['links']),
                           'links_to_replace': sum(s == 'replace' for _, _, s, _ in data['links']),
                           'preserved': data['preserved'],
                           'shared_excludes_retained': data['shared_excludes_retained']})
            if args.apply:
                apply_plan(data)
                report.update(verify(repo))
    except (ValueError, OSError, KeyError, json.JSONDecodeError) as error:
        report['errors'].append(str(error))
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return bool(report['errors'])


if __name__ == '__main__':
    sys.exit(main())
