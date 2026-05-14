# Architecture - NEPTUNO Smart Coastal Intelligence Platform

## System Architecture Overview

NEPTUNO follows a microservices architecture orchestrated via Docker Compose, with Python application services running on the host. The system integrates the three mandatory FIWARE components (Orion-LD, IoT Agent JSON, QuantumLeap) with supporting services (MongoDB, CrateDB, Grafana) and application-layer components (FastAPI backend, vanilla JS frontend, ML/CV modules).

## Architecture Diagram

```
+=====================================================================+
|                        EXTERNAL DATA SOURCES                         |
+=====================================================================+
|  MeteoGalicia API v5/mgrss  |  INTECMAR  |  Puertos del Estado  |  Xunta  |
|  (MeteoSIX obs/fcst)  |  (water Q) |  (buoy sea state)    |  (cat)  |
+-----------+-----------+------+-----+----------+-----------+----+----+
            |                  |                |                |
            v                  v                v                v
+=====================================================================+
|                    HOST PYTHON APPLICATIONS                          |
+=====================================================================+
|                                                                     |
|  +---------------------+    +------------------+                    |
|  | simulator.py        |    | init_orion.py    |                    |
|  | - Fetches real APIs |    | - Creates static |                    |
|  | - Falls back to sim |    |   entities       |                    |
|  | - Direct Orion PATCH|    | - Provisions IoT |                    |
|  | - Alert generation  |    |   Agent devices  |                    |
|  +----------+----------+    +------------------+                    |
|                                                                     |
|  +---------------------+                                           |
|  | backfill.py         |                                           |
|  | - 7-day historical  |                                           |
|  |   data load         |                                           |
|  | - Direct CrateDB    |                                           |
|  +---------------------+                                           |
|             |                                                       |
|  +----------+----------+    +------------------+                    |
|  | ml/predict.py       |    | cv/alerts.py     |                    |
|  | - GradientBoosting  |    | - YOLOv11 ONNX   |                    |
|  | - WQ prediction     |    | - Person detect  |                    |
|  | - Alert generation  |    | - Crowd alerts   |                    |
|  +---------------------+    +------------------+                    |
|                                                                     |
|  +--------------------------------------------------------------+  |
|  | FastAPI Backend (:8000)                                       |  |
|  | - GET /api/health          (backend + Ollama status)          |  |
|  | - GET /api/beaches         (current state from Orion)         |  |
|  | - GET /api/beaches/{id}    (detail with all sub-entities)     |  |
|  | - GET /api/beaches/{id}/history  (QuantumLeap time series)    |  |
|  | - GET /api/beaches/{id}/predict  (ML predictions from Orion)  |  |
|  | - GET /api/beaches/{id}/webcam   (Camaramar/Windy cam info)   |  |
|  | - GET /api/beaches/{id}/webcam/snapshot (CORS proxy image)    |  |
|  | - GET /api/beaches/{id}/tide     (harmonic tide prediction)   |  |
|  | - GET /api/alerts          (active WeatherAlert entities)     |  |
|  | - POST /api/chat           (Ollama LLM with Orion context)    |  |
|  | - Static file server for frontend/                            |  |
|  +------+----------------------------+--------------------------+  |
|         |                            |                              |
+=========|============================|==============================+
          |                            |
          v                            v
+=========|============================|==============================+
|         |    DOCKER COMPOSE NETWORK (neptuno)                       |
+=========|============================|==============================+
|         |                            |                              |
|  +------+------+             +-------+--------+                    |
|  | Ollama      |             | Frontend SPA   |                    |
|  | :11434      |             | (served by     |                    |
|  | Llama 3.1   |             |  FastAPI)      |                    |
|  | (host, not  |             | - Three.js     |                    |
|  |  Docker)    |             | - Leaflet.js   |                    |
|  +-------------+             | - Chart.js     |                    |
|                              +----------------+                    |
|                                                                     |
|  +--------------------------------------------------------------+  |
|  |              FIWARE CORE COMPONENTS                           |  |
|  +--------------------------------------------------------------+  |
|  |                                                               |  |
|  |  +-----------------+     +------------------+                 |  |
|  |  | Orion-LD :1026  |<--->| MongoDB :27017   |                 |  |
|  |  | Context Broker  |     | (entity storage) |                 |  |
|  |  | NGSI-LD API     |     +------------------+                 |  |
|  |  +--------+--------+                                          |  |
|  |           |                                                   |  |
|  |     +-----+------+                                            |  |
|  |     |            |                                             |  |
|  |     v            v                                             |  |
|  |  +--+----------+ +--+---------------+                         |  |
|  |  | IoT Agent   | | QuantumLeap :8668|                         |  |
|  |  | JSON :4041  | | (subscription    |                         |  |
|  |  | :7896 (data)| |  notifications)  |                         |  |
|  |  | NGSI-LD mode| +--------+---------+                         |  |
|  |  +-------------+          |                                   |  |
|  |                           v                                   |  |
|  |                  +--------+---------+                         |  |
|  |                  | CrateDB :4200    |                         |  |
|  |                  | :5432 (PgSQL)    |                         |  |
|  |                  | Time-series store|                         |  |
|  |                  +--------+---------+                         |  |
|  |                           |                                   |  |
|  |                           v                                   |  |
|  |                  +--------+---------+                         |  |
|  |                  | Grafana :3003    |                         |  |
|  |                  | 6 dashboards     |                         |  |
|  |                  +------------------+                         |  |
|  |                                                               |  |
|  |  +------------------+                                         |  |
|  |  | Context (nginx)  |                                         |  |
|  |  | :3004            |                                         |  |
|  |  | JSON-LD @context |                                         |  |
|  |  +------------------+                                         |  |
|  +--------------------------------------------------------------+  |
+=====================================================================+
```

