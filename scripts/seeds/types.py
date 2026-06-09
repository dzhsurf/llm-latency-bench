from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Seed:
    id: str
    title: str
    body: str
