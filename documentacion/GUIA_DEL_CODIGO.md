# Guía completa del código de RallyHub

> Para quién es: para quien conoce algo de programación pero quiere entender **todo** RallyHub, de lo más básico a lo más avanzado. Cada sección cita los archivos reales del proyecto (rutas relativas a la carpeta `RallyHub/`).
>
> Cómo usarla: léala en orden. Cada parte se apoya en la anterior. Al final hay ejercicios y preguntas típicas de sustentación.
>
> Esta guía describe **la versión que usted tiene** (la anterior a los dos ajustes de seguridad opcionales). Donde importa, se indica.

---

# PARTE 1. Conceptos básicos que necesita antes de leer el código

## 1.1 ¿Qué es RallyHub, en una frase?
Una aplicación web para un club de tenis de mesa: el administrador registra estudiantes, entrenadores, sedes y mesas; los estudiantes reservan mesas; los entrenadores crean clases y toman asistencia; y todos ven estadísticas y torneos según su rol.

## 1.2 Cliente, servidor y base de datos
Una aplicación web tiene tres piezas que se hablan entre sí:

1. **El navegador (cliente / frontend):** lo que usted ve. Aquí son archivos HTML, CSS y JavaScript (`backend/app/static/`).
2. **El servidor (backend):** un programa Python que recibe peticiones, aplica las reglas y responde. Aquí usa **FastAPI** (`backend/app/`).
3. **La base de datos:** donde viven los datos de forma permanente. Aquí es **MariaDB**.

Flujo mínimo: el navegador pide algo → el servidor lo valida → pregunta o escribe en la base de datos → responde → el navegador lo dibuja.

## 1.3 HTTP, API REST y JSON
- **HTTP** es el idioma entre navegador y servidor. Cada petición tiene un **método** (qué quiere hacer) y una **ruta** (sobre qué):
  - `GET` leer, `POST` crear, `PATCH` modificar parcialmente, `DELETE` borrar/desactivar.
- **API REST:** el servidor expone "recursos" con rutas predecibles: `GET /api/v1/students` lista estudiantes; `GET /api/v1/students/5` trae el 5; `POST /api/v1/reservations` crea una reserva.
- **JSON:** el formato de texto en el que viajan los datos: `{"table_id": 3, "starts_at": "2026-11-20T15:00:00Z"}`.
- **Código de estado:** número con el resultado. Los que usa RallyHub:
  - `200` OK, `201` creado, `204` OK sin contenido.
  - `400` petición mal formada o regla de negocio violada, `401` no autenticado, `403` autenticado pero sin permiso, `404` no existe, `409` conflicto (por ejemplo, la mesa ya está reservada), `422` datos inválidos, `429` demasiados intentos, `500` error interno.

## 1.4 Autenticación vs. autorización
- **Autenticación:** ¿quién eres? (login con correo y contraseña).
- **Autorización:** ¿qué puedes hacer? (un estudiante no puede crear mesas). RallyHub usa tres **roles**: `ADMIN`, `COACH`, `STUDENT`.

## 1.5 Cookies y sesiones
Después del login el servidor le entrega al navegador unas **cookies**; el navegador las reenvía solas en cada petición. RallyHub usa dos:
- `rh_session`: contiene el **JWT** (un "pase" firmado). Es `HttpOnly`: el JavaScript de la página **no puede leerlo**, lo que protege contra robo por XSS.
- `rh_csrf`: un valor aleatorio que el JavaScript **sí** puede leer, para defenderse de CSRF (explicado en las Partes 11 y 16).

## 1.6 ORM y migraciones
- Un **ORM** (aquí **SQLAlchemy**) permite trabajar con tablas como si fueran clases de Python: `Reservation` es la tabla `reservations`, y una fila es un objeto. No hay que escribir SQL a mano en casi ningún sitio.
- Una **migración** (aquí **Alembic**) es un archivo que describe cómo crear o cambiar las tablas, con versión. Así el esquema de la base se reproduce igual en cualquier máquina (`alembic upgrade head`).

## 1.7 Docker en 30 segundos
- Una **imagen** es una "foto" de un programa con todo lo que necesita. Un **contenedor** es esa imagen en ejecución.
- **Docker Compose** arranca varios contenedores juntos descritos en `compose.yaml`: aquí uno para la base (`db`) y otro para la aplicación (`app`).
- Un **volumen** guarda datos fuera del contenedor para que sobrevivan al apagarlo (`rallyhub_db`).

## 1.8 Python moderno que verá en el código
- **Type hints:** `def f(x: int) -> str`. No cambian la ejecución, pero ayudan a entender y a revisar (mypy los verifica).
- **`dataclass`:** clase para guardar datos sin escribir el constructor (`BookingPolicy`).
- **`Enum` / `StrEnum`:** conjunto fijo de valores (`Role.ADMIN`).
- **Anotaciones `Annotated[...]` y `Depends(...)`:** la forma en que FastAPI inyecta dependencias (usuario actual, sesión de base de datos).
- **Fechas *aware*:** una fecha con zona horaria. Una fecha *naive* no la tiene y es fuente clásica de errores. RallyHub **solo** acepta fechas *aware*.

---

# PARTE 2. El mapa del proyecto

```
RallyHub/
├── compose.yaml              Cómo arrancan db + app (y el perfil de pruebas)
├── compose.db-local.yaml     Opcional: publica la base en 127.0.0.1 (para DBeaver)
├── .env.example / .env       Variables de entorno (ejemplo / las suyas)
├── backend/
│   ├── Dockerfile            Cómo se construye la imagen de la app
│   ├── requirements*.txt     Dependencias fijadas
│   ├── pyproject.toml        Configuración de pytest y ruff
│   ├── alembic.ini + alembic/  Migraciones
│   ├── app/                  EL CÓDIGO DE LA APLICACIÓN
│   │   ├── main.py           Arranque, middleware, manejadores de errores
│   │   ├── core/             Configuración, tokens, contraseñas, límite de intentos, logs
│   │   ├── db/               Conexión y tipos de columna
│   │   ├── models/           Las 15 tablas como clases
│   │   ├── domain/           Reglas puras (sin BD ni HTTP)
│   │   ├── repositories/     Consultas a la base
│   │   ├── services/         Casos de uso y permisos
│   │   ├── schemas/          Contratos JSON de entrada y salida (Pydantic)
│   │   ├── dependencies/     Inyección: usuario actual, servicios, paginación
│   │   ├── api/              Rutas HTTP (routers)
│   │   └── static/           El frontend
│   └── tests/                Pruebas unitarias e integración
├── scripts/                  entrypoint.sh, wait_for_db.py, seed.py
├── db/init/                  Script que crea la base de pruebas
├── .github/workflows/ci.yml  Integración continua
└── docs/                     Documentación y diagramas
```

## 2.1 La arquitectura en capas (la idea central)
El código está organizado en **capas**, y cada una solo habla con la de abajo:

```
Navegador
   │  HTTP + JSON
   ▼
api/        (routers: reciben la petición, devuelven la respuesta)
   ▼
services/   (casos de uso: permisos + reglas + transacción)
   ▼
repositories/ (consultas SQL a través del ORM)
   ▼
models/     (tablas)  →  MariaDB

domain/  ← reglas puras que los servicios usan (no dependen de nada externo)
```

**Por qué así:** cada pieza tiene una sola responsabilidad. Si cambia una regla de negocio, se toca `domain/` o `services/`; si cambia el formato JSON, `schemas/`; si cambia una consulta, `repositories/`. Y las reglas puras se pueden probar sin base de datos (las 57 pruebas unitarias).

## 2.2 Qué pasa cuando hace clic en "Reservar" (visión general)
1. `static/js/pages/reservations.js` llama a `POST /api/v1/reservations` con el JSON.
2. `main.py` (middleware) revisa tamaño y origen.
3. `dependencies/auth.py` lee la cookie, valida el JWT y el token CSRF, carga el usuario.
4. `api/v1/endpoints/reservations.py` valida el JSON con el schema y llama al servicio.
5. `services/reservations.py` revisa permisos, reglas de horario (`domain/booking_rules.py`), **bloquea la mesa en la base**, busca solapes y guarda.
6. La respuesta vuelve como JSON y el frontend actualiza la pantalla.
Esto se explica paso a paso en la Parte 9.

---

# PARTE 3. Infraestructura: cómo se ejecuta

## 3.1 `.env.example` y `.env`
Un `.env` es un archivo de **variables de entorno**: configuración que cambia según la máquina y que **no se escribe en el código** (sobre todo secretos). Docker Compose lo lee automáticamente.