## Component Details

### Docker Compose Services

| Service | Image | Internal Port | External Port | Purpose |
|---------|-------|--------------|---------------|---------|
| mongo-db | mongo:6.0 | 27017 | 27017 | Persistent store for Orion-LD and IoT Agent |
| orion | fiware/orion-ld:1.5.1 | 1026 | 1026 | NGSI-LD Context Broker |
| iot-agent | fiware/iotagent-json:3.4.0 | 4041, 7896 | 4041, 7896 | IoT device protocol translation |
| crate-db | crate:5.6.4 | 4200, 5432 | 4200, 5432 | Time-series database |
| quantumleap | orchestracities/quantumleap:1.0.0 | 8668 | 8668 | NGSI-LD to CrateDB persistence |
| grafana | grafana/grafana:11.0.4 | 3000 | 3003 | Dashboard visualization |
| context | nginx:alpine | 80 | 3004 | JSON-LD context file server |

### Host Applications

| Component | Technology | Port | Purpose |
|-----------|-----------|------|---------|
| Backend API | FastAPI + Uvicorn | 8000 | REST API + static file server |
| Simulator | Python (async) | - | Data collection, direct Orion updates, automatic alert generation |
| Backfill | Python (async) | - | One-shot 7-day historical data load direct to CrateDB |
| ML Pipeline | scikit-learn, XGBoost | - | Water quality prediction |
| CV Pipeline | ONNX Runtime + YOLOv11 | - | Beach occupancy detection |
| Webcam Service | data/webcams.py | - | Camaramar HLS + Windy snapshot URLs; CORS proxy |
| Tide Service | services/tides.py | - | Harmonic prediction via IHM A Coruna constituents |
| Ollama | Llama 3.1:8b | 11434 | LLM for chat assistant |

## Data Flow Pipelines

### Pipeline 1: Real-time Sea Conditions (Direct Orion Path)

```
Puertos del Estado API / Simulator
    |
    | POST/PATCH :1026/ngsi-ld/v1/entities/{id}/attrs
    v
Orion-LD (:1026)
    |
    | Subscription notification
    v
QuantumLeap (:8668)
    |
    | SQL INSERT
    v
CrateDB (mtsmartbeach.etseaconditions)
```

### Pipeline 1b: Water Quality (IoT Agent Path)

