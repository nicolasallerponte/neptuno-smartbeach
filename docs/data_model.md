# Data Model - NEPTUNO Smart Coastal Intelligence Platform

## Overview

NEPTUNO uses 10 NGSI-LD entity types from official FIWARE Smart Data Models. All entities follow the NGSI-LD specification with `Property`, `GeoProperty`, and `Relationship` attributes. Entities are interconnected through `ref` attributes forming a coherent knowledge graph.

**NGSI-LD Tenant:** `smartbeach`
**Context URL:** `http://context/user-context.jsonld`

## Entity Relationship Diagram

```
+-------------------+          +-------------------+
|  PointOfInterest  |<---------|      Beach        |
|  (static)         |  refPOI  |  (static)         |
+-------------------+          +--------+----------+
                                        |
                    +-------------------+-------------------+
                    |                   |                   |
                    v                   v                   v
          +---------+------+  +---------+------+  +---------+--------+
          |    Device      |  |    Device      |  |     Device       |
          | (boya-*)       |  | (meteo-*)      |  | (sensor-agua-*)  |
          | (semi-static)  |  | (semi-static)  |  | (semi-static)    |
          +-------+--------+  +-------+--------+  +--------+---------+
                  |                    |                     |
                  v                    v                     v
         +--------+-------+  +--------+--------+  +--------+-----------+
         | SeaConditions   |  | WeatherObserved |  | WaterQuality       |
         | (dynamic 10min) |  | (dynamic 1h)    |  | Observed (12h)     |
         +-----------------+  +---------+-------+  +--------------------+
                                        |
                                        v
                              +---------+--------+
                              | WeatherForecast  |
                              | (dynamic 6h)     |
                              +------------------+

         +-----------------+           +-----------------------+
         | WeatherAlert    |           | WaterQualityPredicted |
         | (dynamic, event)|           | (dynamic 6h, ML)      |
         +-----------------+           +-----------------------+
               |                                |
               +--------------------------------+
               |  Both ref Beach via refPointOfInterest
               v
            Beach
```

## Entity Type Details

### 1. PointOfInterest (Static)

**Source:** `dataModel.PointOfInterest`
**Created:** Once at initialization
**Count:** 18 (one per beach)
**ID Pattern:** `urn:ngsi-ld:PointOfInterest:{beachId}`

| Attribute | NGSI-LD Type | Data Type | Example | Static/Dynamic |
|-----------|-------------|-----------|---------|----------------|
| name | Property | String | "Playa de Riazor" | Static |
| description | Property | String | "Urban beach in A Coruna" | Static |
| location | GeoProperty | GeoJSON Point | [-8.4197, 43.3713] | Static |
| category | Property | Array[String] | ["beach"] | Static |
| address | Property | Object | {addressLocality, addressRegion} | Static |

---

### 2. Beach (Static)

**Source:** `dataModel.PointOfInterest`
**Created:** Once at initialization
**Count:** 18
**ID Pattern:** `urn:ngsi-ld:Beach:{beachId}`

| Attribute | NGSI-LD Type | Data Type | Unit | Example | Static/Dynamic |
|-----------|-------------|-----------|------|---------|----------------|
| name | Property | String | - | "Playa de Riazor" | Static |
| description | Property | String | - | "Urban beach..." | Static |
| location | GeoProperty | GeoJSON Point | - | [-8.4197, 43.3713] | Static |
| address | Property | Object | - | {addressLocality: "A Coruna"} | Static |
| length | Property | Number | MTR | 1200 | Static |
| width | Property | Number | MTR | 50 | Static |
| beachType | Property | Array[String] | - | ["urban", "calmWaters"] | Static |
| occupationRate | Property | String | - | "low" | Dynamic (CV) |
| facilities | Property | Array[String] | - | ["lifeGuard", "showers"] | Static |
| accessType | Property | Array[String] | - | ["publicTransport"] | Static |
| refPointOfInterest | Relationship | URI | - | urn:ngsi-ld:PointOfInterest:Riazor | Static |

---

### 3. Device (Semi-static)

**Source:** `dataModel.Device`
**Created:** At initialization, updated on each measurement
**Count:** 36 (3 per beach: buoy, meteo station, water sensor)
**ID Patterns:**
- `urn:ngsi-ld:Device:boya-{beachId}`
- `urn:ngsi-ld:Device:meteo-{beachId}`
- `urn:ngsi-ld:Device:sensor-agua-{beachId}`

