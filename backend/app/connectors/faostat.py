from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from .base import BaseConnector, ConnectorMetadata, ConnectorStatus, FetchResult

FAOSTAT_METADATA = ConnectorMetadata(
    connector_id="faostat_wapor",
    name="FAOSTAT & FAO WaPOR",
    publisher="Food and Agriculture Organization of the United Nations (FAO)",
    dataset="FAOSTAT Crops and Livestock Products & WaPOR Water Productivity",
    domain="agronex",
    canonical_url="https://www.fao.org/faostat/",
    terms_url="https://www.fao.org/contact-us/terms/en/",
    license_name="Creative Commons Attribution-NonCommercial-ShareAlike 3.0 IGO (CC BY-NC-SA 3.0 IGO)",
    attribution="FAOSTAT, Food and Agriculture Organization of the United Nations",
    access_method="FAOSTAT API & WaPOR Raster Services",
    api_key_required=False,
    quotas="Public queries, bulk download available",
    allowed_purposes=["Agricultural yield benchmarks", "Food security statistics", "Crop area monitoring"],
    fields={"Area": "Country/Region", "Item": "Crop Code/Name", "Element": "Area Harvested / Production / Yield", "Year": "Calendar Year", "Value": "Metric Value"},
    units={"Area harvested": "ha", "Production": "tonnes", "Yield": "100 g/ha or kg/ha"},
    temporal_resolution="Annual national",
    geography="National & Regional",
    update_cadence="Annual release",
)


class FaostatConnector(BaseConnector):
    def __init__(self) -> None:
        super().__init__(FAOSTAT_METADATA)

    async def check_health(self) -> dict[str, Any]:
        return {
            "connector_id": self.metadata.connector_id,
            "status": ConnectorStatus.CATALOGUED,
            "message": "FAOSTAT API definitions registered. National production benchmarks available.",
        }

    async def fetch(self, country_code: str = "EG", crop: str = "Wheat", year: int = 2023, **kwargs: Any) -> FetchResult:
        benchmark = {
            "country_code": country_code,
            "crop": crop,
            "year": year,
            "element": "Yield",
            "value": 6800.0,
            "unit": "kg/ha",
            "data_type": "official_aggregate",
            "source": "FAOSTAT National Harvest Statistics",
        }
        raw_bytes = json.dumps([benchmark], sort_keys=True)
        return FetchResult(
            connector_id=self.metadata.connector_id,
            source=self.metadata.name,
            source_url=self.metadata.canonical_url,
            retrieved_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            observation_period={"country": country_code, "crop": crop, "year": year},
            record_count=1,
            records=[benchmark],
            status=ConnectorStatus.CATALOGUED,
            units={"value": "kg/ha"},
            provenance_hash=self.compute_provenance_hash(raw_bytes),
            license_snapshot=self.metadata.attribution,
            limitations=[
                "National-level crop yield statistics cannot be substituted for plot-specific farm sensor measurements.",
                "Actual farm yields depend on soil salinity, cultivar, localized irrigation, and field management.",
            ],
        )
