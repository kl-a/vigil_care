#!/usr/bin/env bash
# Run Vigil locally so you can click through it.
#
#   scripts/run-local.sh           Full stack in Docker (Postgres, backend, frontend)
#   scripts/run-local.sh --dev     Postgres in Docker; backend + frontend on the host with hot reload
#   scripts/run-local.sh --stop    Stop everything this script started
#   scripts/run-local.sh --help
#
# Nothing is installed globally: Python deps go in backend/.venv, Node deps in frontend/node_modules.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$ROOT/.run"          # PID files and logs for --dev (gitignored)
DB_PORT="${VIGIL_DB_PORT:-5432}"
BACKEND_PORT="${VIGIL_BACKEND_PORT:-8000}"
FRONTEND_PORT="${VIGIL_FRONTEND_PORT:-3000}"

bold() { printf '\033[1m%s\033[0m\n' "$*"; }
ok()   { printf '  \033[32m✓\033[0m %s\n' "$*"; }
warn() { printf '  \033[33m!\033[0m %s\n' "$*"; }
die()  { printf '  \033[31m✗\033[0m %s\n' "$*" >&2; exit 1; }

usage() { sed -n '2,9p' "$0" | sed 's/^# \{0,1\}//'; }

need() { command -v "$1" >/dev/null 2>&1 || die "$1 is not installed. $2"; }

check_prerequisites() {
  bold "Checking prerequisites"
  need docker "Install Docker Desktop: https://www.docker.com/products/docker-desktop/"
  docker compose version >/dev/null 2>&1 || die "Docker Compose v2 is missing (it ships with Docker Desktop)."
  if ! docker info >/dev/null 2>&1; then
    if [[ "$(uname)" == "Darwin" ]]; then
      warn "Docker isn't running. Starting Docker Desktop…"
      open -a Docker
      for _ in $(seq 1 60); do docker info >/dev/null 2>&1 && break; sleep 2; done
    fi
    docker info >/dev/null 2>&1 || die "Docker isn't running. Start Docker Desktop and try again."
  fi
  ok "Docker is running"
  if [[ "${1:-}" == "dev" ]]; then
    need node "Install Node.js 20+: https://nodejs.org/"
    need npm "npm ships with Node.js."
    PYTHON="$(command -v python3.12 || command -v python3.13 || command -v python3 || true)"
    [[ -n "$PYTHON" ]] || die "Python 3.12+ is not installed."
    "$PYTHON" -c 'import sys; sys.exit(sys.version_info < (3, 12))' || die "Python 3.12+ is required (found $("$PYTHON" --version))."
    ok "Node $(node --version), $("$PYTHON" --version)"
  fi
}

ensure_env_file() {
  if [[ ! -f "$ROOT/.env" ]]; then
    cp "$ROOT/.env.example" "$ROOT/.env"
    ok "Created .env from .env.example (VIGIL_ENV=dev)"
  else
    ok ".env exists"
  fi
  # Stage demos sign in with the dev login (design doc §15). Older .env files had it off.
  if grep -q '^VIGIL_ENV=dev' "$ROOT/.env" && grep -q '^VIGIL_DEV_LOGIN_ENABLED=false' "$ROOT/.env"; then
    sed -i.bak 's/^VIGIL_DEV_LOGIN_ENABLED=false/VIGIL_DEV_LOGIN_ENABLED=true/' "$ROOT/.env" && rm -f "$ROOT/.env.bak"
    ok "Turned the dev login on in .env (dev only)"
  fi
}

port_in_use() { lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1; }

# First free port from $1 upwards (another app may already own the default, e.g. another Next.js dev server).
free_port_from() {
  local port="$1"
  for _ in $(seq 1 20); do port_in_use "$port" || { echo "$port"; return 0; }; port=$((port + 1)); done
  die "No free port found near $1."
}

