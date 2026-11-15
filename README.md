# RallyHub

Plataforma de gestión para academias y clubes de tenis de mesa: estudiantes, entrenadores, mesas, reservas sin solapes, clases, asistencia, progreso, torneos y panel de estadísticas.

Monolito modular: **FastAPI + SQLAlchemy 2 + Alembic + MariaDB 11.4**, frontend JavaScript nativo servido desde el mismo origen. Proyecto integrador — Taller de Programación, Universidad Manuela Beltrán.

> **Estado honesto:** el código fue escrito y verificado estáticamente y con 57 pruebas unitarias puras. Docker, MariaDB, migraciones y pruebas de integración **no se ejecutaron** en el entorno de construcción. Ver `docs/ESTADO_DEL_PROYECTO.md`.

## Requisitos
Docker y Docker Compose v2.

## Puesta en marcha
```bash
cp .env.example .env        # y cambie los valores change-me
docker compose up --build -d
docker compose ps
docker compose logs -f app
```
- Aplicación: http://localhost:8000/
- API interactiva: http://localhost:8000/docs (requiere acceso a CDN)
- Salud: http://localhost:8000/health

Con `RUN_MIGRATIONS=1` y `SEED_DEMO=1` el contenedor aplica migraciones y carga datos ficticios. Manualmente:
```bash
docker compose exec app alembic upgrade head
docker compose exec app python -m scripts.seed
```
Detener: `docker compose down`. **`docker compose down -v` borra todos los datos.**

### Demo en GitHub Codespaces
En GitHub: **Code → Codespaces → Create codespace on main**. Al arrancar, `.devcontainer/` instala Docker y ejecuta `scripts/codespace-demo.sh`, que crea `.env` con secretos aleatorios y datos de demostración, permite el origen del codespace, levanta todo y publica el puerto 8000. La URL aparece en la terminal y en la pestaña **PORTS** (`https://<codespace>-8000.app.github.dev`). Si el codespace se suspendió, al reanudarlo el script vuelve a levantar la app; también se puede ejecutar a mano con `bash scripts/codespace-demo.sh`. Es un entorno de demostración, no de producción.

## Usuarios de demostración (SOLO DESARROLLO)
| Rol | Correo | Contraseña |
|---|---|---|
| Administrador | admin@rallyhub.demo | Admin-Demo-2026 |
| Entrenadores | coach1@ … coach3@rallyhub.demo | Coach-Demo-2026 |
| Estudiantes | estudiante1@ … estudiante12@rallyhub.demo | Student-Demo-2026 |

Son datos ficticios; nunca los use en producción (el seed se ignora con `ENVIRONMENT=production`).

## Pruebas
Unitarias (sin dependencias de BD), desde `backend/`:
```bash
python -m pytest tests/unit
ruff check .
```
Integración (requiere MariaDB):
```bash
docker compose --profile test run --rm tests
```
La base `rallyhub_test` solo se crea al inicializar un volumen nuevo.

## Variables de entorno
Ver `.env.example`, comentado línea a línea. En producción: `ENVIRONMENT=production`, `COOKIE_SECURE=true`, `DOCS_ENABLED=false`, claves reales y HTTPS.

## Estructura
```
backend/app/   api, services, repositories, models, schemas, domain, core, static (frontend)
backend/alembic/  migraciones
backend/tests/    unit/ e integration/
db/init/          script de BD de pruebas
docs/             arquitectura, requisitos, manuales, diagramas, estado
```

## Solución de problemas
- *La app no arranca en producción:* clave por defecto o `COOKIE_SECURE=false`.
- *Error de conexión a BD:* espere al healthcheck de `db`; revise `docker compose logs db`.
- *No existe `rallyhub_test`:* recree el volumen (`down -v`, pierde datos) o créela a mano.
- *Login bloqueado:* espere la ventana de bloqueo o reinicie la app (límite en memoria).

## Documentación
`docs/` y `documentacion/` (documentación técnica en Word, presentación de sustentación y guía del código). Límites conocidos: `docs/ALCANCE_Y_LIMITACIONES.md`.
