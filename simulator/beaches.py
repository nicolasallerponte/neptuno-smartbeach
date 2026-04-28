"""
Beach catalogue for the province of A Coruna, Galicia.

Contains static data for the 12 monitored beaches. Coordinates and metadata
serve as hardcoded fallback; the init pipeline will attempt to enrich them
from the Xunta de Galicia Open Data catalogue.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class BeachInfo:
    """Immutable record for a single beach."""

    id: str
    name: str
    lat: float
    lon: float
    length: int
    city: str
    width: int = 50
    beach_type: list[str] = field(default_factory=lambda: ["natural"])
    facilities: list[str] = field(default_factory=list)
    access_type: list[str] = field(default_factory=lambda: ["onFoot"])
    description: str = ""

    @property
    def urn(self) -> str:
        return f"urn:ngsi-ld:Beach:{self.id}"

    @property
    def poi_urn(self) -> str:
        return f"urn:ngsi-ld:PointOfInterest:{self.id}"

    @property
    def buoy_urn(self) -> str:
        return f"urn:ngsi-ld:Device:boya-{self.id}"

    @property
    def meteo_urn(self) -> str:
        return f"urn:ngsi-ld:Device:meteo-{self.id}"

    @property
    def water_sensor_urn(self) -> str:
        return f"urn:ngsi-ld:Device:sensor-agua-{self.id}"

    @property
    def coordinates(self) -> list[float]:
        """GeoJSON coordinate pair [longitude, latitude]."""
        return [self.lon, self.lat]


BEACHES: list[BeachInfo] = [
    BeachInfo(
        id="Riazor",
        name="Playa de Riazor",
        lat=43.3713,
        lon=-8.4197,
        length=1200,
        city="A Coruna",
        width=60,
        beach_type=["urban", "calmWaters"],
        facilities=["lifeGuard", "showers", "toilets", "cleaningServices"],
        access_type=["publicTransport", "privateVehicle", "onFoot"],
        description="Iconic urban beach in A Coruna city center with full services",
    ),
    BeachInfo(
        id="Orzan",
        name="Playa de Orzan",
        lat=43.3745,
        lon=-8.4230,
        length=900,
        city="A Coruna",
        width=55,
        beach_type=["urban", "moderateWaves"],
        facilities=["lifeGuard", "showers", "toilets", "cleaningServices"],
        access_type=["publicTransport", "privateVehicle", "onFoot"],
        description="Popular surf beach adjacent to Riazor in the heart of A Coruna",
    ),
    BeachInfo(
        id="Doninos",
        name="Praia de Doninos",
        lat=43.4820,
        lon=-8.2380,
        length=1800,
        city="Ferrol",
        width=70,
        beach_type=["natural", "strongWaves"],
        facilities=["lifeGuard", "showers"],
        access_type=["privateVehicle", "onFoot"],
        description="Wild Atlantic dune beach near Ferrol, known for surfing",
    ),
    BeachInfo(
        id="Valdovino",
        name="Praia de Valdovino",
        lat=43.6080,
        lon=-8.1310,
        length=2100,
        city="Valdovino",
        width=80,
        beach_type=["natural", "moderateWaves"],
        facilities=["lifeGuard", "showers", "toilets"],
        access_type=["privateVehicle", "onFoot"],
        description="Expansive sandy beach in northern coast with protected dunes",
    ),
    BeachInfo(
        id="Pantin",
        name="Praia de Pantin",
        lat=43.6960,
        lon=-7.9550,
        length=1400,
        city="Cedeira",
        width=65,
        beach_type=["natural", "strongWaves"],
        facilities=["lifeGuard", "showers"],
        access_type=["privateVehicle", "onFoot"],
        description="Championship surf beach hosting international competitions",
    ),
    BeachInfo(
        id="Caion",
        name="Praia de Caion",
        lat=43.3580,
        lon=-8.6110,
        length=600,
        city="A Laracha",
        width=40,
        beach_type=["semiUrban", "moderateWaves"],
        facilities=["lifeGuard", "showers", "toilets"],
        access_type=["privateVehicle", "onFoot"],
        description="Charming village beach on the Costa da Morte",
    ),
    BeachInfo(
        id="Baldaio",
        name="Praia de Baldaio",
        lat=43.3370,
        lon=-8.6840,
        length=3200,
        city="Carballo",
        width=90,
        beach_type=["natural", "strongWaves"],
        facilities=["showers"],
        access_type=["privateVehicle", "onFoot"],
        description="Vast wild beach with lagoon system and diverse birdlife",
    ),
    BeachInfo(
        id="Malpica",
        name="Playa de Malpica",
        lat=43.3197,
        lon=-8.8120,
        length=800,
        city="Malpica",
        width=45,
        beach_type=["semiUrban", "calmWaters"],
        facilities=["lifeGuard", "showers", "toilets"],
        access_type=["privateVehicle", "onFoot"],
        description="Sheltered fishing village beach on the Costa da Morte",
    ),
    BeachInfo(
        id="Cabanas",
        name="Praia de Cabanas",
        lat=43.5060,
        lon=-8.0300,
        length=1100,
        city="Cabanas",
        width=50,
        beach_type=["semiUrban", "calmWaters"],
        facilities=["lifeGuard", "showers", "toilets"],
        access_type=["publicTransport", "privateVehicle", "onFoot"],
        description="Family-friendly beach in the Ferrol estuary",
    ),
    BeachInfo(
        id="Carnota",
        name="Praia de Carnota",
        lat=42.8640,
        lon=-9.0820,
        length=7400,
        city="Carnota",
        width=100,
        beach_type=["natural", "moderateWaves"],
        facilities=["showers"],
        access_type=["privateVehicle", "onFoot"],
        description="Longest beach in Galicia at 7.4 km, pristine natural setting",
    ),
    BeachInfo(
        id="Larino",
        name="Praia de Larino",
        lat=42.8920,
        lon=-9.0420,
        length=900,
        city="Carnota",
        width=45,
        beach_type=["natural", "moderateWaves"],
        facilities=["showers"],
        access_type=["privateVehicle", "onFoot"],
        description="Scenic beach near Carnota with crystal-clear waters",
    ),
    BeachInfo(
        id="Barona",
        name="Praia de Barona",
        lat=42.7520,
        lon=-8.9760,
        length=400,
        city="Porto do Son",
        width=30,
        beach_type=["natural", "calmWaters"],
        facilities=[],
        access_type=["onFoot"],
        description="Remote beach at the foot of the Celtic hillfort Castro de Barona",
    ),
]

BEACH_MAP: dict[str, BeachInfo] = {b.id: b for b in BEACHES}


def get_beach(beach_id: str) -> BeachInfo | None:
    """Retrieve a beach by its short ID."""
    return BEACH_MAP.get(beach_id)


# Nearest MeteoGalicia station IDs for each beach (approximate)
METEOGALICIA_STATION_MAP: dict[str, int] = {
    "Riazor": 14000,
    "Orzan": 14000,
    "Doninos": 10157,
    "Valdovino": 10157,
    "Pantin": 10157,
    "Caion": 10148,
    "Baldaio": 10148,
    "Malpica": 10148,
    "Cabanas": 10157,
    "Carnota": 10124,
    "Larino": 10124,
    "Barona": 10124,
}
