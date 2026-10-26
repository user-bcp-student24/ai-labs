# Plan de implementación — API

## Alcance inicial (historial)

No existe `docs/ENDPOINTS.md`; el contrato disponible es el derivado del código y registrado en `HALLAZGOS.md`. Se seleccionan `H-API-02` por severidad alta y exposición de datos entre identidades, y `H-API-04` por severidad alta y alcance acotado a la carga de archivos. Ambos constan como `Pendiente`.

El usuario aprobó ambos IDs mediante la ventana de aprobación del 2026-10-26. Decisiones aprobadas: responder 403 si `owner` difiere de la identidad; aceptar solo `.txt` y `.md`; máximo 5 MiB; responder 415 por extensión no admitida y 413 por exceso de tamaño.

Se conservarán las rutas, métodos HTTP, formatos de entrada y respuestas para solicitudes permitidas: `GET /api/tasks`, `POST /api/tasks` y `GET /api/summary`; `POST /api/requirements` multipart con estado 201 y las claves de respuesta observadas (`owner`, `fileName`, `storedAt`, `size`). Las solicitudes con propietario ajeno y cargas no permitidas se rechazarán según las decisiones aprobadas arriba.

En el plan inicial, `H-API-01`, `H-API-03`, `H-API-05`, `H-API-06` y `H-API-07` quedaban fuera de alcance. La sección posterior **Plan ampliado: todos los hallazgos API** supersede esa limitación; se conserva este registro y su historial de ejecuciones.

## H-API-02 — Autorización ligada a la identidad

- **Hallazgo:** `H-API-02`, componente `api`, estado `Pendiente`, severidad alta. La query `owner` de tareas y resumen, y el `owner` del cuerpo al crear, pueden elegir una identidad distinta a la del token (`api/app/main.py`, funciones `list_tasks`, `create_task` y `summary`).
- **Problema:** un cliente autenticado puede leer datos de otro propietario o crear tareas bajo ese propietario; la autorización no queda ligada a `identity["username"]`.
- **Cambio propuesto:** mantener rutas, parámetros/campos y esquema de respuesta. Usar la identidad autenticada como propietario efectivo. Si `owner` se suministra y difiere de la identidad, responder 403; si se omite, usar la identidad. No introducir acceso por rol sin una política documentada. Aplicar la misma regla en lectura, resumen y creación. Mantener validación, decisión de autorización y consulta en responsabilidades pequeñas, sin duplicar la regla.
- **Archivos a tocar:** `api/app/main.py`; `api/tests/test_api.py`.
- **Caracterización antes de tocar código:** añadir o completar pruebas con base temporal que fijen el comportamiento legítimo: un usuario ve sus tareas y resumen; crear sin `owner` crea bajo su identidad; comprobar estados y claves de respuesta actuales. Ejecutar la suite existente como línea base antes de modificar `main.py`.
- **Pruebas de regresión previas a la implementación:** escribir casos para que un usuario estudiante no pueda consultar `owner=trainer` en tareas ni resumen, y no pueda crear una tarea con `owner=trainer`; con la propuesta, esperar 403. Verificar también que los casos con `owner` omitido o igual a la identidad siguen funcionando con los formatos actuales. Registrar que los casos de acceso ajeno deben fallar contra el código actual hasta aplicar el cambio; no presentarlos como aprobados ni como ejecutados.
- **Decisión de contrato:** 403 para propietario distinto, aprobada por el usuario en la ventana del 2026-10-26.

## H-API-04 — Carga segura de archivos

- **Hallazgo:** `H-API-04`, componente `api`, estado `Pendiente`, severidad alta. `upload_requirement` une `file.filename` directamente al directorio de carga y escribe todo el contenido (`api/app/main.py`).
- **Problema:** un nombre de ruta puede escapar del directorio previsto; tampoco se limita el tamaño ni se valida la extensión antes de guardar.
- **Cambio propuesto:** conservar `POST /api/requirements`, multipart `file`, estado 201 y las claves de respuesta existentes. Normalizar el nombre a un nombre de archivo seguro, confirmar que el destino queda dentro del directorio configurado, aceptar `.txt` y `.md`, y limitar bytes leídos a 5 MiB para rechazar archivos demasiado grandes sin cargarlos completos en memoria. Responder 415 por extensión no admitida y 413 por exceso de tamaño. Usar constantes con nombres claros; no añadir dependencias ni valores mágicos. Extraer normalización y validación en funciones pequeñas reutilizables si separa responsabilidades.
- **Archivos a tocar:** `api/app/main.py`; `api/tests/test_api.py`. Solo añadir configuración dentro de `api/` si la política acordada requiere valores configurables.
- **Caracterización antes de tocar código:** completar la prueba existente de `requirements.txt` con un directorio temporal; fijar 201, presencia de `owner`, `fileName`, `storedAt` y `size`, además del contenido guardado y la ubicación esperada para el nombre ordinario.
- **Pruebas de regresión previas a la implementación:** escribir un caso de nombre con componentes de ruta y verificar que el archivo no se escriba fuera del directorio temporal y que el nombre almacenado esté normalizado; escribir rechazo de extensión no permitida y de archivo por encima del límite, verificando que no quede archivo parcial. Las extensiones y el tamaño de prueba dependen de la política que se acuerde.
- **Decisión de contrato:** `.txt`/`.md`, máximo 5 MiB, 415 por extensión no admitida y 413 por exceso de tamaño; aprobada por el usuario en la ventana del 2026-10-26.

