# API de requisitos del taller

Esta sección describe el código actual de `api/`; no presupone que la API esté refactorizada. Los valores dinámicos de los ejemplos (IDs, fechas y rutas locales) son ilustrativos.

## Contratos y estado

### Contrato observado

Las cinco rutas requieren `Authorization: Bearer <token>`. El servidor elimina `Bearer ` y verifica una firma HMAC-SHA256 y decodifica el payload Base64 con tres campos separados por `|`: username, role y expiración Unix. Comprueba firma y expiración; el rol no participa en la autorización. Token inválido devuelve `401` con `{"detail":"Invalid token: ..."}` y el detalle depende de la causa. ([api/app/main.py:19](../api/app/main.py#L19), [api/app/main.py:22](../api/app/main.py#L22), [api/app/main.py:24](../api/app/main.py#L24), [api/app/main.py:28](../api/app/main.py#L28))

Los ejemplos usan `<token>` como marcador, no como credencial válida. La credencial se obtiene con `POST /auth/login`; la clave de firma viene de `WORKSHOP_TOKEN_SECRET` y no se publica.

### Contrato acordado

El registro humano de `PLAN.md` aprueba `403` cuando `owner` difiere de la identidad, y para uploads aprueba `.txt`/`.md`, máximo 5 MiB, `415` por extensión y `413` por tamaño. El código implementa esas decisiones. No consta un contrato acordado con el emisor JWT. ([api/app/main.py:31](../api/app/main.py#L31), [api/app/main.py:41](../api/app/main.py#L41), [api/app/main.py:45](../api/app/main.py#L45), [api/app/main.py:137](../api/app/main.py#L137), [api/app/main.py:138](../api/app/main.py#L138))

### Riesgos pendientes

- La identidad viene de un token firmado con HMAC-SHA256; `owner` se compara con el username del token verificado. ([api/app/main.py:22](../api/app/main.py#L22), [api/app/main.py:31](../api/app/main.py#L31))
- Las consultas SQL concatenan valores; `POST /api/tasks` recibe un `dict[str, Any]` sin enums ni límites de longitud. ([api/app/main.py:96](../api/app/main.py#L96), [api/app/main.py:104](../api/app/main.py#L104), [api/app/main.py:111](../api/app/main.py#L111), [api/app/main.py:120](../api/app/main.py#L120))
- `backend-health` expone el cuerpo upstream y el texto de excepciones; el upload devuelve la ruta local en `storedAt`. ([api/app/main.py:144](../api/app/main.py#L144), [api/app/main.py:151](../api/app/main.py#L151), [api/app/main.py:153](../api/app/main.py#L153))
- Siguen pendientes el emisor/firma/issuer/audience, los valores válidos de campos de tarea y el contrato de errores de persistencia.

## `GET /api/tasks`

### 1. Propósito de negocio

Lista en orden de ID las tareas del usuario autenticado. ([api/app/main.py:94](../api/app/main.py#L94), [api/app/main.py:96](../api/app/main.py#L96))

### 2. Autenticación y headers

Requiere `Authorization: Bearer <token>`. No requiere cuerpo ni `Content-Type`. ([api/app/main.py:94](../api/app/main.py#L94), [api/app/main.py:19](../api/app/main.py#L19))

### 3. Parámetros de request

| Campo/parámetro | Tipo | Obligatorio | Descripción |
| --- | --- | --- | --- |
| `owner` (query) | string | No | Omitido o vacío usa el username autenticado; si difiere, responde `403`. ([api/app/main.py:94](../api/app/main.py#L94), [api/app/main.py:95](../api/app/main.py#L95), [api/app/main.py:31](../api/app/main.py#L31)) |

Ejemplo completo:

```http
GET /api/tasks?owner=student HTTP/1.1
Host: localhost:8000
Authorization: Bearer <token>
```

### 4. Respuesta exitosa

Responde `200 OK` con un arreglo. Si no hay tareas, devuelve `[]`. ([api/app/main.py:96](../api/app/main.py#L96), [api/app/main.py:97](../api/app/main.py#L97))

| Campo | Tipo | Descripción |
| --- | --- | --- |
| `id` | integer | Identificador de la tarea. |
| `title` | string | Título. |
| `description` | string | Descripción. |
| `status` | string | Estado almacenado. |
| `owner` | string | Propietario. |
| `priority` | string | Prioridad. |
| `createdAt` | string | Fecha y hora SQLite. ([api/app/main.py:82](../api/app/main.py#L82), [api/app/main.py:90](../api/app/main.py#L90)) |

```json
[
  {
    "id": 1,
    "title": "Refactor login",
    "description": "Separar responsabilidades en frontend",
    "status": "TODO",
    "owner": "student",
    "priority": "HIGH",
    "createdAt": "2026-10-26 12:00:00"
  }
]
```

### 5. Errores

| HTTP | Condición | Ejemplo de respuesta |
| --- | --- | --- |
| `401 Unauthorized` | Header ausente o token inválido. | `{"detail":"Invalid token: invalid token"}` ([api/app/main.py:19](../api/app/main.py#L19), [api/app/main.py:28](../api/app/main.py#L28)) |
| `403 Forbidden` | `owner` difiere del username del token. | `{"detail":"Not authorized to access this owner"}` ([api/app/main.py:31](../api/app/main.py#L31), [api/app/main.py:34](../api/app/main.py#L34)) |
| `500 Internal Server Error` | Error no controlado al consultar SQLite. | `Internal Server Error` ([api/app/main.py:96](../api/app/main.py#L96), [api/app/main.py:97](../api/app/main.py#L97)) |

### 6. Notas de seguridad

La consulta SQL concatena el propietario. El 403 liga el filtro a la identidad del token, la identidad se verifica con firma HMAC; la concatenación SQL sigue pendiente (H-API-03). ([api/app/main.py:22](../api/app/main.py#L22), [api/app/main.py:95](../api/app/main.py#L95), [api/app/main.py:96](../api/app/main.py#L96))

## `POST /api/tasks`

### 1. Propósito de negocio

Crea una tarea asignada al usuario autenticado y devuelve el registro creado. ([api/app/main.py:104](../api/app/main.py#L104), [api/app/main.py:110](../api/app/main.py#L110), [api/app/main.py:116](../api/app/main.py#L116))

### 2. Autenticación y headers

Requiere `Authorization: Bearer <token>` y `Content-Type: application/json`. ([api/app/main.py:104](../api/app/main.py#L104), [api/app/main.py:19](../api/app/main.py#L19))

### 3. Parámetros de request

El body debe ser un objeto JSON; cada valor se convierte a string. No se declaran enums ni límites de longitud. ([api/app/main.py:104](../api/app/main.py#L104), [api/app/main.py:105](../api/app/main.py#L105), [api/app/main.py:108](../api/app/main.py#L108))

| Campo/parámetro | Tipo | Obligatorio | Descripción |
| --- | --- | --- | --- |
| `title` (body) | valor JSON convertido a string | No | Default `""`. ([api/app/main.py:105](../api/app/main.py#L105)) |
| `description` (body) | valor JSON convertido a string | No | Default `""`. ([api/app/main.py:106](../api/app/main.py#L106)) |
| `status` (body) | valor JSON convertido a string | No | Default `"TODO"`; sin enum. ([api/app/main.py:107](../api/app/main.py#L107)) |
| `priority` (body) | valor JSON convertido a string | No | Default `"MEDIUM"`; sin enum. ([api/app/main.py:108](../api/app/main.py#L108)) |
| `owner` (body) | valor JSON convertido a string | No | Omitido o `null` usa el username autenticado; valor diferente responde `403`. ([api/app/main.py:109](../api/app/main.py#L109), [api/app/main.py:110](../api/app/main.py#L110)) |

Ejemplo completo:

```http
POST /api/tasks HTTP/1.1
Host: localhost:8000
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "Add tests",
  "description": "Improve API coverage",
  "status": "TODO",
  "priority": "HIGH"
}
```

### 4. Respuesta exitosa

Responde `201 Created`. ([api/app/main.py:103](../api/app/main.py#L103), [api/app/main.py:116](../api/app/main.py#L116))

| Campo | Tipo | Descripción |
| --- | --- | --- |
| `id` | integer | ID generado por SQLite. |
| `title` | string | Valor convertido. |
| `description` | string | Valor convertido. |
| `status` | string | Valor convertido o default `TODO`. |
| `owner` | string | Username autenticado. |
| `priority` | string | Valor convertido o default `MEDIUM`. |
| `createdAt` | string | Fecha y hora SQLite. ([api/app/main.py:82](../api/app/main.py#L82), [api/app/main.py:90](../api/app/main.py#L90)) |

```json
{
  "id": 4,
  "title": "Add tests",
  "description": "Improve API coverage",
  "status": "TODO",
  "owner": "student",
  "priority": "HIGH",
  "createdAt": "2026-10-26 12:00:00"
}
```

### 5. Errores

| HTTP | Condición | Ejemplo de respuesta |
| --- | --- | --- |
| `401 Unauthorized` | Header ausente o token inválido. | `{"detail":"Invalid token: invalid token"}` ([api/app/main.py:19](../api/app/main.py#L19), [api/app/main.py:28](../api/app/main.py#L28)) |
| `403 Forbidden` | `owner` del body difiere del username autenticado. | `{"detail":"Not authorized to access this owner"}` ([api/app/main.py:31](../api/app/main.py#L31)) |
| `422 Unprocessable Entity` | Falta el body o su raíz no es un objeto válido. | `{"detail":[{"type":"dict_type","loc":["body"],"msg":"Input should be a valid dictionary","input":[]}]}` ([api/app/main.py:104](../api/app/main.py#L104)) |
| `500 Internal Server Error` | Error no controlado en SQL/lectura de la fila. | `Internal Server Error` ([api/app/main.py:111](../api/app/main.py#L111), [api/app/main.py:112](../api/app/main.py#L112), [api/app/main.py:115](../api/app/main.py#L115)) |

### 6. Notas de seguridad

El SQL de inserción concatena campos del body (H-API-03); el token ya se verifica con firma HMAC. ([api/app/main.py:22](../api/app/main.py#L22), [api/app/main.py:111](../api/app/main.py#L111))

## `GET /api/summary`

### 1. Propósito de negocio

Resume el total de tareas del usuario, su distribución por estado y las tareas abiertas de prioridad alta. ([api/app/main.py:118](../api/app/main.py#L118), [api/app/main.py:120](../api/app/main.py#L120))

### 2. Autenticación y headers

Requiere `Authorization: Bearer <token>`. No requiere cuerpo ni `Content-Type`. ([api/app/main.py:118](../api/app/main.py#L118), [api/app/main.py:19](../api/app/main.py#L19))

### 3. Parámetros de request

| Campo/parámetro | Tipo | Obligatorio | Descripción |
| --- | --- | --- | --- |
| `owner` (query) | string | No | Omitido o vacío usa el username autenticado; si difiere, responde `403`. ([api/app/main.py:118](../api/app/main.py#L118), [api/app/main.py:119](../api/app/main.py#L119), [api/app/main.py:31](../api/app/main.py#L31)) |

Ejemplo completo:

```http
GET /api/summary?owner=student HTTP/1.1
Host: localhost:8000
Authorization: Bearer <token>
```

### 4. Respuesta exitosa

Responde `200 OK`. `highPriorityOpen` cuenta prioridad `HIGH` con estado distinto de `DONE` y `ARCHIVED`. ([api/app/main.py:120](../api/app/main.py#L120), [api/app/main.py:127](../api/app/main.py#L127), [api/app/main.py:131](../api/app/main.py#L131), [api/app/main.py:133](../api/app/main.py#L133))

| Campo | Tipo | Descripción |
| --- | --- | --- |
| `owner` | string | Username resumido. |
| `total` | integer | Número total de tareas. |
| `byStatus` | `map<string, integer>` | Conteo de tareas por estado. |
| `highPriorityOpen` | integer | Conteo HIGH excepto estados DONE y ARCHIVED. |

```json
{
  "owner": "student",
  "total": 2,
  "byStatus": {
    "TODO": 1,
    "IN_PROGRESS": 1
  },
  "highPriorityOpen": 1
}
```

### 5. Errores

| HTTP | Condición | Ejemplo de respuesta |
| --- | --- | --- |
| `401 Unauthorized` | Header ausente o token inválido. | `{"detail":"Invalid token: invalid token"}` ([api/app/main.py:19](../api/app/main.py#L19), [api/app/main.py:28](../api/app/main.py#L28)) |
| `403 Forbidden` | `owner` difiere del username autenticado. | `{"detail":"Not authorized to access this owner"}` ([api/app/main.py:31](../api/app/main.py#L31)) |
| `500 Internal Server Error` | Error no controlado al consultar SQLite. | `Internal Server Error` ([api/app/main.py:119](../api/app/main.py#L119), [api/app/main.py:120](../api/app/main.py#L120)) |

### 6. Notas de seguridad

La consulta concatena el propietario (H-API-03); la identidad viene de un token verificado con HMAC. ([api/app/main.py:22](../api/app/main.py#L22), [api/app/main.py:119](../api/app/main.py#L119), [api/app/main.py:120](../api/app/main.py#L120))

## `POST /api/requirements`

### 1. Propósito de negocio

Guarda un archivo de requisitos en el directorio de uploads y devuelve su metadata. ([api/app/main.py:135](../api/app/main.py#L135), [api/app/main.py:143](../api/app/main.py#L143), [api/app/main.py:144](../api/app/main.py#L144))

### 2. Autenticación y headers

Requiere `Authorization: Bearer <token>` y `multipart/form-data`; el cliente debe construir el boundary. ([api/app/main.py:135](../api/app/main.py#L135), [api/app/main.py:19](../api/app/main.py#L19))

### 3. Parámetros de request

| Campo/parámetro | Tipo | Obligatorio | Descripción |
| --- | --- | --- | --- |
| `file` (multipart) | archivo | Sí | Extensión `.txt` o `.md`, sin distinción de mayúsculas; máximo 5 MiB. El nombre se normaliza al basename. ([api/app/main.py:15](../api/app/main.py#L15), [api/app/main.py:16](../api/app/main.py#L16), [api/app/main.py:41](../api/app/main.py#L41), [api/app/main.py:45](../api/app/main.py#L45), [api/app/main.py:137](../api/app/main.py#L137), [api/app/main.py:138](../api/app/main.py#L138)) |

Ejemplo completo:

```http
POST /api/requirements HTTP/1.1
Host: localhost:8000
Authorization: Bearer <token>
Content-Type: multipart/form-data; boundary=ExampleBoundary

--ExampleBoundary
Content-Disposition: form-data; name="file"; filename="requirements.txt"
Content-Type: text/plain

Login must be accessible
--ExampleBoundary--
```

### 4. Respuesta exitosa

Responde `201 Created`. `storedAt` depende de `WORKSHOP_UPLOAD_DIR` (o de `upload_dir` al construir la app). ([api/app/main.py:55](../api/app/main.py#L55), [api/app/main.py:56](../api/app/main.py#L56), [api/app/main.py:134](../api/app/main.py#L134), [api/app/main.py:144](../api/app/main.py#L144))

| Campo | Tipo | Descripción |
| --- | --- | --- |
| `owner` | string | Username extraído del token. |
| `fileName` | string | Nombre base almacenado. |
| `storedAt` | string | Ruta local del archivo. |
| `size` | integer | Bytes almacenados. ([api/app/main.py:144](../api/app/main.py#L144)) |

```json
{
  "owner": "student",
  "fileName": "requirements.txt",
  "storedAt": "uploads/requirements.txt",
  "size": 24
}
```

### 5. Errores

| HTTP | Condición | Ejemplo de respuesta |
| --- | --- | --- |
| `401 Unauthorized` | Header ausente o token inválido. | `{"detail":"Invalid token: invalid token"}` ([api/app/main.py:19](../api/app/main.py#L19), [api/app/main.py:28](../api/app/main.py#L28)) |
| `400 Bad Request` | El nombre base queda vacío o el destino escapa del directorio; `filename="."` reproduce el primer caso. | `{"detail":"Invalid filename"}` ([api/app/main.py:41](../api/app/main.py#L41), [api/app/main.py:42](../api/app/main.py#L42), [api/app/main.py:49](../api/app/main.py#L49), [api/app/main.py:50](../api/app/main.py#L50)) |
| `413 Content Too Large` | Más de 5 MiB. | `{"detail":"File exceeds maximum allowed size"}` ([api/app/main.py:137](../api/app/main.py#L137), [api/app/main.py:138](../api/app/main.py#L138), [api/app/main.py:140](../api/app/main.py#L140)) |
| `415 Unsupported Media Type` | Extensión distinta de `.txt`/`.md`. | `{"detail":"Unsupported file type"}` ([api/app/main.py:45](../api/app/main.py#L45), [api/app/main.py:46](../api/app/main.py#L46)) |
| `422 Unprocessable Entity` | Falta el campo `file` o el multipart no se valida. | `{"detail":[{"type":"missing","loc":["body","file"],"msg":"Field required"}]}` ([api/app/main.py:135](../api/app/main.py#L135)) |
| `500 Internal Server Error` | Excepción no controlada al escribir el archivo. | `Internal Server Error` ([api/app/main.py:143](../api/app/main.py#L143)) |

### 6. Notas de seguridad

El nombre se normaliza y se comprueba que el destino quede en uploads, pero no se inspeccionan MIME ni contenido. Un nombre repetido sobrescribe el archivo; `storedAt` expone una ruta local. ([api/app/main.py:41](../api/app/main.py#L41), [api/app/main.py:49](../api/app/main.py#L49), [api/app/main.py:143](../api/app/main.py#L143), [api/app/main.py:144](../api/app/main.py#L144))

## `GET /api/backend-health`

### 1. Propósito de negocio

Consulta el health endpoint configurado o `http://localhost:8080/q/health` si falta `AUTH_HEALTH_URL`. ([api/app/main.py:147](../api/app/main.py#L147), [api/app/main.py:148](../api/app/main.py#L148))

### 2. Autenticación y headers

Requiere `Authorization: Bearer <token>`. No requiere cuerpo ni `Content-Type`. ([api/app/main.py:147](../api/app/main.py#L147), [api/app/main.py:19](../api/app/main.py#L19))

### 3. Parámetros de request

| Campo/parámetro | Tipo | Obligatorio | Descripción |
| --- | --- | --- | --- |
| Ninguno | No aplica | No | No acepta query ni body. |

Ejemplo completo:

```http
GET /api/backend-health HTTP/1.1
Host: localhost:8000
Authorization: Bearer <token>
```

### 4. Respuesta exitosa

La API devuelve `200 OK`; `status` y `body` reflejan el status y body upstream. La llamada usa timeout de 3 segundos. ([api/app/main.py:150](../api/app/main.py#L150), [api/app/main.py:151](../api/app/main.py#L151))

| Campo | Tipo | Descripción |
| --- | --- | --- |
| `requestedBy` | string | Username extraído del token. |
| `status` | integer | Status HTTP upstream. |
| `body` | string | Body upstream decodificado como UTF-8. ([api/app/main.py:151](../api/app/main.py#L151)) |

```json
{
  "requestedBy": "student",
  "status": 200,
  "body": "{\"healthy\":true}"
}
```

### 5. Errores

| HTTP de la API | Condición | Ejemplo de cuerpo |
| --- | --- | --- |
| `401 Unauthorized` | Header ausente o token inválido. | `{"detail":"Invalid token: invalid token"}` ([api/app/main.py:19](../api/app/main.py#L19), [api/app/main.py:28](../api/app/main.py#L28)) |
| `200 OK` | Upstream devuelve status no 2xx; la API lo copia en `status` y devuelve su body. `503` es ejemplo de status upstream, no de la API. | `{"requestedBy":"student","status":503,"body":"Service Unavailable"}` ([api/app/main.py:150](../api/app/main.py#L150), [api/app/main.py:151](../api/app/main.py#L151)) |
| `200 OK` | Excepción upstream; la API devuelve `status: 0` y `str(error)` en `body`. | `{"requestedBy":"student","status":0,"body":"<mensaje de la excepción>"}` ([api/app/main.py:152](../api/app/main.py#L152), [api/app/main.py:153](../api/app/main.py#L153)) |

### 6. Notas de seguridad

La ruta expone el body upstream o `str(error)` y usa una URL configurada por el servidor. La identidad se obtiene de un token verificado con HMAC. ([api/app/main.py:22](../api/app/main.py#L22), [api/app/main.py:147](../api/app/main.py#L147), [api/app/main.py:153](../api/app/main.py#L153))