# Product Requirements Document - NEPTUNO

## 1. Product Overview

**Product Name:** NEPTUNO - Smart Coastal Intelligence Platform
**Version:** 1.0.0
**Target Users:** Beachgoers, surfers, tourists, local authorities, environmental managers
**Scope:** 12 beaches in the province of A Coruna, Galicia, Spain

## 2. Problem Statement

Beachgoers and coastal authorities lack a unified platform to access real-time beach conditions, water quality data, and safety alerts. Current information is fragmented across multiple government websites, weather services, and manual monitoring reports, making it difficult to make timely decisions about beach safety and activity planning.

## 3. Product Goals

1. Provide a single platform aggregating all beach environmental data
2. Deliver real-time and historical views of beach conditions
3. Predict water quality to enable proactive safety measures
4. Automate alert generation for hazardous conditions
5. Offer an AI-powered assistant for natural language beach queries

## 4. Functional Requirements

### FR-1: Real-time Data Collection
- **FR-1.1:** Fetch meteorological observations from MeteoGalicia API v5/mgrss (MeteoSIX) every hour
- **FR-1.2:** Fetch sea condition data from Puertos del Estado API every 10 minutes
- **FR-1.3:** Fetch water quality data from INTECMAR twice daily
- **FR-1.4:** Fall back to realistic simulated values when APIs are unavailable
- **FR-1.5:** Log whether each data point is real or simulated to console

### FR-2: NGSI-LD Entity Management
- **FR-2.1:** Create and maintain 10 entity types following FIWARE Smart Data Models
- **FR-2.2:** Interconnect entities via NGSI-LD Relationship attributes
- **FR-2.3:** Use `NGSILD-Tenant: smartbeach` header on all Orion requests
- **FR-2.4:** Include `@context` reference in all entity bodies

### FR-3: IoT Device Simulation
- **FR-3.1:** Provision virtual buoy, meteo, and water sensor devices in Orion as Device entities
- **FR-3.2:** Update all dynamic entities (SeaConditions, WeatherObserved, WaterQualityObserved, WeatherForecast) via direct PATCH to Orion-LD — IoT Agent is provisioned but bypassed in the current data flow
- **FR-3.3:** IoT Agent HTTP endpoint (port 7896) reserved for future device integration

### FR-4: Time-series Persistence
- **FR-4.1:** Create 6 NGSI-LD subscriptions for dynamic entity types
- **FR-4.2:** Persist all dynamic entity updates via QuantumLeap to CrateDB
- **FR-4.3:** Support historical queries over 7-day windows

### FR-5: Globe Visualization
- **FR-5.1:** Display 3D globe using Three.js r128 centered on A Coruna
- **FR-5.2:** Place 12 beach markers colored by current status (green/yellow/red)
- **FR-5.3:** Support mouse drag rotation and scroll zoom
- **FR-5.4:** Navigate to beach detail view on marker click

### FR-6: Beach Detail View
- **FR-6.1:** Show Leaflet map with dark tiles centered on selected beach
- **FR-6.2:** Display current conditions cards (temperature, waves, wind, UV, water quality, occupation)
- **FR-6.3:** Render 4 Chart.js panels (sea temp, wave height, E. coli, occupation prediction)
- **FR-6.4:** Load historical data from QuantumLeap via backend API

### FR-7: AI Assistant
- **FR-7.1:** Accept natural language queries via chat interface
- **FR-7.2:** Inject current beach state from Orion into Ollama system prompt
- **FR-7.3:** Display responses with typewriter animation effect
- **FR-7.4:** Support Spanish, Galician, and English queries

### FR-8: Alert System
- **FR-8.1:** Generate WeatherAlert entities automatically from simulator sensor thresholds (waves, UV, water quality) on every data cycle — source `IoTSensor`
- **FR-8.2:** Generate WeatherAlert entities from ML model water quality predictions — source `MLModel`
- **FR-8.3:** Generate crowding alerts from CV occupancy detection — source `CVSystem`
- **FR-8.4:** Auto-remove alerts when conditions return to safe thresholds
- **FR-8.5:** Poll for active alerts every 30 seconds
- **FR-8.6:** Display alerts with severity color coding and source badges

### FR-9: ML Water Quality Prediction
- **FR-9.1:** Train Gradient Boosting classifier for quality class (good/acceptable/poor)
- **FR-9.2:** Train Gradient Boosting regressor for E. coli count prediction
- **FR-9.3:** Use CrateDB historical data or synthetic data for training
- **FR-9.4:** Create WaterQualityPredicted entities in Orion every 6 hours

### FR-10: Grafana Dashboards
- **FR-10.1:** Auto-provision CrateDB datasource via PostgreSQL wire protocol
- **FR-10.2:** Display 6 dashboard panels: sea temp, wave height, water quality state, occupation gauge, alerts geomap, pH/E.coli history

## 5. Non-Functional Requirements

### NFR-1: Performance
- Entity updates processed within 2 seconds
- Frontend loads within 3 seconds
- Chart rendering under 1 second

### NFR-2: Reliability
- Automatic fallback to simulated data on API failure
- Service health checks in Docker Compose
- Error logging for all data pipeline stages

### NFR-3: Usability
- Dark theme optimized for readability
- Responsive design for mobile and desktop
- No page reloads (SPA architecture)

### NFR-4: Security
- No sensitive data in frontend code
- Grafana password-protected
- CORS enabled on backend

## 6. Technical Constraints

- NGSI-LD format exclusively (no NGSIv2)
- Python managed with uv (no pip install)
- Vanilla JavaScript only (no frameworks)
- Docker Compose for infrastructure
- Ollama runs outside Docker on host machine

## 7. Data Sources

| Source | Data Type | Update Frequency | Authentication |
|--------|----------|-----------------|----------------|
| MeteoGalicia API v5/mgrss (MeteoSIX) | Weather observations, forecasts | Hourly | None (free) |
| INTECMAR | Water quality (E. coli, enterococci) | Twice daily | None |
| Puertos del Estado | Buoy data (waves, SST) | 10 minutes | None |
| Xunta Open Data | Beach catalogue (static) | Once (init) | None |