## Secuencia y verificación

1. Acordar las decisiones de contrato pendientes de ambos hallazgos.
2. Añadir primero las pruebas de caracterización y regresión en `api/tests/test_api.py`; ejecutar la suite desde `api/` y registrar resultados reales antes de modificar producción.
3. Implementar cada hallazgo en un cambio revisable, solo en `api/`, manteniendo responsabilidades separadas y sin anidamiento profundo ni valores mágicos.
4. Ejecutar pruebas focalizadas y luego la suite del componente; comprobar cobertura del código modificado contra la meta de 85% establecida en `AGENTS.md`. Registrar comandos y resultados en `docs/TESTING.md` solo cuando se realicen; no se registran resultados en este plan.

## Registro de ejecuciones

| fecha | componente | IDs | comando (cwd `api/`) | resultado |
|---|---|---|---|---|
| 2026-10-26 | api | H-API-02, H-API-04 | `pytest -q tests/test_api.py` | No inició: `pytest` no estaba disponible en PATH; 0 pruebas ejecutadas. |
| 2026-10-26 | api | H-API-02, H-API-04 | `.venv/Scripts/python.exe -m pytest -q tests/test_api.py` | Antes de cambios de producción: 4 passed y 4 failed. Los fallos esperados fueron autorización owner (200/200/201 en vez de 403), normalización de nombre (`../outside.txt`), extensión no permitida (201 en vez de 415) y exceso de tamaño (201 en vez de 413). |
| 2026-10-26 | api | H-API-02 | `.venv/Scripts/python.exe -m pytest -q tests/test_api.py -k "owner_overrides or lists_seeded_tasks or creates_task_and_summary"` | Después del cambio H-API-02: 3 passed; acceso habitual conservado y overrides rechazados. |
| 2026-10-26 | api | H-API-04 | `.venv/Scripts/python.exe -m pytest -q tests/test_api.py -k "uploads_requirement or normalizes_uploaded_filename or unsupported_extension or over_size_limit"` | Antes del cambio H-API-04: 1 passed y 3 failed; filename, extensión y límite confirmaron los fallos previstos. |
| 2026-10-26 | api | H-API-04 | `.venv/Scripts/python.exe -m pytest -q tests/test_api.py -k markdown_requirement` | Antes del cambio H-API-04: 1 passed; el comportamiento permitido de `.md` quedó caracterizado. |
| 2026-10-26 | api | H-API-04 | `.venv/Scripts/python.exe -m pytest -q tests/test_api.py -k "uploads_requirement or uploads_markdown or normalizes_uploaded_filename or unsupported_extension or over_size_limit"` | Después del cambio H-API-04: 5 passed. Primera ejecución advirtió que la constante 413 estaba obsoleta; se reemplazó. |
| 2026-10-26 | api | H-API-04 | `.venv/Scripts/python.exe -m pytest -q tests/test_api.py -k "uploads_requirement or uploads_markdown or normalizes_uploaded_filename or unsupported_extension or over_size_limit"` | Repetición tras reemplazar la constante 413: 5 passed; sin esa advertencia. |
| 2026-10-26 | api | H-API-02 | `.venv/Scripts/python.exe -m pytest -q tests/test_api.py -k allows_owner_matching_authenticated_user` | Después del cambio H-API-02: 1 passed; `owner` igual a la identidad permitido. |
| 2026-10-26 | api | H-API-02, H-API-04 | `.venv/Scripts/python.exe -m pytest --cov=app --cov-report=term-missing --cov-branch` | Validación final: 10 passed, 90% cobertura de `app.main`; sin fallos. Permanecen advertencias deprecadas sobre `on_event`/Starlette. |

## Plan ampliado: todos los hallazgos API

