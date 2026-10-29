# Tareas: auth-bootstrap-seguro

Unidad de trabajo del producto: GitHub Issue [#22 (HU-01, bootstrap seguro de autenticación)](https://github.com/user-bcp-student24/ai-labs/issues/22). Componente: `auth/`. Este archivo es el checklist de implementación del cambio OpenSpec; el alcance y los requisitos están en `proposal.md`, `specs/auth-bootstrap/spec.md` y `design.md`.

Comandos de validación: desde la raíz, `python tools/lab.py test auth`; o dentro de `auth/`, `mvn test`. Ningún paso crea ramas, hace push ni abre PR.

## 1. Caracterización del comportamiento actual (sin cambios de producción)

- [x] 1.1 Añadir prueba de login válido con `student/Workshop123!`: `200`, `token` no nulo, `expiresIn == 3600`, `user.username`, `user.role`, `debug` presente.
- [x] 1.2 Añadir prueba que verifica la firma HMAC-SHA256 del token devuelto con `test-only-token-secret` y un `exp` futuro.
- [x] 1.3 Añadir pruebas de `400`: cuerpo nulo o vacío, `username` en blanco, `password` en blanco; fijar el código y el mensaje observados.
- [x] 1.4 Añadir pruebas de `401`: usuario inexistente y contraseña incorrecta; comprobar `message` `Invalid user <u> or password` y ausencia de `token`.
- [x] 1.5 Ejecutar la suite de `auth/`; todas las pruebas de caracterización deben pasar sobre el código actual.

## 2. Preparación de pruebas aisladas (sin cambiar comportamiento)

- [x] 2.1 Sustituir `DB_URL` estático en `LegacyDatabase` por `@ConfigProperty(name = "auth.db.url", defaultValue = "jdbc:sqlite:./data/workshop.db")`; verificar que `AUTH_DB_URL` sigue funcionando.
- [x] 2.2 Añadir `%test.auth.db.url=jdbc:sqlite:target/auth-test.db` en `application.properties`.
- [x] 2.3 Añadir `%test.workshop.test-user.password` con un valor de prueba en `application.properties`.
- [x] 2.4 Crear en `src/test` una clase que prepare la cuenta `auth-test-user` (con `displayName` con caracteres HTML) en la base de pruebas.
- [x] 2.5 Migrar `AuthResourceTest` para usar `auth-test-user`; las pruebas de caracterización de la sección 1 deben seguir en verde.

## 3. Siembra condicionada por configuración

- [x] 3.1 Añadir `workshop.bootstrap.demo-users.enabled` con valor `false` por defecto en `application.properties`.
- [x] 3.2 Envolver en `LegacyDatabase.initialize()` los `INSERT OR IGNORE` de `student` y `trainer` tras esa clave; sin otros cambios de lógica.
- [x] 3.3 Prueba con perfil de producción (`QuarkusTestProfile`) y base temporal nueva: no existe cuenta `student` ni `trainer`; `POST /auth/login` con `student/Workshop123!` responde `401` sin `token`. Cubre el escenario de la spec "Inicialización en producción con base nueva" y "Login con credenciales fijas antiguas".
- [x] 3.4 Prueba de login sin cuenta aprovisionada: base vacía, `401`, sin `token` ni `expiresIn`. Cubre "Cuenta inexistente".
- [x] 3.5 Prueba de siembra activada explícitamente (`demo-users.enabled=true`) que confirma que el mecanismo sigue disponible para entornos no productivos.

## 4. Logs sin credenciales ni tokens

- [x] 4.1 Sustituir `printStackTrace()` en `LegacyDatabase` por un logger que registre la clase de excepción sin SQL ni parámetros.
- [x] 4.2 Prueba que captura la salida de inicialización, un login fallido y uno exitoso, y verifica que no aparecen la contraseña, el valor de `workshop.token.secret` ni el token emitido.

## 5. Documentación y trazabilidad

- [x] 5.1 Comentar en `application.properties` la política de bootstrap por entorno, sin valores de credenciales.
- [x] 5.2 Añadir una sección de `auth/` en `docs/TESTING.md` con las pruebas añadidas; no modificar las secciones de `api/` ni `web/`.
- [x] 5.3 Añadir la entrada H-AUTH-08 en la sección de `auth` de `HALLAZGOS.md`, con su estado de avance.

## 6. Validación y revisión

- [x] 6.1 Ejecutar la suite de `auth/` completa y revisar que todas las pruebas pasan.
- [x] 6.2 Revisar el reporte de JaCoCo: cobertura del código modificado de `auth/` igual o superior a 85%.
- [x] 6.3 Revisar la salida de las pruebas de logs: no contiene credenciales, secretos ni tokens.
- [x] 6.4 Ejecutar `openspec validate auth-bootstrap-seguro`.
- [ ] 6.5 Revisión humana del cambio antes de integrarlo; no integrar ni hacer push sin aprobación.

## 7. Consulta parametrizada (P1, aprobada)

- [x] 7.1 Sustituir la concatenación SQL de `findByCredentials` por `PreparedStatement` con parámetros; mismo resultado para credenciales válidas.
- [x] 7.2 Añadir prueba de regresión: username y password con comillas y operadores SQL devuelven `401` sin `token`.
- [x] 7.3 Ejecutar la suite de `auth/` y comprobar que las pruebas de caracterización siguen en verde.

## Pendiente de decisión (no ejecutar hasta aprobación)

Estas tareas dependen de las decisiones abiertas de `design.md`. No forman parte del checklist activo.

- P1. Incorporada como sección 7 tras aprobación del alcance.
- P2. Activar `demo-users.enabled` en el perfil `dev`. Decisión sobre la demostración local.
- P3. Mecanismo de aprovisionamiento de cuentas reales. Bloquea el uso de `auth` en Docker y en producción; se decide en un cambio aparte.
- P4. Limpieza de cuentas sembradas en bases existentes, con copia previa (riesgo R3).