choose_ports() {
  # Release Vigil's own containers first so their ports don't count as taken (the database volume is kept).
  (cd "$ROOT" && docker compose stop >/dev/null 2>&1 || true)
  local wanted_db="$DB_PORT" wanted_backend="$BACKEND_PORT" wanted_frontend="$FRONTEND_PORT"
  DB_PORT="$(free_port_from "$DB_PORT")"
  BACKEND_PORT="$(free_port_from "$BACKEND_PORT")"
  FRONTEND_PORT="$(free_port_from "$FRONTEND_PORT")"
  [[ "$DB_PORT" == "$wanted_db" ]] || warn "Port $wanted_db is taken by another app (e.g. a local Postgres); Vigil's database will use $DB_PORT."
  [[ "$BACKEND_PORT" == "$wanted_backend" ]] || warn "Port $wanted_backend is taken by another app; the backend will use $BACKEND_PORT."
  [[ "$FRONTEND_PORT" == "$wanted_frontend" ]] || warn "Port $wanted_frontend is taken by another app; the frontend will use $FRONTEND_PORT."
  BACKEND_URL="http://localhost:$BACKEND_PORT"
  FRONTEND_URL="http://localhost:$FRONTEND_PORT"
  export VIGIL_DB_PORT="$DB_PORT" VIGIL_BACKEND_PORT="$BACKEND_PORT" VIGIL_FRONTEND_PORT="$FRONTEND_PORT"
}

wait_for() { # url, label, seconds. "Up" means it answers at all; health is reported separately.
  local url="$1" label="$2" limit="${3:-120}" code
  for _ in $(seq 1 "$limit"); do
    code="$(curl -s -o /dev/null -w '%{http_code}' "$url" 2>/dev/null || true)"
    if [[ "$code" != "000" && -n "$code" ]]; then ok "$label is up ($url)"; return 0; fi
    sleep 1
  done
  die "$label didn't come up at $url within ${limit}s. See the logs above (or in $RUN_DIR)."
}

report_health() {
  local body; body="$(curl -s "$BACKEND_URL/health" || true)"
  if [[ "$body" == *'"status":"ok"'* ]]; then ok "Health: $body"; else warn "Health: $body"; fi
}

start_docker() {
  choose_ports
  bold "Starting the full stack in Docker (first run builds images; allow a few minutes)"
  (cd "$ROOT" && docker compose up --build -d)
  wait_for "$BACKEND_URL/health" "Backend" 180
  bold "Loading the synthetic demo Practice"
  (cd "$ROOT" && docker compose exec -T backend python -m app.db.demo_data)
  wait_for "$FRONTEND_URL/login" "Frontend" 180
  report_health
}

