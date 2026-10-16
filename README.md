# Sismo Platform

Plataforma modular para monitoreo de eventos sísmicos observados, análisis y trazabilidad. En esta primera fase se entrega la base técnica y un prototipo navegable; todavía no hay una fuente sísmica conectada y no se presentan estimaciones ni alertas como información oficial.

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

Las sesiones usan cookies `HttpOnly`, `SameSite=Strict`, tokens CSRF de doble envío y tokens firmados de duración limitada. En producción define una `JWT_SECRET_KEY` única de al menos 32 caracteres y activa `SESSION_COOKIE_SECURE=true` detrás de HTTPS.

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
- La Fase 3 consulta `https://ultimosismo.igp.gob.pe/api/ultimo-sismo`, que entrega un único evento reciente. No es un feed histórico; sincronizarlo periódicamente solo conserva los eventos que el proveedor publique entre consultas. Confirmar términos de uso y disponibilidad de un catálogo histórico con el IGP antes de producción.
- Las gráficas, el mapa y los indicadores con datos reales pertenecen a la Fase 4. El sistema no predice terremotos y separa eventos observados de estimaciones experimentales y alertas oficiales.

## Ingesta y catálogo

Con una cuenta administradora creada y una sesión abierta, la sección **Fuentes de datos** permite lanzar la sincronización manual del IGP. Cada ejecución registra estado, fecha, filas observadas, insertadas, actualizadas y duplicadas. Los eventos se deduplican por fuente e identificador externo; los cambios del proveedor actualizan el registro conservando la huella del payload actual.

La API expone `GET /api/v1/events` con filtros `start_date`, `end_date`, `min_magnitude`, `max_magnitude`, `source_key`, `limit` y `offset`; `GET /api/v1/events/{id}` consulta el detalle. La consulta requiere el permiso `events:read`. `GET /api/v1/sources` requiere `sources:read`; `POST /api/v1/sources/{id}/sync` requiere `sources:manage` y CSRF.