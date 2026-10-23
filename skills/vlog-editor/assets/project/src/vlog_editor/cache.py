"""Content-addressed cache. Each artifact is checksum-verified before reuse."""
from pathlib import Path
import tempfile

from .common import digest, fingerprint, read_json, write_json

# Bump when FFmpeg construction changes; kept in keys to invalidate old outputs.
ENGINE_VERSION = "natural-vlog-5-title-ending-cards"


class Cache:
    def __init__(self, directory, environment):
        self.root = Path(directory)
        self.root.mkdir(parents=True, exist_ok=True)
        self.environment = environment
        self.events = []

    def get(self, kind, payload, suffix, build):
        key = digest({"engine": ENGINE_VERSION, "environment": self.environment, "payload": payload})
        directory = self.root / kind
        directory.mkdir(parents=True, exist_ok=True)
        artifact = directory / (key + suffix)
        receipt = directory / (key + ".json")
        valid = False
        if artifact.is_file() and receipt.is_file():
            try:
                valid = read_json(receipt).get("fingerprint") == fingerprint(artifact)
            except (OSError, ValueError):
                pass
        if not valid:
            with tempfile.TemporaryDirectory(prefix="build-", dir=directory) as temp:
                staged = Path(temp) / ("artifact" + suffix)
                build(staged)
                if not staged.is_file() or staged.stat().st_size == 0:
                    raise ValueError(f"Cache builder produced no {kind} artifact")
                staged.replace(artifact)
            write_json(receipt, {"fingerprint": fingerprint(artifact), "key": key})
        self.events.append({"kind": kind, "key": key, "status": "reused" if valid else "rendered"})
        return artifact
