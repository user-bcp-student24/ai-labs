## Contexto

- Componente: `auth/` (Quarkus 3.27, Java 21, SQLite vía JDBC). `api/` y `web/` no cambian.
- `LegacyDatabase.initialize()` (`@PostConstruct`) crea `legacy_users` y ejecuta `INSERT OR IGNORE` de `student/Workshop123!` y `trainer/Trainer123!` sin condicionar por perfil. La URL sale de `System.getenv("AUTH_DB_URL")` con valor por defecto `jdbc:sqlite:./data/workshop.db`, leída en un campo `static final`.
- `findByCredentials` concatena `username` y `password` en el SQL y, ante excepciones, hace `printStackTrace()`.
- `AuthResource.login` valida el cuerpo, llama a `findByCredentials`, firma con `LegacyTokenUtil.create` (HMAC-SHA256, TTL 3600 s, payload `username|role|exp` en Base64) y responde con `token`, `expiresIn`, `user` y `debug`.
- `application.properties` define `%prod.quarkus.http.host` y `%test.workshop.token.secret=test-only-token-secret`. No hay control de siembra por perfil.
- `compose.yaml` ejecuta `auth` desde el jar empaquetado (`java -jar quarkus-run.jar`), que arranca con el perfil `prod`.
- Pruebas actuales: `AuthResourceTest` (`@QuarkusTest`) inicia sesión con `student/Workshop123!`; `LegacyTokenUtilTest` valida formato y firma del token.

## Objetivos

- Sin cuentas con credenciales fijas tras inicializar con perfil `prod` sobre base nueva (proposal, requisito 1).
- Ninguna respuesta `200` con `token` sin una cuenta aprovisionada válida (requisito 2).
- Pruebas de login con una cuenta de prueba aislada, sin `student/Workshop123!` (requisito 4).
- Política de bootstrap descrita en `application.properties` y en la documentación de `auth/` (requisito 5).
- Logs de inicialización y login sin contraseñas, secretos ni tokens (requisito 6).

## No objetivos

- Hash de contraseñas (BCrypt u otro): otro cambio.
- Cambiar emisor, firma, formato o TTL del token.
- Refactorizar `AuthResource` o separar capas más allá de lo necesario para testear la siembra.
- Mecanismo de aprovisionamiento real de cuentas de producción (CLI o API de administración): se decide aparte, pero bloquea el despliegue (ver riesgos).
- Cambios en `api/`, `web/`, `compose.yaml`.

## Contratos protegidos

Se fijan con pruebas de caracterización antes de cambiar código:

| Contrato | Verificación |
| --- | --- |
| `POST /auth/login` `200` con `token`, `expiresIn=3600`, `user{username,displayName,role}`, `debug` | Test de login válido |
| `400` `Request is null`, `Username is required`, `Password is required` | Tests de cuerpo nulo, usuario vacío y contraseña vacía |
| `401` con `message` `Invalid user <u> or password` | Test de usuario inexistente y de contraseña incorrecta |
| `displayName` escapado HTML (`StringEscapeUtils.escapeHtml4`) | Cuenta de prueba con `displayName` con caracteres especiales |
| Token con formato `base64(username|role|exp).hmac` firmado con `workshop.token.secret` | Verificación HMAC en el test de login, como en `LegacyTokenUtilTest` |
| `workshop.token.secret` / `WORKSHOP_TOKEN_SECRET` | Sin cambio de nombre ni de origen |
| `AUTH_DB_URL` como variable de entorno de la base | Sin cambio de nombre; se mantiene el mapeo |

No se fija como contrato el comportamiento ante inyección SQL (ver riesgo R1).

## Componentes afectados

- `LegacyDatabase.java`: siembra condicionada, URL de base inyectable, consulta, logs.
- `AuthResource.java`: sin cambios funcionales esperados.
- `application.properties`: nueva clave de siembra y claves `%test`.
- `src/test/java/.../AuthResourceTest.java`: usa la cuenta de prueba.
- Nueva clase de prueba (en `src/test`) que prepara la cuenta de prueba en una base temporal.
- Documentación: sección de `auth/` en `docs/` y fila para H-AUTH-08 en `HALLAZGOS.md` (ambos archivos generales; se edita solo la sección de `auth`).

## Decisiones técnicas

### D1. Siembra controlada por configuración

- Clave `workshop.bootstrap.demo-users.enabled`, `boolean`, por defecto `false`. Se activa solo si se configura explícitamente.
- Razón: el perfil `prod` del jar empaquetado usa el valor por defecto, así que producción no siembra. Es más simple que detectar el perfil con `LaunchMode`, que no distingue bien el jar empaquetado de otros entornos.
- Alternativas descartadas:
  - Eliminar la siembra por completo: deja sin forma de tener cuentas de demostración en desarrollo sin cambiar el código.
  - Bootstrap por variables de entorno (`AUTH_BOOTSTRAP_USER` y contraseña): la contraseña quedaría en texto plano (la columna `password` no tiene hash) y en el entorno del contenedor; además arrastra el problema de hash. Se considera en el cambio de hash.
  - Mantener la siembra en `prod` con contraseñas distintas: sigue siendo credencial fija en el repositorio.

### D2. Cuenta de prueba aislada

- Una clase de prueba en `src/test` inserta una cuenta `auth-test-user` con contraseña tomada de `%test.workshop.test-user.password` (valor de prueba en `application.properties`) y `displayName` con caracteres HTML para cubrir el escape.
- `AuthResourceTest` pasa a usar esa cuenta. `student/Workshop123!` deja de usarse en pruebas.
- Razón: las pruebas no dependen de la siembra y no hace falta activar `demo-users` en `%test`.