```
Simulator (update_water_quality, every 12h)
    |
    | POST :7896/iot/json?k=neptuno-smartbeach-2026&i=sensor-agua-{id}
    | Payload: {temp, ph, cond, turb, do, ecoli, entero}
    v
IoT Agent JSON (:7896)
    |
    | Translates to NGSI-LD, PATCH :1026/ngsi-ld/v1/entities/
    | urn:ngsi-ld:WaterQualityObserved:{id}/attrs
    v
Orion-LD (:1026)
    |
    | Subscription notification
    v
QuantumLeap -> CrateDB (mtsmartbeach.etwaterqualityobserved)
```

### Pipeline 2: Weather Data (Direct Orion Path)

```
MeteoGalicia API v5/mgrss (MeteoSIX)
    |
    | HTTP GET (observation/forecast)
    v
simulator.py (parse + transform)
    |
    | PATCH :1026/ngsi-ld/v1/entities/{id}/attrs
    v
Orion-LD (:1026)
    |
    | Subscription notification
    v
QuantumLeap -> CrateDB (mtsmartbeach.etweatherobserved)
```

### Pipeline 3: ML Prediction

```
CrateDB (historical data)
    |
    | SQL query for training features
    v
ml/train.py (GradientBoosting model)
    |
    | joblib.dump(model)
    v
ml/models/*.joblib
    |
    v
ml/predict.py
    |
    | 1. Fetch current conditions from Orion
    | 2. Predict water quality with model
    | 3. POST WaterQualityPredicted to Orion
    | 4. POST WeatherAlert if dangerous
    v
Orion-LD -> QuantumLeap -> CrateDB
```

### Pipeline 3b: Automatic Alert Generation (Simulator)

```
simulator.py (every ~10 min cycle)
    |
    | Check thresholds: waveHeight / uVIndexMax / escherichiaColi
    |   - Condition exceeded → POST/PATCH WeatherAlert entity to Orion
    |   - Condition cleared  → DELETE WeatherAlert entity from Orion
    v
Orion-LD (:1026)
    |
    | Subscription notification
    v
QuantumLeap -> CrateDB (mtsmartbeach.etweatheralert)
```

### Pipeline 4: Frontend Data Access

```
User Browser
    |
    | HTTP GET /api/beaches
    v
FastAPI Backend (:8000)
    |
    | HTTP GET :1026/ngsi-ld/v1/entities?type=Beach
    v
Orion-LD (current state)
    |
    v
FastAPI -> JSON response -> Frontend
    |
    | Three.js globe / Leaflet map / Chart.js
    v
User visualization
```

### Pipeline 5: Live Webcam

```
User Browser (beach detail view)
    |
    | GET /api/beaches/{id}/webcam
    v
FastAPI Backend
    |
    | data/webcams.py lookup (WEBCAM_MAP)
    | Returns: hls_url (Camaramar playlist.m3u8) or snapshot_url (Windy JPEG)
    v
Browser
    |
    | If HLS available: HLS.js loads stream from Camaramar directly (CORS *)
    | If snapshot only: GET /api/beaches/{id}/webcam/snapshot (CORS proxy)
    |                   Backend fetches from Windy/Camaramar, relays to browser
    v
Webcam panel in beach detail view (auto-refresh every 5 min)
```

### Pipeline 5b: Tide Prediction

```
User Browser (beach detail view)
    |
    | GET /api/beaches/{id}/tide
    v
FastAPI Backend
    |
    | services/tides.py: harmonic prediction
    |   - 11 IHM tidal constituents for A Coruna reference port
    |   - Computes height (m), trend (rising/falling), next extreme
    |   (no external API call, pure calculation)
    v
JSON response: {height, trend, trend_es, trend_arrow, next_extreme, phase_pct}
    v
Tide card in beach detail view
```

### Pipeline 6: LLM Chat

```
User types message in chat UI
    |
    | POST /api/chat {message: "..."}
    v
FastAPI Backend
    |
    | 1. GET all beaches from Orion (current state)
    | 2. Build context string with real sensor data
    | 3. Inject context into system prompt
    | 4. POST to Ollama :11434/api/chat
    v
Ollama (Llama 3.1:8b)
    |
    | Response text
    v
Frontend (typewriter animation)
```