| Variable | Qué hace |
|---|---|
| `ENVIRONMENT` | `development`, `test` o `production`. En producción se activan validaciones extra. |
| `SECRET_KEY` | Clave con la que se **firman** los JWT. ≥ 32 caracteres. Si alguien la conoce, puede falsificar sesiones. |
| `COOKIE_SECURE` | Si es `true`, las cookies solo viajan por HTTPS. En local (http) debe ser `false`; en producción, `true`. |
| `ALLOWED_ORIGINS` | Orígenes extra permitidos para escrituras. Vacío = solo el mismo origen. |
| `DOCS_ENABLED` | Activa Swagger en `/docs`. |
| `APP_PORT` | Puerto del equipo donde se publica la app (usted puso 8080). |
| `DB_*` | Nombre, usuario y contraseñas de MariaDB. |
| `TIMEZONE`, `OPENING_TIME`, `CLOSING_TIME` | Zona y horario del club. |
| `RESERVATION_*`, `CANCEL_MIN_HOURS_BEFORE` | Reglas de reserva. |
| `RUN_MIGRATIONS`, `SEED_DEMO` | Si el contenedor migra y carga datos demo al arrancar. |

Los valores de ejemplo dicen `change-me`: sirven solo para desarrollo.

## 3.2 `compose.yaml`
Define tres servicios y una red:
- **`db`**: imagen `mariadb:11.4.5` (versión fijada, no `latest`, para que sea reproducible). Crea la base y el usuario a partir de las variables `MARIADB_*`. Arranca con juego de caracteres `utf8mb4` (acentos y emojis) y zona horaria del servidor `+00:00` (UTC). Monta el volumen `rallyhub_db` (los datos) y `db/init` (scripts que se ejecutan **solo la primera vez**). Tiene `healthcheck`: Compose espera a que la base esté realmente lista antes de arrancar `app` (`depends_on: condition: service_healthy`). **No tiene `ports`**: la base no es accesible desde fuera.
- **`app`**: se construye con `backend/Dockerfile` (objetivo `runtime`), recibe las variables de entorno y publica `${APP_PORT}:8000`.
- **`tests`**: tiene `profiles: ["test"]`, así que **no** arranca con `up`; solo con `docker compose --profile test run --rm tests`. Usa la etapa `dev` de la imagen (incluye pytest) y apunta a la base **`rallyhub_test`**, distinta de la real, con una clave `SECRET_KEY` de prueba.

La sintaxis `${VAR:-valor}` significa "usa VAR o, si falta, `valor`". `${VAR:?mensaje}` significa "VAR es obligatoria; si falta, falla con ese mensaje" (por eso le pidió definir `SECRET_KEY` cuando no tenía `.env`).

## 3.3 `backend/Dockerfile` (construcción multietapa)
Una imagen se construye por pasos. Aquí hay cuatro etapas:
1. **`base`**: Python 3.12.8 slim, con variables para no escribir `.pyc`, ver logs al instante y no cachear pip. `WORKDIR /app`.
2. **`builder`**: instala las dependencias como "ruedas" (`pip wheel`) en `/wheels`.
3. **`runtime`** (la imagen final): crea un usuario **sin privilegios** (`rally`, uid 10001), instala las dependencias desde `/wheels` sin red (`--no-index`), copia `app`, `alembic`, `alembic.ini` y `scripts`, y ejecuta como ese usuario. Tiene `HEALTHCHECK` que llama a `/health/live`. El `ENTRYPOINT` es `scripts/entrypoint.sh`.
4. **`dev`**: parte de `runtime` y añade pytest, ruff y los tests.

Ejecutar como no-root es una buena práctica: si alguien explotara un fallo, tendría menos poder dentro del contenedor.

## 3.4 `scripts/entrypoint.sh`
Lo primero que ejecuta el contenedor `app`:
1. `python -m scripts.wait_for_db`: reintenta conectar cada 2 s hasta 90 s (`wait_for_db.py`); si no logra conectar, falla.
2. Si `RUN_MIGRATIONS=1`: `alembic upgrade head` (crea/actualiza las tablas).
3. Si `SEED_DEMO=1` **y** no es producción: `python -m scripts.seed` (datos ficticios, idempotente).
4. `exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1 --proxy-headers`. `exec` reemplaza el proceso del script por uvicorn para que las señales (parar el contenedor) lleguen bien. **Un solo worker** a propósito: el límite de intentos de login vive en memoria del proceso, y así las migraciones y el seed se ejecutan una sola vez.

## 3.4b `db/init/01-create-test-db.sh`
Crea la base `rallyhub_test` y da permisos al usuario. Solo se ejecuta cuando el volumen de datos es nuevo (así funciona la imagen de MariaDB con `docker-entrypoint-initdb.d`). Por eso, si el volumen ya existía, hay que crear esa base a mano.

## 3.5 `backend/requirements.txt` y `requirements-dev.txt`
Las dependencias directas con versión exacta (`==`). Qué hace cada una:
- `fastapi`: el framework web; `uvicorn`: el servidor que lo ejecuta (ASGI).
- `pydantic`: validación de datos; `pydantic-settings`: lee `.env`/variables; `email-validator`: valida correos.
- `SQLAlchemy`: ORM; `alembic`: migraciones; `PyMySQL`: el driver para hablar con MariaDB (Python puro, sin compilar).
- `pwdlib[argon2]`: hash de contraseñas Argon2id; `PyJWT`: tokens; `tzdata`: base de zonas horarias (la imagen slim no la trae).
- Solo desarrollo: `pytest`, `pytest-cov` (cobertura), `httpx` (necesario para el cliente de pruebas de FastAPI), `ruff` (linter).

## 3.6 `backend/pyproject.toml`
- **pytest**: `pythonpath = ["."]` para que `import app...` funcione; `testpaths = ["tests"]`; un marcador `integration`.
- **ruff** (analizador de estilo y errores): línea máxima 130; reglas activas `E,F,W` (errores y estilo), `I` (orden de imports), `B` (bugs probables), `UP` (sintaxis moderna), `S` (seguridad, tipo bandit), `SIM` (simplificaciones). Se ignoran algunas con motivo (por ejemplo `B008`: `Depends()` en argumentos es el patrón normal de FastAPI).

## 3.7 `.github/workflows/ci.yml`
**Integración continua (CI)**: en cada `push` o `pull_request` GitHub ejecuta automáticamente: levanta MariaDB 11.4.5 como servicio, instala dependencias, corre ruff, aplica las migraciones desde cero y ejecuta todas las pruebas con cobertura. **No despliega nada** (eso sería CD, y el proyecto lo excluye a propósito). Tiene `permissions: contents: read` (mínimo privilegio).

## 3.8 `.dockerignore` y `.gitignore`
Listas de lo que **no** debe entrar en la imagen ni en Git: `.env`, cachés, `.git`, documentación, zips. Importante: `.env` nunca debe subirse.

---

# PARTE 4. El núcleo (`backend/app/core/`)

## 4.1 `core/config.py`: la configuración
La clase `Settings` hereda de `BaseSettings` (pydantic-settings): cada atributo se llena desde una variable de entorno del mismo nombre (sin distinguir mayúsculas). Si falta una obligatoria o tiene un tipo incorrecto, **la aplicación no arranca** (falla rápido, mejor que fallar a medias).

Puntos clave:
- `secret_key: SecretStr = Field(min_length=32)`: `SecretStr` evita que el valor aparezca por accidente en logs o `repr`; para usarlo hay que llamar `.get_secret_value()`.
- `access_token_minutes` entre 5 y 1440 (por defecto 60): duración de la sesión.
- `cookie_secure`, `allowed_origins`, `max_body_bytes` (1 MiB).
- Datos de la base (`db_host`, `db_name`...) y `database_url` opcional que, si existe, tiene prioridad.
- Reglas de negocio: zona horaria, horario, duraciones, anticipación, cancelación.
- Límite de login: 5 intentos en 900 s.
- **`@model_validator(mode="after") _check`**: valida combinaciones: apertura < cierre; mínimo ≤ máximo; y **si es producción**: la `SECRET_KEY` no puede empezar por `change-me` y `COOKIE_SECURE` debe ser `true`.
- Propiedades calculadas: `tz` (objeto `ZoneInfo`), `sqlalchemy_url` (construye `mysql+pymysql://...` con `URL.create`, que escapa bien caracteres especiales de la contraseña), `origins` (conjunto limpio), `open_minutes_per_day` (minutos operativos, usado en ocupación) y `booking_policy` (empaqueta las reglas en un `BookingPolicy`).
- `get_settings()` con `@lru_cache`: se crea **una sola vez** y se reutiliza (patrón singleton).

