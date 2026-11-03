# Hallazgos

| id | componente | hallazgo | tipo | explicacion | evidencia (archivo:linea) | severidad | estado |
|---|---|---|---|---|---|---|---|
| H-AUTH-01 | auth | Concatenacion de credenciales en SQL | Vulnerabilidad | `username` y `password` se insertan directamente en la clausula `WHERE` y la consulta se ejecuta con `Statement`. Una entrada con sintaxis SQL puede alterar la condicion de autenticacion en vez de tratarse como valor literal. | auth/src/main/java/com/bcp/workshop/auth/LegacyDatabase.java:31-35 | alta | Pendiente |
| H-AUTH-02 | auth | Token Base64 con secreto constante, sin firma | Vulnerabilidad | El token es una codificacion Base64 de username, role, expiracion y un valor constante; Base64 no firma ni protege esos campos. Un consumidor que confie en ese contenido no puede distinguir un token emitido de uno fabricado. | auth/src/main/java/com/bcp/workshop/auth/LegacyTokenUtil.java:8-15, auth/src/main/java/com/bcp/workshop/auth/AuthResource.java:39-42 | alta | Pendiente |
| H-AUTH-03 | auth | Contrasenas almacenadas y verificadas en texto plano | Vulnerabilidad | La tabla declara una columna `password` sin hash y los usuarios de ejemplo insertan contrasenas literales; la consulta compara directamente el valor recibido. Una copia de la base expone las credenciales utilizables. | auth/src/main/java/com/bcp/workshop/auth/LegacyDatabase.java:22-24, auth/src/main/java/com/bcp/workshop/auth/LegacyDatabase.java:32 | alta | Pendiente |
| H-AUTH-04 | auth | Secreto de token fijo y CORS demasiado permisivo | Vulnerabilidad | La constante del token esta en codigo y CORS acepta cualquier origen (`/.*/`). Esto deja la configuracion de autenticacion embebida y habilita solicitudes cross-origin desde origenes arbitrarios; el secreto no constituye una firma criptografica en el flujo actual. | auth/src/main/java/com/bcp/workshop/auth/LegacyTokenUtil.java:8, auth/src/main/resources/application.properties:4-7 | alta | Pendiente |
| H-AUTH-05 | auth | Respuesta de error expone detalles internos | Vulnerabilidad | La respuesta 500 devuelve `error.getMessage()` y el nombre de clase de la excepcion. El cliente puede recibir detalles de implementacion que deberian permanecer en logs controlados. | auth/src/main/java/com/bcp/workshop/auth/AuthResource.java:54-58 | media | Pendiente |
| H-AUTH-06 | auth | Resource concentra validacion, persistencia, negocio y respuesta | Refactor | `login` valida campos, llama directamente a la base, decide autenticacion, crea el token y ensambla la respuesta HTTP. El acoplamiento dificulta probar y cambiar cada responsabilidad sin efectos colaterales. | auth/src/main/java/com/bcp/workshop/auth/AuthResource.java:24-52 | media | Pendiente |
| H-AUTH-07 | auth | Versiones de Quarkus y Commons Text requieren evaluacion SCA | Sugerencia | El manifiesto declara Quarkus 3.27.4 y Commons Text 1.9, los candidatos indicados por RETO. La version por si sola no confirma un CVE; falta revisar advisories y compatibilidad antes de recomendar un cambio. | auth/pom.xml:13, auth/pom.xml:49-50 | baja | Pendiente |

## Contrato observado

No existe `docs/ENDPOINTS.md`; no hay contrato acordado documentado que pueda contrastarse. El codigo observa `POST /auth/login` con JSON: requiere `username` y `password` no nulos ni vacios (400 si faltan); `client` se acepta en el DTO pero no se usa. Credenciales validas responden 200 con `token`, `expiresIn`, `user` (`username`, `displayName`, `role`) y `debug`. Credenciales no validas responden 401 con un mensaje que incluye el username. Una excepcion no manejada por capas inferiores responde 500 incluyendo mensaje y clase de excepcion.

## Riesgos pendientes

- No se ejecutaron pruebas ni se reprodujo la entrada SQL; la confirmacion de este Discovery es estatica, basada en la construccion/ejecucion de la consulta.
- No se evaluaron advisories de Quarkus ni Commons Text; H-AUTH-07 no afirma que las versiones sean vulnerables.
- No se comprobo el comportamiento de consumidores externos del token ni existe contrato acordado para su formato.

