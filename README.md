# NEPTUNO — Smart Coastal Intelligence

Plataforma de monitorización costera en tiempo real para 12 playas de A Coruña (Galicia). Construida sobre el ecosistema FIWARE con entidades NGSI-LD y Smart Data Models oficiales.

---

## Prerequisitos

| Herramienta | Version minima | Instalacion |
|-------------|---------------|-------------|
| Docker + Docker Compose | Docker 24+ | https://docs.docker.com/get-docker/ |
| Python | 3.11+ | https://python.org |
| uv | cualquiera | `curl -Lsf https://astral.sh/uv/install.sh \| sh` |
| Ollama | cualquiera | https://ollama.com |

---

## Arranque completo (orden obligatorio)

### Paso 1 — Infraestructura FIWARE

```bash
docker-compose up -d
```

Espera ~30 segundos a que Orion-LD este healthy:

```bash
docker-compose ps   # todos deben estar "Up"
curl http://localhost:1026/ngsi-ld/v1/entities -H "NGSILD-Tenant: smartbeach"
# debe devolver [] (array vacio, no error)
```

### Paso 2 — Variables de entorno

Copia y edita el fichero de configuracion:

```bash
cp .env.example .env   # si existe; si no, el .env ya esta creado
```

Valores minimos que debes rellenar (ver seccion **Credenciales** mas abajo):

```
GF_SECURITY_ADMIN_PASSWORD=TU_PASSWORD_GRAFANA
IOT_API_KEY=TU_CLAVE_IOT_INTERNA
```

### Paso 3 — Inicializar Orion-LD

Registra los 12 servicios IoT, los 12 dispositivos buoy, y las 12 entidades Beach en Orion:

```bash
uv run python init/init_orion.py
```

Salida esperada: `Initialization complete — 12 beaches registered`.

### Paso 4 — Crear subscripciones a QuantumLeap

```bash
uv run python subscriptions/create_subscriptions.py
```

Salida esperada: `6 subscriptions created`.

### Paso 5 — Simulador de datos (en segundo plano)

```bash
uv run python simulator/simulator.py &
```

El simulador intenta datos reales de MeteoGalicia/INTECMAR/Puertos del Estado. Si fallan, usa datos simulados realistas. Logs: `[SEA REAL] Riazor` o `[SEA SIM] Riazor`.

### Paso 6 — Backend FastAPI

```bash
uv run fastapi dev backend/main.py --port 8000
```

El frontend se sirve en `http://localhost:8000`.

### Paso 7 — Ollama (asistente IA)

Una sola vez, descarga el modelo (3-5 GB):

```bash
ollama pull llama3.1:8b
```

Arrancar el servidor Ollama (si no arranca automaticamente al instalar):

```bash
ollama serve
```

Verificar: `curl http://localhost:11434/api/tags` debe devolver el modelo.

### Paso 8 — (Opcional) Modelo ML de calidad del agua

```bash
uv run python ml/train.py     # entrena con datos de CrateDB (necesita datos en QuantumLeap)
uv run python ml/predict.py   # genera entidades WaterQualityPredicted en Orion
```

---

## Que deberia verse

| Vista | URL | Descripcion |
|-------|-----|-------------|
| **Globo** | `http://localhost:8000/#globe` | Globo 3D con 12 markers coloreados por estado. Panel lateral con lista de playas. |
| **Playa** | Click en marker o card | Tarjetas de condicion (temperatura, olas, viento, E.coli, UV, ocupacion). Mapa Leaflet. 4 graficas históricas/prediccion. |
| **Asistente** | `http://localhost:8000/#chat` | Chat en lenguaje natural con Llama 3.1. Responde sobre condiciones de las playas en tiempo real. |
| **Alertas** | `http://localhost:8000/#alerts` | Alertas activas desde Orion (IoT, ML, CV). Actualizadas cada 30s. |
| **Grafana** | `http://localhost:3003` | Dashboards de series temporales en CrateDB. |
| **Orion** | `http://localhost:1026` | API NGSI-LD directa. |

---

## Servicios Docker

| Servicio | Puerto | Descripcion |
|----------|--------|-------------|
| MongoDB | 27017 | Backend de Orion-LD |
| Orion-LD | 1026 | Context Broker NGSI-LD |
| IoT Agent JSON | 4041 (north) / 7896 (south) | Traduce JSON IoT a NGSI-LD |
| CrateDB | 4200 | Base de datos de series temporales |
| QuantumLeap | 8668 | Histórico de entidades Orion |
| Grafana | 3003 | Dashboards |
| nginx (context) | 8080 | Sirve el @context JSONLD |

---

## Credenciales

### Que debes definir tu (sin coste, sin registro externo)

| Variable en `.env` | Para que | Como elegirla |
|--------------------|----------|---------------|
| `GF_SECURITY_ADMIN_PASSWORD` | Login de Grafana (`admin` / tu_password) | Cualquier string seguro, ej. `neptuno2026!` |
| `IOT_API_KEY` | Clave compartida entre el simulador y el IoT Agent | Cualquier string, ej. `neptuno-smartbeach-2026` |
| `POSTGRES_PASSWORD` | No se usa directamente (CrateDB no usa Postgres) | Puedes dejarlo como esta |