## 4.2 `core/tokens.py`: el JWT de sesión
Un **JWT** es un texto con tres partes (cabecera, contenido, firma). El servidor lo firma con `SECRET_KEY`; nadie puede alterar el contenido sin invalidar la firma.
- `create_session_token(...)` arma el contenido: `sub` (id del usuario), `ver` (token_version), `csrf` (valor CSRF), `iss` ("rallyhub", emisor), `iat` (emitido) y `exp` (expira). Firma con **HS256**.
- `decode_session_token(...)` lo verifica con `algorithms=[ALGORITHM]` (lista explícita: rechaza `alg=none` y ataques de confusión de algoritmo), exige el emisor y que existan todas las claims requeridas (`options={"require": [...]}`). Cualquier problema (firma mala, vencido, malformado) se convierte en `InvalidToken`.
- `new_csrf_token()` genera 32 bytes aleatorios seguros (`secrets.token_urlsafe`).
- `SessionClaims` es una `dataclass` inmutable (`frozen=True`) con lo que se extrae del token.

## 4.3 `core/passwords.py`: contraseñas
- Nunca se guarda la contraseña: se guarda su **hash Argon2id** (función deliberadamente lenta y que consume memoria, resistente a ataques por fuerza bruta). Cada hash lleva su propia "sal".
- `hash_password` y `verify_password`.
- Detalle importante: si el correo **no existe** (`password_hash is None`), igual se verifica contra un hash falso precalculado (`_DUMMY_HASH`) para que la respuesta tarde lo mismo. Así un atacante no puede descubrir qué correos existen midiendo el tiempo (ataque de *timing*).
- Si el hash guardado está corrupto, se trata como credencial inválida en vez de romper.

## 4.4 `core/ratelimit.py`: límite de intentos de login
`LoginThrottle` guarda, por clave (IP + correo), una `deque` con los instantes de los intentos fallidos:
- `check(key)`: poda los intentos fuera de la ventana (los más viejos salen por la izquierda, O(1) cada uno) y, si quedan ≥ 5, lanza `TooManyRequests` (HTTP 429).
- `register_failure(key)`: añade un fallo. Si se llega a `max_keys` (10 000) expulsa la clave más antigua: así la memoria **no crece sin límite** aunque alguien pruebe millones de correos.
- `reset(key)`: borra la clave tras un login correcto.
- Usa un `threading.Lock` porque FastAPI ejecuta endpoints síncronos en varios hilos.
- El reloj es inyectable (`clock`) para poder probarlo sin esperar 15 minutos reales.
- **Limitación honesta:** vive en memoria de un proceso. Con varios workers cada uno tendría su contador; por eso hay un solo worker. Y como la clave incluye el correo, alguien podría bloquear temporalmente a otra persona probando claves malas con su correo.

## 4.5 `core/logging.py`
Configura el log a la salida estándar con fecha, nivel, nombre y mensaje. Desactiva el log de acceso de uvicorn porque el middleware de `main.py` ya registra cada petición con un identificador. No se registran cuerpos de petición ni contraseñas.

---

# PARTE 5. La base de datos (`backend/app/db/`)

## 5.1 `db/base.py`
`Base` es la clase de la que heredan todos los modelos. Define una **convención de nombres** para restricciones e índices (`ix_`, `uq_`, `ck_`, `fk_`, `pk_`): así los nombres son predecibles y Alembic puede compararlos y modificarlos de forma fiable.

## 5.2 `db/session.py`
- `get_engine()`: crea **una vez** el "motor" de conexión con `isolation_level="READ COMMITTED"`, `pool_pre_ping` (comprueba que la conexión siga viva), `pool_recycle=1800`, un pool de `db_pool_size` conexiones más 5 de desborde.
- **Por qué READ COMMITTED (decisión importante):** por defecto InnoDB usa REPEATABLE READ, que toma una "instantánea" al primer SELECT de la transacción. Como autenticar al usuario ya hace un SELECT, esa instantánea quedaría **anterior** al bloqueo de la mesa y podría no ver una reserva que otra transacción acaba de confirmar. Con READ COMMITTED cada sentencia ve lo último confirmado, y el control de solapes funciona.
- `get_sessionmaker()`: fábrica de sesiones con `autoflush=False` (no envía cambios a la base automáticamente antes de cada consulta; el código llama `flush()` cuando corresponde) y `expire_on_commit=False` (los objetos siguen utilizables tras el commit sin recargarse).
- `get_db()`: es una **dependencia de FastAPI con `yield`**: abre una `Session` por solicitud; si ocurre cualquier excepción hace `rollback`; al final siempre `close()`. Es el patrón "una sesión por petición".

## 5.3 `db/types.py`: `UTCDateTime`
Tipo de columna propio. Problema: MariaDB `DATETIME` no guarda zona horaria. Solución: **al guardar**, convierte a UTC y quita la zona; **al leer**, devuelve el valor con zona UTC. Y **rechaza** fechas sin zona (`ValueError`). Resultado: en toda la aplicación circulan fechas *aware*; la conversión a hora de Bogotá solo ocurre al mostrar (frontend) o al evaluar el horario de apertura (`domain`).

---

# PARTE 6. Los modelos: las tablas (`backend/app/models/`)

Un **modelo** es una clase que representa una tabla. `Mapped[int]` declara el tipo Python y `mapped_column(...)` los detalles SQL. `relationship(...)` define cómo navegar entre objetos relacionados (por ejemplo `reserva.student`).

## 6.1 Piezas comunes: `_common.py` y `enums.py`
- `enum_col(Enum, nombre)`: guarda un enum como **VARCHAR(20) + restricción CHECK** (`native_enum=False`, `create_constraint=True`), con el *valor* del enum. Es portable y la base misma rechaza valores inválidos.
- `created_at_col()`: marca de creación asignada por **la aplicación** (`default=utcnow`), no por SQL.
- `enums.py` define los estados: `Role`, `Level`, `TableStatus` (ACTIVE/MAINTENANCE/OUT_OF_SERVICE), `ReservationStatus` (CONFIRMED/CANCELLED/COMPLETED/NO_SHOW), `ClassStatus` (DRAFT/PUBLISHED/CANCELLED), `EnrollmentStatus`, `AttendanceStatus` (PRESENT/ABSENT/JUSTIFIED), `TournamentStatus`, `Modality`.

## 6.2 Las 15 tablas

| Tabla (modelo) | Qué guarda | Detalles importantes |
|---|---|---|
| `users` (`User`) | Cuenta de acceso | `email` único; `password_hash`; `role`; `is_active`; **`token_version`** (invalida sesiones al cambiarlo) |
| `students` (`Student`) | Perfil de estudiante | `user_id` único (1 a 1 con `users`); nombre, nacimiento, teléfono, acudiente, nivel |
| `coaches` (`Coach`) | Perfil de entrenador | `user_id` único; especialidad, bio |
| `facilities` (`Facility`) | Sedes | nombre único |
| `tables` (`GameTable`) | Mesas | código único **dentro de la sede**; estado; la clase se llama `GameTable` para no chocar con `Table` de SQLAlchemy |
| `maintenance_blocks` | Rangos de mantenimiento de una mesa | `CHECK ends_at > starts_at`; índice (mesa, inicio, fin) |
| `reservations` | Reservas | `CHECK ends_at > starts_at`; índices para buscar por mesa+rango y por estudiante; estado; `cancelled_at` |
| `classes` (`ClassSession`) | Clases (sesión única) | entrenador, mesa opcional, nivel, cupo, estado (DRAFT/PUBLISHED/CANCELLED) |
| `class_enrollments` | Inscripciones | único (clase, estudiante) |
| `attendances` | Asistencia | **una por inscripción** (`enrollment_id` único) |
| `progress_records` | Progreso técnico | cinco habilidades con `CHECK BETWEEN 1 AND 5` |
| `tournaments` | Torneos | rango de fechas, cupo ≥ 2 |
| `tournament_participants` | Participantes | único (torneo, estudiante) |
| `tournament_matches` | Resultados | `CHECK participant_a <> participant_b`, marcadores ≥ 0 |
| `audit_logs` | Bitácora | quién, qué acción, sobre qué entidad, detalle |

**Ideas de diseño a destacar:**
- **No existe un estado RESERVED en la mesa**: la ocupación se **deriva** de reservas, clases y bloqueos. Guardarla sería duplicar información y se desincronizaría.
- **Restricciones en la base y no solo en el código:** `CHECK`, `UNIQUE` y claves foráneas hacen que los datos sigan siendo correctos aunque alguien entre a la base saltándose la aplicación (integridad).
- **Propiedades de conveniencia** (`facility_name`, `student_name`, `full_name`, `table_code`...): permiten que los schemas de salida lean `reserva.student_name` sin armar JOINs a mano. (Un fallo clásico aquí es olvidar una de ellas: la prueba `test_schema_model_contract.py` lo vigila.)
- **Claves primarias INT autoincrementales** (la especificación recomendaba BIGINT; es una desviación documentada).
- **Relaciones 1 a 1**: `User.student` y `User.coach` con `uselist=False`.

