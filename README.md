# Damm Smart Truck

Herramienta de optimización logística para rutas de última milla y planificación de carga de camiones, construida para **Interhack BCN 2026**. Simula la distribución de un camión de Estrella Damm por Barcelona, optimizando el orden de ruta, la carga de palés y la recogida de envases retornables.

El sistema tiene tres capas: un **backend** Python que corre los algoritmos de optimización, un **panel web** para gestores que visualiza las rutas resultantes, y una **app móvil** para el conductor con navegación GPS en tiempo real.

---

## Stack tecnológico

| Capa | Tecnología |
|------|-----------|
| Backend | Python, FastAPI, OR-Tools (Google) |
| Panel web | HTML + CSS + JavaScript vanilla |
| App móvil | React Native, Expo, react-native-maps, Three.js |
| Mapas (móvil) | Google Maps Directions API, expo-location |

---

## Estructura del proyecto

```
interhack-2026-damm/
├── backend/
│   ├── main.py                    # FastAPI — endpoints REST
│   ├── pipeline.py                # Orquestador del pipeline completo
│   ├── models/                    # Modelos de dominio
│   │   ├── zona.py                # Zona con tiendas + matriz de distancias
│   │   ├── tienda.py              # Punto de entrega (bar, restaurante, super...)
│   │   ├── pedido.py              # Pedido con líneas de producto
│   │   ├── product.py             # Definición de SKU
│   │   ├── ruta.py                # Ruta con paradas ordenadas
│   │   ├── palet.py               # Palé físico
│   │   └── truck.py               # Tipo de camión y plan de carga
│   ├── solvers/
│   │   ├── orchestrator.py        # run_pipeline() — punto de entrada
│   │   ├── vrptw_solver.py        # Solver VRPTW con OR-Tools
│   │   └── palletizer.py          # Paletizado, retornables, carga del camión
│   └── data/
│       ├── loader.py              # load_zona() — carga los JSON
│       ├── tienda.json            # ~1500 tiendas de Granollers
│       ├── pedido.json            # Pedidos por tienda
│       ├── producto.json          # Catálogo de SKUs
│       └── zona.json              # Definición de zonas
│
├── frontend/
│   └── index.html                 # Panel web (app de una sola página)
│
├── mobile/
│   ├── App.js                     # Raíz de la app — navegación por pestañas
│   ├── metro.config.js            # Configuración del bundler Metro
│   └── src/
│       ├── api.js                 # Cliente HTTP hacia el backend
│       ├── constants.js           # Colores, configs de camión, MOCK_DEPOT
│       ├── screens/
│       │   ├── RouteScreen.js     # Mapa + paradas + navegación GPS
│       │   └── LoadScreen.js      # Visualización 3D del camión + listado
│       ├── components/
│       │   ├── TruckGrid3D.js     # Modelo 3D del camión (Three.js)
│       │   ├── TruckGrid.js       # Vista 2D de la rejilla de palés
│       │   ├── ReportPreviewModal.js  # Modal de previsualización del informe
│       │   ├── MetricsBar.js      # Barra de KPIs
│       │   └── StopsList.js       # Lista de paradas
│       ├── services/
│       │   └── directionsService.js   # Google Directions API
│       └── utils/
│           ├── transform.js       # JSON del backend → objetos internos
│           └── reportGenerator.js # Generación y descarga de informes PDF
│
└── output/
    └── routes/                    # Archivos JSON de rutas generadas
```

---

## Flujo de datos — visión general

```
┌───────────────────────────────────────────────────────┐
│                  PANEL WEB (gestor)                   │
│  1. Selecciona zona                                   │
│  2. Ajusta cajas/palé                                 │
│  3. Pulsa "Optimizar"  ──── POST /api/solve ──────►  │
│                                                       │
│  ◄── rutas + métricas ────────────────────────────── │
│  4. Visualiza rutas, paradas, métricas                │
└───────────────────────────────────────────────────────┘
                          │
               Backend ejecuta pipeline
                          │
┌───────────────────────────────────────────────────────┐
│                APP MÓVIL (conductor)                  │
│  1. Carga ruta asignada                               │
│  2. Pestaña "Ruta": mapa + navegación GPS             │
│  3. Marca paradas como entregadas                     │
│  4. Pestaña "Carga": visualización 3D del camión      │
│  5. Genera informe PDF al finalizar                   │
└───────────────────────────────────────────────────────┘
```

---

## Backend

### API REST — `backend/main.py`

FastAPI corriendo en el puerto 8000. Sirve también el panel web como archivos estáticos.

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/api/zona/list` | Lista de zonas disponibles |
| `GET` | `/api/zona/{zona_id}` | Metadatos de una zona |
| `POST` | `/api/solve` | Ejecuta el pipeline completo de optimización |
| `GET` | `/health` | Health check |

**`POST /api/solve`**
```json
// Request
{ "zona_id": "granollers-center-01", "cajas_por_palet": 60 }

