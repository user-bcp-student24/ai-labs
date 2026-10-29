## Purpose

Define el comportamiento verificable de la inicialización de cuentas y del login de `auth/` tras retirar las credenciales de bootstrap fijas (Issue #22, H-AUTH-08).

## ADDED Requirements

### Requirement: Sin credenciales fijas en producción
En perfil de producción, la inicialización de una base de datos nueva SHALL NOT crear cuentas accesibles con credenciales de bootstrap fijas.

#### Scenario: Inicialización en producción con base nueva
- **WHEN** el servicio `auth/` se inicializa con el perfil de producción sobre una base de datos temporal vacía
- **THEN** no existe ninguna cuenta autenticable con `student`/`Workshop123!` ni con `trainer`/`Trainer123!`

#### Scenario: Login con credenciales fijas antiguas en producción
- **WHEN** se envía `POST /auth/login` con `student`/`Workshop123!` sobre la base inicializada en producción
- **THEN** la respuesta es `401` con `message` y el cuerpo no contiene el campo `token`

### Requirement: Sin token para cuentas no aprovisionadas
`POST /auth/login` SHALL NOT emitir un token cuando la cuenta no está inicializada o aprovisionada válidamente.

#### Scenario: Cuenta inexistente
- **WHEN** se envía `POST /auth/login` con un `username` que no existe en la base
- **THEN** la respuesta es `401` con `message`, sin los campos `token` ni `expiresIn`

#### Scenario: Contraseña incorrecta para cuenta existente
- **WHEN** se envía `POST /auth/login` con un `username` existente y una contraseña que no coincide
- **THEN** la respuesta es `401` con `message`, sin los campos `token` ni `expiresIn`

#### Scenario: Metacaracteres SQL en credenciales
- **WHEN** se envían `username` y `password` con comillas y operadores SQL sobre una base con cuentas aprovisionadas
- **THEN** las credenciales se tratan como datos, la respuesta es `401` con `message` y no contiene `token` ni `expiresIn`

### Requirement: Contrato de login preservado para cuentas válidas
Para una cuenta aprovisionada válidamente, `POST /auth/login` SHALL responder con el mismo contrato observado hoy.

#### Scenario: Login válido
- **WHEN** se envía `POST /auth/login` con `username`, `password` válidos de una cuenta aprovisionada
- **THEN** la respuesta es `200` con `token`, `expiresIn` y `user` que contiene `username`, `displayName` y `role`

#### Scenario: Cuerpo incompleto
- **WHEN** se envía `POST /auth/login` sin cuerpo, con `username` vacío o con `password` vacío
- **THEN** la respuesta es `400` con `message`, igual que hoy

### Requirement: Preparación de usuarios en pruebas sin credenciales reales
El entorno de pruebas de `auth/` SHALL preparar las cuentas necesarias para el login mediante valores de prueba aislados, sin reutilizar credenciales de bootstrap ni credenciales reales.

#### Scenario: Suite de login con usuario de prueba
- **WHEN** se ejecuta la suite de autenticación en el perfil de pruebas
- **THEN** los tests de login usan una cuenta preparada por el mecanismo de pruebas con valores de prueba, y la suite pasa sin depender de `student`/`Workshop123!`

### Requirement: Política de bootstrap documentada
La política de inicialización de cuentas por entorno SHALL quedar descrita en configuración o documentación revisable, sin incluir valores de credenciales ni secretos.

#### Scenario: Revisión del artefacto
- **WHEN** se revisa la configuración o documentación actualizada de `auth/`
- **THEN** describe el mecanismo de bootstrap por entorno y sus requisitos operativos, y no contiene contraseñas, secretos ni tokens

### Requirement: Logs sin credenciales ni tokens
Los logs generados durante la inicialización y el login SHALL NOT contener contraseñas, secretos de firma ni tokens.

#### Scenario: Salida de inicialización y login
- **WHEN** se ejecuta una prueba de inicialización seguida de un login fallido y uno exitoso
- **THEN** la salida de log no contiene contraseñas, valores de `workshop.token.secret` ni el token emitido