## 6.3 La migración `alembic/versions/0001_initial_schema.py` y `alembic/env.py`
- `env.py` usa **la misma configuración y los mismos metadatos que la aplicación** (`Base.metadata` tras importar `app.models`). `compare_type=True` hace que Alembic detecte cambios de tipo.
- `0001_initial_schema.py` crea las 15 tablas con `op.create_table(...)` (motor InnoDB, `utf8mb4`). Tiene funciones auxiliares (`pk()`, `created()`, `enum(...)`) para no repetir. Una prueba de integración compara los modelos con la migración para asegurarse de que no se desfasen.
- Comandos: `alembic upgrade head` (aplicar todo), y para crear una nueva migración `alembic revision --autogenerate -m "mensaje"`.

---

# PARTE 7. El dominio: reglas puras (`backend/app/domain/`)

"Puro" = no importa FastAPI, ni SQLAlchemy, ni la base. Solo recibe datos y devuelve un resultado o lanza un error. Por eso se prueba muy fácil y rápido.

## 7.1 `domain/errors.py`: excepciones del dominio
`DomainError` es la raíz; cada subclase define un `status_code` HTTP y un `code` estable que el frontend puede interpretar:

| Excepción | HTTP | `code` |
|---|---|---|
| `InvalidInterval`, `DurationOutOfRange`, `OutsideOperatingHours`, `PastDateError`, `AdvanceLimitExceeded`, `InvalidCurrentPassword` | 400 | `invalid_interval`, `duration_out_of_range`, `outside_operating_hours`, `past_date`, `advance_limit_exceeded`, `invalid_current_password` |
| `AuthenticationError` | 401 | `not_authenticated` |
| `ForbiddenError` | 403 | `forbidden` |
| `NotFoundError` | 404 | `not_found` |
| `ConflictError` y sus hijas: `ReservationConflict`, `ResourceUnavailable`, `CapacityExceeded`, `DuplicateError`, `FutureReservationsExist`, `CancellationNotAllowed` | 409 | `conflict`, `reservation_conflict`, `resource_unavailable`, `capacity_exceeded`, `duplicate`, `has_future_reservations`, `cancellation_not_allowed` |
| `TooManyRequests` | 429 | `too_many_requests` |

`InvalidCurrentPassword` es 400 y no 401 a propósito: el frontend trata cualquier 401 como "sesión caducada" y lo mandaría al login.

`main.py` registra **un solo manejador** que convierte cualquier `DomainError` en JSON `{"code": ..., "detail": ...}`. Así los servicios solo hacen `raise ...` y no saben nada de HTTP.

## 7.2 `domain/booking_rules.py`: reglas de reserva
- `BookingPolicy` (dataclass congelada): zona, apertura, cierre, duración mínima y máxima, anticipación máxima, horas mínimas para cancelar.
- **`intervals_overlap(a_start, a_end, b_start, b_end)`** = `a_start < b_end and a_end > b_start`. Es la fórmula central. Los intervalos son **semiabiertos** `[inicio, fin)`: una reserva 10:00–11:00 y otra 11:00–12:00 **no** se solapan. Ejemplo: A = 9:30–11:30, B = 11:30–12:00 → `9:30 < 12:00` (sí) y `11:30 > 11:30` (no) → no se solapan. Cubre todos los casos (parcial, contenido, igual) sin enumerarlos.
- `validate_interval`: ambas fechas con zona y `fin > inicio`.
- `validate_operating_hours`: convierte a la hora **local del club**, exige el mismo día y que esté entre apertura y cierre.
- `validate_not_past`: el inicio no puede ser anterior a "ahora".
- `validate_booking_window`: orquesta todo para una **reserva** (duración 30–120, no pasado, no más de 30 días, horario).
- `validate_class_window`: para una **clase** (sin límites de duración).
- `can_student_cancel`: `ahora <= inicio − 2 horas`.

Nota de diseño: "ahora" **se recibe como parámetro** (`now`), no se llama `datetime.now()` dentro. Por eso las pruebas pueden fijar la hora.

## 7.3 `domain/stats.py`: estadísticas
- `clipped_minutes`: minutos de un intervalo que caen dentro de una ventana (recorta con `max`/`min`).
- `occupancy_by_table`: ocupación % = minutos reservados / minutos operativos. Usa `defaultdict(float)`; recorre reservas una vez y mesas una vez: **O(R + T)**. Se limita a 100 % y se redondea a 1 decimal.
- `attendance_rate`: PRESENT / (PRESENT + ABSENT); los JUSTIFIED no cuentan; si no hay datos devuelve `None` (no inventa 0 %).
- `count_by`: cuenta ocurrencias (diccionario).
- `local_day_bounds` / `local_week_bounds`: límites del día y de la semana (lunes a lunes) en hora local.

## 7.4 `domain/csv_utils.py`
Al exportar CSV, si una celda empieza por `=`, `+`, `-`, `@`, tab o retorno, Excel podría interpretarla como **fórmula** (inyección de fórmulas). `safe_cell` antepone un apóstrofo `'` para neutralizarla. `to_csv` escribe con el módulo `csv` (que escapa comas y comillas correctamente).

---

# PARTE 8. Repositorios: las consultas (`backend/app/repositories/`)

Un **repositorio** agrupa las consultas de una entidad. Los servicios piden cosas como "estudiantes de este entrenador" y el repositorio sabe cómo escribirlo con SQLAlchemy. Así el SQL no está regado por todo el código.

