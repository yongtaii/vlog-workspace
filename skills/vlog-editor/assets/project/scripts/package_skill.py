#!/usr/bin/env python3
"""Bundle maintained project sources into the portable Skill; optionally install it."""
import argparse
import os
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--install', action='store_true')
    parser.add_argument('--agent', choices=('codex', 'claude', 'all'), default='codex', help='Which agent to install the user Skill for')
    args = parser.parse_args()
    skill = ROOT / 'skills/vlog-editor'
    template = skill / 'assets/project'
    template.mkdir(parents=True, exist_ok=True)
    for name in ('pyproject.toml', 'config.json', 'hints.example.json', 'AGENTS.md', 'CLAUDE.md', 'README.md', '.gitignore'):
        shutil.copy2(ROOT / name, template / name)
    for name in ('src', 'tests'):
        shutil.copytree(ROOT / name, template / name, dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__','*.egg-info'))
    (template / 'scripts').mkdir(exist_ok=True)
    for name in ('vlog.sh','vlog-claude.sh','smoke_test.py','test_incremental.py','package_skill.py','test_photos.py'):
        shutil.copy2(ROOT / 'scripts' / name, template / 'scripts' / name)
    (template / '.claude').mkdir(exist_ok=True)
    shutil.copy2(ROOT / '.claude/settings.json', template / '.claude/settings.json')
    shutil.copytree(ROOT / '.claude/skills', template / '.claude/skills', dirs_exist_ok=True)
    shutil.copy2(ROOT / 'config.claude.json', template / 'config.claude.json')
    print(f'Bundled Skill: {skill}')
    if args.install and args.agent in ('codex', 'all'):
        home = Path(os.environ.get('CODEX_HOME', Path.home() / '.codex'))
        destination = home / 'skills/vlog-editor'
        alias = Path.home() / '.agents/skills/vlog-editor'
        if alias.exists() or alias.is_symlink():
            raise SystemExit(f'Existing user Skill preserved: {alias}')
        if destination.exists():
            raise SystemExit(f'Existing Skill preserved; choose a new destination or update it explicitly: {destination}')
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(skill, destination, ignore=shutil.ignore_patterns('__pycache__'))
        alias.parent.mkdir(parents=True, exist_ok=True)
        alias.symlink_to(destination, target_is_directory=True)
        print(f'Installed Skill: {destination}\nCodex user discovery link: {alias}')
    if args.install and args.agent in ('claude', 'all'):
        home = Path(os.environ.get('CLAUDE_CONFIG_DIR', Path.home() / '.claude'))
        destination = home / 'skills/vlog-editor'
        if destination.exists() or destination.is_symlink():
            raise SystemExit(f'Existing Claude Skill preserved: {destination}')
        destination.parent.mkdir(parents=True, exist_ok=True)
        # Claude has its own Skill; it reads shared engine contracts from the project's skills/vlog-editor/references.
        shutil.copytree(ROOT / '.claude/skills/vlog-editor', destination, ignore=shutil.ignore_patterns('__pycache__'))
        print(f'Installed Claude Code Skill: {destination}')

if __name__ == '__main__':
    main()
