## Por qué

El Issue [#22 (HU-01 — Bootstrap seguro de autenticación)](https://github.com/user-bcp-student24/ai-labs/issues/22) registra el hallazgo H-AUTH-08: el componente `auth/` siembra al iniciar cuentas con credenciales fijas (`student/Workshop123!` y `trainer/Trainer123!`), sin distinguir entorno. La cuenta de rol `TRAINER` obtiene un token firmado con su rol, por lo que un bootstrap predecible permite obtener una identidad autenticada con privilegios en producción.

Evidencia verificada en el repositorio:

- La siembra está en `auth/src/main/java/com/bcp/workshop/auth/LegacyDatabase.java` (método `initialize`, `INSERT OR IGNORE` de ambas cuentas). Se ejecuta sin importar el perfil.
- `auth/src/test/java/com/bcp/workshop/auth/AuthResourceTest.java` depende de la cuenta sembrada `student`/`Workshop123!`; por eso, al retirar la siembra, las pruebas de login necesitan otro mecanismo de preparación de usuarios.

## Qué cambia

- Definir la política de inicialización de cuentas de `auth/` por entorno: en producción no se siembran credenciales fijas; el aprovisionamiento de cuentas se hace mediante un mecanismo controlado y externo al código.
- Mantener en pruebas un mecanismo de preparación de usuarios con valores de prueba aislados, sin credenciales reales ni de producción.
- Documentar la política elegida y sus requisitos operativos en configuración o documentación revisable.
- Asegurar que los logs de inicialización y login no contengan credenciales, secretos ni tokens.

## Alcance

- Inicialización de cuentas en `auth/` (siembra de `legacy_users` y su perfil de ejecución).
- Comportamiento de `POST /auth/login` ante cuentas no aprovisionadas.
- Consulta de credenciales de `LegacyDatabase.findByCredentials`, parametrizada (aprobada como P1).
- Mecanismo de preparación de usuarios en el entorno de pruebas de `auth/`.
- Documentación de la política de bootstrap.

## Fuera de alcance

- Cambiar el emisor, la firma o el formato de los tokens (`LegacyTokenUtil`), salvo que sea necesario para no romper el flujo autorizado.
- Hash de contraseñas, migración a BCrypt o cambios al modelo de persistencia más allá de la siembra (otros hallazgos de `auth/`).
- Refactorización por capas de `AuthResource`/`LegacyDatabase` más allá de la consulta de credenciales; se trata en otros cambios.
- Cualquier cambio en `api/` o `web/`.
- Definir la política de aprovisionamiento final de usuarios reales: el Issue indica que todavía no está acordada; esta propuesta fija solo los requisitos verificables y deja la elección concreta del mecanismo para la fase de diseño.

## Comportamiento que debe preservarse

Baseline: el código observado de `POST /auth/login` (`AuthResource.login`), porque `docs/ENDPOINTS.md` documenta solo `api/` y no contiene un contrato de login.

- Ruta `POST /auth/login` con cuerpo JSON `username` y `password`.
- `400` con `message` cuando el cuerpo es nulo, `username` vacío o `password` vacío.
- `200` con `token`, `expiresIn` y `user` (`username`, `displayName`, `role`) cuando las credenciales corresponden a una cuenta aprovisionada.
- `401` con `message` cuando la cuenta no existe o la contraseña no coincide.
- Los tokens siguen firmándose con `workshop.token.secret` (`WORKSHOP_TOKEN_SECRET`), sin cambiar el formato.
- El campo `debug` de la respuesta exitosa es comportamiento actual; no se elimina en este cambio salvo decisión explícita.

## Discrepancias con el Issue

- El Issue cita `UserRepository.java` y `AuthService.java`, que no existen en `auth/`. La siembra real está en `LegacyDatabase.java`.
- El Issue cita `auth/src/main/resources/application.properties:3` como evidencia de credenciales; esa línea configura el host HTTP y no contiene credenciales. El secreto de firma está en `workshop.token.secret`.
- El Issue indica que H-AUTH-02 figura como Resuelto en `HALLAZGOS.md`, pero el archivo no contiene entradas `H-AUTH-*`. La trazabilidad de H-AUTH-08 debe registrarse en la matriz antes de implementar.

## Impacto

- Código afectado previsto: `auth/` (`LegacyDatabase`, pruebas de `AuthResourceTest`, configuración en `application.properties`).
- Pruebas: nueva prueba de integración con base temporal en perfil de producción; pruebas del endpoint para cuentas no aprovisionadas; la suite de login debe pasar sin credenciales reales.
- Cobertura: meta del código modificado en `auth/` de 85% o superior, según `AGENTS.md`.
- Sin impacto esperado en `api/` ni `web/`.