## Hallazgos candidatos adicionales - auth (discovery posterior)

Nota de alcance: esta ronda solo investigo `auth/`; la lectura de `api/app/security.py` y `api/tests/test_api.py` fue unicamente para contrastar el contrato del token consumido por otro componente (evidencia de frontera), sin modificar ni auditar el resto de `api/`.

### H-AUTH-08 - Token legado Base64 incompatible con el JWT que `api` ya exige
- Estado: CANDIDATO
- Evidencia: `auth/src/main/java/com/bcp/workshop/auth/LegacyTokenUtil.java:7-16` genera `Base64(username|role|expiry|SECRET)`, una cadena sin la forma `header.payload.signature`. `api/app/security.py:18-44` decodifica el header `Authorization: Bearer` como JWT HS256 y exige claims `exp/iss/aud/sub`. El propio `api/tests/test_api.py:117-124` (`test_rejects_legacy_base64_token`) confirma que ese formato es rechazado con 401.
- Impacto: un login exitoso en `POST /auth/login` (200, `token` no nulo) produce un valor que no puede usarse para autenticar contra `api` (por ejemplo `GET /api/tasks`); el flujo end-to-end descrito implicitamente por el contrato (login en `auth` y luego usar ese `token` como credencial portadora en `api`) esta roto hoy, aunque cada componente pase sus propias pruebas en aislamiento.
- Prioridad propuesta: alta.
- Contrato potencialmente afectado: formato de `token` devuelto por `POST /auth/login` y el contrato de `verified_identity` en `api` (claims `sub`, `role`, `exp`, `iss`, `aud`).
- Como validarlo: levantar `auth` y `api` (o ejecutar sus pruebas), tomar el `token` de un login valido en `auth` y enviarlo como credencial portadora a un endpoint protegido de `api`; confirmar si responde 401. Alternativamente, ejecutar `api/tests/test_api.py::test_rejects_legacy_base64_token` con un token generado por `LegacyTokenUtil.create` real.

### H-AUTH-09 - Diferencia de tiempo entre usuario inexistente y password incorrecta
- Estado: CANDIDATO
- Evidencia: `auth/src/main/java/com/bcp/workshop/auth/LegacyDatabase.java:46` evalua `!result.next() || !PASSWORD_HASHER.verify(password, result.getString("password"))`. Por cortocircuito de `||`, si el usuario no existe nunca se ejecuta `PasswordHasher.verify` (PBKDF2 con 210000 iteraciones, `PasswordHasher.java:14-17`); si el usuario existe pero el password es incorrecto, si se ejecuta.
- Impacto: aunque el mensaje de error es identico en ambos casos (`Invalid user {username} or password`, `AuthResource.java:40`), el tiempo de respuesta puede diferir de forma medible y permitir enumerar usuarios validos sin depender del contenido de la respuesta.
- Prioridad propuesta: media.
- Contrato potencialmente afectado: `POST /auth/login` (confidencialidad de existencia de usuario; el codigo/mensaje de respuesta no cambiaria).
- Como validarlo: medir con repeticiones (por ejemplo decenas de llamadas) el tiempo de respuesta de `POST /auth/login` para un username inexistente vs. un username existente con password incorrecta, y comparar las distribuciones de latencia.

### H-AUTH-10 - Seed de credenciales conocidas sin condicion de perfil, incluido `%prod`
- Estado: CANDIDATO
- Evidencia: `auth/src/main/java/com/bcp/workshop/auth/LegacyDatabase.java:30-31` invoca `insertDefaultUser` para `student`/`trainer` con contraseñas fijas del repositorio dentro de `initialize()`, sin verificar el perfil activo ni una bandera de entorno para omitirlo. `auth/src/main/resources/application.properties:3` habilita `%prod.quarkus.http.host=0.0.0.0` para el mismo binario, y `compose.yaml` no define variable alguna para deshabilitar el seed.
- Impacto: si el artefacto se despliega tal cual (perfil `prod`), cualquiera que conozca las credenciales de ejemplo publicas en el repositorio puede autenticarse, incluyendo el rol `TRAINER`.
- Prioridad propuesta: media (alta si se confirma despliegue real sin variables adicionales).
- Contrato potencialmente afectado: `POST /auth/login` (usuarios validos preexistentes), inicializacion de `LegacyDatabase`.
- Como validarlo: ejecutar el servicio con un perfil/variable que simule produccion y confirmar si los usuarios `student`/`trainer` igual se crean; revisar si existe o deberia existir una variable de entorno que condicione el seed fuera de desarrollo/pruebas.