## 8.1 `repositories/base.py`
- **`apply_sort(stmt, allowed, sort_by, order, default, tiebreak)`**: ordena **solo** por columnas de una lista blanca (`SORTABLE`). Si el cliente pide `sort_by=password_hash`, se rechaza con `InvalidSortField`. Esto evita que un parámetro de la URL permita ordenar por (y por tanto inferir) columnas arbitrarias. Siempre añade un desempate por `id` para que la paginación sea estable.
- **`BaseRepository[M]`**: clase genérica con `get(id)`, `add(obj)` (añade y hace `flush()` para obtener el `id` sin cerrar la transacción) y **`paginate(stmt, limit, offset)`**, que ejecuta dos consultas: un `COUNT(*)` del total y la página (`LIMIT/OFFSET`). El `.unique()` es necesario cuando se usan `joinedload` sobre colecciones.
- **`like_pattern(q)`**: prepara el texto de búsqueda para `LIKE`: escapa `\`, `%` y `_` para que el usuario no pueda usar comodines como si fueran sus propios caracteres. Se usa con `ilike(pat, escape="\\")`.
- Los valores **siempre** viajan como parámetros enlazados (el ORM los separa del SQL), por eso no hay inyección SQL.

## 8.2 `repositories/people.py`
- `UserRepository.by_email` (normaliza a minúsculas).
- `StudentRepository`: `get_full` (carga también el `User` con `joinedload` para evitar consultas extra: el problema "N+1"), `by_user_id`, **`coach_teaches(coach_id, student_id)`** (¿el estudiante está inscrito y activo en alguna clase del entrenador? — es la base del permiso "un entrenador solo ve a sus estudiantes"), y `search` con filtros (texto, nivel, activo, entrenador) usando una **subconsulta** `IN (SELECT ...)`.
- `CoachRepository`: igual para entrenadores.

## 8.3 `repositories/facilities.py`
- `FacilityRepository`: buscar por nombre, listar con filtros.
- `TableRepository`:
  - **`get_for_update(table_id)`**: `SELECT ... FROM tables WHERE id = ? FOR UPDATE`. **Bloquea esa fila** hasta que termine la transacción. Cualquier otra transacción que intente bloquear la misma mesa **espera**. Es la *sección crítica* del sistema (explicada a fondo en la Parte 10). Se hace sin JOINs para bloquear solo la fila de `tables`.
  - **`busy_slots(table_ids, start, end, exclude_class_id=None)`**: devuelve los intervalos ocupados que se solapan con `[start, end)`, de **tres fuentes**: reservas no canceladas (`RESERVATION`), clases no canceladas (`CLASS`) y bloqueos (`MAINTENANCE`). La condición de solape en SQL es `starts_at < end AND ends_at > start`. Hace una consulta por fuente (no una por mesa).
  - `bookable_tables`, `maintenance_for` (más recientes primero), y los tres métodos para mantenimiento y bajas: `reservations_overlapping`, `future_confirmed_reservations`, `future_classes`.

## 8.4 `repositories/scheduling.py`
- `ReservationRepository`: `get_full` (carga estudiante, mesa y sede de una vez), `get_for_update` (bloquea la reserva al cancelarla o cerrarla), `search` con muchos filtros. Nótese que el filtro de fechas usa **solape** (`ends_at > date_from` y `starts_at < date_to`), no "empieza dentro".
- `ClassRepository`: `lock_coach` (bloquea al entrenador para serializar la creación de sus clases), `coach_has_conflict` (¿tiene otra clase solapada?), `enrolled_counts` (`GROUP BY` para contar inscritos de varias clases en **una** consulta).
- `EnrollmentRepository` y `AttendanceRepository`: búsquedas por clase/estudiante.

---

# PARTE 9. Schemas: los contratos JSON (`backend/app/schemas/`)

Un **schema** (modelo Pydantic) describe la forma de un JSON y **valida** automáticamente. FastAPI los usa para tres cosas: validar la entrada, serializar la salida y generar la documentación en `/docs`.

- `schemas/common.py`: `ORMModel` (con `from_attributes=True`, permite construir el schema directamente desde un objeto SQLAlchemy), `Page[T]` (respuesta paginada: `items`, `total`, `limit`, `offset`), `Message`, y validadores reutilizables: `check_phone` (regex) y **`check_password`** (10–128 caracteres, con letras y números).
- Reglas de validación visibles en los schemas: `Field(min_length=1, max_length=120)`, `Field(ge=1, le=100)` para la capacidad, `Score = Annotated[int, Field(ge=1, le=5)]` para el progreso.
- **`AwareDatetime`**: tipo de Pydantic que **rechaza** fechas sin zona horaria. Es la primera barrera de la política "todo en fechas aware".
- Patrón **Create / Update / Read**: `StudentCreate` (todos los datos necesarios), `StudentUpdate` (todos opcionales: PATCH parcial; se usa `model_dump(exclude_unset=True)` para saber qué campos mandó realmente el cliente), `StudentRead` (lo que se devuelve, sin `password_hash`).
- `ReservationCreate`: `student_id` es opcional y solo lo usa el ADMIN; un estudiante siempre reserva para sí mismo.
- `ClassUpdate.clear_table`: bandera para quitar la mesa (porque `table_id: null` es ambiguo con "no lo mandé").
- `schemas/dashboard.py`: forma de los tres tableros.

Por qué separar schemas de modelos: el modelo es la tabla (incluye `password_hash`); el schema es el **contrato público**. Cambiar uno no obliga a cambiar el otro, y nunca se filtra un campo por error.

---

# PARTE 10. Servicios: los casos de uso (`backend/app/services/`)

Aquí vive la lógica real. Cada método de un servicio es un **caso de uso** y sigue casi siempre el mismo patrón: **(1) permisos → (2) validar reglas → (3) operar → (4) auditar → (5) `commit`**.

## 10.1 `services/base.py`
- `Service`: recibe la sesión de BD, la configuración y un **reloj inyectable** (`clock`). `self.now()` devuelve "ahora" en UTC. Inyectar el reloj permite que las pruebas controlen el tiempo.
- `audit(actor, acción, entidad, id, detalle)`: añade un registro a `audit_logs` en la **misma transacción** (si la operación falla y se revierte, la auditoría también; si tiene éxito, quedan juntas).
- `require_roles(actor, *roles)`: lanza `ForbiddenError` si el rol no está permitido.

## 10.2 `services/auth.py`
- `login`: busca el usuario por correo, verifica la contraseña (con tiempo constante aunque no exista), exige que esté activo, genera el CSRF y el JWT. Mensaje único "Credenciales inválidas" para todos los casos de fallo (no revela qué falló).
- `logout`: incrementa `token_version` → **todos** los tokens anteriores de ese usuario dejan de valer.
- `change_password`: verifica la actual (si falla lanza `InvalidCurrentPassword`), guarda el hash nuevo e incrementa `token_version`.
- `change_email`: pide la contraseña actual, normaliza, comprueba que no exista, audita y maneja la carrera con `IntegrityError` (si dos personas intentan el mismo correo a la vez, la restricción `UNIQUE` de la base decide).
- `me`, `list_users`, `admin_reset_password`.

## 10.3 `services/people.py` (estudiantes y entrenadores)
- `StudentService.create` (solo ADMIN): crea **a la vez** el `User` (con hash Argon2id) y el `Student`, en una transacción. Si el correo ya existe, `DuplicateError`.
- **Permisos de lectura (`_can_view`)**: ADMIN todo; STUDENT solo a sí mismo; COACH solo estudiantes inscritos en sus clases.
- **Permisos de edición**: ADMIN todos los campos; el estudiante o entrenador **solo los suyos y solo los campos de una lista** (`STUDENT_EDITABLE = {first_name, last_name, phone, guardian_name}`, `COACH_EDITABLE = {first_name, last_name, phone, bio, specialty}`). Si intenta tocar `level` o `is_active`, `ForbiddenError`.
- `_apply`: no permite vaciar campos obligatorios (ignora `None` para ellos).
- `deactivate`: **baja lógica**: `is_active=False` en el perfil y en el usuario, y se incrementa `token_version` para expulsar sesiones abiertas. No se borran filas (se conserva el historial).

## 10.4 `services/reservations.py`: el caso de uso más importante
`create` paso a paso:
1. **Quién es el estudiante** (`_student_for_create`): si es STUDENT, él mismo (y si manda otro `student_id`, 403); si es ADMIN, debe indicar uno; otro rol, 403.
2. El estudiante debe estar activo.
3. **Validaciones puras** `rules.validate_booking_window(...)`: duración 30–120, no pasado, ≤ 30 días, dentro del horario, un solo día. Si algo falla, no se toca la base.
4. **Bloqueo**: `tables.get_for_update(table_id)`. Desde aquí, cualquier otra transacción que quiera reservar *esa* mesa queda esperando.
5. Comprobar que la mesa existe, está `ACTIVE` y su sede activa.
6. **Buscar solapes** con `busy_slots`: si hay `MAINTENANCE` → `ResourceUnavailable` ("mantenimiento programado"); si hay cualquier otra cosa (reserva o clase) → `ReservationConflict` (HTTP 409).
7. Insertar la reserva (`CONFIRMED`) y **`commit`**, que libera el bloqueo.

**Por qué funciona (carrera):** supongamos que Ana y Luis reservan la misma mesa a la misma hora a la vez. Ambos pasan las validaciones puras. Ana obtiene el bloqueo primero; Luis **espera** en el paso 4. Ana busca solapes (nada), inserta y hace commit. Ahora Luis obtiene el bloqueo y busca solapes: gracias a **READ COMMITTED** ve la reserva de Ana, y recibe 409. Sin el bloqueo, ambos habrían visto "libre" e insertado (doble reserva). Existe una prueba de concurrencia que lanza reservas simultáneas y exige que solo una gane (`tests/integration/test_reservation_concurrency.py`).

Otros métodos:
- `cancel`: bloquea la reserva; el estudiante solo cancela las suyas; solo se cancelan las `CONFIRMED`; el estudiante además debe cumplir `can_student_cancel` (≥ 2 h antes) → si no, `CancellationNotAllowed`. El administrador puede cancelar sin esa restricción. Guarda `cancelled_at`.
- `set_outcome` (ADMIN): marca `COMPLETED` o `NO_SHOW` solo si estaba confirmada **y ya comenzó**.
- `search`: aplica el filtro por rol (ADMIN todo, STUDENT solo suyas, COACH las de sus estudiantes).
- `export_csv` (ADMIN): hasta 5000 filas, fechas en hora local, con `to_csv` seguro.

## 10.5 `services/facilities.py` (sedes, mesas, disponibilidad, mantenimiento)
- `_TableRelease._release_tables`: lógica común cuando una mesa o sede **deja de servir**. Primero mira las clases futuras: si hay, **bloquea siempre** (`ResourceUnavailable`: hay que reprogramarlas). Luego las reservas confirmadas futuras: si hay y no se pidió cancelarlas, lanza `FutureReservationsExist` (409 `has_future_reservations`); con `cancel_reservations=True` las cancela una por una y deja auditoría "auto: mesa no disponible".
- `FacilityService`: crear (nombre único), actualizar, `deactivate`. Al desactivar una sede, `_lock_tables` bloquea **todas sus mesas ordenadas por id** (el orden fijo evita interbloqueos o *deadlocks*) y aplica `_release_tables`.
- `TableService`: crear (código único por sede), `update` y `retire` (baja lógica = `OUT_OF_SERVICE`): ambos bloquean primero la fila de la mesa para serializarse con las reservas, y si el nuevo estado no es `ACTIVE` aplican `_release_tables`.
- **`availability`**: para un rango (máximo 7 días) devuelve, por mesa, si está disponible, el motivo si no ("Instalación inactiva", "Mesa en mantenimiento", "Ocupada…") y los tramos ocupados. Lo usa la pantalla de reservas.
- **`add_maintenance`**: valida el intervalo; **no acepta bloqueos que ya terminaron**; bloquea la mesa; si hay clases en el rango, rechaza; si hay reservas **completadas o no-show** solapadas, rechaza; si hay reservas **confirmadas** solapadas: sin `cancel_conflicts` responde 409 `has_future_reservations`, con él las cancela. Después crea el bloqueo y audita.
- `list_maintenance`, `remove_maintenance`.

## 10.6 `services/classes.py` (clases, inscripciones, asistencia)
- **Clase**: sesión única con estado `DRAFT` → `PUBLISHED` → `CANCELLED`. Nace en borrador; solo las publicadas las ven y se inscriben los estudiantes.
- `create`: ADMIN debe indicar entrenador; COACH solo crea las suyas. Validaciones de ventana (sin límite de duración). Luego **dos bloqueos en orden fijo: entrenador → mesa**. Mantener un **orden global de bloqueos** es lo que evita que dos transacciones se esperen mutuamente (deadlock). `_check_resources` comprueba mantenimiento/ocupación de la mesa y que el entrenador no tenga otra clase solapada.
- `update`: bloquea entrenador, mesas (ids ordenados) y la propia clase; no permite modificar canceladas ni ya iniciadas; la capacidad no puede bajar de los inscritos.
- `set_status`: máquina de estados con reglas (solo publicar borradores futuros; solo ocultar publicadas sin inscritos).
- `EnrollmentService.enroll`: STUDENT para sí mismo o ADMIN para otro; **bloquea la fila de la clase** (protege el cupo); la clase debe estar publicada y no haber iniciado; no duplicados; cupo disponible. Si el estudiante estuvo retirado, se **reinscribe** reutilizando la fila (por la restricción única). `withdraw`: el estudiante solo antes de que inicie; no si ya hay asistencia.
- `AttendanceService.record`: solo el entrenador de la clase o un ADMIN; la clase **debe haber comenzado**, no estar cancelada, la inscripción activa y no haber asistencia previa (para eso existe `update`, que corrige y deja auditoría).

## 10.7 `services/dashboard.py`
Tres tableros por rol. Para el admin: conteos (`SELECT COUNT(*)`), reservas de hoy y de la semana (en hora local), **ocupación por mesa** de los últimos 7 días (reservas CONFIRMED/COMPLETED + clases no canceladas, usando `stats.occupancy_by_table`), tasa de asistencia de 30 días y estudiantes por nivel. La ocupación se calcula sobre minutos operativos reales (`open_minutes_per_day × 7`).

## 10.8 `services/progress.py` y `services/tournaments.py`
- **Progreso:** solo un COACH crea observaciones, y solo de estudiantes que cursan sus clases; la fecha no puede ser futura. El resumen (`summary`) lo ven ADMIN, el propio estudiante o su entrenador. Solo se habla de "evolución" si hay **al menos 2** observaciones (`sufficient_data`); el promedio es la media de las cinco habilidades.
- **Torneos:** el ADMIN crea y actualiza; estudiantes se inscriben ellos mismos (o el ADMIN a otros). La inscripción **bloquea la fila del torneo** para proteger el cupo, y exige estado `OPEN`. Retirarse no es posible si ya jugó partidos. `add_match` (ADMIN): participantes distintos y del torneo, **sin empates**, y calcula el ganador (resultado manual; no hay generador de llaves).

---

# PARTE 11. Dependencias, endpoints y arranque

## 11.1 `dependencies/auth.py`: quién es el usuario (el corazón de la seguridad)
`get_current_user` se ejecuta antes de cada endpoint protegido:
1. Lee la cookie `rh_session`; si no hay, `AuthenticationError` (401).
2. Decodifica y verifica el JWT (firma, expiración, emisor). Si falla, 401.
3. Carga el usuario de la base y comprueba: existe, **está activo** y su **`token_version` coincide** con el del token. Así, cambiar contraseña, cerrar sesión o desactivar al usuario **invalida inmediatamente** todos sus tokens.
4. **CSRF:** si el método no es seguro (`POST/PATCH/DELETE`), exige la cabecera `X-CSRF-Token` y la compara con la claim `csrf` **dentro del JWT firmado**, con `hmac.compare_digest` (comparación de tiempo constante).

**¿Qué es CSRF?** Si usted está logueado en RallyHub y visita una página maliciosa, esa página podría hacer que su navegador envíe `POST /api/v1/...` y el navegador adjuntaría la cookie sola. La defensa: exigir una cabecera que una página ajena **no puede leer ni poner** (necesita el valor de la cookie `rh_csrf`, y esa cookie solo es legible desde el mismo origen). Además, `SameSite=Lax` y el middleware que verifica `Origin` son capas adicionales.

`CurrentUser = Annotated[User, Depends(get_current_user)]` es un alias para usarlo cómodo en los endpoints. `require_role(*roles)` y `AdminUser` añaden la comprobación de rol (403 si no coincide).

## 11.2 `dependencies/services.py`
`_factory(cls)` fabrica una dependencia que construye el servicio con la sesión de BD de la petición y el reloj. `AuthSvc`, `StudentSvc`, `ReservationSvc`... son alias `Annotated`. `Pager` valida `limit` (1–200, por defecto 50) y `offset` ≥ 0; `page(...)` arma la respuesta paginada. `get_clock` existe para poder sustituirlo en pruebas.

## 11.3 Los endpoints (`api/v1/endpoints/`)
Cada archivo es un `APIRouter` con un prefijo. Un endpoint típico:

```python
@router.post("", response_model=ReservationRead, status_code=201)
def create_reservation(body: ReservationCreate, actor: CurrentUser, svc: ReservationSvc):
    return svc.create(actor, body)
