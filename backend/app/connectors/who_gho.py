from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
import httpx

from .base import BaseConnector, ConnectorMetadata, ConnectorStatus, FetchResult

WHO_METADATA = ConnectorMetadata(
    connector_id="who_gho",
    name="WHO Global Health Observatory",
    publisher="World Health Organization (WHO)",
    dataset="Global Health Observatory (GHO) OData API",
    domain="vitalis",
    canonical_url="https://www.who.int/data/gho/info/gho-odata-api",
    terms_url="https://www.who.int/about/policies/publishing/data-policy",
    license_name="Creative Commons Attribution-NonCommercial-ShareAlike 3.0 IGO (CC BY-NC-SA 3.0 IGO)",
    attribution="World Health Organization (WHO) Global Health Observatory Data Repository",
    access_method="OData v4 REST API",
    api_key_required=False,
    quotas="Public access; rate limit politely",
    allowed_purposes=["Public health epidemiology", "Comparative health indicators", "Preventive health context"],
    fields={"IndicatorCode": "WHO Indicator Code", "SpatialDim": "Country or Region ISO code", "TimeDim": "Year", "NumericValue": "Reported value"},
    units={"LIFE_EXP": "Years", "U5MR": "Deaths per 1000 live births"},
    temporal_resolution="Annual",
    geography="National and Regional aggregates",
    update_cadence="Annual / Periodic",
)


class WhoGhoConnector(BaseConnector):
    def __init__(self, base_url: str = "https://ghoapi.azureedge.net/api") -> None:
        super().__init__(WHO_METADATA)
        self.base_url = base_url

    async def check_health(self) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.get(f"{self.base_url}/Dimension")
                if res.status_code == 200:
                    return {"connector_id": self.metadata.connector_id, "status": ConnectorStatus.CONNECTED, "latency_ms": res.elapsed.total_seconds() * 1000}
                return {"connector_id": self.metadata.connector_id, "status": ConnectorStatus.DEGRADED, "http_code": res.status_code}
        except Exception as exc:
            return {"connector_id": self.metadata.connector_id, "status": ConnectorStatus.DEGRADED, "error": type(exc).__name__}

    async def fetch(
        self,
        indicator_code: str = "WHOSIS_000001",  # Life expectancy at birth
        country_code: str = "EGY",
        timeout_seconds: float = 20.0,
    ) -> FetchResult:
        url = f"{self.base_url}/{indicator_code}"
        params = {"$filter": f"SpatialDim eq '{country_code}'"}

        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            res = await client.get(url, params=params)
            res.raise_for_status()
            data = res.json()

        raw_bytes = json.dumps(data, sort_keys=True)
        prov_hash = self.compute_provenance_hash(raw_bytes)
        items = data.get("value", [])

        records = []
        for item in items:
            records.append({
                "indicator": indicator_code,
                "country": item.get("SpatialDim"),
                "year": item.get("TimeDim"),
                "value": item.get("NumericValue"),
                "low": item.get("Low"),
                "high": item.get("High"),
                "comments": item.get("Comments"),
            })

        return FetchResult(
            connector_id=self.metadata.connector_id,
            source=self.metadata.name,
            source_url=url,
            retrieved_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            observation_period={"country": country_code, "indicator": indicator_code},
            record_count=len(records),
            records=records,
            status=ConnectorStatus.CONNECTED,
            units={"value": "Reported national indicator unit"},
            provenance_hash=prov_hash,
            license_snapshot=self.metadata.attribution,
            limitations=[
                "National aggregates cannot be used to infer individual patient diagnosis or prognosis.",
                "Indicator definitions vary by series and survey method; refer to GHO indicator metadata.",
                "WHO data is strictly epidemiological and advisory.",
            ],
        )
