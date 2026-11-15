#!/usr/bin/env bash
# Levanta RallyHub en GitHub Codespaces para la demostración.
# - Crea .env (si no existe) con secretos aleatorios y los datos ficticios de demo.
# - Permite el origen https://<codespace>-8000.<dominio> (si no, el login responde 403 bad_origin).
# - Construye y arranca db + app con Docker Compose y espera a que respondan.
# Uso: bash scripts/codespace-demo.sh
set -euo pipefail
cd "$(dirname "$0")/.."

PORT=8000
if [[ -n "${CODESPACE_NAME:-}" ]]; then
  PUBLIC_URL="https://${CODESPACE_NAME}-${PORT}.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN:-app.github.dev}"
else
  PUBLIC_URL="http://localhost:${PORT}"
fi

rand() { openssl rand -hex "$1"; }

if [[ ! -f .env ]]; then
  echo "Creando .env para la demo…"
  sed -e "s|^SECRET_KEY=.*|SECRET_KEY=$(rand 32)|" \
      -e "s|^DB_ROOT_PASSWORD=.*|DB_ROOT_PASSWORD=$(rand 16)|" \
      -e "s|^DB_PASSWORD=.*|DB_PASSWORD=$(rand 16)|" \
      -e "s|^SEED_DEMO=.*|SEED_DEMO=1|" \
      -e "s|^APP_PORT=.*|APP_PORT=${PORT}|" \
      .env.example > .env
fi
# El nombre del codespace no cambia, pero se reescribe por si .env viene de otro entorno.
if grep -q '^ALLOWED_ORIGINS=' .env; then
  sed -i "s|^ALLOWED_ORIGINS=.*|ALLOWED_ORIGINS=${PUBLIC_URL}|" .env
else
  echo "ALLOWED_ORIGINS=${PUBLIC_URL}" >> .env
fi

# docker-in-docker puede tardar unos segundos en estar listo al arrancar el codespace.
for _ in $(seq 1 30); do docker info >/dev/null 2>&1 && break; sleep 2; done

docker compose up --build -d

echo "Esperando a que RallyHub responda…"
for _ in $(seq 1 90); do
  if curl -fsS "http://localhost:${PORT}/health/ready" >/dev/null 2>&1; then
    # Hace pública la URL para que el público pueda abrirla (requiere gh dentro del codespace).
    if [[ -n "${CODESPACE_NAME:-}" ]] && command -v gh >/dev/null 2>&1; then
      gh codespace ports visibility "${PORT}:public" -c "${CODESPACE_NAME}" >/dev/null 2>&1 \
        || echo "Aviso: no se pudo hacer público el puerto; hazlo en la pestaña PORTS (clic derecho → Port Visibility → Public)."
    fi
    echo
    echo "RallyHub está listo: ${PUBLIC_URL}"
    echo "Usuarios de demo: admin@rallyhub.demo, coach1@rallyhub.demo, estudiante1@rallyhub.demo (contraseñas en el README)."
    exit 0
  fi
  sleep 2
done
echo "RallyHub no respondió a tiempo. Revisa: docker compose logs app" >&2
exit 1
