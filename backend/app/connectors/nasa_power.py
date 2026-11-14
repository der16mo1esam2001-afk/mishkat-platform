from __future__ import annotations

import json
from datetime import date, datetime, timezone
from typing import Any, Literal
import httpx

from .base import BaseConnector, ConnectorMetadata, ConnectorStatus, FetchResult

NASA_ALLOWED_PARAMETERS = {
    "AG": {"T2M", "T2M_MAX", "T2M_MIN", "PRECTOTCORR", "RH2M", "WS10M"},
    "RE": {"ALLSKY_SFC_SW_DWN"},
}

NASA_UNITS = {
    "T2M": "degC",
    "T2M_MAX": "degC",
    "T2M_MIN": "degC",
    "PRECTOTCORR": "mm/day",
    "RH2M": "%",
    "WS10M": "m/s",
    "ALLSKY_SFC_SW_DWN": "MJ/m2/day",
}

NASA_METADATA = ConnectorMetadata(
    connector_id="nasa_power",
    name="NASA POWER Daily API",
    publisher="NASA Langley Research Center",
    dataset="Prediction of Worldwide Energy Resources (POWER)",
    domain="agronex_and_energis",
    canonical_url="https://power.larc.nasa.gov/docs/services/api/temporal/daily/",
    terms_url="https://power.larc.nasa.gov/docs/about/acknowledging-power/",
    license_name="Public Domain / Open NASA Data Policy",
    attribution="NASA POWER Project, NASA Langley Research Center",
    access_method="REST JSON API",
    api_key_required=False,
    quotas="Reasonable use; max ~371 days per daily request",
    allowed_purposes=["Agricultural meteorology", "Solar resource assessment", "Climate baseline"],
    fields={"T2M": "Temperature at 2m", "PRECTOTCORR": "Corrected Precipitation", "ALLSKY_SFC_SW_DWN": "All-Sky Solar Insolation"},
    units=NASA_UNITS,
    temporal_resolution="Daily",
    geography="Global 0.5x0.5 degree grid",
    update_cadence="Daily with 2-3 day latency",
)


class NasaPowerConnector(BaseConnector):
    def __init__(self, base_url: str = "https://power.larc.nasa.gov/api/temporal/daily/point") -> None:
        super().__init__(NASA_METADATA)
        self.base_url = base_url

    async def check_health(self) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                params = {
                    "parameters": "T2M",
                    "community": "AG",
                    "longitude": 31.23,
                    "latitude": 30.04,
                    "start": "20240101",
                    "end": "20240101",
                    "format": "JSON",
                }
                res = await client.get(self.base_url, params=params)
                if res.status_code == 200:
                    return {"connector_id": self.metadata.connector_id, "status": ConnectorStatus.CONNECTED, "latency_ms": res.elapsed.total_seconds() * 1000}
                return {"connector_id": self.metadata.connector_id, "status": ConnectorStatus.DEGRADED, "http_code": res.status_code}
        except Exception as exc:
            return {"connector_id": self.metadata.connector_id, "status": ConnectorStatus.DEGRADED, "error": type(exc).__name__}

    async def fetch(
        self,
        latitude: float,
        longitude: float,
        start_date: date,
        end_date: date,
        community: Literal["AG", "RE"] = "AG",
        parameters: list[str] | None = None,
        timeout_seconds: float = 25.0,
    ) -> FetchResult:
        if end_date < start_date:
            raise ValueError("end_date must be on or after start_date")
        if (end_date - start_date).days > 370:
            raise ValueError("A maximum 371-day interval is allowed per request")

        requested = [p.upper() for p in (parameters or ["T2M", "PRECTOTCORR"])]
        allowed = NASA_ALLOWED_PARAMETERS[community]
        invalid = sorted(set(requested) - allowed)
        if invalid:
            raise ValueError(f"Invalid parameters for community {community}: {invalid}. Allowed: {sorted(allowed)}")

        params = {
            "parameters": ",".join(requested),
            "community": community,
            "longitude": longitude,
            "latitude": latitude,
            "start": start_date.strftime("%Y%m%d"),
            "end": end_date.strftime("%Y%m%d"),
            "format": "JSON",
            "time-standard": "UTC",
        }

        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.get(self.base_url, params=params)
            response.raise_for_status()
            raw = response.json()

        raw_bytes = json.dumps(raw, sort_keys=True)
        prov_hash = self.compute_provenance_hash(raw_bytes)

        properties = raw.get("properties", {})
        parameter_data = properties.get("parameter", {})
        parameter_metadata = raw.get("parameters", {})

        if not parameter_data:
            raise ValueError("NASA POWER returned no parameter series")

        rows: list[dict[str, Any]] = []
        for parameter, observations in parameter_data.items():
            meta = parameter_metadata.get(parameter, {}) if isinstance(parameter_metadata, dict) else {}
            source_unit = meta.get("units") or meta.get("unit") or NASA_UNITS.get(parameter, "unknown")
            for timestamp, value in observations.items():
                cleaned_val = None if value in (None, -999, -999.0) else float(value)
                rows.append({
                    "date": timestamp,
                    "parameter": parameter,
                    "value": cleaned_val,
                    "unit": source_unit,
                    "is_missing": cleaned_val is None,
                })

        return FetchResult(
            connector_id=self.metadata.connector_id,
            source=self.metadata.name,
            source_url=self.base_url,
            retrieved_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            observation_period={"start": start_date.isoformat(), "end": end_date.isoformat(), "time_standard": "UTC"},
            record_count=len(rows),
            records=rows,
            status=ConnectorStatus.CONNECTED,
            units={p: NASA_UNITS.get(p, "unknown") for p in requested},
            provenance_hash=prov_hash,
            license_snapshot=self.metadata.attribution,
            limitations=[
                "NASA POWER provides gridded meteorological estimates (0.5x0.5 deg resolution); not an in-situ farm sensor or electricity meter.",
                "Missing values coded as -999 are normalized to null and never converted to zero.",
                "Observations are UTC standardized.",
            ],
        )
