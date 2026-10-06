"""Write artifacts beneath an explicitly owned output directory."""

import json
from pathlib import Path


class ArtifactStore:
    def __init__(self, directory):
        self.directory = Path(directory).resolve()

    def _target(self, name):
        target = (self.directory / name).resolve()
        if not target.is_relative_to(self.directory) or target == self.directory:
            raise ValueError("Artifact name must stay within its output directory")
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    def write_text(self, name, text):
        target = self._target(name)
        target.write_text(text, encoding="utf-8")
        return target

    def write_json(self, name, payload):
        return self.write_text(name, json.dumps(payload, ensure_ascii=False, indent=2))
