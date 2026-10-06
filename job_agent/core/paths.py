"""Resolve all project data independently of the caller's working directory."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ProjectPaths:
    root: Path = field(default_factory=lambda: Path(__file__).resolve().parents[2])

    def __post_init__(self):
        object.__setattr__(self, "root", Path(self.root).resolve())

    def resolve(self, path):
        path = Path(path)
        return path if path.is_absolute() else self.root / path

    @property
    def knowledge(self):
        return self.root / "knowledge"

    @property
    def guidelines(self):
        return self.root / "more_info"

    @property
    def results(self):
        return self.root / "result"

    def browser_profile(self, site):
        return self.results / "browser_profiles" / site


def load_environment(paths=None):
    from dotenv import load_dotenv

    load_dotenv((paths or ProjectPaths()).root / ".env")