### Contrato y decisiones

No existe `docs/ENDPOINTS.md`; se conserva el contrato observado en la sección correspondiente de `HALLAZGOS.md`. Las rutas y las formas de respuesta para solicitudes válidas no cambian. La decisión anterior aprobada para H-API-02 es 403 cuando `owner` difiere de la identidad. Para H-API-04 se aprobaron `.txt`/`.md`, máximo 5 MiB, 415 por extensión y 413 por tamaño.

Para H-API-01 se eligió planear JWT estricto con PyJWT, HS256, claims `iss`, `aud` y `exp`, y secreto provisto por entorno; no se aceptará fallback al token legacy. La decisión actual es esperar coordinación interna con el emisor antes de cambiar producción; deben acordarse issuer/audience y despliegue sin leer ni modificar otros componentes. La autorización previa para consulta pública de H-API-06 queda supersedida por la instrucción más reciente: no enviar datos fuera de la organización; solo se permite evidencia local/offline.

### Aprobaciones y gates

- **H-API-01:** aprobado el enfoque JWT estricto, condicionado a coordinación interna con el emisor. Sin confirmación del contrato `iss`/`aud`, no comenzar cambios de producción ni avanzar al siguiente item.
- **H-API-02:** aprobada la respuesta 403 para `owner` distinto; la implementación sigue condicionada a resolver H-API-01.
- **H-API-03, H-API-05 y H-API-07:** aprobados por el usuario en la ventana de decisiones del 2026-10-26.
- **H-API-04:** aprobadas previamente las políticas `.txt`/`.md`, 5 MiB, 415/413; ya figura Resuelto.
- **H-API-06:** aprobada validación solo con fuentes locales/offline. La consulta pública previamente aprobada queda cancelada; si no hay base local o scanner interno disponible, dejar Pendiente.
- **Inyección de clave JWT:** el usuario eligió HS256 compartida e inyectada. La API leerá `AUTH_JWT_SECRET_FILE`; la clave local se generará sin imprimirla en `api/.secrets/jwt-signing-key`, excluida de Git. La misma clave deberá ser inyectada al emisor mediante el mecanismo interno de la organización; issuer/audience deben coincidir. Esta elección no reemplaza la confirmación del emisor ni autoriza a compartir la clave fuera del entorno.

## Item: H-API-01 — Token firmado y validado

- **Estado en HALLAZGOS.md:** Pendiente.
- **Problema:** `legacy_identity` decodifica Base64, confía en el username/role del contenido y compara un secreto fijo; no autentica firma, issuer ni audience. Las excepciones se devuelven al cliente.
- **Evidencia actual:** `api/app/main.py:14`, `api/app/main.py:19`, `api/app/main.py:22`, `api/app/main.py:24`, `api/app/main.py:28`.
- **Cambio propuesto:** reemplazar el formato legacy por JWT verificado con PyJWT y algoritmo HS256 fijado en servidor; exigir `iss`, `aud` y `exp`, y leer la clave desde `AUTH_JWT_SECRET_FILE` sin secreto por defecto. Rechazar token ausente/malformado con un 401 genérico y no aceptar tokens legacy como fallback. Justificación de dependencia: reutilizar una implementación JWT mantenida en vez de implementar criptografía propia. El cambio queda condicionado a coordinar compatibilidad con el emisor y confirmar los valores de claims/despliegue.
- **Archivos a tocar:** `api/app/main.py`, `api/requirements.txt`, `api/tests/test_api.py`, `api/.gitignore`; `api/.secrets/jwt-signing-key` se genera localmente y nunca se versiona.
- **Prueba antes de tocar:** añadir caracterización del contrato legacy actual (token válido y expirado) y casos JWT con clave de prueba: firma inválida, expirado, issuer/audience incorrectos, claims ausentes y éxito. Registrar que el caso legacy exitoso se reemplazará después de coordinar el emisor; no cambiar producción hasta tener ese contrato.
- **Dependencia/compatibilidad:** la API sola no puede asegurar una transición funcional si el emisor continúa generando tokens Base64. No hay contrato formal documentado.

## Item: H-API-02 — Autorización ligada a identidad confiable

