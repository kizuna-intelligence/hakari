from dataclasses import dataclass
from typing import Mapping, Protocol, Sequence

from hakari.contract.model import Landing


class History(Protocol):
    def landings(self) -> Sequence[Landing]: ...


class Tree(Protocol):
    def files(self) -> Mapping[str, int]: ...


@dataclass(frozen=True)
class InMemoryHistory:
    _landings: tuple[Landing, ...]

    def landings(self) -> Sequence[Landing]: return self._landings


@dataclass(frozen=True)
class InMemoryTree:
    _files: Mapping[str, int]

    def files(self) -> Mapping[str, int]: return self._files