already_running() {
  local pidfile
  for pidfile in "$RUN_DIR"/*.pid; do
    [[ -f "$pidfile" ]] && kill -0 "$(cat "$pidfile")" 2>/dev/null && return 0
  done
  return 1
}

start_dev() {
  mkdir -p "$RUN_DIR"
  already_running && die "Vigil is already running in --dev mode. Stop it first with: $0 --stop"
  bold "Starting Postgres in Docker"
  choose_ports
  (cd "$ROOT" && docker compose up -d db)

  bold "Preparing the backend (backend/.venv)"
  if [[ ! -x "$ROOT/backend/.venv/bin/python" ]]; then
    "$PYTHON" -m venv "$ROOT/backend/.venv"
  fi
  "$ROOT/backend/.venv/bin/pip" install -q -e "$ROOT/backend[dev]"
  ok "Backend dependencies installed"

  bold "Preparing the frontend (frontend/node_modules)"
  (cd "$ROOT/frontend" && npm ci --silent)
  ok "Frontend dependencies installed"

  bold "Creating database roles and migrating the schema"
  (cd "$ROOT/backend" && VIGIL_DB_ADMIN_URL="postgresql://vigil:vigil@127.0.0.1:$DB_PORT/vigil" .venv/bin/python -m app.db.provision)
  ok "Schema at head"
  (cd "$ROOT/backend" && VIGIL_ENV=dev VIGIL_DATABASE_URL="postgresql://vigil_app:vigil_app_dev@127.0.0.1:$DB_PORT/vigil" \
    .venv/bin/python -m app.db.demo_data)

  bold "Starting backend, worker and frontend with hot reload"
  trap 'on_dev_failure' EXIT
  (cd "$ROOT/backend" && VIGIL_ENV=dev VIGIL_DEV_LOGIN_ENABLED=true \
    VIGIL_DATABASE_URL="postgresql://vigil_app:vigil_app_dev@127.0.0.1:$DB_PORT/vigil" \
    nohup .venv/bin/uvicorn app.main:create_app --factory --reload --port "$BACKEND_PORT" >"$RUN_DIR/backend.log" 2>&1 &
    echo $! >"$RUN_DIR/backend.pid")
  # The job queue's worker (#18): runs Refreshes and, later, document processing.
  (cd "$ROOT/backend" && VIGIL_ENV=dev \
    VIGIL_DATABASE_URL="postgresql://vigil_app:vigil_app_dev@127.0.0.1:$DB_PORT/vigil" \
    nohup .venv/bin/python -m app.orchestrator.worker >"$RUN_DIR/worker.log" 2>&1 &
    echo $! >"$RUN_DIR/worker.pid")
  (cd "$ROOT/frontend" && VIGIL_API_URL="$BACKEND_URL" nohup npm run dev -- -p "$FRONTEND_PORT" >"$RUN_DIR/frontend.log" 2>&1 & echo $! >"$RUN_DIR/frontend.pid")
  wait_for "$BACKEND_URL/health" "Backend" 60
  wait_for "$FRONTEND_URL/login" "Frontend" 120
  trap - EXIT
  report_health
  ok "Logs: $RUN_DIR/backend.log, $RUN_DIR/worker.log and $RUN_DIR/frontend.log"
}

# If --dev fails part-way, don't leave host processes running.
on_dev_failure() {
  local status=$?
  [[ $status -eq 0 ]] && return 0
  warn "Startup failed; stopping what was started. Logs are in $RUN_DIR."
  stop_host_processes
}

stop_host_processes() {
  for name in backend worker frontend; do
    local pidfile="$RUN_DIR/$name.pid"
    if [[ -f "$pidfile" ]]; then
      local pid; pid="$(cat "$pidfile")"
      pkill -P "$pid" 2>/dev/null || true
      kill "$pid" 2>/dev/null || true
      rm -f "$pidfile"
      ok "Stopped host $name"
    fi
  done
}

stop_all() {
  bold "Stopping Vigil"
  stop_host_processes
  if docker info >/dev/null 2>&1; then
    (cd "$ROOT" && docker compose down)
    ok "Stopped Docker services (database volume kept)"
  fi
}

print_guide() {
  cat <<EOF

$(bold "Vigil is running")
  App:        $FRONTEND_URL
  Health:     $BACKEND_URL/health
  API docs:   $BACKEND_URL/docs

$(bold "Click-through guide (Stage 1 so far; the full script is docs/demos/stage-1.md)")
  1. Open $FRONTEND_URL. The dev login lists the synthetic Harbourside Oncology Users. Choose one:
       Dr Alex Rivera (synthetic), Clinician        → every item
       Sam Lee (synthetic), Trial coordinator       → no Users or Settings
       Jordan Park (synthetic), Secretary           → Users, but no Settings
       Casey Dev (synthetic), Developer admin       → only Users, Settings, System status; no Patient search
  2. Log out (top right) and choose someone else to watch the sidebar change.
  3. As Casey Dev, open $FRONTEND_URL/patients/jane/summary: you get "Not available for your Job Title".
  4. As Dr Alex Rivera → Patients → "Jane Citizen (synthetic)" → click through the Patient tabs.
     Summary, Overview and Clinical Data show sections registered by the Oncology module;
     "Treatment Options" is an Oncology tab.
  5. Try the moon icon (dark theme), the sidebar toggle, and a bad URL like $FRONTEND_URL/nope (404 with the badge).
  6. Open $BACKEND_URL/health: {"status":"ok","environment":"dev","database":"ok",...}
  7. Open docs/data-model/index.html in a browser to click through every table (ticket #2).

  Every screen is a placeholder for now; later tickets fill them in.
  Stop everything with: $0 --stop
EOF
}

open_browser() {
  [[ -n "${VIGIL_NO_BROWSER:-}" ]] && return 0
  if [[ "$(uname)" == "Darwin" ]]; then open "$FRONTEND_URL"; fi
}

case "${1:-}" in
  --help|-h) usage ;;
  --stop) stop_all ;;
  --dev) check_prerequisites dev; ensure_env_file; start_dev; print_guide; open_browser ;;
  "") check_prerequisites; ensure_env_file; start_docker; print_guide; open_browser ;;
  *) usage; exit 2 ;;
esac
