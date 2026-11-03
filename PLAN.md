# Plan de correccion - auth

## Alcance y contrato

Este plan cubre H-AUTH-01 a H-AUTH-05 porque los cinco IDs aparecen como `Pendiente` en `HALLAZGOS.md`. `docs/ENDPOINTS.md` no existe; se toma como contrato observado `POST /auth/login` con JSON, validacion 400 para request/campos ausentes, 401 para credenciales invalidas y 200 para validas. En el caso 200 se conservan `token`, `expiresIn`, `user` y sus campos, asi como `debug`, salvo que una revision de contrato acuerde otra cosa. H-AUTH-05 cambia intencionalmente el contenido de respuestas 500 para no revelar excepciones.

La firma y el formato del token cambiaran para cumplir H-AUTH-02. El nombre del campo `token` y las claims necesarias (`sub`/username, role, expiracion, issuer y audience) se proponen como continuidad funcional, pero no se puede certificar compatibilidad con consumidores externos porque estan fuera del alcance y no hay contrato acordado. Coordinar y registrar esa compatibilidad antes del corte; no mantener un fallback Base64 inseguro.

## H-AUTH-01 - Concatenacion de credenciales en SQL

- **Hallazgo:** H-AUTH-01, credenciales concatenadas directamente en SQL.
- **Problema:** valores controlados por el request se interpolan en la clausula `WHERE` y se ejecutan con `Statement`; una entrada puede cambiar el significado de la consulta o hacerla fallar.
- **Cambio propuesto:** preparar el `SELECT` con `username = ? AND password = ?`, enlazar ambos valores con `PreparedStatement` y cerrar los recursos como ahora con try-with-resources. Mantener el comportamiento de usuario encontrado/no encontrado y los codigos HTTP observados.
- **Archivos a tocar:** `auth/src/main/java/com/bcp/workshop/auth/LegacyDatabase.java`, `auth/src/test/java/com/bcp/workshop/auth/AuthResourceTest.java`.
- **Caracterizacion antes del cambio:** ampliar la prueba de integracion para credenciales validas (`student` / `Workshop123!`, 200 y campos actuales), password incorrecto (401) y username/password de prueba que contengan una comilla (401, nunca 500 ni autenticacion de otro usuario). Registrar que el SQL actual falla o interpreta valores por concatenacion solo si la prueba local lo demuestra; no declarar un resultado antes de ejecutar. Despues del cambio, la comilla debe tratarse como dato literal.

## H-AUTH-02 - Token Base64 sin firma

- **Hallazgo:** H-AUTH-02, token Base64 con secreto constante y sin firma.
- **Problema:** el token solo codifica campos legibles y una constante; no permite verificar que lo emitio el servidor ni protege sus claims.
- **Cambio propuesto:** emitir JWT firmado con expiracion y claims explicitas de identidad, rol, issuer y audience. Fijar algoritmos permitidos y obtener el material criptografico de configuracion externa, relacionado con H-AUTH-04. Evaluar la extension de construccion/verificacion JWT soportada por la version de Quarkus del proyecto; cualquier dependencia nueva debe justificarse, verificarse contra advisories y fijarse de forma compatible, sin implementar criptografia propia. No aceptar el formato Base64 como fallback.
- **Archivos a tocar:** `auth/src/main/java/com/bcp/workshop/auth/LegacyTokenUtil.java` o un proveedor JWT con responsabilidad unica, `auth/src/main/java/com/bcp/workshop/auth/AuthResource.java`, `auth/src/main/resources/application.properties`, `auth/pom.xml` solo si se justifica una extension, y `auth/src/test/java/com/bcp/workshop/auth/AuthResourceTest.java`.
- **Caracterizacion antes del cambio:** fijar primero el login valido (200, `token` no nulo, `expiresIn`, estructura `user`) y el invalido (401). Agregar pruebas para validar firma, expiracion, issuer y audience del JWT nuevo, y para rechazar tokens alterados y el formato legado. La prueba de contrato debe tratar el valor de `token` como opaco; coordinar al consumidor antes de cambiar su formato.

## H-AUTH-03 - Contrasenas en texto plano