## Network Architecture

```
Docker Network: neptuno (bridge)
+-------------------------------------------------------+
|  mongo-db  <-->  orion  <-->  iot-agent               |
|                    |                                   |
|                    v                                   |
|             quantumleap  -->  crate-db  <--  grafana  |
|                                                       |
|             context (nginx)                           |
+-------------------------------------------------------+
       ^              ^              ^
       |              |              |
   Host:1026     Host:7896      Host:8668
       |              |              |
+------+--------------+--------------+---+
|              Host Machine              |
|  simulator.py  |  backend  |  Ollama   |
+--------------------------------------------+
```

## NGSI-LD Subscription Configuration

Six subscriptions are created, one per dynamic entity type. All notify QuantumLeap at `http://quantumleap:8668/v2/notify`.

| Subscription | Entity Type | Condition | Notification |
|-------------|-------------|-----------|-------------|
| Sub-1 | SeaConditions | Any attribute change | QuantumLeap |
| Sub-2 | WeatherObserved | Any attribute change | QuantumLeap |
| Sub-3 | WeatherForecast | Any attribute change | QuantumLeap |
| Sub-4 | WeatherAlert | Any attribute change | QuantumLeap |
| Sub-5 | WaterQualityObserved | Any attribute change | QuantumLeap |
| Sub-6 | WaterQualityPredicted | Any attribute change | QuantumLeap |

## CrateDB Table Schema

QuantumLeap automatically creates tables in the `mtsmartbeach` schema:

| Table | Source Entity | Key Columns |
|-------|--------------|-------------|
| mtsmartbeach.etseaconditions | SeaConditions | time_index, entity_id, waveheight, seasurfacetemperature |
| mtsmartbeach.etweatherobserved | WeatherObserved | time_index, entity_id, temperature, windspeed |
| mtsmartbeach.etweatherforecast | WeatherForecast | time_index, entity_id, precipitationprobability |
| mtsmartbeach.etweatheralert | WeatherAlert | time_index, entity_id, severity, category |
| mtsmartbeach.etwaterqualityobserved | WaterQualityObserved | time_index, entity_id, escherichiacoli |
| mtsmartbeach.etwaterqualitypredicted | WaterQualityPredicted | time_index, entity_id, escherichiacoli |

## Grafana Connection

Grafana connects to CrateDB via the PostgreSQL wire protocol:

- **Host:** crate-db:5432 (internal Docker network)
- **Database:** doc
- **User:** crate
- **Password:** (empty)
- **SSL:** disabled
- **Queries:** Use fully qualified table names (e.g., `mtsmartbeach.etseaconditions`)

## Security Considerations

- All FIWARE services communicate internally via Docker bridge network
- External access is limited to mapped ports
- Grafana is password-protected (admin/neptuno2026)
- No authentication on Orion-LD (academic project scope)
- CORS enabled on FastAPI backend for development
- Ollama runs locally on the host machine (no external API exposure)

## Technology Stack Summary

| Layer | Technology | Version |
|-------|-----------|---------|
| Context Broker | Orion-LD | 1.5.1 |
| IoT Agent | IoT Agent JSON | 3.4.0 |
| Time-series Broker | QuantumLeap | 1.0.0 |
| Document Store | MongoDB | 6.0 |
| Time-series Store | CrateDB | 5.6.4 |
| Dashboards | Grafana | 11.0.4 |
| Backend | FastAPI + Uvicorn | 0.111+ |
| HTTP Client | httpx | 0.27+ |
| ML Framework | scikit-learn + XGBoost | 1.4+ / 2.0+ |
| CV Framework | ONNX Runtime | 1.17+ |
| LLM | Ollama + Llama 3.1 | 8b |
| 3D Visualization | Three.js | r128 |
| Map Visualization | Leaflet.js | 1.9.4 |
| Charts | Chart.js | 4.4+ |
| Package Manager | uv | Latest |
| Container Runtime | Docker Compose | 3.8 |