### D3. URL de base inyectable para pruebas

- Sustituir el `static final DB_URL` por `@ConfigProperty(name = "auth.db.url", defaultValue = "jdbc:sqlite:./data/workshop.db")`.
- Quarkus mapea `auth.db.url` a la variable de entorno `AUTH_DB_URL`, por lo que el contrato de entorno no cambia.
- `%test.auth.db.url=jdbc:sqlite:target/auth-test.db` aísla la base de pruebas de `data/`.
- Para la prueba de "prod sin siembra" se usa un `QuarkusTestProfile` con `demo-users.enabled=false` y base temporal nueva.

### D4. Consulta y logs

- Propuesta: cambiar `findByCredentials` a `PreparedStatement` con parámetros (ver R1). Cambio mínimo en un único método, mismo resultado para credenciales válidas.
- Sustituir `printStackTrace()` por un logger que registre la clase de excepción sin el SQL ni los parámetros.
- `AuthResource` devuelve `error.getMessage()` en `500`; no se cambia aquí y queda anotado como hallazgo pendiente.

## Pruebas de caracterización (antes de modificar comportamiento)

Escritas y ejecutadas en verde contra el código actual, en `AuthResourceTest` o una clase nueva:

1. Login válido: `200`, `token` no nulo, `expiresIn == 3600`, `user.username`, `user.role`, `debug` presente.
2. Verificación HMAC del token devuelto con el secreto de prueba y `exp` futuro.
3. `displayName` escapado HTML en la respuesta.
4. Cuerpo nulo o vacío: `400`. Documentar el código y el mensaje observados antes de fijarlos.
5. `username` en blanco: `400` `Username is required`; `password` en blanco: `400` `Password is required`.
6. Usuario inexistente y contraseña incorrecta: `401` con `message` `Invalid user <u> or password`, sin campo `token`.

Estas pruebas deben pasar antes y después del cambio; cualquier diferencia es regresión salvo que el requisito la cambie.

## Estrategia incremental

1. Pruebas de caracterización (puntos 1 a 6) sobre el código actual; todas en verde.
2. Introducir `auth.db.url` y la cuenta de prueba (D2, D3); `AuthResourceTest` migrado. Sin cambio funcional.
3. Añadir `workshop.bootstrap.demo-users.enabled` con valor `false` por defecto y envolver la siembra; prueba `prod` sin siembra con base temporal nueva.
4. Prueba de login sin cuenta: `401`, sin `token`, con base vacía.
5. Parametrizar `findByCredentials` (si se aprueba R1) y repetir las pruebas de caracterización y de inyección.
6. Logs: reemplazar `printStackTrace`; prueba que la salida de inicialización y de un login fallido no contiene la contraseña ni el token (captura de `System.err`/logger en la prueba).
7. Documentación: sección de `auth/` y fila H-AUTH-08 en `HALLAZGOS.md`.
8. Ejecutar la suite de `auth/` y revisar cobertura del código modificado (meta 85%).

Cada paso debe ser un cambio revisable y dejar la suite en verde.

## Riesgos y trade-offs

- R1 (crítico para el criterio de "sin token sin cuenta"): `findByCredentials` concatena SQL. Con una cuenta cualquiera en la base, un `username` como `x' OR 1=1 --` devuelve la primera fila y emite token aunque el usuario no exista. Quitar la siembra no elimina este bypass; solo lo oculta en una base vacía. Recomendación: incluir la consulta parametrizada en este cambio y ampliar el alcance del proposal. Requiere aprobación.
- R2: `compose.yaml` ejecuta `auth` en perfil `prod`. Tras el cambio, el flujo de demostración `student/Workshop123!` del `web` deja de funcionar en Docker hasta que exista un mecanismo de aprovisionamiento. Se acepta como consecuencia del Issue; requiere aviso al equipo.
- R3: bases existentes con las cuentas sembradas. `INSERT OR IGNORE` no las borra, y el cambio de código no las elimina. Hace falta un paso explícito de limpieza documentado (o un script), con copia previa de la base. No se hace automáticamente al arrancar.
- R4: `debug` y el mensaje `Invalid user <u>` reflejan entrada del cliente; se mantienen por contrato, con riesgo de enumeración de usuarios. Fuera de alcance.
- R5: el escape HTML y la firma dependen de `commons-text` y de la clave; sin cambio de dependencias.
- Trade-off D1: el valor por defecto `false` es seguro, pero en desarrollo hay que activar la clave explícitamente para tener cuentas de demostración.

## Decisiones abiertas (requieren confirmación)

1. Resuelta: la consulta parametrizada (R1) se incluye en este cambio; ver sección 7 de tasks.md.
2. Si `demo-users.enabled` debe ser `true` en el perfil `dev` para mantener la demostración local.
3. Mecanismo de aprovisionamiento de cuentas reales (bloquea el uso de `auth` en Docker y en producción).
4. Procedimiento de limpieza de cuentas sembradas en bases existentes (R3).

## Rollback

- Revertir el commit del cambio restaura la siembra incondicional y `printStackTrace`.
- Si la limpieza de R3 ya se ejecutó, restaurar la copia previa de la base para recuperar las cuentas de demostración.
- Poner `workshop.bootstrap.demo-users.enabled=true` en el entorno restaura la siembra sin revertir código (solo para entornos no productivos).
