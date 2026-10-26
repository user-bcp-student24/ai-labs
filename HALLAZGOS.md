# Hallazgos de Discovery

## Contrato observado de API (derivado del código)

No existe `docs/ENDPOINTS.md`; por ello no hay un contrato acordado que contrastar. Lo siguiente describe el código, no una prueba de comportamiento ejecutada:

| Ruta | Contrato observado |
|---|---|
| `GET /api/tasks` | Requiere token Bearer; admite `owner` opcional y devuelve tareas con `id`, `title`, `description`, `status`, `owner`, `priority` y `createdAt`. |
| `POST /api/tasks` | Requiere token Bearer; recibe un objeto JSON y devuelve la tarea creada con estado 201. El código acepta `owner` del cuerpo y aplica valores predeterminados a campos ausentes. |
| `GET /api/summary` | Requiere token Bearer; admite `owner` opcional y devuelve propietario, total, conteo por estado y tareas abiertas de prioridad alta. |
| `POST /api/requirements` | Requiere token Bearer; recibe `file` multipart y devuelve propietario, nombre, ruta almacenada y tamaño con estado 201. |
| `GET /api/backend-health` | Requiere token Bearer; consulta la URL configurada en `AUTH_HEALTH_URL` o la URL local predeterminada y devuelve estado y cuerpo de la respuesta. |

El token observado es Base64 de cuatro campos separados por `|` (`username`, `role`, expiración Unix y secreto compartido); el código comprueba el secreto y la expiración, pero no verifica una firma criptográfica. Contrato acordado y compatibilidad con consumidores: pendientes.

## Matriz de seguimiento

| id | componente | hallazgo | tipo | explicacion | evidencia (archivo:linea) | severidad | estado |
|---|---|---|---|---|---|---|---|
| H-API-01 | api | Token Base64 con secreto embebido, sin firma | Vulnerabilidad | Base64 solo codifica el contenido; al no existir firma criptográfica, quien conozca el secreto puede fabricar tokens con identidad y rol arbitrarios. | api/app/main.py:14, api/app/main.py:20, api/app/main.py:21, api/app/main.py:22 | alta | Pendiente |
| H-API-02 | api | Autorización de tareas controlada por el cliente | Vulnerabilidad | Pendiente: la comparación de `owner` ahora responde 403 ante una identidad distinta, pero `legacy_identity` acepta un token Base64 con secreto hardcodeado y sin firma; se puede falsificar el username y superar este control. H-API-01 sigue pendiente. | api/app/main.py:14, api/app/main.py:22, api/app/main.py:24, api/app/main.py:31, api/app/main.py:95, api/app/main.py:110, api/app/main.py:119 | alta | Pendiente |
| H-API-03 | api | Filtros e inserts SQL construidos por concatenación | Vulnerabilidad | Valores de query y del cuerpo se interpolan directamente en SQL; comillas u otros caracteres pueden romper las consultas y la entrada puede alterar su estructura. | api/app/main.py:70, api/app/main.py:84, api/app/main.py:93 | alta | Pendiente |
| H-API-04 | api | Nombre y contenido de archivo sin validación visible | Vulnerabilidad | Resuelto: el nombre se normaliza y el destino se confina a uploads; solo se aceptan `.txt`/`.md` y se limita la lectura a 5 MiB, con 415/413 para rechazos. | api/app/main.py:15, api/app/main.py:16, api/app/main.py:42, api/app/main.py:45, api/app/main.py:48, api/app/main.py:50, api/app/main.py:136, api/app/main.py:137, api/app/main.py:138, api/app/main.py:140, api/app/main.py:143 | alta | Resuelto |
| H-API-05 | api | Tipado débil, excepciones amplias y lógica anidada | Refactor | `dict[str, Any]` reduce la validación del payload; capturar `Exception` y devolver detalles al cliente puede exponer información, y el anidamiento complica mantener reglas. La duplicación mencionada en el reto no queda confirmada por esta lectura. | api/app/main.py:25, api/app/main.py:26, api/app/main.py:78, api/app/main.py:97, api/app/main.py:98, api/app/main.py:99, api/app/main.py:101, api/app/main.py:102, api/app/main.py:103, api/app/main.py:104, api/app/main.py:120, api/app/main.py:121 | media | Pendiente |
| H-API-06 | api | Versiones de dependencias candidatas a revisión SCA | Sugerencia | El manifiesto fija `urllib3==2.5.0` y `python-multipart==0.0.21`, versiones señaladas por el reto. La presencia y versión están confirmadas; no se consultaron advisories, así que no se afirma que sean vulnerables. | api/requirements.txt:4, api/requirements.txt:5 | baja | Pendiente |
| H-API-07 | api | Rutas, token, SQL, archivos y lógica en un solo módulo | Refactor | `main.py` concentra inicialización de SQLite, validación del token, endpoints, consultas, reglas y escritura de archivos, aumentando el acoplamiento y el costo de probar cambios aislados. | api/app/main.py:29, api/app/main.py:35, api/app/main.py:56, api/app/main.py:67, api/app/main.py:78, api/app/main.py:91, api/app/main.py:108, api/app/main.py:115 | baja | Pendiente |