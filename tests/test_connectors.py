from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.connectors import (
    BaseConnector,
    ConnectorMetadata,
    ConnectorStatus,
    FetchResult,
    connector_registry,
)
from app.connectors.nasa_power import NasaPowerConnector
from app.connectors.who_gho import WhoGhoConnector
from app.connectors.water_risk import WaterRiskConnector
from app.connectors.faostat import FaostatConnector
from app.connectors.ember import EmberEnergyConnector
from app.connectors.unesco_uis import UnescoUisConnector


def test_registry_contains_all_six_connectors():
    all_connectors = connector_registry.list_all()
    assert len(all_connectors) == 6
    ids = {c.connector_id for c in all_connectors}
    assert ids == {
        "nasa_power",
        "who_gho",
        "aqueduct_aquastat",
        "faostat_wapor",
        "ember_energy",
        "unesco_uis",
    }


@pytest.mark.anyio
async def test_nasa_power_connector_live_fetch():
    connector = NasaPowerConnector()
    result = await connector.fetch(
        latitude=30.04,
        longitude=31.23,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 2),
        community="AG",
        parameters=["T2M", "PRECTOTCORR"],
    )
    assert result.status == ConnectorStatus.CONNECTED
    assert result.record_count > 0
    assert result.provenance_hash is not None
    assert len(result.provenance_hash) == 64  # SHA-256
    assert "NASA POWER" in result.source
    # Verify no -999 leaked into cleaned values
    for row in result.records:
        assert row["value"] != -999 and row["value"] != -999.0


@pytest.mark.anyio
async def test_nasa_power_invalid_date_or_params():
    connector = NasaPowerConnector()
    with pytest.raises(ValueError, match="end_date must be on or after start_date"):
        await connector.fetch(
            latitude=30.0,
            longitude=31.0,
            start_date=date(2024, 1, 5),
            end_date=date(2024, 1, 1),
        )

    with pytest.raises(ValueError, match="Invalid parameters"):
        await connector.fetch(
            latitude=30.0,
            longitude=31.0,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 2),
            community="AG",
            parameters=["ALLSKY_SFC_SW_DWN"],  # RE parameter, not AG
        )


@pytest.mark.anyio
async def test_who_gho_connector_health_and_fetch():
    connector = WhoGhoConnector()
    health = await connector.check_health()
    assert health["connector_id"] == "who_gho"
    assert health["status"] in (ConnectorStatus.CONNECTED, ConnectorStatus.DEGRADED)

    result = await connector.fetch(indicator_code="WHOSIS_000001", country_code="EGY")
    assert result.connector_id == "who_gho"
    assert result.record_count >= 1
    assert len(result.provenance_hash) == 64
    assert any("not be used to infer individual patient diagnosis" in lim for lim in result.limitations)


@pytest.mark.anyio
async def test_water_risk_and_faostat_and_ember_and_unesco():
    water = WaterRiskConnector()
    w_res = await water.fetch(basin_id="Nile_Lower")
    assert w_res.connector_id == "aqueduct_aquastat"
    assert w_res.records[0]["score"] == 4.2
    assert "strategic" in w_res.limitations[0].lower()

    fao = FaostatConnector()
    f_res = await fao.fetch(country_code="EG", crop="Wheat")
    assert f_res.connector_id == "faostat_wapor"
    assert f_res.records[0]["value"] == 6800.0

    ember = EmberEnergyConnector(api_key=None)
    e_health = await ember.check_health()
    assert e_health["status"] == ConnectorStatus.CREDENTIALS_MISSING

    unesco = UnescoUisConnector()
    u_res = await unesco.fetch(country_code="EG")
    assert u_res.connector_id == "unesco_uis"
    assert u_res.records[0]["indicator"] == "ADULT_LITERACY"