- **Estado en HALLAZGOS.md:** Pendiente; el control de `owner` ya compara contra `identity`, pero H-API-01 impide confiar todavía en esa identidad.
- **Problema:** una identidad falsificada puede superar el 403 añadido para `owner` de tareas, resumen y creación.
- **Evidencia actual:** `api/app/main.py:31`, `api/app/main.py:95`, `api/app/main.py:110`, `api/app/main.py:119`; origen de identidad no verificable: `api/app/main.py:22`, `api/app/main.py:24`.
- **Cambio propuesto:** después de H-API-01, conservar el helper `authorized_owner`; para cualquier `owner` omitido usar el username del JWT verificado y para uno distinto responder 403, según la decisión ya aprobada. No añadir acceso por rol sin política acordada.
- **Archivos a tocar:** `api/app/main.py`, `api/tests/test_api.py`.
- **Prueba antes de tocar:** conservar/añadir casos para lectura y resumen propios, creación con `owner` omitido o coincidente, y 403 para query/body con otro owner. Generar tokens firmados únicamente con clave de prueba para que las pruebas dependan de una identidad verificada.
- **Dependencia:** implementar y validar H-API-01 primero; este apartado mantiene alcance y pruebas propios.

## Item: H-API-03 — Consultas SQL parametrizadas

- **Estado en HALLAZGOS.md:** Pendiente.
- **Problema:** filtros, campos del insert y la lectura posterior del ID se concatenan a SQL. La autorización de `owner` no corrige la concatenación de `title`, `description`, `status` o `priority`.
- **Evidencia actual:** `api/app/main.py:96`, `api/app/main.py:111`, `api/app/main.py:112`, `api/app/main.py:114`, `api/app/main.py:120`.
- **Cambio propuesto:** usar parámetros SQLite `?` en SELECT de tareas, SELECT de resumen, INSERT y consulta de la fila insertada. Mantener nombres de columnas, orden, filtros, respuestas y códigos actuales. No mezclar aquí la extracción de repositorio que pertenece a H-API-07.
- **Archivos a tocar:** `api/app/main.py`, `api/tests/test_api.py`.
- **Prueba antes de tocar:** crear tareas con comillas ordinarias en título/descripción y verificar que se guardan exactamente, que el conteo no cambia indebidamente y que consultas con owner autenticado que contenga comilla solo devuelven sus filas. Conservar las caracterizaciones existentes de lista, creación y resumen.

## Item: H-API-04 — Carga segura de archivos

- **Estado en HALLAZGOS.md:** Resuelto según la evidencia actual.
- **Problema original:** nombre sin normalizar, sin allowlist ni límite de tamaño.
- **Evidencia actual:** `api/app/main.py:15`, `api/app/main.py:16`, `api/app/main.py:41`, `api/app/main.py:45`, `api/app/main.py:48`, `api/app/main.py:50`, `api/app/main.py:137`, `api/app/main.py:138`, `api/app/main.py:143`.
- **Cambio propuesto:** no reabrir el cambio de producción si la revisión confirma el estado actual. La implementación existente normaliza el nombre, confina el destino al directorio, acepta `.txt`/`.md`, lee como máximo 5 MiB + 1 byte y responde 415/413. Si una prueba revela regresión, corregir solo este apartado/alcance.
- **Archivos a tocar:** ninguno previsto; solo `api/tests/test_api.py` si se añade la prueba de frontera.
- **Prueba antes de tocar:** las caracterizaciones existentes cubren `.txt` y `.md` válidos, traversal, extensión no permitida y tamaño sobre el máximo. Como complemento, añadir antes de cualquier ajuste una prueba de archivo de exactamente 5 MiB aceptado y comprobar que no queda archivo al rechazar el tamaño superior.

## Item: H-API-05 — Modelos, errores y funciones pequeñas

- **Estado en HALLAZGOS.md:** Pendiente.
- **Problema:** `dict[str, Any]` deja payloads/respuestas sin contrato tipado, `except Exception` expone detalles en errores y `summary` contiene decisiones anidadas. La duplicación señalada en RETO.md no quedó demostrada en Discovery y no se eliminará sin evidencia concreta.
- **Evidencia actual:** `api/app/main.py:27`, `api/app/main.py:28`, `api/app/main.py:104`, `api/app/main.py:118`, `api/app/main.py:152`, `api/app/main.py:153`.
- **Cambio propuesto:** definir modelos Pydantic para request y response que mantengan campos, alias `createdAt`, defaults y serialización válida observados; extraer la regla de conteo de summary a una función simple con guard clauses; capturar excepciones esperadas en backend-health y devolver mensaje genérico, manteniendo diagnóstico solo en logging controlado. No duplicar la conversión de filas. La respuesta de errores inválidos se caracterizará antes de decidir si cambia.
- **Archivos a tocar:** `api/app/main.py`, `api/tests/test_api.py`; `api/app/models.py` solo si el modelo no cabe limpiamente en el módulo sin mezclar responsabilidades.
- **Prueba antes de tocar:** fijar forma/aliases de tareas y summary, defaults del body, estado y cuerpo de respuestas válidas; mockear fallo local de backend-health y comprobar que el cliente no recibe `str(exception)`. Añadir pruebas de tipos/validación solo después de acordar el comportamiento para payloads inválidos.

