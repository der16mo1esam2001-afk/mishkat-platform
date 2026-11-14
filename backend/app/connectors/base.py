from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Sequence


class ConnectorStatus(str, Enum):
    CATALOGUED = "catalogued"
    CREDENTIALS_MISSING = "credentials_missing"
    LICENSE_REVIEW = "license_review"
    PARTNER_REQUIRED = "partner_required"
    CONNECTED = "connected"
    DEGRADED = "degraded"
    DISABLED = "disabled"


@dataclass(frozen=True)
class ConnectorMetadata:
    connector_id: str
    name: str
    publisher: str
    dataset: str
    domain: str
    canonical_url: str
    terms_url: str
    license_name: str
    attribution: str
    access_method: str
    api_key_required: bool
    quotas: str
    allowed_purposes: list[str]
    fields: dict[str, str]
    units: dict[str, str]
    temporal_resolution: str
    geography: str
    update_cadence: str


@dataclass
class FetchResult:
    connector_id: str
    source: str
    source_url: str
    retrieved_at: str
    observation_period: dict[str, Any]
    record_count: int
    records: list[dict[str, Any]]
    status: ConnectorStatus
    units: dict[str, str]
    provenance_hash: str
    license_snapshot: str
    limitations: list[str] = field(default_factory=list)


class BaseConnector(ABC):
    def __init__(self, metadata: ConnectorMetadata) -> None:
        self.metadata = metadata

    @abstractmethod
    async def check_health(self) -> dict[str, Any]:
        """Check endpoint reachability and return connector status dictionary."""
        raise NotImplementedError

    @abstractmethod
    async def fetch(self, **kwargs: Any) -> FetchResult:
        """Fetch real data, validate types/schemas, and attach full provenance."""
        raise NotImplementedError

    def compute_provenance_hash(self, payload: bytes | str) -> str:
        import hashlib
        data = payload.encode("utf-8") if isinstance(payload, str) else payload
        return hashlib.sha256(data).hexdigest()
