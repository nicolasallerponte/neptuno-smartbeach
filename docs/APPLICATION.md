# APPLICATION - NEPTUNO Smart Coastal Intelligence Platform

## Objective

NEPTUNO is a smart coastal monitoring platform that provides real-time environmental intelligence for 12 beaches along the province of A Coruna, Galicia, Spain. The system collects, processes, and visualizes meteorological, oceanographic, and water quality data using the FIWARE ecosystem, enabling beachgoers, local authorities, and environmental managers to make informed decisions about beach safety and environmental conditions.

## State of the Art

Coastal monitoring has traditionally relied on manual measurements and periodic sampling. Modern IoT-based approaches leverage sensor networks, real-time data aggregation, and predictive analytics to provide continuous monitoring. The FIWARE ecosystem provides standardized Smart Data Models and context management components that enable interoperable smart city applications. NEPTUNO extends this paradigm to coastal environments by integrating multiple real data sources (MeteoGalicia, INTECMAR, Puertos del Estado) with simulation capabilities and machine learning predictions.

## Main Features

1. **Real-time Monitoring** - Continuous data collection from meteorological stations, oceanographic buoys, and water quality sensors (real APIs + simulated fallback)
2. **3D Globe Visualization** - Interactive Three.js globe showing all 12 beaches with color-coded status indicators
3. **Beach Detail Dashboard** - Per-beach view with Leaflet maps, Chart.js time series, and current condition metrics
4. **AI Assistant** - Ollama-powered LLM chat with real-time beach context injection from Orion-LD
5. **Automated Alerts** - ML and CV-generated safety alerts for dangerous conditions (high waves, poor water quality, crowding)
6. **Historical Analytics** - Grafana dashboards connected to CrateDB for time-series analysis
7. **Water Quality Prediction** - Gradient Boosting ML models predicting E. coli levels and bathing water classification
8. **Computer Vision** - YOLOv11 ONNX person detection for beach occupancy estimation

## Detailed Features Summary

| Feature | Technology | Data Source |
|---------|-----------|-------------|
| Weather monitoring | MeteoGalicia API v4 | Real API + simulated fallback |
| Sea conditions | Puertos del Estado API | Real API + simulated fallback |
| Water quality | INTECMAR data | Real scraping + simulated fallback |
| Beach catalogue | Xunta Open Data | Real catalogue + hardcoded fallback |
| 3D visualization | Three.js r128 | Orion-LD current state |
| Map visualization | Leaflet.js + CartoDB Dark | Per-beach detail |
| Charts | Chart.js 4.x | QuantumLeap time series |
| Historical dashboards | Grafana 11.0.4 + CrateDB | 6 specialized panels |
| ML prediction | scikit-learn + GradientBoosting | Historical + synthetic training data |
| CV detection | YOLOv11 + ONNX Runtime | Beach camera images |
| LLM assistant | Ollama + Llama 3.1:8b | Context-enriched prompts |
| IoT simulation | IoT Agent JSON (NGSI-LD) | HTTP device measurements |
| Data persistence | Orion-LD + QuantumLeap + CrateDB | NGSI-LD subscriptions |

## Architecture Diagram

```
+------------------+     +------------------+     +------------------+
|  MeteoGalicia    |     |    INTECMAR       |     | Puertos Estado   |
|  API v4          |     |  Water Quality    |     | Buoy Data        |
+--------+---------+     +--------+---------+     +--------+---------+
         |                        |                        |
         v                        v                        v
+--------+--------------------------------------------------------+
|                    simulator/simulator.py                        |
|  (fetches real data, falls back to simulation)                  |
+--------+----------------------------+---------------------------+
         |                            |
   IoT Agent :7896              Direct PATCH
   (buoy + water sensor)        (weather data)
         |                            |
         v                            v
+--------+----------------------------+---------------------------+
|                    Orion-LD :1026                                |
|              (NGSI-LD Context Broker)                           |
+--------+----------------------------+---------------------------+
         |                            |
   Subscriptions                  REST API
         |                            |
         v                            v
+--------+---------+     +--------+---------+     +-----------+
| QuantumLeap :8668|     | FastAPI :8000    |     | Ollama    |
+--------+---------+     | (Backend API)    |     | :11434    |
         |               +--------+---------+     +-----+-----+
         v                        |                      |
+--------+---------+              v                      |
| CrateDB :4200    |     +-------+--------+             |
| (Time Series)    |     |  Frontend SPA  |<------------+
+--------+---------+     | Three.js Globe |
         |               | Leaflet Maps   |
         v               | Chart.js       |
+--------+---------+     | Chat UI        |
| Grafana :3003    |     +----------------+
| (6 Dashboards)   |
+------------------+
```

## Data Model Diagram

```
PointOfInterest <---- Beach <---- SeaConditions
                        ^              |
                        |         refDevice
                        |              v
                        +-------- Device
                        |
                        +<--- WeatherObserved
                        |
                        +<--- WeatherForecast
                        |
                        +<--- WeatherAlert
                        |
                        +<--- WaterQualityObserved
                        |
                        +<--- WaterQualityPredicted
```

All relationships are implemented as NGSI-LD `Relationship` attributes using `refPointOfInterest` and `refDevice` references.
