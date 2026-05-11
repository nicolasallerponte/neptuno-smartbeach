# NEPTUNO — Smart Coastal Intelligence

Plataforma de monitorización costera en tiempo real para 18 playas de A Coruña. Integra datos reales de MeteoGalicia, Puertos del Estado e INTECMAR sobre el ecosistema FIWARE con entidades NGSI-LD, series temporales, ML y un asistente IA local.

**Repositorio:** https://github.com/nicolasallerponte/neptuno-smartbeach

---

## Requisitos

| Herramienta | Versión |
|-------------|---------|
| Docker + Docker Compose | 24+ |
| Python | 3.11+ |
| uv | cualquiera — `curl -Lsf https://astral.sh/uv/install.sh \| sh` |
| Ollama | cualquiera — https://ollama.com |

---

## Arranque

```bash
# 1. Clonar e instalar dependencias
git clone https://github.com/nicolasallerponte/neptuno-smartbeach
cd neptuno-smartbeach
cp .env.example .env        # editar si se quiere cambiar algo
uv sync

# 2. Infraestructura FIWARE
docker compose up -d

# 3. Inicializar entidades en Orion-LD
uv run python init/init_orion.py

# 4. Crear subscripciones a QuantumLeap
uv run python subscriptions/create_subscriptions.py

# 5. Simulador de datos (terminal aparte)
uv run python -m simulator.simulator

# 6. Backend + frontend
uv run python -m backend.main
# → http://localhost:8000
```

### Ollama (asistente IA)

```bash
sudo systemctl enable --now ollama   # si se instaló con el script oficial
ollama pull llama3.1:8b              # descarga ~5 GB, solo una vez
```

### Historial (opcional pero recomendado)

```bash
# Carga 7 días de datos históricos en CrateDB para que las gráficas tengan contexto
uv run python simulator/backfill.py
```

### ML de calidad del agua (opcional)

```bash
uv run python ml/train.py    # requiere datos en QuantumLeap
uv run python ml/predict.py  # genera entidades WaterQualityPredicted en Orion
```

---

## Vistas

| URL | Descripción |
|-----|-------------|
| `http://localhost:8000` | Mapa principal con 18 playas coloreadas por estado |
| `http://localhost:8000/#beach/<id>` | Detalle: condiciones actuales, mapa Leaflet, 4 gráficas históricas |
| `http://localhost:8000/#chat` | Chat en lenguaje natural con Llama 3.1 (datos en tiempo real de Orion) |
| `http://localhost:8000/#alerts` | Alertas activas (oleaje, UV, calidad del agua) |
| `http://localhost:3003` | Grafana — dashboards de series temporales en CrateDB |

---

## Servicios Docker

| Servicio | Puerto | Descripción |
|----------|--------|-------------|
| Orion-LD | 1026 | Context Broker NGSI-LD |
| IoT Agent JSON | 4041 / 7896 | Protocolo IoT → NGSI-LD |
| QuantumLeap | 8668 | Persistencia histórica vía suscripciones |
| CrateDB | 4200 | Base de datos de series temporales |
| MongoDB | 27017 | Almacén de entidades de Orion |
| Grafana | 3003 | Dashboards (admin / neptuno2026) |
| nginx (context) | 3004 | Servidor del `@context` JSON-LD |

---

## Stack

- **FIWARE:** Orion-LD 1.5.1, IoT Agent JSON 3.4.0, QuantumLeap 1.0.0
- **Backend:** FastAPI + Python 3.11, httpx, uv
- **Frontend:** SPA vanilla JS — Three.js r128, Leaflet.js 1.9.4, Chart.js 4.4.1
- **IA:** Ollama + Llama 3.1:8b (local), scikit-learn GradientBoosting, YOLOv11 ONNX
- **Datos externos:** MeteoGalicia v5/mgrss (MeteoSIX), Puertos del Estado, INTECMAR
- **Infraestructura:** Docker Compose, CrateDB, MongoDB, Grafana
