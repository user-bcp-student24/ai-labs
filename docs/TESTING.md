# Evidencia de pruebas — API

## Alcance

Esta evidencia corresponde solo al componente `api` y a los contratos observados en [docs/ENDPOINTS.md](ENDPOINTS.md). El código de producción no se modificó; las pruebas se añadieron en [api/tests/test_api.py](../api/tests/test_api.py). Los tokens son fixtures locales del formato legacy y `backend-health` usa mocks: no se llamó a servicios externos.

## Matriz de casos

| endpoint | caso | tipo | resultado esperado |
| --- | --- | --- | --- |
| `GET /api/tasks` | Listar tareas sembradas del usuario | Camino feliz | `200`, arreglo con las claves documentadas. |
| `GET /api/tasks` | `owner=` y usuario sin tareas | Borde | `200`, usa la identidad del token y devuelve `[]`. |
| `GET /api/tasks` | Token inválido | Error | `401`, detalle `Invalid token`. |
| `GET /api/tasks` | Solicitar otro owner | Error, H-API-02 | `403`, `Not authorized to access this owner`; no devuelve tareas ajenas. |
| `GET /api/tasks` | SQLite cerrado | Error | `500`, `Internal Server Error`. |
| `POST /api/tasks` | Crear tarea completa | Camino feliz | `201`, objeto creado y owner de la identidad. |
| `POST /api/tasks` | Body `{}` | Borde | `201`, defaults `title/description=""`, `status="TODO"`, `priority="MEDIUM"`. |
| `POST /api/tasks` | Token inválido | Error | `401`, detalle `Invalid token`. |
| `POST /api/tasks` | Owner del body distinto | Error, H-API-02 | `403`, `Not authorized to access this owner`. |
| `POST /api/tasks` | Body ausente o raíz no objeto | Error | `422`, detalle de validación FastAPI/Pydantic. |
| `POST /api/tasks` | SQLite cerrado | Error | `500`, `Internal Server Error`. |
| `GET /api/summary` | Resumen después de crear tarea | Camino feliz | `200`, total y conteos por estado. |
| `GET /api/summary` | Owner vacío y sin tareas | Borde | `200`, `total=0`, `byStatus={}`, `highPriorityOpen=0`. |
| `GET /api/summary` | HIGH en `DONE`, `ARCHIVED` e `IN_PROGRESS` | Borde | `200`; solo HIGH no archivadas ni terminadas cuentan como abiertas. |
| `GET /api/summary` | Token inválido | Error | `401`, detalle `Invalid token`. |
| `GET /api/summary` | Solicitar otro owner | Error, H-API-02 | `403`, `Not authorized to access this owner`. |
| `GET /api/summary` | SQLite cerrado | Error | `500`, `Internal Server Error`. |
| `POST /api/requirements` | Upload `.txt`, `.md` y nombre normalizado | Camino feliz, H-API-04 | `201`, metadata documentada y archivo guardado bajo uploads. |
| `POST /api/requirements` | Archivo vacío y extensión `.TXT` | Borde | `201`, `size=0`; la extensión se compara sin distinguir mayúsculas. |
| `POST /api/requirements` | Archivo de exactamente 5 MiB | Borde, H-API-04 | `201`, `size=5242880`. |
| `POST /api/requirements` | Token inválido | Error | `401`, detalle `Invalid token`. |
| `POST /api/requirements` | Nombre `.` o destino resuelto fuera de uploads | Error, H-API-04 | `400`, `Invalid filename`. |
| `POST /api/requirements` | Archivo mayor de 5 MiB | Error, H-API-04 | `413`, `File exceeds maximum allowed size`; no queda archivo. |
| `POST /api/requirements` | Extensión `.exe` o sin extensión | Error, H-API-04 | `415`, `Unsupported file type`. |
| `POST /api/requirements` | Campo multipart `file` ausente | Error | `422`, error de campo requerido. |
| `POST /api/requirements` | Fallo al escribir en disco | Error | `500`, `Internal Server Error`. |
| `GET /api/backend-health` | Upstream responde `200` | Camino feliz, H-API-05 | API `200`, refleja username, status y body upstream. |
| `GET /api/backend-health` | Upstream responde `503` | Borde | API `200`, JSON contiene `status=503` y body upstream. |
| `GET /api/backend-health` | Token inválido | Error | `401`, detalle `Invalid token`. |
| `GET /api/backend-health` | Excepción/timeout upstream | Error capturado | API `200`, JSON contiene `status=0` y texto de excepción. |

