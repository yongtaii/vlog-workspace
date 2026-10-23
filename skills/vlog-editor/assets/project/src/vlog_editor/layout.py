"""Workspace paths; source data is separate from every generated artifact."""
from pathlib import Path


def paths(root):
    root = Path(root).resolve()
    return {"input": root/"input", "analysis": root/"analysis", "preview": root/"preview",
            "output": root/"output", "cache": root/"analysis/cache", "timeline": root/"analysis/timeline.json"}
