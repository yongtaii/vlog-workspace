#!/usr/bin/env python3
"""Create a standalone project from this skill's bundled local template."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--install', action='store_true', help='Create .venv and pip install project dependencies')
    args = parser.parse_args()
    skill = Path(__file__).resolve().parents[1]
    template = skill / 'assets/project'
    target = args.project.expanduser().resolve()
    if not template.is_dir():
        raise SystemExit('Skill template missing; rebuild with scripts/package_skill.py')
    if target == skill or skill in target.parents or target in skill.parents:
        raise SystemExit('Project must be separate from the Skill bundle')
    if target.exists() and any(target.iterdir()):
        raise SystemExit(f'Refusing to overwrite a nonempty project: {target}')
    target.mkdir(parents=True, exist_ok=True)
    shutil.copytree(template, target, dirs_exist_ok=True)
    local = target / 'skills/vlog-editor'
    local.mkdir(parents=True)
    shutil.copy2(skill / 'SKILL.md', local / 'SKILL.md')
    shutil.copytree(skill / 'references', local / 'references')
    shutil.copytree(skill / 'scripts', local / 'scripts', ignore=shutil.ignore_patterns('__pycache__'))
    discovery = target / '.agents/skills'
    discovery.mkdir(parents=True)
    (discovery / 'vlog-editor').symlink_to('../../skills/vlog-editor',target_is_directory=True)
    for directory in ('input/videos', 'input/photos', 'music', 'analysis', 'preview', 'output', 'analysis/lanes/claude', 'preview/claude', 'output/claude'):
        (target / directory).mkdir(parents=True,exist_ok=True)
        (target / directory / '.gitkeep').touch()
    if args.install:
        subprocess.run([sys.executable, '-m', 'venv', str(target / '.venv')], check=True)
        python = target / '.venv/bin/python'
        subprocess.run([str(python), '-m', 'pip', 'install', '-e', str(target)], check=True)
    print(f'Project ready: {target}\nAdd local videos to input/videos/ and photos to input/photos/, then run scripts/vlog.sh run')


if __name__ == '__main__':
    main()
