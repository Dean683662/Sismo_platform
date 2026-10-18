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

El cuerpo de entrenamiento acepta `name`, `dataset_id`, `test_fraction` (0.1–0.5, por defecto 0.2) y `task_type` (`regression` o `classification`). La regresión requiere cinco eventos válidos y compara MAE/RMSE/R² con un baseline de media. La clasificación requiere diez eventos y al menos dos ejemplos por cada banda (`low`, `moderate`, `high`) en el bloque cronológico de entrenamiento; devuelve accuracy, métricas macro, baseline mayoritario y matriz de confusión. Ambas tareas usan latitud, longitud y profundidad para analizar magnitudes ya reportadas; no predicen terremotos futuros ni son una alerta oficial. Se registran semilla y versiones de NumPy, pandas y scikit-learn.

## Centro de alertas

Todas las rutas requieren sesión. Los cambios exigen `alerts:manage` y `X-CSRF-Token`; la consulta requiere `alerts:read`.

| Método y ruta | Descripción |
| --- | --- |
| `GET /api/v1/alerts/rules` | Lista reglas, umbrales, región, fuentes, canal y aprobación. |
| `POST /api/v1/alerts/rules` | Crea una regla. Acepta `name`, `min_magnitude`, `min_depth_km`, `region_bounds`, `source_ids`, `channel=in_app|webhook`, `requires_approval`, `template` e `is_enabled`. Para `webhook`, configura `ALERT_WEBHOOK_URL` en el entorno privado de la API. |
| `PATCH /api/v1/alerts/rules/{id}` | Actualiza los campos enviados; desactiva reglas al pausarlas sin borrar su historial. |
| `POST /api/v1/alerts/rules/{id}/test` | Envía una prueba por el canal seleccionado, asociada al último evento de una fuente verificada activa. Requiere que exista ese evento. |
| `GET /api/v1/alerts/deliveries` | Historial paginado; admite `status` (`queued`, `pending_approval`, `delivered`, `rejected`, `failed`), `rule_id`, `limit` y `offset`. |
| `POST /api/v1/alerts/deliveries/{id}/approve` | Aprueba y entrega una alerta pendiente. |
| `POST /api/v1/alerts/deliveries/{id}/reject` | Rechaza y audita una alerta pendiente. |
| `POST /api/v1/alerts/deliveries/{id}/retry` | Reintenta manualmente una entrega fallida hasta tres intentos. |

Los campos permitidos para plantillas son `{magnitude}`, `{place}`, `{occurred_at}` y `{source_name}`. La detección automática evalúa los eventos nuevos recibidos de fuentes verificadas activas y usa una clave única por regla/fuente/evento para deduplicar. El webhook recibe un `POST` JSON con `delivery_id`, `deduplication_key`, regla, evento, mensaje e indicador de prueba; también recibe el encabezado `Idempotency-Key` (SHA-256 de la clave). El timeout es de cinco segundos por defecto, configurable entre 1 y 30. Las entregas empiezan en `queued`, luego quedan `delivered` o `failed`; se permiten hasta tres intentos acumulados, incluidos los reintentos manuales.

## Reportes, configuración y operación

| Método y ruta | Permiso | Descripción |
| --- | --- | --- |
| `POST /api/v1/reports` | `reports:read` + CSRF | Genera una instantánea inmutable. Tipos: `events`, `models`, `sources`, `alerts`, `quality`; admite intervalo temporal y filtros de magnitud/fuente para eventos; máximo 50.000 filas (por defecto 5.000). |
| `GET /api/v1/reports` | `reports:read` | Lista las últimas 100 ejecuciones (límite configurable hasta 500). |
| `GET /api/v1/reports/{id}/export?format=csv|json|xlsx|pdf` | `reports:read` | Exporta el snapshot inmutable; las descargas quedan auditadas y preservan el solicitante y corte temporal. |
| `GET /api/v1/admin/settings` | `settings:manage` | Consulta retención de auditoría e historial de alertas. |
| `PATCH /api/v1/admin/settings` | `settings:manage` + CSRF | Establece auditoría/reportes entre 30 y 3.650 días e historial de alertas entre 7 y 3.650 días. |
| `POST /api/v1/admin/retention/run` | `settings:manage` + CSRF | Limpia auditoría, snapshots de reportes y entregas terminales vencidas; conserva eventos, datasets y entregas pendientes. La ejecución es manual. |
| `GET /health` | Público | Liveness del proceso API. |
| `GET /ready` | Público | Readiness con comprobación de conexión a la base; responde 503 si no está disponible. |

Los snapshots guardan los filtros y `cutoff_at` junto a las filas exportadas; volver a descargar un reporte no vuelve a consultar ni altera datos.

## Conexión PostgreSQL Supabase

Configura los cinco valores `DB_HOST`, `DB_PORT`, `DB_DATABASE`, `DB_USERNAME` y `DB_PASSWORD` que entrega Supabase para **Session Pooler**; el host debe terminar en `.pooler.supabase.com` y el puerto debe ser `5432`. La aplicación arma la URL PostgreSQL de manera segura sin pedir concatenar ni codificar la contraseña, fuerza TLS y usa `postgresql+psycopg`. Los cinco campos deben estar definidos a la vez. Este formato tiene prioridad sobre `SUPABASE_DATABASE_URL` (URI alternativa opcional) y `DATABASE_URL`. El pool SQLAlchemy se limita con `DB_POOL_SIZE`, `DB_POOL_TIMEOUT` y `DB_POOL_RECYCLE_SECONDS`. El Transaction Pooler del puerto `6543` no está habilitado por esta configuración.

La revisión actual activa Row Level Security sin políticas para las tablas de la aplicación, bloqueando el acceso del Data API a los roles cliente predeterminados. El backend sigue usando su conexión PostgreSQL de servidor. No conectes el frontend directamente con la clave `service_role` ni publiques credenciales.

Para inicializar una base vacía, aplica `alembic upgrade head` o ejecuta `backend/database/supabase_schema.sql` en Supabase SQL Editor (una sola vía). Si usaste el SQL, ejecuta después `alembic stamp head` para que futuras migraciones partan de la revisión correcta. La cadena de conexión es un secreto de servidor; el frontend no debe conectarse directamente a PostgreSQL.