### API keys externas (opcionales — el sistema funciona sin ellas)

| API | Como obtenerla | Donde ponerla |
|-----|---------------|---------------|
| **MeteoGalicia** | Envia un correo a `sistemas@meteogalicia.gal` solicitando acceso a la API v4 de observaciones y predicciones. Indica que es para investigacion academica. Tiempo de respuesta: 1-5 dias habiles. | `.env` → `METEOGALICIA_API_KEY=tu_clave` |
| **INTECMAR** | API publica, no requiere key. Los endpoints pueden fallar ocasionalmente. | No aplica |
| **Puertos del Estado** | API publica, no requiere key. | No aplica |
| **AEMET** | Registro gratuito en https://opendata.aemet.es/centrodedescargas/altaUsuario | No usado actualmente, disponible para extension |

> **Sin API keys:** el simulador detecta automaticamente los fallos de las APIs externas y genera datos simulados realistas (con ruido gaussiano y patrones diurnos/estacionales). El sistema es completamente funcional en modo simulacion.

---

## Smart Data Models utilizados

Todos conformes con https://smartdatamodels.org:

| Tipo de entidad | Smart Data Model | Namespace |
|----------------|-----------------|-----------|
| `Beach` | Smart-Cities/Beach | `https://smartdatamodels.org/dataModel.Beach/Beach` |
| `PointOfInterest` | Smart-Cities/PointOfInterest | `https://smartdatamodels.org/dataModel.PointOfInterest/PointOfInterest` |
| `SeaConditions` | Environment/SeaConditions | `https://smartdatamodels.org/dataModel.Environment/SeaConditions` |
| `WeatherObserved` | Weather/WeatherObserved | `https://smartdatamodels.org/dataModel.Weather/WeatherObserved` |
| `WeatherForecast` | Weather/WeatherForecast | `https://smartdatamodels.org/dataModel.Weather/WeatherForecast` |
| `WeatherAlert` | Weather/WeatherAlert | `https://smartdatamodels.org/dataModel.Weather/WeatherAlert` |
| `WaterQualityObserved` | Environment/WaterQualityObserved | `https://smartdatamodels.org/dataModel.WaterQuality/WaterQualityObserved` |
| `WaterQualityPredicted` | Environment/WaterQualityPredicted | — |
| `Device` | Device/Device | `https://smartdatamodels.org/dataModel.Device/Device` |

Relaciones entre entidades via `refPointOfInterest`, `refDevice`, `refBeach` (NGSI-LD `Relationship`).

---

## Verificacion rapida

```bash
# 12 playas registradas en Orion
curl -s "http://localhost:1026/ngsi-ld/v1/entities?type=Beach&limit=12" \
  -H "NGSILD-Tenant: smartbeach" | python3 -m json.tool | grep '"id"'

# Datos historicos en QuantumLeap
curl -s "http://localhost:8668/v2/entities?type=SeaConditions" \
  -H "Fiware-Service: smartbeach" | python3 -m json.tool

# Backend respondiendo
curl http://localhost:8000/api/health

# Ollama activo
curl http://localhost:11434/api/tags
```

---

## Troubleshooting

| Sintoma | Causa probable | Solucion |
|---------|---------------|----------|
| El globo esta vacio, sin markers | Orion no tiene playas | Ejecutar `init/init_orion.py` |
| El chat responde "Ollama no disponible" | Ollama no esta corriendo | `ollama serve` en otra terminal |
| Las graficas muestran datos demo | QuantumLeap sin historial | Esperar al menos 1 ciclo del simulador (~2 min) |
| Grafana muestra "No data" | CrateDB vacio o subscripciones no creadas | Ejecutar `subscriptions/create_subscriptions.py` y esperar datos del simulador |
| `init_orion.py` falla con 409 | Entidades ya existen | Normal en segunda ejecucion; los 409 son ignorados |
| `simulator.py` muestra `[SIM]` en todos los logs | APIs externas no responden | Correcto; el sistema usa datos simulados automaticamente |
| Puerto 1026 ocupado | Otro proceso o instancia | `docker-compose down && docker-compose up -d` |

---

## Stack tecnologico

- **FIWARE**: Orion-LD Context Broker, IoT Agent for JSON, QuantumLeap
- **Base de datos**: MongoDB (Orion), CrateDB (series temporales)
- **Backend**: FastAPI (Python 3.11+), uv
- **Frontend**: HTML5 SPA, Three.js r128, Leaflet.js 1.9.4, Chart.js 4.4.1
- **IA**: Ollama + Llama 3.1:8b (local, sin cloud)
- **Datos externos**: MeteoGalicia v4, INTECMAR, Puertos del Estado, Xunta Open Data
- **Visualizacion**: Grafana + CrateDB datasource
- **Infraestructura**: Docker Compose

---

*NEPTUNO v1.0 · UDC XDEI 2026 · Nicolás Aller*
