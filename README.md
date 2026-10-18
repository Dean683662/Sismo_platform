# Sismo Platform

Plataforma modular para monitoreo de eventos sísmicos observados, análisis y trazabilidad. Incluye una integración con el endpoint de último evento del IGP, alertas internas o por webhook, reportes reproducibles, administración por roles y retención controlada. Las alertas y los modelos experimentales no son avisos oficiales ni predicen sismos futuros.

## Requisitos

- Docker y Docker Compose para ejecutar el entorno completo.
- Node.js 22+ y Python 3.12+ para desarrollo local.

## Entorno completo

1. Copiar `.env.example` a `.env`. Las credenciales incluidas son solo para desarrollo local; cambiarlas antes de exponer el entorno.
2. Desde la raíz del repositorio, ejecutar `docker compose -f infra/docker-compose.yml up --build`.
3. Abrir `http://localhost:8080`; la API queda disponible en `http://localhost:8000` y su documentación OpenAPI en `/docs`.

Compose espera a que PostgreSQL esté saludable, aplica las migraciones Alembic y luego inicia la API. Nginx sirve la SPA y reenvía `/api` y `/health` al backend.

### Crear el primer administrador

No existe una cuenta ni contraseña predeterminada. Configura `BOOTSTRAP_ADMIN_EMAIL` y `BOOTSTRAP_ADMIN_PASSWORD` en `.env` (mínimo 12 caracteres) y, con Compose en ejecución, crea la cuenta una sola vez:

```bash
docker compose -f infra/docker-compose.yml exec api python -m backend.services.bootstrap_admin
```

Para desarrollo local, con `DATABASE_URL` configurada y migraciones aplicadas, ejecuta `python -m backend.services.bootstrap_admin`.

### Supabase PostgreSQL con Session Pooler

1. En Supabase, abre **Connect → Session pooler** y copia sus datos de conexión: host `*.pooler.supabase.com`, puerto `5432`, base de datos `postgres`, usuario del pooler y contraseña del proyecto.
2. Coloca esos cinco valores en `DB_HOST`, `DB_PORT`, `DB_DATABASE`, `DB_USERNAME` y `DB_PASSWORD` en tu `.env` local o en el gestor de secretos del despliegue. No necesitas construir ni codificar una URI; la contraseña se maneja separada. No compartas esos valores ni los pongas en el frontend o en el repositorio.
3. El backend construye la URL con el driver `psycopg`, exige TLS y prioriza el conjunto completo de `DB_*` sobre `SUPABASE_DATABASE_URL` y `DATABASE_URL`. `SUPABASE_DATABASE_URL` queda como alternativa opcional si prefieres una URI. El pool SQLAlchemy predeterminado es de 5 conexiones sin overflow, con pre-ping y reciclaje cada 30 minutos. Ajusta `DB_POOL_SIZE`, `DB_POOL_TIMEOUT` y `DB_POOL_RECYCLE_SECONDS` según los límites del proyecto Supabase y el número de réplicas.
4. Antes del primer arranque, aplica el esquema **una sola vez** con `alembic upgrade head` desde la raíz. Como alternativa para una base nueva, puedes ejecutar [backend/database/supabase_schema.sql](backend/database/supabase_schema.sql) en Supabase SQL Editor y luego sincronizar el marcador con `alembic stamp head`. No ejecutes el SQL de inicialización y `alembic upgrade head` sobre la misma base sin marcar la revisión: las tablas ya existirían.
5. Comprueba la conexión con `GET /ready`. Las migraciones y la aplicación usan el mismo Session Pooler URL.

El Session Pooler usa el puerto `5432`; el Transaction Pooler del puerto `6543` no pasa la validación de configuración de esta integración. Solo configura los cinco `DB_*` en conjunto, no parcialmente. Las credenciales son secretos de servidor. Supabase Auth/RLS no reemplaza los permisos de la API: la aplicación mantiene su login y roles propios. Las variables `POSTGRES_*` son solo para el contenedor PostgreSQL local de Docker y no son necesarias para conectarse a Supabase.

Las sesiones usan cookies `HttpOnly`, `SameSite=Strict`, tokens CSRF de doble envío y tokens firmados de duración limitada. En producción define una `JWT_SECRET_KEY` única de al menos 32 caracteres y activa `SESSION_COOKIE_SECURE=true` detrás de HTTPS. La migración Supabase también activa RLS sin políticas para las tablas de la aplicación; el backend opera mediante su conexión PostgreSQL de servidor y el navegador no debe acceder directamente al Data API.

## Desarrollo local

Backend, desde la raíz:

```bash
python -m pip install -r backend/requirements.txt
python -m uvicorn backend.main:app --reload
```

Frontend, desde la raíz:

```bash
npm --prefix frontend install
npm --prefix frontend run dev
```

Vite reenvía `/api` y `/health` a `http://localhost:8000`. Para migraciones locales, configurar `DATABASE_URL` en `.env` y ejecutar `alembic upgrade head` desde la raíz.

## Verificación

```bash
python -m pytest tests/backend
npm --prefix frontend run build
```

La integración CI ejecuta ambas verificaciones para cada push y pull request.

## Estado de alcance

