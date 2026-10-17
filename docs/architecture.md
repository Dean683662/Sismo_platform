# Arquitectura

La plataforma separa interfaz React, API FastAPI, persistencia PostgreSQL y las funciones Python de preparación/evaluación ML. Las rutas de analítica consultan eventos observados; datasets y experimentos son registros separados y versionados.

## Flujo de analítica y ML

1. La ingesta conserva el evento normalizado y su proveedor.
2. Dashboard, series y mapa leen los eventos guardados; cada resultado muestra su periodo y conserva la procedencia.
3. Un analista captura un dataset como snapshot inmutable con filtros y un informe de calidad.
4. El laboratorio ordena temporalmente el snapshot, elimina duplicados, valida rangos y crea features de ubicación/profundidad con magnitud observada como target.
5. El entrenamiento reserva la parte más reciente para evaluación, ajusta imputación y regresión solo sobre entrenamiento y registra MAE, RMSE, R², features, dataset y periodos.

El baseline es exploratorio: no estima la ocurrencia de futuros sismos ni genera alertas. El feed IGP conectado actualmente reporta un único evento reciente, por lo que el MVP necesita una fuente histórica autorizada antes de cualquier análisis longitudinal significativo.

## Persistencia

- `seismic_events`: evento normalizado, coordenadas, tiempo de ocurrencia, procedencia y hash.
- `datasets`: consulta, periodo, número de filas, calidad y snapshot JSON versionado.
- `ml_experiments`: dataset asociado, algoritmo, features, target, parámetros, métricas, validación temporal y limitaciones.

La migración `20261016_0004` agrega las tablas del laboratorio. Ejecutar `alembic upgrade head` tras configurar la base de datos.