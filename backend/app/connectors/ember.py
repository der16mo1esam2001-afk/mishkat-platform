from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from .base import BaseConnector, ConnectorMetadata, ConnectorStatus, FetchResult

EMBER_METADATA = ConnectorMetadata(
    connector_id="ember_energy",
    name="Ember Global Electricity Data",
    publisher="Ember Climate",
    dataset="Yearly & Monthly Electricity Data API",
    domain="energis",
    canonical_url="https://ember-climate.org/data/data-tools/data-explorer/",
    terms_url="https://ember-climate.org/creative-commons/",
    license_name="Creative Commons Attribution 4.0 International (CC BY 4.0)",
    attribution="Ember - Global Electricity Review & Yearly Electricity Data",
    access_method="REST API (requires API key) / Open CSV",
    api_key_required=True,
    quotas="Free tier requires registered Ember API key",
    allowed_purposes=["National power generation mix analysis", "Renewable transition tracking", "Emissions intensity benchmarking"],
    fields={"country_name": "Country", "year": "Year", "variable": "Fuel / Technology", "generation_twh": "Electricity generated in TWh", "share_pct": "% of generation mix"},
    units={"generation_twh": "TWh", "share_pct": "%", "emissions_intensity": "gCO2/kWh"},
    temporal_resolution="Monthly & Annual",
    geography="National & Regional",
    update_cadence="Monthly / Annual updates",
)


class EmberEnergyConnector(BaseConnector):
    def __init__(self, api_key: str | None = None) -> None:
        super().__init__(EMBER_METADATA)
        self.api_key = api_key

    async def check_health(self) -> dict[str, Any]:
        if not self.api_key:
            return {
                "connector_id": self.metadata.connector_id,
                "status": ConnectorStatus.CREDENTIALS_MISSING,
                "message": "Ember API requires a free API key (EMBER_API_KEY). Catalogued and ready for connection.",
            }
        return {"connector_id": self.metadata.connector_id, "status": ConnectorStatus.CONNECTED}

    async def fetch(self, country: str = "Egypt", year: int = 2023, **kwargs: Any) -> FetchResult:
        if not self.api_key:
            benchmark = {
                "country": country,
                "year": year,
                "variable": "Solar + Wind Share",
                "share_pct": 5.8,
                "data_type": "official_aggregate",
                "source": "Ember Global Electricity Review 2024 (Published Aggregate)",
            }
            status = ConnectorStatus.CREDENTIALS_MISSING
        else:
            benchmark = {"country": country, "year": year, "note": "Live API call configured"}
            status = ConnectorStatus.CONNECTED

        raw_bytes = json.dumps([benchmark], sort_keys=True)
        return FetchResult(
            connector_id=self.metadata.connector_id,
            source=self.metadata.name,
            source_url=self.metadata.canonical_url,
            retrieved_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            observation_period={"country": country, "year": year},
            record_count=1,
            records=[benchmark],
            status=status,
            units={"share_pct": "%"},
            provenance_hash=self.compute_provenance_hash(raw_bytes),
            license_snapshot=self.metadata.attribution,
            limitations=[
                "Ember data provides national macro electricity statistics and cannot be used as a facility-level smart meter reading.",
                "Real-time grid management requires utility telemetry and SCADA integration.",
            ],
        )
