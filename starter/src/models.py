"""Shared data contracts; keep traceability from chunk back to source."""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DocumentPage:
    document_id: str
    source: str
    page: int
    text: str
    page_id: str = ""
    page_number: Any = None
    char_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Chunk:
    chunk_id: str
    document_id: str
    source: str = ""
    page: int = 0
    text: str = ""
    page_id: str = ""
    index: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