### H-AUTH-11 - Estado "Pendiente" de H-AUTH-01, H-AUTH-03, H-AUTH-05 y la parte CORS de H-AUTH-04 no coincide con el codigo actual
- Estado: CANDIDATO
- Evidencia: el codigo ya usa `PreparedStatement` parametrizado (`LegacyDatabase.java:40-44`), hash PBKDF2 con migracion de contraseñas en texto plano (`LegacyDatabase.java:57-71` y `74-95`, `PasswordHasher.java`), una respuesta 500 generica sin mensaje ni clase de excepcion (`AuthResource.java:54-58`) y CORS restringido al origen configurado por `AUTH_CORS_ORIGINS` (`application.properties:4`). Existen pruebas de caracterizacion que cubren estos casos: `AuthResourceTest.treatsQuoteInUsernameAsData`, `AuthResourceTest.doesNotReturnInternalExceptionDetails`, `AuthResourceTest.doesNotAllowCorsFromUnlistedOrigin`, `LegacyDatabaseTest.migratesPlaintextPasswordsAndKeepsExistingHashes`, `PasswordHasherTest`. En esta inspeccion se observaba un secreto fijo en `LegacyTokenUtil.java:8`; el cambio local registrado para H-AUTH-08 lo reemplaza por configuracion externa.
- Impacto: riesgo de reinvertir esfuerzo o de reportar como abierto un riesgo ya mitigado si no se reconcilia la tabla antes de continuar con la migracion a JWT (H-AUTH-02) prevista en `PLAN.md`.
- Prioridad propuesta: baja (gestion de la evidencia, no vulnerabilidad nueva).
- Contrato potencialmente afectado: ninguno directo; afecta la trazabilidad de `HALLAZGOS.md`/`PLAN.md`.
- Como validarlo: re-ejecutar `mvn test` en `auth/` y confirmar que los tests citados pasan contra el codigo actual; contrastar manualmente cada linea citada contra la fila correspondiente en la tabla antes de cerrar o reabrir el estado.

Estado al cerrar discovery: H-AUTH-08 a H-AUTH-11 se registraron como CANDIDATO para revision humana. H-AUTH-08 fue aprobado posteriormente; su implementación local y validación se documentan a continuación. H-AUTH-09 a H-AUTH-11 siguen pendientes de revisión y no se crearon issues.

## Evidencia de implementación local - H-AUTH-08

- Estado: implementado en la rama local `day1/prompting`; pendiente de revisión humana. Durante el Día 1 no se crea PR ni se hace push.
- Cambio: `auth` emite JWT HS256 con `sub`, `role`, `exp`, `iss` y `aud`, usando `WORKSHOP_JWT_SECRET` (mínimo 32 bytes), `WORKSHOP_JWT_ISSUER` y `WORKSHOP_JWT_AUDIENCE`. `compose.yaml` comparte las variables entre `auth` y `api` y exige que el secreto sea provisto externamente. `POST /auth/login` conserva la estructura de respuesta y `expiresIn`.
- Caracterización: `python tools/lab.py test auth` falló antes del cambio en `AuthResourceTest.issuesApiCompatibleHs256Token` (token legado: 1 segmento, se esperaban 3).
- Validación: `python tools/lab.py test auth` pasó: 12 pruebas, 0 fallos/errores; JaCoCo reportó 100% de líneas y ramas para `AuthResource` y `LegacyTokenUtil`.
- Regresión: `python tools/lab.py test api` pasó: 25 pruebas y 100% de cobertura total de esa suite.
- Integración local: login real en `auth` dio 200; el token resultante obtuvo 200 en `GET /api/tasks`; el token alterado obtuvo 401.
- Pendiente: `docker compose config --quiet` no pudo ejecutarse porque Docker no está instalado/disponible en el entorno. No se verificó un despliegue Compose.
