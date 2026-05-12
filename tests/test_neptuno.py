"""
NEPTUNO SmartBeach — test suite
Covers: orion helpers, simulator data generators, BeachInfo, FastAPI endpoints.
All external HTTP calls (Orion, Ollama, MeteoGalicia) are mocked.
"""

from __future__ import annotations

import sys
import os

# Make sure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

# ---------------------------------------------------------------------------
# orion.py — pure helper functions
# ---------------------------------------------------------------------------

from backend.services.orion import _extract_values, _local_name, _val


class TestLocalName:
    def test_short_key_unchanged(self):
        assert _local_name("waveHeight") == "waveHeight"

    def test_uri_with_slash(self):
        assert _local_name("https://smartdatamodels.org/dataModel.Weather/severity") == "severity"

    def test_uri_with_hash(self):
        assert _local_name("https://example.org/ontology#temperature") == "temperature"

    def test_at_context_key(self):
        assert _local_name("@context") == "@context"

    def test_id_key(self):
        assert _local_name("id") == "id"

    def test_uri_nested_path(self):
        assert _local_name("https://uri.etsi.org/ngsi-ld/location") == "location"


class TestExtractValues:
    def test_property_wrapper(self):
        entity = {"waveHeight": {"type": "Property", "value": 1.2}}
        result = _extract_values(entity)
        assert result["waveHeight"] == 1.2

    def test_relationship_wrapper(self):
        entity = {"refPointOfInterest": {"type": "Relationship", "object": "urn:ngsi-ld:Beach:Riazor"}}
        result = _extract_values(entity)
        assert result["refPointOfInterest"] == "urn:ngsi-ld:Beach:Riazor"

    def test_geo_property_wrapper(self):
        geo = {"type": "Point", "coordinates": [-8.42, 43.37]}
        entity = {"location": {"type": "GeoProperty", "value": geo}}
        result = _extract_values(entity)
        assert result["location"] == geo

    def test_uri_key_normalised(self):
        entity = {
            "https://smartdatamodels.org/dataModel.Weather/waveHeight": {
                "type": "Property",
                "value": 0.8,
            }
        }
        result = _extract_values(entity)
        assert result["waveHeight"] == 0.8

    def test_id_passthrough(self):
        entity = {"id": "urn:ngsi-ld:Beach:Riazor", "type": "Beach"}
        result = _extract_values(entity)
        assert result["id"] == "urn:ngsi-ld:Beach:Riazor"

    def test_at_context_passthrough(self):
        entity = {"@context": "http://context/user-context.jsonld"}
        result = _extract_values(entity)
        assert result["@context"] == "http://context/user-context.jsonld"

    def test_plain_value_passthrough(self):
        entity = {"name": "Riazor"}
        result = _extract_values(entity)
        assert result["name"] == "Riazor"

    def test_multiple_properties(self):
        entity = {
            "waveHeight": {"type": "Property", "value": 1.5},
            "severity": {"type": "Property", "value": "medium"},
            "refPointOfInterest": {"type": "Relationship", "object": "urn:ngsi-ld:Beach:Pantin"},
        }
        result = _extract_values(entity)
        assert result == {
            "waveHeight": 1.5,
            "severity": "medium",
            "refPointOfInterest": "urn:ngsi-ld:Beach:Pantin",
        }


class TestVal:
    def test_plain_value(self):
        assert _val({"temp": 18.5}, "temp") == 18.5

    def test_wrapped_value(self):
        assert _val({"temp": {"value": 18.5}}, "temp") == 18.5

    def test_missing_key_returns_default(self):
        assert _val({}, "temp", 99) == 99

    def test_none_value_returns_default(self):
        assert _val({"temp": None}, "temp", 0) == 0


# ---------------------------------------------------------------------------
# simulator/beaches.py — BeachInfo and BEACHES catalogue
# ---------------------------------------------------------------------------

from simulator.beaches import BeachInfo, BEACHES


class TestBeachInfo:
    def setup_method(self):
        self.beach = BeachInfo(
            id="Riazor",
            name="Playa de Riazor",
            lat=43.3713,
            lon=-8.4197,
            length=1200,
            city="A Coruña",
        )

    def test_urn(self):
        assert self.beach.urn == "urn:ngsi-ld:Beach:Riazor"

    def test_buoy_urn(self):
        assert self.beach.buoy_urn == "urn:ngsi-ld:Device:boya-Riazor"

    def test_meteo_urn(self):
        assert self.beach.meteo_urn == "urn:ngsi-ld:Device:meteo-Riazor"

    def test_water_sensor_urn(self):
        assert self.beach.water_sensor_urn == "urn:ngsi-ld:Device:sensor-agua-Riazor"

    def test_coordinates(self):
        assert self.beach.coordinates == [-8.4197, 43.3713]


class TestBeachesCatalogue:
    def test_eighteen_beaches(self):
        assert len(BEACHES) == 18

    def test_all_have_valid_lat(self):
        for b in BEACHES:
            assert 42.0 < b.lat < 44.0, f"{b.id} lat out of range: {b.lat}"

    def test_all_have_valid_lon(self):
        for b in BEACHES:
            assert -10.0 < b.lon < -7.0, f"{b.id} lon out of range: {b.lon}"

    def test_all_ids_unique(self):
        ids = [b.id for b in BEACHES]
        assert len(ids) == len(set(ids))

    def test_all_have_name(self):
        for b in BEACHES:
            assert b.name, f"{b.id} has empty name"

    def test_riazor_exists(self):
        ids = [b.id for b in BEACHES]
        assert "Riazor" in ids


