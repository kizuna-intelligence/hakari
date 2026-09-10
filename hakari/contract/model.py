from dataclasses import dataclass
from datetime import date, datetime


class ConfigError(ValueError): pass


@dataclass(frozen=True)
class FileChange:
    path: str
    added: int | None
    deleted: int | None


@dataclass(frozen=True)
class Landing:
    sha: str
    author_at: datetime
    subject: str
    body: str
    files: tuple[FileChange, ...]


@dataclass(frozen=True)
class Window:
    start: date
    end: date
    days: int

    def contains(self, d: date) -> bool: return self.start <= d <= self.end


@dataclass(frozen=True)
class MeasureRequest:
    repo_dir: str
    as_of: date | None


@dataclass(frozen=True)
class MetricResult:
    id: str
    value: object
    unit: str
    details: dict