```
FastAPI: valida `body` contra el schema (422 si no cumple), resuelve `actor` (401/403 si corresponde), crea `svc`, llama al servicio y serializa el resultado con `ReservationRead`. **El endpoint no contiene lógica**: delega.

| Archivo | Rutas principales |
|---|---|
| `auth.py` | `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`, `POST /auth/change-password`, `POST /auth/change-email`, `GET /users`, `POST /users/{id}/reset-password` |
| `students.py` | CRUD de estudiantes, `GET /students/export.csv` |
| `coaches.py` | CRUD de entrenadores |
| `facilities.py` | CRUD de sedes (DELETE = desactivar; admite `?cancel_reservations=true`) |
| `tables.py` | CRUD de mesas, `/tables/availability`, `/tables/{id}/availability`, `/tables/{id}/maintenance` (GET/POST/DELETE) |
| `reservations.py` | listar, crear, `GET /policy`, `GET /export.csv`, `POST /{id}/cancel`, `PATCH /{id}/status` |
| `classes.py` | `/classes` (+ `publish`, `unpublish`, `cancel`), `/enrollments`, `/attendances` |
| `extras.py` | `/progress`, `/tournaments` (+ participantes y partidos), `/dashboard/{admin,coach,student}`, `/audit` |

Detalle a notar: en `reservations.py` las rutas **fijas** (`/policy`, `/export.csv`) están declaradas **antes** de `/{reservation_id}`; si no, FastAPI intentaría interpretar "policy" como un número de reserva. El parámetro `status_filter` evita chocar con el módulo `status` de FastAPI.

`api/v1/router.py` junta todos los routers en `api_router`, que `main.py` monta bajo `/api/v1`.

## 11.4 `api/health.py`
`GET /health/live` (el proceso responde) y `GET /health/ready` (hace `SELECT 1`; si la base falla responde 503 y registra el error en el log **sin** mostrar detalles al cliente). Docker usa `/health/live` en su `HEALTHCHECK`.

## 11.5 `main.py`: el ensamblaje
- **`create_app()`** construye la aplicación FastAPI. En el arranque (`lifespan`) registra un log y al apagar cierra el pool de conexiones.
- **Middleware `security`** (se ejecuta en **cada** petición):
  - Rechaza cuerpos mayores de 1 MiB (por `Content-Length`) con 413.
  - Para escrituras a `/api/`, si trae cabecera `Origin` y no coincide con el host ni está permitida → 403 `bad_origin`.
  - Añade cabeceras de seguridad a **todas** las respuestas: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy` y **`Content-Security-Policy`**.
  - `Cache-Control: no-store` a `/api/` (las respuestas con datos personales no se cachean).
  - `Strict-Transport-Security` si `COOKIE_SECURE`.
  - Registra método, ruta, código, milisegundos y un `X-Request-ID`.