# ---------------------------------------------------------------------------
# simulator/meteo_fetcher.py — simulated data generators
# ---------------------------------------------------------------------------

from simulator.meteo_fetcher import (
    simulated_observation,
    simulated_sea_conditions,
    simulated_water_quality,
    simulated_forecast,
)


class TestSimulatedObservation:
    def setup_method(self):
        self.obs = simulated_observation(43.37)

    def test_required_keys(self):
        for key in ("temperature", "windSpeed", "windDirection", "relativeHumidity", "precipitation"):
            assert key in self.obs, f"Missing key: {key}"

    def test_temperature_range(self):
        assert 0 < self.obs["temperature"] < 40

    def test_wind_speed_positive(self):
        assert self.obs["windSpeed"] >= 0

    def test_humidity_in_range(self):
        assert 0.0 <= self.obs["relativeHumidity"] <= 1.0

    def test_precipitation_non_negative(self):
        assert self.obs["precipitation"] >= 0


class TestSimulatedSeaConditions:
    def setup_method(self):
        self.sea = simulated_sea_conditions(43.37)

    def test_required_keys(self):
        for key in ("waveHeight", "wavePeriod", "waveLevel", "seaSurfaceTemperature", "pH", "salinity"):
            assert key in self.sea, f"Missing key: {key}"

    def test_wave_height_positive(self):
        assert self.sea["waveHeight"] > 0

    def test_wave_level_range(self):
        assert 1 <= self.sea["waveLevel"] <= 5

    def test_ph_range(self):
        assert 7.0 < self.sea["pH"] < 9.0

    def test_sst_range(self):
        assert 5 < self.sea["seaSurfaceTemperature"] < 30


class TestSimulatedWaterQuality:
    def setup_method(self):
        self.wq = simulated_water_quality()

    def test_required_keys(self):
        for key in ("temperature", "pH", "escherichiaColi", "intestinalEnterococci", "dissolvedOxygen"):
            assert key in self.wq, f"Missing key: {key}"

    def test_ecoli_non_negative(self):
        assert self.wq["escherichiaColi"] >= 0

    def test_dissolved_oxygen_range(self):
        assert 0 < self.wq["dissolvedOxygen"] < 20


class TestSimulatedForecast:
    def setup_method(self):
        self.fc = simulated_forecast()

    def test_required_keys(self):
        for key in ("temperature_min", "temperature_max", "windSpeed", "precipitationProbability", "uVIndexMax"):
            assert key in self.fc, f"Missing key: {key}"

    def test_temp_min_below_max(self):
        assert self.fc["temperature_min"] <= self.fc["temperature_max"]

    def test_precipitation_probability_range(self):
        assert 0.0 <= self.fc["precipitationProbability"] <= 1.0

    def test_uv_index_positive(self):
        assert self.fc["uVIndexMax"] >= 0


# ---------------------------------------------------------------------------
# FastAPI backend — endpoints with mocked external services
# ---------------------------------------------------------------------------

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


class TestHealthEndpoint:
    def test_health_ollama_connected(self):
        with patch("backend.services.ollama.check_health", new_callable=AsyncMock, return_value=True):
            resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["ollama"] == "connected"

    def test_health_ollama_disconnected(self):
        with patch("backend.services.ollama.check_health", new_callable=AsyncMock, return_value=False):
            resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["ollama"] == "disconnected"


class TestAlertsEndpoint:
    def test_returns_list(self):
        mock_alerts = [
            {"id": "urn:ngsi-ld:WeatherAlert:Riazor-waves", "severity": "medium", "name": "Oleaje elevado"}
        ]
        with patch("backend.services.orion.get_alerts", new_callable=AsyncMock, return_value=mock_alerts):
            resp = client.get("/api/alerts")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_empty_alerts(self):
        # Mock at the router's import path, not the service module
        with patch("backend.routers.alerts.get_alerts", new_callable=AsyncMock, return_value=[]):
            resp = client.get("/api/alerts")
        assert resp.status_code == 200
        assert resp.json() == []


class TestBeachesEndpoint:
    def test_returns_list(self):
        mock_beaches = [
            {"id": "urn:ngsi-ld:Beach:Riazor", "name": "Playa de Riazor"}
        ]
        with patch("backend.routers.beaches.get_all_beaches", new_callable=AsyncMock, return_value=mock_beaches):
            resp = client.get("/api/beaches")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        assert len(resp.json()) == 1


class TestChatEndpoint:
    def test_chat_returns_response(self):
        with patch("backend.services.ollama.chat", new_callable=AsyncMock, return_value="El oleaje en Riazor es moderado."):
            with patch("backend.services.orion.get_all_beaches_summary", new_callable=AsyncMock, return_value="Riazor: waves=1.2m"):
                resp = client.post("/api/chat", json={"message": "Como está Riazor?"})
        assert resp.status_code == 200
        assert "response" in resp.json()

    def test_chat_missing_message(self):
        resp = client.post("/api/chat", json={})
        assert resp.status_code == 422
