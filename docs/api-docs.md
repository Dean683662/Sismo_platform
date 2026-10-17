# API REST v1

Todos los endpoints funcionales requieren una sesión autenticada. Las operaciones `POST` requieren además el encabezado `X-CSRF-Token` leído de la cookie `sismo_csrf`. El control de permisos se aplica en el backend.

## Eventos y analítica

| Método y ruta | Permiso | Descripción |
| --- | --- | --- |
| `GET /api/v1/events` | `events:read` | Catálogo con filtros y paginación. |
| `GET /api/v1/events/{id}` | `events:read` | Detalle de un evento. |
| `GET /api/v1/events/geojson` | `events:read` | FeatureCollection de puntos observados; máximo 5.000. |
| `GET /api/v1/dashboard/summary` | `analytics:read` | Totales y estado de fuentes. |
| `GET /api/v1/analytics/timeseries` | `analytics:read` | Conteo por día o semana; máximo 50.000 eventos por solicitud. |

Filtros temporales: `start_date`, `end_date`; magnitud: `min_magnitude`, `max_magnitude`; agrupación: `group_by=day|week`.

## Calidad y datasets

| Método y ruta | Permiso | Descripción |
| --- | --- | --- |
| `POST /api/v1/datasets` | `datasets:manage` | Crea un snapshot versionado y su informe de calidad. |
| `GET /api/v1/datasets` | `analytics:read` | Lista las últimas 100 versiones. |
| `GET /api/v1/datasets/{id}/quality` | `analytics:read` | Recupera el informe asociado. |

El cuerpo de creación acepta `name`, `start_date`, `end_date`, `min_magnitude` y `max_magnitude`. Cada versión conserva la selección y los registros válidos usados por el experimento; se limita a 50.000 filas.

## Machine Learning

| Método y ruta | Permiso | Descripción |
| --- | --- | --- |
| `POST /api/v1/ml/experiments` | `models:manage` | Ejecuta la regresión lineal baseline con una partición cronológica. |
| `GET /api/v1/ml/experiments` | `models:read` | Lista los últimos 100 experimentos. |
| `GET /api/v1/ml/experiments/{id}` | `models:read` | Consulta métricas, variables y periodos de validación. |

El cuerpo de entrenamiento acepta `name`, `dataset_id` y `test_fraction` (0.1–0.5, por defecto 0.2). Requiere cinco eventos válidos como mínimo. Features: latitud, longitud y profundidad; target: magnitud ya reportada. Métricas: MAE, RMSE y R². El resultado incluye la limitación explícita de que no predice terremotos futuros ni es una alerta oficial.