from __future__ import annotations

from typing import Any
from .base import BaseConnector, ConnectorMetadata, ConnectorStatus, FetchResult
from .nasa_power import NasaPowerConnector
from .who_gho import WhoGhoConnector
from .water_risk import WaterRiskConnector
from .faostat import FaostatConnector
from .ember import EmberEnergyConnector
from .unesco_uis import UnescoUisConnector


class ConnectorRegistry:
    def __init__(self) -> None:
        self._connectors: dict[str, BaseConnector] = {
            "nasa_power": NasaPowerConnector(),
            "who_gho": WhoGhoConnector(),
            "aqueduct_aquastat": WaterRiskConnector(),
            "faostat_wapor": FaostatConnector(),
            "ember_energy": EmberEnergyConnector(),
            "unesco_uis": UnescoUisConnector(),
        }

    def get(self, connector_id: str) -> BaseConnector | None:
        return self._connectors.get(connector_id)

    def list_all(self) -> list[ConnectorMetadata]:
        return [c.metadata for c in self._connectors.values()]

    async def get_all_statuses(self) -> list[dict[str, Any]]:
        results = []
        for c in self._connectors.values():
            health = await c.check_health()
            results.append({
                "connector_id": c.metadata.connector_id,
                "name": c.metadata.name,
                "publisher": c.metadata.publisher,
                "domain": c.metadata.domain,
                "dataset": c.metadata.dataset,
                "canonical_url": c.metadata.canonical_url,
                "license_name": c.metadata.license_name,
                "attribution": c.metadata.attribution,
                "health": health,
            })
        return results


connector_registry = ConnectorRegistry()