| Attribute | NGSI-LD Type | Data Type | Example | Static/Dynamic |
|-----------|-------------|-----------|---------|----------------|
| name | Property | String | "Virtual buoy Riazor" | Static |
| description | Property | String | "Virtual IoT buoy..." | Static |
| deviceCategory | Property | Array[String] | ["sensor"] | Static |
| controlledProperty | Property | Array[String] | ["waveHeight", "pH"] | Static |
| location | GeoProperty | GeoJSON Point | [-8.4197, 43.3713] | Static |
| controlledAsset | Relationship | URI | urn:ngsi-ld:Beach:Riazor | Static |
| batteryLevel | Property | Number (0-1) | 0.95 | Dynamic |
| dateLastValueReported | Property | DateTime | "2026-04-21T16:00:00Z" | Dynamic |

---

### 4. SeaConditions (Dynamic)

**Source:** `dataModel.Weather`
**Update Frequency:** Every 10 minutes
**Data Path:** Simulator -> Orion (direct PATCH)
**Count:** 18
**ID Pattern:** `urn:ngsi-ld:SeaConditions:{beachId}`

| Attribute | NGSI-LD Type | Data Type | Unit | Example | Source |
|-----------|-------------|-----------|------|---------|--------|
| dateObserved | Property | DateTime | - | "2026-04-21T16:00:00Z" | Generated |
| location | GeoProperty | GeoJSON Point | - | [-8.4197, 43.3713] | Beach catalog |
| waveHeight | Property | Number | MTR | 0.8 | Puertos del Estado / Sim |
| wavePeriod | Property | Number | SEC | 6.2 | Puertos del Estado / Sim |
| waveLevel | Property | Number (1-5) | - | 2 | Calculated |
| seaSurfaceTemperature | Property | Number | CEL | 17.4 | Puertos del Estado / Sim |
| pH | Property | Number | - | 8.1 | Sim |
| salinity | Property | Number | - | 35.2 | Sim |
| waveHeightText | Property | String | - | "1 - 1.5 m" | Puertos del Estado (optional) |
| seaStateDescription | Property | String | - | "Marejadilla" | Puertos del Estado (optional) |
| swellDescription | Property | String | - | "Mar de fondo del NW" | Puertos del Estado (optional) |
| refPointOfInterest | Relationship | URI | - | urn:ngsi-ld:Beach:Riazor | Static |
| refDevice | Relationship | URI | - | urn:ngsi-ld:Device:boya-Riazor | Static |

---

### 5. WeatherObserved (Dynamic)

**Source:** `dataModel.Weather`
**Update Frequency:** Every hour
**Data Path:** MeteoGalicia API -> Simulator -> Orion (direct PATCH)
**Count:** 18
**ID Pattern:** `urn:ngsi-ld:WeatherObserved:{beachId}`

| Attribute | NGSI-LD Type | Data Type | Unit | Example | Source |
|-----------|-------------|-----------|------|---------|--------|
| dateObserved | Property | DateTime | - | "2026-04-21T16:00:00Z" | Generated |
| location | GeoProperty | GeoJSON Point | - | [-8.4197, 43.3713] | Beach catalog |
| temperature | Property | Number | CEL | 18.5 | MeteoGalicia / Sim |
| feelsLikeTemperature | Property | Number | CEL | 17.0 | Calculated |
| windSpeed | Property | Number | KMH | 12.3 | MeteoGalicia / Sim |
| windDirection | Property | Number (0-360) | - | 270 | MeteoGalicia / Sim |
| relativeHumidity | Property | Number (0-1) | - | 0.75 | MeteoGalicia / Sim |
| precipitation | Property | Number | MMT | 0.0 | MeteoGalicia / Sim |
| uVIndexMax | Property | Number | - | 6 | Calculated |
| weatherType | Property | String | - | "sunnyDay" | Derived |
| visibility | Property | String | - | "good" | Default |
| dataProvider | Property | String | - | "MeteoGalicia" | Static |
| source | Property | String | - | URL | Static |
| atmosphericPressure | Property | Number | HPA | 1013.2 | MeteoGalicia (optional) |
| windGust | Property | Number | MTS | 8.5 | MeteoGalicia (optional) |
| temperatureMax | Property | Number | CEL | 21.0 | MeteoGalicia (optional) |
| temperatureMin | Property | Number | CEL | 14.0 | MeteoGalicia (optional) |
| dewPoint | Property | Number | CEL | 12.0 | MeteoGalicia (optional) |
| refPointOfInterest | Relationship | URI | - | urn:ngsi-ld:Beach:Riazor | Static |
| refDevice | Relationship | URI | - | urn:ngsi-ld:Device:meteo-Riazor | Static |