- **CSP**: `default-src 'self'` (solo recursos del mismo origen), `script-src 'self'` (no se ejecutan scripts incrustados ni de terceros → mitiga XSS), `frame-ancestors 'none'` (no se puede incrustar la app en un iframe: anti-clickjacking). `style-src` permite `'unsafe-inline'` porque el frontend asigna estilos en línea; es una concesión consciente. Swagger (`/docs`) queda exento porque carga recursos de un CDN.
- **Manejadores de error**: `DomainError` → JSON `{code, detail}` con su HTTP; validación 422 → lista de `{field, message}` **sin eco del valor** (no se devuelven contraseñas); errores HTTP de Starlette; y cualquier excepción inesperada → 500 genérico (el detalle va al log, no al cliente).
- Monta `/static` (archivos del frontend) y sirve `/` (`index.html`) y `/login` (`login.html`).

---

# PARTE 12. El frontend (`backend/app/static/`)

Es una **aplicación de una sola página (SPA)** hecha con JavaScript nativo (módulos ES), sin React ni compilación. FastAPI la sirve como archivos estáticos, así que **mismo origen** que la API: no hay CORS y la CSP puede ser estricta.

## 12.1 Archivos
- `index.html`: el "cascarón": barra lateral (`#nav`), cabecera (`#who`, botón de cerrar sesión), `<main>` con título y `#view` donde se pinta cada página, y `#toasts` para avisos. Carga **un solo script**: `js/app.js` (`type="module"`).
- `login.html` + `js/login.js`: página aparte para iniciar sesión.
- `css/app.css`: estilos (109 líneas), con foco visible, tablas responsivas y menú móvil.
- `js/api.js`, `js/ui.js`, `js/app.js` y `js/pages/*.js` (una por sección).

## 12.2 `api.js`: el cliente HTTP único
- `api(path, {method, body, params})`: todas las llamadas pasan por aquí. Usa `fetch` con `credentials: 'same-origin'` (el navegador adjunta la cookie `rh_session`).
- **CSRF**: si el método no es `GET`, lee la cookie `rh_csrf` (la única legible por JS) y la envía en la cabecera `X-CSRF-Token`. El servidor la compara con la claim firmada del JWT.
- Si la respuesta es **401** y no estamos ya en `/login`, redirige a `/login` (sesión vencida o invalidada).
- Errores: se convierten en `ApiError(status, code, message, errors)`. `code` permite decisiones de interfaz (ej.: `has_future_reservations`). `errors` trae los errores por campo del 422.
- `get/post/patch/del` son atajos. `qs()` arma el query string omitiendo valores vacíos.
- **No usa `localStorage`**: el token jamás está al alcance de JavaScript (por eso la cookie es HttpOnly), así un XSS no puede robarlo.

## 12.3 `ui.js`: la caja de herramientas
- **`h(tag, attrs, ...children)`**: crea elementos DOM. Todo texto entra como **nodo de texto** (`createTextNode`), nunca como HTML → **imposible inyectar HTML/JS** con datos de usuario (defensa XSS principal). `children.flat(Infinity)` aplana arreglos anidados (este fue el origen del error `[object HTMLElement]` ya corregido).
- Fechas: el servidor entrega UTC; `fmtDateTime/fmtRange` muestran en `America/Bogota`. `localToIso` convierte lo que el usuario escribe en un `<input type="datetime-local">` (hora de Bogotá) a ISO UTC calculando el desplazamiento con `Intl` (no asume un offset fijo).
- Etiquetas (`LABELS`) traducen los enums (`CONFIRMED` → "Confirmada") y `badge()` los colorea.
- `toast`, `UserError` (error con mensaje apto para mostrar), `errMsg`/`fail` (un `Error` inesperado muestra un texto genérico, no detalles internos).
- **`dialog` / `confirmDialog`**: usan el `<dialog>` nativo (`showModal`), que ya trae foco atrapado y cierre con Esc (accesibilidad sin librerías).
- **`formModal`**: construye un formulario a partir de una lista de campos; valida "obligatorio" en el cliente (solo ayuda de UX: **el servidor es la fuente de verdad**) y pinta los errores 422 junto a cada campo.
- **`dataTable`**: tabla con búsqueda (con *debounce* de 300 ms), filtros y paginación; recibe una función `load` que llama a la API.

## 12.4 `app.js`: el enrutador
1. `start()`: pide `/auth/me`; si falla, a `/login`. Con el rol, construye el menú (`NAV` define qué roles ven cada sección) y el saludo.
2. **Router por hash**: la URL `#/reservations` se mapea a `js/pages/reservations.js`, importado dinámicamente (`import()`), y se llama a su `render(box, ctx)`.
3. **`token` anti-carrera**: si el usuario navega rápido, cada `route()` incrementa un contador y descarta resultados de navegaciones anteriores.
4. El menú oculto **no es seguridad**: aunque alguien escriba una ruta, el servidor valida el rol en cada endpoint.

## 12.5 Las páginas (`js/pages/`)
| Página | Qué hace |
|---|---|
| `dashboard` | Tablero según el rol; gráficas de barras en CSS |
| `reservations` | Pestañas "Nueva reserva" (busca disponibilidad por fecha/hora, muestra mesas libres/ocupadas y el motivo, confirma y reserva; si recibe 409 vuelve a buscar) y "Listado" (cancelar, completar, no asistió, exportar CSV). Calcula en cliente si la cancelación aún es posible, pero el servidor decide |
| `tables` | CRUD de mesas y modal de mantenimiento. **`withRelease`**: llama la acción; si el servidor responde `has_future_reservations`, pregunta al usuario y reintenta con `cancel_reservations=true` |
| `facilities`, `students`, `coaches` | Listados y formularios |
| `classes`, `attendance`, `progress`, `tournaments` | Gestión académica |
| `audit` | Bitácora (solo ADMIN) |
| `profile` | Datos propios, cambio de correo y de contraseña (tras cambiarla, redirige a login porque la sesión quedó invalidada) |

---

# PARTE 13. Datos de demostración (`scripts/seed.py`)

Se ejecuta con `python -m scripts.seed` (el entrypoint lo hace si `SEED_DEMO=1`). Es **idempotente**: las personas se buscan por correo antes de crear (`get_or_create_user`); clases, reservas, asistencia, progreso y torneo se crean una sola vez gracias al marcador `[DEMO]`, así que correrlo dos veces no duplica. Crea 1 administrador, 3 entrenadores, 12 estudiantes (los tres niveles), sedes con mesas en distintos estados, clases, reservas y un torneo. Las fechas se calculan relativas a hoy (`local_dt`), por lo que la demo siempre parece "vigente". Las contraseñas están en el propio archivo y son **solo de desarrollo**; todos los datos son ficticios.

---

# PARTE 14. Pruebas (`backend/tests/`)

## 14.1 Unitarias (`tests/unit/`): no necesitan base de datos
- `test_booking_rules.py`: horarios, duración, 30 días, solapes (incluidos los bordes: consecutivas no chocan), cancelación a 2 h.
- `test_stats_csv_tokens.py`: ocupación, progreso, CSV con inyección de fórmulas, JWT (firma, expiración).
- `test_ratelimit.py`: el limitador de intentos.
- `test_schema_model_contract.py`: comprueba que los schemas no pidan atributos que el modelo no tenga (evita el error "campo fantasma").

## 14.2 Integración (`tests/integration/`): necesitan MariaDB real
- `conftest.py`: **se niega a correr si la base no termina en `_test`** (protege los datos reales). Al empezar borra todas las tablas y aplica las migraciones (`alembic upgrade head`), con lo que también prueba las migraciones; tras cada prueba hace `TRUNCATE` de todo. `make_client` crea clientes HTTP (`TestClient`) ya logueados, con cookie y cabecera CSRF.
- `helpers.py`: fábricas (`make_student`, `make_table`...) y `slot(día, hora)` para crear fechas futuras.
- Archivos: autenticación y permisos, CRUD, reservas, clases/asistencia, ciclo de vida de mesas y perfil, migraciones y semilla, y **concurrencia**.

## 14.3 La prueba de concurrencia, línea a línea
`_race` lanza **10 hilos**, cada uno con **su propia sesión** (su propia transacción) y una `Barrier`, que obliga a todos a esperar y arrancar juntos para maximizar la colisión. Cada uno intenta reservar la **misma mesa y hora**. La aserción exige exactamente 1 `ok`, 9 `conflict` y 1 fila en la tabla. La segunda prueba usa intervalos solapados en cadena (10:00–11:00, 10:30–11:30...) y verifica que ningún par de reservas guardadas se solape. La tercera confirma que mesas distintas **no se bloquean entre sí**.

## 14.4 Resultados y honestidad
Usted ejecutó en Docker: **121 pruebas pasaron, cobertura 82 %**. En el entorno donde se construyó el proyecto solo pudieron correrse las unitarias, ruff, mypy y una prueba de humo del frontend contra un servidor simulado. Comando: `docker compose --profile test run --rm tests`. Dentro de CI el flujo es equivalente con un servicio MariaDB.

---

# PARTE 15. Flujos completos, de extremo a extremo