## Item: H-API-06 — Evaluación SCA de dependencias

- **Estado en HALLAZGOS.md:** Pendiente; versiones fijadas no prueban por sí solas un CVE.
- **Problema:** `urllib3==2.5.0` y `python-multipart==0.0.21` requieren verificación contra advisories actuales; todavía no se ha producido evidencia de vulnerabilidad ni de parche disponible.
- **Evidencia actual:** `api/requirements.txt:4`, `api/requirements.txt:5`.
- **Cambio propuesto:** buscar primero una base de advisories cacheada o scanner interno offline para auditar exclusivamente los manifiestos de `api/`; registrar paquete, versión, advisory, versión corregida y compatibilidad. No realizar llamadas externas ni enviar nombres/versiones de paquetes fuera de la organización. Cambiar solo dependencias con advisory local verificable y parche compatible; si no hay fuente local, no inferir ausencia de CVEs ni elegir versiones a ciegas: mantener el hallazgo Pendiente.
- **Archivos a tocar:** `api/requirements.txt` únicamente si hay upgrade justificado; `api/requirements-dev.txt` solo si una herramienta queda como dependencia de desarrollo aprobada; `api/tests/test_api.py` si el cambio afecta compatibilidad observable.
- **Prueba antes de tocar:** guardar evidencia del escaneo local/offline inicial y ejecutar suite/import smoke test con el entorno actual. Si hay upgrade, repetir el escaneo local y suite completa con las versiones corregidas; no considerar una prueba funcional como sustituto del escaneo.
- **Privacidad/estado:** la autorización anterior para consulta pública quedó supersedida el 2026-10-26. No se ha comprobado que exista una fuente offline disponible; hasta encontrarla, H-API-06 sigue Pendiente.

## Item: H-API-07 — Separación de capas

- **Estado en HALLAZGOS.md:** Pendiente.
- **Problema:** `main.py` agrupa inicialización de SQLite, rutas, reglas, acceso a datos, serialización, carga y health check; un cambio en una responsabilidad aumenta el riesgo sobre las demás.
- **Evidencia actual:** `api/app/main.py:55`, `api/app/main.py:82`, `api/app/main.py:94`, `api/app/main.py:104`, `api/app/main.py:118`, `api/app/main.py:135`, `api/app/main.py:147`.
- **Cambio propuesto:** separar composición de la aplicación, rutas, servicios y repositorios siguiendo `docs/GOOD_PRACTICES.md`; preservar paths, métodos, payloads, respuestas, estados y comportamiento observado. Evitar mover o reescribir reglas de seguridad como parte mecánica: consumir los servicios ya verificados de H-API-01 a H-API-06. Mantener funciones pequeñas y no introducir abstracciones que no reduzcan acoplamiento real.
- **Archivos a tocar:** `api/app/main.py`, `api/tests/test_api.py` y módulos nuevos bajo `api/app/` (por ejemplo `routes/`, `services.py`, `repositories.py`); añadir `__init__.py` solo donde la estructura de paquetes lo requiera.
- **Prueba antes de tocar:** completar caracterización de cada ruta observada con TestClient y base/directorio temporales: autenticación, lista, creación, summary, upload y health con dependencia simulada. Registrar status, claves de respuesta y filtros antes del movimiento; ejecutar el mismo conjunto después.
- **Secuencia:** planear después de H-API-01/02/03/05 para no duplicar refactor y luego revalidar los siete IDs. No requiere cambios en otros componentes ni nuevos endpoints.

## Secuencia general

1. Confirmar contrato JWT con el emisor antes de cambiar producción para H-API-01/02; no aceptar legacy como fallback.
2. Resolver H-API-01, después H-API-02; parametrizar SQL de H-API-03 en su cambio separado.
3. Mantener H-API-04 resuelto y completar solo la prueba del límite exacto si se aprueba como complemento.
4. Resolver tipos/errores de H-API-05 y evaluar dependencias de H-API-06 con evidencia externa.
5. Separar capas bajo H-API-07 después de las correcciones conductuales; ejecutar suite y cobertura del diff con meta mínima 85%.

Los estados de `HALLAZGOS.md` se cambiarán únicamente con pruebas y evidencia correspondientes. No se crea `docs/ENDPOINTS.md` ni `docs/TESTING.md` en esta etapa; las ejecuciones futuras se registrarán allí en su paso de documentación.