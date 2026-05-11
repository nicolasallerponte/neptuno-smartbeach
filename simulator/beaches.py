"""
Beach catalogue for the province of A Coruna, Galicia.

Contains static data for the 18 monitored beaches. Coordinates sourced from
official cartographic references (AEMET, IGN, Masmar, Turismo de Galicia).
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
    # --- A Coruña city ---
    BeachInfo(
        id="Riazor",
        name="Playa de Riazor",
        lat=43.3686,
        lon=-8.4114,
        length=1200,
        city="A Coruña",
        width=60,
        beach_type=["urban", "calmWaters"],
        facilities=["lifeGuard", "showers", "toilets", "cleaningServices"],
        access_type=["publicTransport", "privateVehicle", "onFoot"],
        description="Iconic urban beach in A Coruña city center with full services",
    ),
    BeachInfo(
        id="Orzan",
        name="Playa de Orzán",
        lat=43.3709,
        lon=-8.4054,
        length=900,
        city="A Coruña",
        width=55,
        beach_type=["urban", "moderateWaves"],
        facilities=["lifeGuard", "showers", "toilets", "cleaningServices"],
        access_type=["publicTransport", "privateVehicle", "onFoot"],
        description="Popular surf beach adjacent to Riazor in the heart of A Coruña",
    ),
    # --- Oleiros (east shore of Ría de A Coruña) ---
    BeachInfo(
        id="SantaCristina",
        name="Praia de Santa Cristina",
        lat=43.3398,
        lon=-8.3801,
        length=700,
        city="Oleiros",
        width=40,
        beach_type=["semiUrban", "calmWaters"],
        facilities=["lifeGuard", "showers", "toilets"],
        access_type=["publicTransport", "privateVehicle", "onFoot"],
        description="Family beach in Oleiros on the eastern shore of the Ría de A Coruña",
    ),
    BeachInfo(
        id="Bastiagueiro",
        name="Praia de Bastiagueiro",
        lat=43.3407,
        lon=-8.3623,
        length=800,
        city="Oleiros",
        width=45,
        beach_type=["semiUrban", "moderateWaves"],
        facilities=["lifeGuard", "showers", "toilets"],
        access_type=["publicTransport", "privateVehicle", "onFoot"],
        description="Urban beach in Oleiros on the Ría de A Coruña with good amenities",
    ),
    # --- Ría de Betanzos / Miño ---
    BeachInfo(
        id="Mino",
        name="Praia de Miño",
        lat=43.3573,
        lon=-8.2121,
        length=1500,
        city="Miño",
        width=60,
        beach_type=["semiUrban", "calmWaters"],
        facilities=["lifeGuard", "showers", "toilets", "cleaningServices"],
        access_type=["publicTransport", "privateVehicle", "onFoot"],
        description="Long sandy beach at the Miño estuary in the Golfo Ártabro, calm and family-friendly",
    ),
    BeachInfo(
        id="Cabanas",
        name="Praia de Cabanas",
        lat=43.4180,
        lon=-8.1722,
        length=1100,
        city="Cabanas",
        width=50,
        beach_type=["semiUrban", "calmWaters"],
        facilities=["lifeGuard", "showers", "toilets"],
        access_type=["publicTransport", "privateVehicle", "onFoot"],
        description="Family-friendly beach (A Magdalena) in Cabanas on the Ría de Ares",
    ),
    # --- Ferrol area ---
    BeachInfo(
        id="Doninos",
        name="Praia de Doniños",
        lat=43.4969,
        lon=-8.3187,
        length=1800,
        city="Ferrol",
        width=70,
        beach_type=["natural", "strongWaves"],
        facilities=["lifeGuard", "showers"],
        access_type=["privateVehicle", "onFoot"],
        description="Wild Atlantic dune beach near Ferrol, known for surfing",
    ),
    # --- Northern coast (Valdoviño) ---
    BeachInfo(
        id="Valdovino",
        name="Praia de Valdoviño",
        lat=43.6128,
        lon=-8.1694,
        length=2100,
        city="Valdoviño",
        width=80,
        beach_type=["natural", "moderateWaves"],
        facilities=["lifeGuard", "showers", "toilets"],
        access_type=["privateVehicle", "onFoot"],
        description="Expansive lagoon beach (A Frouxeira) in northern A Coruña with protected dunes",
    ),
    BeachInfo(
        id="Pantin",
        name="Praia de Pantín",
        lat=43.6394,
        lon=-8.1098,
        length=1400,
        city="Valdoviño",
        width=65,
        beach_type=["natural", "strongWaves"],
        facilities=["lifeGuard", "showers"],
        access_type=["privateVehicle", "onFoot"],
        description="Championship surf beach in Valdoviño, host of international surf competitions",
    ),
    # --- Arteixo ---
    BeachInfo(
        id="Sabon",
        name="Praia de Sabón",
        lat=43.3297,
        lon=-8.5089,
        length=1000,
        city="Arteixo",
        width=50,
        beach_type=["semiUrban", "moderateWaves"],
        facilities=["lifeGuard", "showers", "toilets"],
        access_type=["privateVehicle", "onFoot"],
        description="Sandy beach near Arteixo with Atlantic views",
    ),
    # --- Costa da Morte north ---
    BeachInfo(
        id="Caion",
        name="Praia de Caión",
        lat=43.3156,
        lon=-8.6103,
        length=600,
        city="A Laracha",
        width=40,
        beach_type=["semiUrban", "moderateWaves"],
        facilities=["lifeGuard", "showers", "toilets"],
        access_type=["privateVehicle", "onFoot"],
        description="Charming village beach (Salseiras) in A Laracha on the Costa da Morte",
    ),
    BeachInfo(
        id="Baldaio",
        name="Praia de Baldaio",
        lat=43.2976,
        lon=-8.6801,
        length=3200,
        city="Carballo",
        width=90,
        beach_type=["natural", "strongWaves"],
        facilities=["showers"],
        access_type=["privateVehicle", "onFoot"],
        description="Vast wild beach with lagoon system and diverse birdlife",
    ),
    BeachInfo(
        id="Razo",
        name="Praia de Razo",
        lat=43.2897,
        lon=-8.7125,
        length=2500,
        city="Carballo",
        width=80,
        beach_type=["natural", "strongWaves"],
        facilities=["showers"],
        access_type=["privateVehicle", "onFoot"],
        description="Long natural beach near Carballo with strong Atlantic swells",
    ),
    BeachInfo(
        id="Malpica",
        name="Playa de Malpica",
        lat=43.3244,
        lon=-8.8150,
        length=800,
        city="Malpica de Bergantiños",
        width=45,
        beach_type=["semiUrban", "calmWaters"],
        facilities=["lifeGuard", "showers", "toilets"],
        access_type=["privateVehicle", "onFoot"],
        description="Sheltered fishing village beach (Maior) on the Costa da Morte",
    ),
    # --- Costa da Morte south ---
    BeachInfo(
        id="Laxe",
        name="Praia de Laxe",
        lat=43.2165,
        lon=-8.9983,
        length=2000,
        city="Laxe",
        width=70,
        beach_type=["natural", "moderateWaves"],
        facilities=["lifeGuard", "showers", "toilets"],
        access_type=["privateVehicle", "onFoot"],
        description="Scenic beach on the Costa da Morte in the town of Laxe",
    ),
    BeachInfo(
        id="Carnota",
        name="Praia de Carnota",
        lat=42.8363,
        lon=-9.1045,
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
        name="Praia de Lariño",
        lat=42.7656,
        lon=-9.1169,
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
        lat=42.6905,
        lon=-9.0282,
        length=400,
        city="Porto do Son",
        width=30,
        beach_type=["natural", "calmWaters"],
        facilities=[],
        access_type=["onFoot"],
        description="Remote beach (Area Longa) at the foot of the Celtic hillfort Castro de Baroña",
    ),
]

BEACH_MAP: dict[str, BeachInfo] = {b.id: b for b in BEACHES}


def get_beach(beach_id: str) -> BeachInfo | None:
    """Retrieve a beach by its short ID."""
    return BEACH_MAP.get(beach_id)


# Nearest MeteoGalicia observation station for each beach
METEOGALICIA_STATION_MAP: dict[str, int] = {
    "Riazor": 14000,
    "Orzan": 14000,
    "SantaCristina": 14000,
    "Bastiagueiro": 14000,
    "Mino": 10157,
    "Cabanas": 10157,
    "Doninos": 10157,
    "Valdovino": 10157,
    "Pantin": 10157,
    "Sabon": 10148,
    "Caion": 10148,
    "Baldaio": 10148,
    "Razo": 10148,
    "Malpica": 10148,
    "Laxe": 10124,
    "Carnota": 10124,
    "Larino": 10124,
    "Barona": 10124,
}

# MeteoGalicia maritime forecast zone for each beach
# Zone 2: Ferrol-Bares  |  Zone 3: Ártabro  |  Zone 4: Costa da Morte
MARITIME_ZONE_MAP: dict[str, int] = {
    "Riazor": 3,
    "Orzan": 3,
    "SantaCristina": 3,
    "Bastiagueiro": 3,
    "Mino": 3,       # Golfo Ártabro (was incorrectly Zone 2)
    "Cabanas": 3,    # Ría de Ares/Betanzos, Ártabro (was incorrectly Zone 2)
    "Doninos": 2,
    "Valdovino": 2,
    "Pantin": 2,
    "Sabon": 3,
    "Caion": 3,
    "Baldaio": 3,
    "Razo": 3,
    "Malpica": 3,
    "Laxe": 4,
    "Carnota": 4,
    "Larino": 4,
    "Barona": 4,
}