- **Hallazgo:** H-AUTH-03, contrasenas persistidas y comparadas como texto plano.
- **Problema:** la tabla y los datos iniciales guardan el secreto reversible/visible; una copia de SQLite permite recuperar credenciales.
- **Cambio propuesto:** almacenar un hash lento con salt individual (por ejemplo, PBKDF2-HMAC-SHA-256 con `SecureRandom` y parametros nombrados) y verificar mediante comparacion segura, nunca comparando la contrasena recibida en SQL. Persistir el formato/salt requerido por el algoritmo y migrar filas existentes de manera transaccional e idempotente para no invalidar cuentas durante la actualizacion. No agregar dependencia si se usa la API criptografica del JDK; si se elige BCrypt mediante extension, justificarla y revisar compatibilidad/advisories.
- **Archivos a tocar:** `auth/src/main/java/com/bcp/workshop/auth/LegacyDatabase.java`, posible nuevo `auth/src/main/java/com/bcp/workshop/auth/PasswordHasher.java`, `auth/src/test/java/com/bcp/workshop/auth/AuthResourceTest.java` y cualquier test de base local que se agregue bajo `auth/src/test/`.
- **Caracterizacion antes del cambio:** fijar que el usuario seeded valido sigue recibiendo 200 y que un password incorrecto recibe 401. Agregar una prueba de persistencia que compruebe el formato no reversible del valor guardado y una prueba de migracion sobre una base temporal preexistente con password legado; tras migrar, el login valido debe seguir funcionando y el invalido continuar en 401. No inspeccionar ni modificar datos fuera de `auth/`.

## H-AUTH-04 - Secreto fijo y CORS permisivo

- **Hallazgo:** H-AUTH-04, constante de token en codigo y CORS con origenes permisivos.
- **Problema:** el valor fijo no puede rotarse sin cambiar codigo; `/.*/` permite cualquier origen y amplia las aplicaciones web que pueden iniciar solicitudes cross-origin.
- **Cambio propuesto:** eliminar secretos por defecto del codigo y usar configuracion externa requerida para firma/issuer/audience, sin secretos reales en repositorio ni valores de produccion. Sustituir `quarkus.http.cors.origins=/.*/` por una lista configurable y acotada para desarrollo local; mantener metodos/headers solo si son necesarios para el contrato. Definir comportamiento seguro y explicito cuando falte la configuracion requerida.
- **Archivos a tocar:** `auth/src/main/java/com/bcp/workshop/auth/LegacyTokenUtil.java` o el proveedor JWT, `auth/src/main/resources/application.properties`, `auth/pom.xml` solo si la extension de H-AUTH-02 lo requiere, y `auth/src/test/java/com/bcp/workshop/auth/AuthResourceTest.java`.
- **Caracterizacion antes del cambio:** agregar pruebas de preflight CORS para un origen local permitido y otro no permitido, preservando el acceso previsto de desarrollo. Comprobar que una configuracion JWT ausente no emite tokens y que configurar material de prueba permite mantener la respuesta 200 y los campos observados. Usar secretos aislados de test, no secretos reales.

## H-AUTH-05 - Respuesta expone excepciones

- **Hallazgo:** H-AUTH-05, respuestas 500 incluyen mensaje y clase de excepcion.
- **Problema:** detalles internos de SQL, rutas o implementacion pueden llegar al cliente; `LegacyDatabase` tambien imprime stack traces directamente y oculta fallos devolviendo `null`.
- **Cambio propuesto:** responder con un mensaje generico y estable manteniendo HTTP 500, registrar el detalle solo en el logger del servidor y no devolver la clase de excepcion. Reemplazar `printStackTrace` y evitar convertir errores de persistencia en credenciales invalidas; separar error de autenticacion de error operativo usando excepciones especificas y manejo en una sola capa.
- **Archivos a tocar:** `auth/src/main/java/com/bcp/workshop/auth/AuthResource.java`, `auth/src/main/java/com/bcp/workshop/auth/LegacyDatabase.java`, posible excepcion de persistencia bajo `auth/src/main/java/com/bcp/workshop/auth/`, y `auth/src/test/java/com/bcp/workshop/auth/AuthResourceTest.java`.
- **Caracterizacion antes del cambio:** preservar pruebas de 200 para credenciales validas y 401 para invalidas; agregar una prueba unitaria con un `LegacyDatabase` de prueba que lance una excepcion controlada. Antes del cambio, registrar que la respuesta expone message/exception; despues, exigir 500 con mensaje generico, sin nombre ni texto de la excepcion en el body, y confirmar que el detalle solo se registra en servidor.

## Secuencia y salida

1. Escribir primero las pruebas de caracterizacion en `auth/src/test/` y ejecutarlas con `mvn test` desde `auth/`; el test existente cubre solo login valido y no constituye evidencia para casos invalidos o comillas.
2. Implementar SQL parametrizado y hash de contrasenas preservando usuarios y codigos observados; despues migrar token/configuracion y errores en cambios revisables.
3. Coordinar la incompatibilidad del formato JWT con los consumidores externos sin leer ni modificar componentes fuera de alcance. Si no se obtiene esa evidencia, dejar el riesgo pendiente; no afirmar aprobacion.
4. Repetir pruebas desde `auth/`, comprobar cobertura del codigo modificado con la meta de 85% y registrar solo resultados reales. Mantener metodos con una responsabilidad, reutilizar validacion/hash sin duplicacion, evitar anidamiento profundo y definir constantes/configuracion con nombre.
5. Actualizar estados de `HALLAZGOS.md` solo despues de implementar y verificar; este plan no cambia estados ni registra pruebas ejecutadas.