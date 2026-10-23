#!/usr/bin/env bash
# Claude Code lane: own timeline/history/storyboard (analysis/lanes/claude), preview/claude, output/claude.
# Titles are clip.card overlays on real shots. Shares source analysis and the verified cache with scripts/vlog.sh.
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
exec "$project_dir/.venv/bin/python" -m vlog_editor --project "$project_dir" --lane claude --title-style cards "$@"
