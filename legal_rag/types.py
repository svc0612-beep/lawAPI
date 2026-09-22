from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from hashlib import sha256
from typing import Protocol


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def digest(text):
    return sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Document:
    id: str
    kind: str  # statute | precedent | administrative_rule | local_ordinance | bibliography
    title: str
    text: str  # Complete article or bounded source section; never model text.
    url: str
    source_id: str
    version: str
    content_hash: str
    retrieved_at: str
    fresh_until: str
    valid_from: str = ""
    valid_to: str = ""
    metadata: dict = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


@dataclass
class Hit:
    document: Document
    score: float
    channels: list[str] = field(default_factory=list)


@dataclass
class Result:
    status: str
    session_id: str
    turn_id: str
    answer: str
    citations: list[dict] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)
    verification: dict = field(default_factory=dict)
    diagnostics: dict = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


class JSONModel(Protocol):
    def generate(self, task: str, payload: dict, schema: dict) -> dict: ...


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...