## Código de las pruebas

El código ejecutable y los fixtures están en [api/tests/test_api.py](../api/tests/test_api.py). Los casos principales incluyen `test_rejects_invalid_token_for_each_endpoint`, `test_rejects_owner_overrides_from_authenticated_user`, `test_empty_owner_filters_default_to_authenticated_user_and_empty_summary`, `test_creates_task_with_empty_object_defaults`, `test_rejects_missing_or_non_object_task_body`, `test_database_errors_return_internal_server_error_for_task_routes`, los tests `test_upload_*` y los tres `test_backend_health_*`.

## Ejecuciones registradas

Fecha de las ejecuciones: 2026-10-26. Todos los comandos se ejecutaron con cwd `api/`; código de salida `0` significa que pytest terminó correctamente.

| fecha | componente | IDs relacionados | comando | código de salida | resultado |
| --- | --- | --- | --- | --- | --- |
| 2026-10-26 | api | H-API-01, H-API-02, H-API-04, H-API-05 | `.venv/Scripts/python.exe -m pytest -q tests/test_api.py -k "rejects_invalid_token_for_each_endpoint or empty_owner_filters or creates_task_with_empty_object or rejects_missing_or_non_object or database_errors_return or upload_accepts_empty or exact_size_limit or filename_without_extension or empty_normalized_filename or requires_file_field or upload_write_error or backend_health"` | 0 | 19 casos completados sin fallos. |
| 2026-10-26 | api | H-API-01, H-API-02, H-API-04, H-API-05 | `.venv/Scripts/python.exe -m pytest -q tests/test_api.py -k "rejects_expired_or_malformed or excludes_done_and_archived or path_resolving_outside"` | 0 | 4 casos completados sin fallos. |
| 2026-10-26 | api | H-API-01, H-API-02, H-API-04, H-API-05 | `.venv/Scripts/python.exe -m pytest tests/test_api.py -o addopts="" --cov=app --cov-branch --cov-report=term-missing --cov-report="json:$env:TEMP/ai-labs-api-final-coverage.json"` | 0 | Suite completa: 32 passed, 67 warnings, 1.80 s. |

## Cobertura

Medición con `pytest-cov`/Coverage.py, configuración de ramas activa (`--cov=app --cov-branch`), fuente global `app` definida en `api/pyproject.toml`.

| alcance | cubierto | total | porcentaje | método |
| --- | ---: | ---: | ---: | --- |
| `api/app/main.py` sentencias | 117 | 117 | 100% | Coverage.py statements |
| `api/app/main.py` ramas | 26 | 26 | 100% | Coverage.py branch destinations |
| Global API combinado | 143 | 143 | 100% | 117 sentencias + 26 ramas |
| Código de producción modificado en este paso | N/A | 0 líneas modificadas | N/A | No se cambió código de producción; el reporte global anterior cubre el módulo API. |

El módulo API medido supera el objetivo de 85%. La cobertura global se informa aparte; no se presenta como cobertura de un diff de producción inexistente.

## Fallos

No hubo fallos de pytest en las ejecuciones registradas. La suite final reportó advertencias deprecadas de `FastAPI.on_event`/Starlette `BlockingPortal`; no se silenciaron ni modificaron porque están fuera del alcance de tests/documentación.

## Pendientes

- H-API-01/H-API-02: las pruebas usan el token Base64 legacy de test; no prueban un emisor JWT real ni demuestran que la identidad actual sea confiable.
- H-API-03: no se valida la remediación de SQL concatenado. No se agregó una prueba que acepte el bug como comportamiento esperado; falta prueba de round-trip para texto con comillas después de parametrizar SQL.
- H-API-06: esta suite no sustituye un escaneo SCA offline; permanece pendiente según el plan.
- `backend-health` se probó con mocks y sin red. La integración con el servicio real queda pendiente de coordinación.
- No se hicieron cambios de arquitectura H-API-07 en este paso.

## Pruebas propuestas

- Tras acordar issuer/audience con el emisor, añadir integración que obtenga un JWT real de prueba y valide firma, expiración e identidad (H-API-01/H-API-02).
- Tras parametrizar las consultas, añadir regresión para crear/consultar texto ordinario con comillas y confirmar round-trip sin alterar consultas (H-API-03).
- Ejecutar SCA únicamente con fuente local/offline aprobada y registrar evidencia separada (H-API-06).