---

### 6. WeatherForecast (Dynamic)

**Source:** `dataModel.Weather`
**Update Frequency:** Every 6 hours
**Data Path:** MeteoGalicia API -> Simulator -> Orion (direct PATCH)
**Count:** 18
**ID Pattern:** `urn:ngsi-ld:WeatherForecast:{beachId}`

| Attribute | NGSI-LD Type | Data Type | Unit | Example | Source |
|-----------|-------------|-----------|------|---------|--------|
| dateIssued | Property | DateTime | - | "2026-04-21T16:00:00Z" | Generated |
| validFrom | Property | DateTime | - | "2026-04-21T18:00:00Z" | Calculated |
| validTo | Property | DateTime | - | "2026-04-22T18:00:00Z" | Calculated |
| validity | Property | String | - | "from/to ISO interval" | Calculated |
| temperature | Property | Object | - | {minimum: 15, maximum: 21} | MeteoGalicia / Sim |
| feelsLikeTemperature | Property | Object | - | {minimum: 13.5, maximum: 19.5} | Calculated |
| relativeHumidity | Property | Number (0-1) | - | 0.70 | Sim |
| precipitationProbability | Property | Number (0-1) | - | 0.1 | MeteoGalicia / Sim |
| windSpeed | Property | Number | KMH | 15.0 | MeteoGalicia / Sim |
| windDirection | Property | Number (0-360) | - | 260 | MeteoGalicia / Sim |
| weatherType | Property | String | - | "partlyCloudy" | Derived |
| uVIndexMax | Property | Number | - | 5 | MeteoGalicia / Sim |
| dataProvider | Property | String | - | "MeteoGalicia" | Static |
| refPointOfInterest | Relationship | URI | - | urn:ngsi-ld:Beach:Riazor | Static |

---

### 7. WeatherAlert (Dynamic - Event)

**Source:** `dataModel.Weather`
**Update Frequency:** Periodic (every simulator cycle ~10 min for IoTSensor alerts) + event-driven (ML prediction, CV detection)
**Data Path:** Simulator / ML / CV -> Orion (direct POST/PATCH)
**Count:** Variable (up to 3 per beach from simulator: waves, UV, water quality)
**ID Pattern:**
- Simulator-generated (deterministic): `urn:ngsi-ld:WeatherAlert:{beachId}-waves`, `{beachId}-uv`, `{beachId}-water-quality`
- ML/CV-generated: `urn:ngsi-ld:WeatherAlert:{uuid}`

| Attribute | NGSI-LD Type | Data Type | Example | Source |
|-----------|-------------|-----------|---------|--------|
| name | Property | String | "Oleaje elevado en Riazor" | Generated |
| dateIssued | Property | DateTime | "2026-04-21T16:00:00Z" | Generated |
| validFrom | Property | DateTime | "2026-04-21T16:00:00Z" | Generated |
| validTo | Property | DateTime | "2026-04-21T20:00:00Z" | ML/CV only |
| alertSource | Property | String | "IoTSensor" / "MLModel" / "CVSystem" / "Citizen" | System |
| category | Property | String | "highWaves" / "poorWaterQuality" / "highUVIndex" / "crowding" | System |
| severity | Property | String | "medium" / "high" | Threshold-based |
| description | Property | String | "Altura de ola: 2.1 m..." | Generated |
| refPointOfInterest | Relationship | URI | urn:ngsi-ld:Beach:Riazor | Static |

**Simulator alert thresholds:**

| Category | Medium | High |
|----------|--------|------|
| highWaves | waveHeight ≥ 1.5 m | waveHeight ≥ 2.5 m |
| highUVIndex | uVIndexMax ≥ 8 | uVIndexMax ≥ 11 |
| poorWaterQuality | E. coli ≥ 200 UFC/100mL | E. coli ≥ 500 UFC/100mL |