## 15.1 Iniciar sesión
1. `login.js` envía `POST /api/v1/auth/login {email, password}`.
2. El middleware revisa tamaño y `Origin`. El endpoint consulta el limitador (por `IP|correo`): demasiados fallos → 429.
3. `AuthService.login` valida credenciales (Argon2id), genera `csrf` aleatorio y un JWT con `sub`, `role`, `ver` (= `token_version`) y `csrf`.
4. La respuesta fija **dos cookies**: `rh_session` (HttpOnly) y `rh_csrf` (legible). Devuelve datos básicos.
5. El navegador va a `/`; `app.js` llama `/auth/me`, arma el menú del rol y enruta.

## 15.2 Reservar una mesa (estudiante)
1. `reservations.js` convierte fecha/hora local → ISO UTC y pide `GET /tables/availability`.
2. Se muestran mesas libres; al pulsar "Reservar" y confirmar: `POST /reservations` con cabecera CSRF.
3. FastAPI valida el schema (fechas con zona), resuelve el usuario (cookie + `token_version` + CSRF) y llama `ReservationService.create`.
4. Servicio: reglas puras → `FOR UPDATE` en la mesa → solapes (reservas, clases, mantenimiento) → insertar → auditar → `commit`.
5. Éxito: 201 y aviso verde. Conflicto: 409 y la pantalla vuelve a consultar disponibilidad.

## 15.3 Poner una mesa en mantenimiento con reservas futuras
1. Admin: `POST /tables/{id}/maintenance {starts_at, ends_at, reason}`.
2. El servicio bloquea la mesa y busca reservas confirmadas solapadas. Hay → **409 `has_future_reservations`** con mensaje.
3. `tables.js` (`withRelease`) muestra el diálogo "¿Cancelar reservas y continuar?". Si acepta, reintenta con `cancel_conflicts=true`.
4. El servicio cancela cada reserva (con auditoría "auto"), crea el bloqueo y hace commit. Si hay **clases** en ese rango, siempre se rechaza (hay que reprogramarlas primero).

## 15.4 Cambiar correo o contraseña
- **Correo:** `POST /auth/change-email {new_email, current_password}`: verifica la contraseña, normaliza, valida unicidad (y atrapa la carrera con `IntegrityError`), audita. La interfaz recarga.
- **Contraseña:** verifica la actual (si falla, **400**, no 401, para no expulsar al usuario por un error de tecleo), guarda el hash nuevo y sube `token_version`: todas las sesiones, incluida la actual, quedan inválidas; el frontend redirige a login.

---

# PARTE 16. Seguridad: resumen por capas

| Amenaza | Defensa | Dónde |
|---|---|---|
| Contraseñas robadas de la BD | Argon2id con sal | `core/passwords.py` |
| Robo de sesión por XSS | Cookie HttpOnly; sin `localStorage`; `h()` sin `innerHTML`; CSP `script-src 'self'` | `main.py`, `ui.js` |
| CSRF | Doble envío contra claim firmada + `SameSite=Lax` + verificación de `Origin` | `dependencies/auth.py`, `main.py` |
| Fuerza bruta | Limitador por IP+correo; Argon2 lento | `core/ratelimit.py` |
| Sesión que no muere | `token_version` (logout, cambio de clave, desactivación) | `AuthService` |
| Escalada de privilegios | Rol en cada endpoint + propiedad del recurso en el servicio + lista blanca de campos editables | `dependencies`, `services` |
| Inyección SQL | ORM con parámetros; ordenamiento por lista blanca; `LIKE` escapado | `repositories` |
| Inyección CSV/fórmulas | Prefijo seguro en celdas que empiezan con `= + - @` | `domain/csv_utils.py` |
| Fuga de información | Mensaje único de login; 422 sin eco; 500 genérico; `no-store` | `main.py` |
| Carreras | `FOR UPDATE` + `READ COMMITTED` + restricciones UNIQUE/CHECK | servicios, modelos |
| Clickjacking | `X-Frame-Options: DENY`, `frame-ancestors 'none'` | `main.py` |
| Secretos | Todo por `.env` (fuera de Git); validación de `SECRET_KEY` en producción | `core/config.py` |

---

# PARTE 17. Limitaciones y qué faltaría para producción

**Limitaciones conocidas (honestas):**
- El limitador de intentos vive en **memoria de un solo proceso** (por eso un solo worker); además puede usarse para bloquear a una víctima concreta (IP+correo).
- Swagger (`/docs`) necesita un CDN y queda sin CSP.
- El límite de tamaño de cuerpo mira `Content-Length`; no cubre cuerpos *chunked*.
- "Eliminar" una clase equivale a cancelarla. Claves `INT` en lugar de `BIGINT`. Torneos solo con resultado manual, sin llaves automáticas. Solo el entrenador crea registros de progreso.
- No implementado: RallyBot/IA, correo electrónico, clases recurrentes, multi-sede/multi-tenant, app móvil.
- Su `compose.yaml` publica la app en todas las interfaces de red (`0.0.0.0`); en una máquina compartida conviene enlazarla a `127.0.0.1`. Es una diferencia respecto de una variante endurecida que se le ofreció y que usted decidió no adoptar.
- La documentación (README/Word/`ESTADO_DEL_PROYECTO.md`) aún dice que cerrar sesión no revoca el token y que Docker no se ejecutó; el código actual **sí** revoca en logout y usted **sí** ejecutó Docker (121 pruebas). Pendiente de actualizar si desea.

**Para producción:** HTTPS (y `COOKIE_SECURE=1`), `ENVIRONMENT=production`, `SECRET_KEY` y contraseñas nuevas y largas, `SEED_DEMO=0`, no publicar el puerto de la BD, copias de seguridad, y un limitador compartido (p. ej. Redis) si se usan varios workers.

---

# PARTE 18. Glosario rápido
- **API REST:** servicio web que expone recursos por URL y verbos HTTP.
- **ORM:** traduce objetos Python a tablas SQL.
- **Migración:** script versionado que cambia el esquema de la base.
- **Transacción:** grupo de operaciones que se confirman (`commit`) o se deshacen (`rollback`) juntas.
- **Bloqueo `FOR UPDATE`:** impide que otra transacción toque esa fila hasta terminar.
- **Deadlock:** dos transacciones se esperan mutuamente; se evita con orden fijo de bloqueos.
- **JWT:** token firmado con los datos de la sesión. **CSRF:** petición falsa desde otro sitio con su cookie. **XSS:** inyección de scripts en la página. **CSP:** política que limita qué scripts/recursos puede cargar la página.
- **Idempotente:** repetirlo no cambia el resultado (la semilla).
- **N+1:** hacer una consulta por cada fila en vez de una sola.

---

# PARTE 19. Ejercicios y preguntas de sustentación

**Ejercicios (en este orden):**
1. Arranque con Docker, entre como `estudiante1@rallyhub.demo` y cree una reserva. Entre en otra ventana de incógnito como admin y véala en el listado.
2. Intente reservar la misma mesa y hora desde dos sesiones: observe el 409.
3. Cambie `MIN_MINUTES` en `booking_rules.py`, ejecute `pytest tests/unit` y vea cuál prueba falla y por qué.
4. Añada un campo `notes` a `Reservation`: modelo → migración nueva (`alembic revision`) → schema → servicio → frontend → prueba.
5. En DevTools borre la cookie `rh_csrf`, intente cancelar una reserva y observe el error 403.
6. Cambie `READ COMMITTED` por `REPEATABLE READ` y estudie por qué la prueba de concurrencia podría empezar a fallar.

**Preguntas probables:**
1. ¿Por qué capas y qué gana con ello? *(separación de responsabilidades, pruebas sin BD, cambios localizados).*
2. ¿Cómo evita la doble reserva? *(FOR UPDATE sobre la mesa + READ COMMITTED + comprobación de solape + prueba con 10 hilos).*
3. ¿Por qué `a_start < b_end and a_end > b_start`? *(intervalos semiabiertos; reservas consecutivas no chocan).*
4. ¿Dónde se guardan los tokens y por qué ahí? *(cookie HttpOnly; JS no puede leerlos).*
5. ¿Cómo funciona su CSRF? *(doble envío: cookie legible + cabecera comparada con la claim firmada).*
6. ¿Cómo se invalida una sesión? *(`token_version`).*
7. ¿Por qué UTC en la base y Bogotá en pantalla? *(consistencia; conversión solo en los bordes).*
8. ¿Qué no se pudo verificar en el entorno de construcción y qué sí se verificó después? *(Docker/MariaDB: usted corrió 121 pruebas, 82 %).*
9. ¿Qué limitaciones tiene y cómo las resolvería? *(Parte 17).*
10. ¿Por qué no hay `innerHTML`? *(XSS).*
