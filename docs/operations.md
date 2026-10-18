# Manual técnico, despliegue y recuperación

## Alcance y límites operativos

- La integración verificada del IGP ofrece la consulta del último evento y una importación del catálogo histórico oficial (1471–1959) desde el [portal de datos sísmicos](https://ultimosismo.igp.gob.pe/repositorio/datos-sismicos). Confirma disponibilidad, licencia y condiciones de uso antes de producción. El backfill es manual, idempotente y no emite alertas retroactivas.
- Las reglas pueden entregar a la bandeja interna o al `ALERT_WEBHOOK_URL` configurado en el servidor. En producción, el destino debe usar HTTPS. Se generan al ingresar un evento nuevo de una fuente verificada activa; las aprobaciones, reintentos y cambios quedan en auditoría. El webhook no debe usarse como sistema de alerta oficial a la población.
- Los reportes guardan snapshots inmutables sujetos a retención manual. La limpieza elimina auditoría, entregas terminales y snapshots vencidos; conserva eventos, datasets y entregas pendientes.
- Los modelos incluidos son experimentales y no predicen sismos futuros.

## Configuración y despliegue

1. Mantén secretos en el gestor de secretos del entorno. Para `APP_ENV=production`, configura una `JWT_SECRET_KEY` única de al menos 32 caracteres, `SESSION_COOKIE_SECURE=true`, una contraseña PostgreSQL no predeterminada y orígenes CORS explícitos.
2. Para Supabase, configura los cinco valores de **Session Pooler** del panel en `DB_HOST`, `DB_PORT`, `DB_DATABASE`, `DB_USERNAME` y `DB_PASSWORD` (host `*.pooler.supabase.com`, puerto `5432`). La aplicación ensambla la conexión de forma segura, usa `postgresql+psycopg`, exige TLS y limita cada proceso a cinco conexiones SQLAlchemy sin overflow. Dimensiona `DB_POOL_SIZE` según `pool_size × réplicas` y el límite de conexiones de Supabase. También se admite `SUPABASE_DATABASE_URL` como alternativa opcional, pero no configures ambos formatos a medias. No incluyas credenciales en imágenes, navegador ni logs. La migración activa RLS sin políticas de cliente en las tablas de la aplicación: usa la conexión privada del backend para las operaciones normales.
3. Termina TLS en un proxy confiable antes de exponer la plataforma. No publiques PostgreSQL ni la API directamente a Internet; limita el puerto de base de datos a la red de operación.
4. Revisa cambios de esquema y toma un backup antes de desplegar. Compose aplica `alembic upgrade head` al iniciar la API.
5. Despliega y comprueba:

   ```powershell
   docker compose -f infra/docker-compose.yml up --build -d
   docker compose -f infra/docker-compose.yml ps
   Invoke-RestMethod http://localhost:8080/health
   Invoke-RestMethod http://localhost:8080/ready
   ```

6. Para importar el catálogo histórico, entra en **Fuentes de datos** con un usuario que tenga `sources:manage` y selecciona **Importar catálogo histórico** en la fuente IGP verificada. El proceso consulta el XLSX oficial, crea una ejecución auditable y conserva el historial de registros insertados, actualizados, duplicados y omitidos por datos obligatorios incompletos; no genera entregas de alertas por eventos pasados.

7. Revisa `docker compose -f infra/docker-compose.yml logs --tail 200 api web db`. No compartas ni archives logs que contengan datos personales o secretos.

Para una base nueva, el esquema también está en [../backend/database/supabase_schema.sql](../backend/database/supabase_schema.sql). Elige un único método: Alembic o SQL Editor. Si inicializas manualmente con el script, ejecuta `alembic stamp head` antes de dejar que la aplicación gestione revisiones posteriores.

`/health` confirma que el proceso vive. `/ready` prueba la base; Compose no considera sana a la API hasta que responde readiness. El backend agrega cabeceras de seguridad y HSTS en producción; Nginx añade CSP, protección de framing y políticas de navegador para la SPA.

## Backup y restauración PostgreSQL

Los comandos siguientes preservan el archivo binario en Windows evitando la redirección de salida de PowerShell. Guarda backups cifrados fuera del repositorio, aplica controles de acceso y verifica periódicamente su restauración.

### Crear y verificar un backup

```powershell
$compose = "infra/docker-compose.yml"
$container = docker compose -f $compose ps -q db
if (-not $container) { throw "El contenedor de PostgreSQL no está activo." }
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backup = "sismo-$stamp.dump"
docker compose -f $compose exec -T db sh -c 'pg_dump -Fc -U "$POSTGRES_USER" "$POSTGRES_DB" -f /tmp/sismo-backup.dump'
if ($LASTEXITCODE -ne 0) { throw "Falló pg_dump." }
docker compose -f $compose exec -T db pg_restore --list /tmp/sismo-backup.dump
if ($LASTEXITCODE -ne 0) { throw "El archivo generado no pasó la verificación de pg_restore." }
docker cp "${container}:/tmp/sismo-backup.dump" $backup
if ($LASTEXITCODE -ne 0) { throw "No se pudo copiar el backup al host." }
docker compose -f $compose exec -T db rm -f /tmp/sismo-backup.dump
if ($LASTEXITCODE -ne 0) { throw "No se pudo limpiar el archivo temporal del contenedor." }
```

`pg_restore --list` se ejecuta dentro del contenedor sobre el archivo temporal antes de retirarlo del contenedor.

### Restaurar sin sobrescribir producción

1. Detén escrituras y verifica que existe un backup íntegro y descifrable.
2. Crea una instancia o base **aislada** para recuperación; no ejecutes `pg_restore --clean` contra la base activa.
3. Copia el dump al contenedor aislado con `docker cp <archivo.dump> <contenedor>:/tmp/sismo-restore.dump`.
4. Restaura sobre una base vacía: `docker compose exec -T db sh -c 'pg_restore --no-owner -U "$POSTGRES_USER" -d "$POSTGRES_DB" /tmp/sismo-restore.dump'`. Sustituye `db` y los valores de conexión por los del entorno aislado.
5. Ejecuta `alembic upgrade head`, comprueba `/ready`, usuarios/roles, eventos, fuentes, alertas, reportes y auditoría; valida conteos y procedencia contra el backup.
6. Cambia tráfico a la instancia recuperada solo tras la aceptación del responsable. Registra alcance, punto de recuperación, hora y resultado de la prueba.

Define RPO/RTO, frecuencia/cifrado de backups y responsables con operaciones antes de producción; no se fijan aquí porque dependen del servicio objetivo. La restauración debe ensayarse antes de declarar candidata la versión.

## Pruebas y aceptación

Desde la raíz del repositorio:

```powershell
python -m pytest tests/backend
npm --prefix frontend run build
npm --prefix frontend run test:e2e
.\scripts\check-health.ps1 -BaseUrl http://localhost:8080
.\scripts\verify-postgres-restore.ps1
```

El runner E2E crea una base SQLite temporal aislada, un administrador y un evento sintéticos; usa los puertos `8010` y `5174`, no lee el `.env` del proyecto y elimina su carpeta temporal al finalizar. Cubre autenticación/permisos, persistencia de reglas y reportes, historial de entrega, descarga CSV y escaneos axe-core WCAG 2.1 A/AA del dashboard y reportes. La CI también ejecuta este runner con Chromium y conserva sus artefactos. La prueba de restauración trabaja solo con el PostgreSQL local de Compose: crea una base aleatoria temporal, restaura allí el dump, comprueba revisión Alembic/esquema y limpia los temporales. No apunta a Supabase.

Antes de producción, completa y conserva evidencia de esta lista en un entorno aislado:

- [ ] Flujo de aprobación/rechazo de alertas y notificación a receptor webhook controlado.
- [ ] Migraciones aplicadas desde el esquema anterior y `/ready` saludable.
- [ ] Login, roles, permisos, cookies seguras en TLS y rechazo de escrituras sin CSRF verificados.
- [ ] Fuente activa/verificada y procedencia de eventos comprobadas contra el IGP.
- [ ] Regla por magnitud, profundidad, zona y fuente: evento que coincide, evento fuera del umbral y evento duplicado comprobados.
- [ ] Alerta de prueba ligada a evento real; aprobación y rechazo dejan estado y auditoría correctos.
- [ ] Webhook probado con receptor controlado, `Idempotency-Key`, fallos, reintentos acotados y URL ausente; comprobar que no aparecen secretos en logs.
- [ ] CSV, JSON, XLSX y PDF descargados, filtros/fecha de corte conservados y contenido reconciliado con el snapshot.
- [ ] Retención revisada; no se eliminan eventos, datasets ni entregas pendientes, y los snapshots vencidos sí respetan su plazo.
- [ ] Navegación completa por teclado, foco visible, mensajes de error y diseño móvil revisados con lector de pantalla; axe automatizado no sustituye pruebas asistidas.
- [ ] Carga ensayada contra umbrales acordados con el probe acotado de lectura. Ejemplo: `python tests/load_api.py --base-url https://staging.example --workers 5 --seconds 30 --max-p95-ms 2000 --max-error-rate 0.01`. El comando devuelve error cuando supera p95 o tasa de error configurados; los valores predeterminados son límites de referencia, no un SLO aprobado.
- [ ] Backup restaurado en una instancia aislada y procedimiento de recuperación aprobado.
- [ ] Alertas de monitorización para errores de API y estado de PostgreSQL configuradas por el operador. `scripts/check-health.ps1` permite comprobar `/health` y `/ready` puntualmente o en bucle, pero no sustituye una plataforma de monitorización/alertas.

El probe de carga requiere `SISMO_LOAD_EMAIL` y `SISMO_LOAD_PASSWORD` de una cuenta de pruebas dedicada, inyectados desde el gestor de secretos. No acepta destinos HTTP remotos inseguros ni se debe apuntar a proveedores externos. La monitorización externa y las pruebas de aceptación específicas del entorno deben configurarse y adjuntarse por operaciones; el repositorio no incluye un proveedor de monitorización externo.