- Fase 1: base FastAPI, configuración, interfaz navegable, PostgreSQL, migración inicial, contenedores y CI.
- Fase 2: sesiones seguras, roles de mínimo privilegio, gestión de usuarios protegida y bitácora de acciones críticas implementadas.
- Fase 3: conector IGP verificado, normalización, deduplicación, registro de ejecuciones, catálogo filtrable y procedencia de eventos.
- La Fase 3 consulta el último evento publicado por el IGP y permite importar manualmente su catálogo histórico oficial (1471–1959) desde el [portal de datos sísmicos](https://ultimosismo.igp.gob.pe/repositorio/datos-sismicos). El backfill es idempotente, auditable y no genera alertas retroactivas; los registros sin campos obligatorios se omiten y contabilizan. Confirmar términos de uso y disponibilidad con el IGP antes de producción.
- Fase 4: resumen operativo, series temporales, distribuciones descriptivas, dispersión magnitud/profundidad y mapa GeoJSON/Leaflet con filtros por periodo.
- Fase 5: snapshots inmutables de eventos, numeración de versiones e informe de filas válidas, inválidas, duplicados y valores faltantes.
- Fase 6: regresión y clasificación descriptiva de magnitudes ya reportadas; evaluación cronológica, comparación con baselines, matriz de confusión y metadatos reproducibles de librerías. No predice eventos futuros.
- Fase 7: reglas de umbral/zona/fuente, aprobación humana opcional, bandeja interna o webhook HTTPS, deduplicación, intentos acotados, pruebas e historial auditado.
- Fase 8: snapshots reproducibles de eventos, modelos, fuentes, alertas y calidad de datasets; exportación CSV/JSON/XLSX/PDF, administración de retención, usuarios y permisos RBAC.
- Fase 9: controles de seguridad del navegador, liveness/readiness, pruebas de integración, CI de build y guía de despliegue, respaldo, restauración y aceptación.
- El baseline es didáctico y no predice terremotos futuros. La importación histórica amplía los datos disponibles para análisis, pero no convierte los modelos experimentales en predictores de sismos.

## Analítica y experimentos

Las rutas nuevas requieren sesión autenticada y permisos RBAC. Crear datasets y entrenar modelos también requiere CSRF; los roles `administrator` y `analyst` tienen permisos de gestión del laboratorio.

- `GET /api/v1/dashboard/summary`: total de eventos, actividad de 24 horas y estado resumido de fuentes.
- `GET /api/v1/analytics/timeseries`: conteos diarios/semanales con filtros de fechas y magnitud.
- `GET /api/v1/events/geojson`: puntos GeoJSON de eventos observados, con límite de 5.000.
- `POST /api/v1/datasets`: crea una versión nueva del snapshot filtrado, máximo 50.000 filas.
- `GET /api/v1/datasets` y `GET /api/v1/datasets/{id}/quality`: catálogo de snapshots e informe de calidad.
- `POST /api/v1/ml/experiments`: entrena/evalúa un baseline sobre una versión inmutable; requiere al menos cinco eventos válidos.
- `GET /api/v1/ml/experiments` y `GET /api/v1/ml/experiments/{id}`: historial de métricas, features, objetivo y periodo de validación.

Aplicar el esquema con `alembic upgrade head` después de configurar `DATABASE_URL`.

## Ingesta y catálogo

Con una cuenta administradora creada y una sesión abierta, la sección **Fuentes de datos** permite lanzar la sincronización manual del IGP. Cada ejecución registra estado, fecha, filas observadas, insertadas, actualizadas y duplicadas. Los eventos se deduplican por fuente e identificador externo; los cambios del proveedor actualizan el registro conservando la huella del payload actual.

La API expone `GET /api/v1/events` con filtros `start_date`, `end_date`, `min_magnitude`, `max_magnitude`, `source_key`, `limit` y `offset`; `GET /api/v1/events/{id}` consulta el detalle. La consulta requiere el permiso `events:read`. `GET /api/v1/sources` requiere `sources:read`; `POST /api/v1/sources/{id}/sync` requiere `sources:manage` y CSRF.

## Fases 7–9: alertas, reportes y operación

- **Alertas:** crea umbrales por magnitud/profundidad, fuentes verificadas y zona rectangular; configura una plantilla validada y aprobación humana opcional. Los eventos nuevos se evalúan durante la ingesta. La bandeja interna conserva estado, fuente, evento, intentos y auditoría; las pruebas usan un evento real reciente. Se deduplica por regla, fuente e identificador externo del evento. Solo está implementado el canal interno: no se envían correos ni webhooks.
- **Reportes:** crea snapshots inmutables de eventos, modelos, fuentes, alertas o calidad de datasets, guarda filtros y fecha de corte y exporta el mismo contenido en CSV, JSON, XLSX o PDF. Las exportaciones tabulares protegen celdas que podrían interpretarse como fórmulas.
- **Webhook:** configura `ALERT_WEBHOOK_URL` en el entorno privado de la API (HTTPS obligatorio en producción; HTTP solo para localhost en desarrollo). El destino recibe JSON con `Idempotency-Key`; sus errores no contienen ni registran la URL. Se aplican hasta tres intentos acumulados y la cola ingresa en el historial. No configure esta URL en Vite ni la envíe al navegador.
- **Administración:** la configuración de retención tiene límites validados. La limpieza manual elimina auditoría, snapshots y entregas terminales vencidas; conserva eventos, datasets y aprobaciones pendientes. La gestión de usuarios y la bitácora requieren los permisos existentes.
- **Seguridad y operación:** `/health` verifica vida del proceso y `/ready` comprueba conexión a la base; Compose usa readiness. La SPA y la API añaden cabeceras de seguridad; las sesiones de producción exigen una clave JWT propia y cookies seguras.

Aplicar la revisión de esquema con `alembic upgrade head`. Para procedimientos de despliegue, backup/restauración, monitorización, comprobación accesible y criterios de aceptación, consulta [docs/operations.md](docs/operations.md). La Fase 9 requiere completar la restauración y la prueba de aceptación en el entorno de despliegue real antes de declarar una versión candidata.