// Response
{
  "zona_id": "granollers-center-01",
  "num_rutas": 3,
  "metrics": { "num_rutas": 3, "total_palets": 8, "coste_total": 450.75, ... },
  "routes": [
    {
      "route": {
        "tipo_camion": "grande",
        "paradas": [
          {
            "orden": 1,
            "llegada_min": 510,
            "coordenadas": { "lat": 41.405, "lon": 2.160 },
            "clientes": [
              {
                "nombre": "Bar Central",
                "total_cajas": 24,
                "productos": [{ "sku": "DAMM-LATA-33", "cantidad_cajas": 12, "tipo_envase": "caja" }]
              }
            ]
          }
        ]
      }
    }
  ]
}
```

### Pipeline de optimización — `backend/solvers/orchestrator.py`

`run_pipeline(zona_id)` ejecuta estas etapas en orden:

1. **Carga de datos** — `load_zona()` hidrata los objetos Zona, Tienda, Pedido desde los JSON
2. **Matriz de distancias** — distancia euclídea entre tiendas (o Google Maps si está disponible)
3. **Clustering** — agrupa tiendas cercanas en Paradas (una parada puede incluir varias tiendas)
4. **VRPTW** — OR-Tools asigna paradas a camiones respetando ventanas horarias y capacidad
5. **Paletizado** — asigna las cajas de cada parada a palés físicos
6. **Retornables** — calcula envases vacíos a recoger, reserva slots traseros
7. **Plan de carga** — mapea palés a los slots del camión respetando restricciones LIFO

**Modelo de tráfico:**

| Franja horaria | Velocidad |
|----------------|-----------|
| 07:00–09:00 | 15 km/h (hora punta) |
| 09:00–13:00 | 25 km/h |
| 13:00–15:00 | 20 km/h (mediodía) |
| Resto | 30 km/h |

**Tipos de camión:**

| Tipo | Slots de palé |
|------|--------------|
| Furgoneta | 3 |
| Mediano | 6 |
| Grande | 8 |

**Geometría del camión (vista desde arriba):**
```
[PUERTA TRASERA]
[ P1 | P2 ]  fila 1  ← primero en descargar  (acceso trasero + lona)
[ P3 | P4 ]  fila 2                           (acceso lona)
[ P5 | P6 ]  fila 3  ← último en descargar   (acceso lona)
[CABINA]
```

---

## Panel web

**Archivo único:** `frontend/index.html` — HTML + CSS + JavaScript vanilla, sin framework ni build step.

**Flujo de uso:**
1. Al cargar la página → `GET /api/zona/list` → renderiza tarjetas de zona
2. El gestor selecciona una zona y ajusta el slider de cajas/palé
3. Al pulsar "Optimizar" → `POST /api/solve` → muestra spinner con mensajes de carga
4. Con la respuesta renderiza: métricas globales, productos por SKU y tarjetas de ruta con paradas

---

## App móvil

React Native + Expo con dos pestañas principales.

### Pestaña Ruta — `RouteScreen.js`

Gestiona la navegación del conductor desde la salida hasta la última entrega.

**Estados de la pantalla:**

| Estado | Descripción |
|--------|-------------|
| `preview` | Vista completa de la ruta en el mapa, antes de salir |
| `navigating` | Navegación activa: mapa centrado en el conductor, distancia a la próxima parada |
| `completed` | Todas las paradas entregadas, opción de generar informe |

**Al pulsar "Iniciar Ruta":**
1. Solicita permisos de ubicación
2. Obtiene la posición GPS actual del conductor (`getCurrentPositionAsync`)
3. Recalcula los tramos de ruta desde esa posición real (Google Directions API)
4. Inicia seguimiento continuo (`watchPositionAsync`) — el mapa sigue al conductor

**Seguimiento GPS:**
- Actualización cada 2 segundos o cada 10 metros de desplazamiento
- `haversineM()` calcula la distancia en tiempo real a la próxima parada

### Pestaña Carga — `LoadScreen.js`

Muestra el plan de carga del camión y el listado de entregas.

- **TruckGrid3D** (Three.js): modelo 3D del camión con los palés coloreados por parada; las entregas realizadas se atenúan
- **Listado de entregas** (panel deslizable): divide las paradas en "Por entregar" y "Entregado", con el conteo de cajas y barriles por cliente

### Generación de informes — `reportGenerator.js`

Al finalizar la ruta, el conductor puede generar un PDF con el resumen de entregas (paradas, cajas, barriles por SKU) y compartirlo vía la hoja de compartir nativa del dispositivo.

---

## Ejecución

**Backend:**
```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000
```

**Panel web:** abrir `frontend/index.html` directamente en el navegador (o servirlo desde FastAPI en `localhost:8000`).

**App móvil:**
```bash
cd mobile
npm install
npx expo start --clear
```

Editar `mobile/src/constants.js` → `BASE_URL` con la IP local del servidor backend.
