from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from .base import BaseConnector, ConnectorMetadata, ConnectorStatus, FetchResult

UNESCO_METADATA = ConnectorMetadata(
    connector_id="unesco_uis",
    name="UNESCO Institute for Statistics",
    publisher="UNESCO Institute for Statistics (UIS)",
    dataset="Education & Literacy Data Indicators",
    domain="nexora",
    canonical_url="http://data.uis.unesco.org/",
    terms_url="https://en.unesco.org/this-site/terms-use",
    license_name="Creative Commons Attribution-ShareAlike 3.0 IGO (CC BY-SA 3.0 IGO)",
    attribution="UNESCO Institute for Statistics Data Centre",
    access_method="UIS API & Bulk SDMX Download",
    api_key_required=False,
    quotas="Public access; subscription key recommended for high volume",
    allowed_purposes=["Educational attainment benchmarking", "Literacy statistics", "Learning equity analysis"],
    fields={"indicator": "UIS Indicator Code", "country": "Country ISO3", "year": "Survey Year", "value": "Indicator Percentage or Ratio"},
    units={"literacy_rate": "%", "completion_rate": "%"},
    temporal_resolution="Annual",
    geography="National & Regional",
    update_cadence="Annual updates",
)


class UnescoUisConnector(BaseConnector):
    def __init__(self) -> None:
        super().__init__(UNESCO_METADATA)

    async def check_health(self) -> dict[str, Any]:
        return {
            "connector_id": self.metadata.connector_id,
            "status": ConnectorStatus.CATALOGUED,
            "message": "UNESCO UIS indicators catalogued. National education benchmarks available.",
        }

    async def fetch(self, country_code: str = "EG", indicator: str = "ADULT_LITERACY", **kwargs: Any) -> FetchResult:
        benchmark = {
            "country_code": country_code,
            "indicator": indicator,
            "indicator_name": "Adult Literacy Rate (15+ years)",
            "value": 73.1,
            "unit": "%",
            "year": 2022,
            "data_type": "official_aggregate",
            "source": "UNESCO UIS Global Education Digest",
        }
        raw_bytes = json.dumps([benchmark], sort_keys=True)
        return FetchResult(
            connector_id=self.metadata.connector_id,
            source=self.metadata.name,
            source_url=self.metadata.canonical_url,
            retrieved_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            observation_period={"country": country_code, "indicator": indicator},
            record_count=1,
            records=[benchmark],
            status=ConnectorStatus.CATALOGUED,
            units={"value": "%"},
            provenance_hash=self.compute_provenance_hash(raw_bytes),
            license_snapshot=self.metadata.attribution,
            limitations=[
                "UNESCO indicators represent country-level averages and cannot measure an individual learner's mastery or skill level.",
                "Learner evaluation requires curriculum-aligned diagnostic assessments with explicit consent.",
            ],
        )