---

### 8. WaterQualityObserved (Dynamic)

**Source:** `dataModel.WaterQuality`
**Update Frequency:** Twice daily (every 12 hours)
**Data Path:** Simulator -> IoT Agent -> Orion
**Count:** 18
**ID Pattern:** `urn:ngsi-ld:WaterQualityObserved:{beachId}`

| Attribute | NGSI-LD Type | Data Type | Unit | Example | Source |
|-----------|-------------|-----------|------|---------|--------|
| dateObserved | Property | DateTime | - | "2026-04-21T08:00:00Z" | Generated |
| location | GeoProperty | GeoJSON Point | - | [-8.4197, 43.3713] | Beach catalog |
| temperature | Property | Number | CEL | 17.4 | INTECMAR / Sim |
| pH | Property | Number | - | 8.1 | INTECMAR / Sim |
| conductivity | Property | Number | D10 | 45.2 | Sim |
| turbidity | Property | Number | NTU | 1.2 | Sim |
| dissolvedOxygen | Property | Number | M1 | 8.5 | Sim |
| escherichiaColi | Property | Number | UFC | 45 | INTECMAR / Sim |
| intestinalEnterococci | Property | Number | UFC | 12 | INTECMAR / Sim |
| refDevice | Relationship | URI | - | urn:ngsi-ld:Device:sensor-agua-Riazor | Static |
| refPointOfInterest | Relationship | URI | - | urn:ngsi-ld:Beach:Riazor | Static |

---

### 9. WaterQualityPredicted (Dynamic)

**Source:** `dataModel.WaterQuality`
**Update Frequency:** Every 6 hours (ML model output)
**Data Path:** ML predict.py -> Orion (direct POST)
**Count:** 18
**ID Pattern:** `urn:ngsi-ld:WaterQualityPredicted:{beachId}`

| Attribute | NGSI-LD Type | Data Type | Unit | Example | Source |
|-----------|-------------|-----------|------|---------|--------|
| dateObserved | Property | DateTime | - | "2026-04-22T08:00:00Z" | Generated |
| dateIssued | Property | DateTime | - | "2026-04-21T16:00:00Z" | Generated |
| location | GeoProperty | GeoJSON Point | - | [-8.4197, 43.3713] | Beach catalog |
| pH | Property | Number | - | 8.0 | ML model |
| escherichiaColi | Property | Number | UFC | 52 | ML model |
| intestinalEnterococci | Property | Number | UFC | 15 | ML model |
| refPointOfInterest | Relationship | URI | - | urn:ngsi-ld:Beach:Riazor | Static |

---

### 10. DeviceMeasurement (Dynamic)

**Source:** `dataModel.Device`
**Update Frequency:** Per-measurement (via IoT Agent)
**Data Path:** IoT Agent internal entity
**Count:** Variable
**ID Pattern:** Auto-generated by IoT Agent

This entity type is implicitly created by the IoT Agent as it processes device measurements. Each measurement from a provisioned device creates or updates entries that the IoT Agent maps to the target entity type (SeaConditions, WaterQualityObserved).

## Relationship Summary

| From Entity | Relationship Attribute | To Entity |
|------------|----------------------|-----------|
| Beach | refPointOfInterest | PointOfInterest |
| SeaConditions | refPointOfInterest | Beach |
| SeaConditions | refDevice | Device (boya) |
| WeatherObserved | refPointOfInterest | Beach |
| WeatherObserved | refDevice | Device (meteo) |
| WeatherForecast | refPointOfInterest | Beach |
| WeatherAlert | refPointOfInterest | Beach |
| WaterQualityObserved | refPointOfInterest | Beach |
| WaterQualityObserved | refDevice | Device (sensor-agua) |
| WaterQualityPredicted | refPointOfInterest | Beach |
| Device | controlledAsset | Beach |

## EU Bathing Water Quality Classification

Water quality classification follows the EU Bathing Water Directive 2006/7/EC:

| Classification | E. coli (UFC/100ml) | Enterococci (UFC/100ml) | Color |
|---------------|--------------------|-----------------------|-------|
| Excellent | < 250 | < 100 | Green |
| Good | < 500 | < 200 | Yellow |
| Sufficient | < 500 | < 185 | Orange |
| Poor | >= 500 | >= 185 | Red |
