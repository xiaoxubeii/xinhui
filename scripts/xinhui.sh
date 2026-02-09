#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="${ROOT_DIR}/var/xinhui"
LOG_DIR="${ROOT_DIR}/logs/xinhui"
ENV_FILE="${ROOT_DIR}/.env"
DEFAULT_FRONTEND_PORT_FALLBACK="5173"
DEFAULT_FRONTEND_DEV_FALLBACK="0"
DEFAULT_BACKEND_PORT_FALLBACK="8000"
DEFAULT_BACKEND_HOST_FALLBACK="127.0.0.1"
DEFAULT_OPENCODE_PORT_FALLBACK="4096"
DEFAULT_OPENCODE_HOST_FALLBACK="127.0.0.1"
DEFAULT_OPENCODE_MODE_FALLBACK="web"
DEFAULT_OPENCODE_BIN_FALLBACK="/home/cheng/workspace/opencode"
DEFAULT_OPENCODE_APP_ENABLE_FALLBACK="0"
DEFAULT_OPENCODE_APP_DIR_FALLBACK="/home/cheng/workspace/opencode/packages/app"
DEFAULT_OPENCODE_APP_HOST_FALLBACK="0.0.0.0"
DEFAULT_OPENCODE_APP_PORT_FALLBACK="3000"
DEFAULT_OPENCODE_APP_POLLING_FALLBACK="1"
DEFAULT_OPENCODE_APP_POLLING_INTERVAL_FALLBACK="1000"

usage() {
  cat <<'EOF'
Usage: scripts/xinhui.sh <start|stop|restart|status> [backend|frontend|opencode|opencode-ui|all] [--backend-port PORT] [--backend-host HOST] [--opencode-port PORT] [--opencode-host HOST] [--opencode-mode serve|web] [--opencode-bin PATH|DIR] [--opencode-app-enable 0|1] [--opencode-app-dir DIR] [--opencode-app-host HOST] [--opencode-app-port PORT] [--opencode-app-polling 0|1] [--opencode-app-polling-interval MS] [PORT] [HOST]

Examples:
  scripts/xinhui.sh start
  scripts/xinhui.sh stop all
  scripts/xinhui.sh restart backend
  scripts/xinhui.sh status
  scripts/xinhui.sh start 8000 0.0.0.0
  scripts/xinhui.sh start backend --backend-port 8000 --backend-host 0.0.0.0
  scripts/xinhui.sh restart opencode --opencode-mode web --opencode-host 0.0.0.0 --opencode-port 4096
  scripts/xinhui.sh restart opencode --opencode-bin /home/cheng/workspace/opencode
  scripts/xinhui.sh restart opencode-ui --opencode-app-enable 1
EOF
}

load_env() {
  if [[ -f "${ENV_FILE}" ]]; then
    set -a
    # shellcheck disable=SC1090
    . "${ENV_FILE}"
    set +a
  fi
}

ensure_dirs() {
  mkdir -p "${RUN_DIR}" "${LOG_DIR}"
}

require_cmd() {
  local cmd="$1"
  if [[ "${cmd}" == */* ]]; then
    if [[ ! -x "${cmd}" ]]; then
      echo "Missing command: ${cmd}" >&2
      return 1
    fi
    return 0
  fi
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    echo "Missing command: ${cmd}" >&2
    return 1
  fi
}

find_pids_by_port() {
  local port="$1"
  local pids=""
  if command -v lsof >/dev/null 2>&1; then
    pids="$(lsof -tiTCP:"${port}" -sTCP:LISTEN 2>/dev/null || true)"
  elif command -v ss >/dev/null 2>&1; then
    pids="$(ss -lptn "sport = :${port}" 2>/dev/null | awk 'NR>1 {print $6}' | sed -E 's/.*pid=([0-9]+).*/\1/' | sort -u | tr '\n' ' ' | xargs echo -n || true)"
  elif command -v fuser >/dev/null 2>&1; then
    pids="$(fuser -n tcp "${port}" 2>/dev/null | tr ' ' '\n' | sort -u | tr '\n' ' ' | xargs echo -n || true)"
  fi
  echo "${pids}"
}

port_listening() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof -iTCP:"${port}" -sTCP:LISTEN >/dev/null 2>&1
    return $?
  elif command -v ss >/dev/null 2>&1; then
    ss -ltn "sport = :${port}" 2>/dev/null | awk 'NR>1 {print $1}' | grep -q .
    return $?
  elif command -v fuser >/dev/null 2>&1; then
    fuser -n tcp "${port}" >/dev/null 2>&1
    return $?
  fi
  return 1
}

pidfile_for() {
  echo "${RUN_DIR}/$1.pid"
}

logfile_for() {
  echo "${LOG_DIR}/$1.log"
}

is_running() {
  local pidfile="$1"
  local pid=""
  if [[ -f "${pidfile}" ]]; then
    pid="$(cat "${pidfile}" 2>/dev/null || true)"
  fi
  if [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null; then
    return 0
  fi
  return 1
}

wait_for_exit() {
  local pid="$1"
  local timeout="${2:-10}"
  local start_ts
  start_ts="$(date +%s)"
  while kill -0 "${pid}" 2>/dev/null; do
    if (( $(date +%s) - start_ts >= timeout )); then
      return 1
    fi
    sleep 0.5
  done
  return 0
}

start_backend() {
  require_cmd uvicorn
  ensure_dirs
  local pidfile
  pidfile="$(pidfile_for backend)"
  local logfile
  logfile="$(logfile_for backend)"
  if is_running "${pidfile}"; then
    echo "backend: already running (pid $(cat "${pidfile}"))"
    return 0
  fi
  (
    cd "${ROOT_DIR}"
    if [[ "${FRONTEND_DEV}" == "1" || "${FRONTEND_DEV,,}" == "true" ]]; then
      FRONTEND_DEV_SERVER="http://localhost:${FRONTEND_PORT}" \
        uvicorn backend.api:app --reload --reload-dir backend --host "${BACKEND_HOST}" --port "${BACKEND_PORT}" \
        >>"${logfile}" 2>&1 &
    else
      uvicorn backend.api:app --reload --reload-dir backend --host "${BACKEND_HOST}" --port "${BACKEND_PORT}" \
        >>"${logfile}" 2>&1 &
    fi
    echo $! > "${pidfile}"
  )
  echo "backend: started (pid $(cat "${pidfile}"))"
}

start_frontend() {
  require_cmd npm
  ensure_dirs
  local pidfile
  pidfile="$(pidfile_for frontend)"
  local logfile
  logfile="$(logfile_for frontend)"
  if is_running "${pidfile}"; then
    echo "frontend: already running (pid $(cat "${pidfile}"))"
    return 0
  fi
  if ! [[ "${FRONTEND_DEV}" == "1" || "${FRONTEND_DEV,,}" == "true" ]]; then
    echo "frontend: skipped (FRONTEND_DEV=${FRONTEND_DEV})"
    return 0
  fi
  (
    cd "${ROOT_DIR}/frontend"
    VITE_DEV_BASE="/app/" \
      VITE_HMR="${FRONTEND_HMR}" \
      VITE_POLLING="${FRONTEND_POLLING}" \
      VITE_POLLING_INTERVAL="${FRONTEND_POLLING_INTERVAL}" \
      CHOKIDAR_USEPOLLING="${FRONTEND_POLLING}" \
      CHOKIDAR_INTERVAL="${FRONTEND_POLLING_INTERVAL}" \
      npm run dev -- --host 0.0.0.0 --port "${FRONTEND_PORT}" \
      >>"${logfile}" 2>&1 &
    echo $! > "${pidfile}"
  )
  echo "frontend: started (pid $(cat "${pidfile}"))"
}

start_opencode() {
  require_cmd "${OPENCODE_BIN_CMD}"
  ensure_dirs
  local pidfile
  pidfile="$(pidfile_for opencode)"
  local logfile
  logfile="$(logfile_for opencode)"
  if is_running "${pidfile}"; then
    echo "opencode: already running (pid $(cat "${pidfile}"))"
    return 0
  fi
  local opencode_command
  case "${OPENCODE_MODE}" in
    serve|web)
      opencode_command="${OPENCODE_MODE}"
      ;;
    *)
      echo "opencode: invalid mode '${OPENCODE_MODE}' (expected serve or web)" >&2
      return 1
      ;;
  esac
  (
    cd "${OPENCODE_WORKDIR}"
    if command -v setsid >/dev/null 2>&1; then
      setsid "${OPENCODE_BIN_CMD}" "${OPENCODE_BIN_ARGS[@]}" "${opencode_command}" --hostname "${OPENCODE_HOST}" --port "${OPENCODE_PORT}" \
        >>"${logfile}" 2>&1 &
    else
      "${OPENCODE_BIN_CMD}" "${OPENCODE_BIN_ARGS[@]}" "${opencode_command}" --hostname "${OPENCODE_HOST}" --port "${OPENCODE_PORT}" \
        >>"${logfile}" 2>&1 &
    fi
    echo $! > "${pidfile}"
  )
  echo "opencode: started (pid $(cat "${pidfile}"))"
}

start_opencode_ui() {
  require_cmd "${OPENCODE_APP_BIN}"
  ensure_dirs
  local pidfile
  pidfile="$(pidfile_for opencode_ui)"
  local logfile
  logfile="$(logfile_for opencode_ui)"
  if is_running "${pidfile}"; then
    echo "opencode-ui: already running (pid $(cat "${pidfile}"))"
    return 0
  fi
  if [[ ! -d "${OPENCODE_APP_DIR}" ]]; then
    echo "opencode-ui: missing app dir ${OPENCODE_APP_DIR}" >&2
    return 1
  fi
  local server_host
  server_host="${OPENCODE_APP_SERVER_HOST:-}"
  if [[ -z "${server_host}" ]]; then
    if [[ "${OPENCODE_HOST}" == "0.0.0.0" ]]; then
      server_host="localhost"
    else
      server_host="${OPENCODE_HOST}"
    fi
  fi
  local server_port
  server_port="${OPENCODE_APP_SERVER_PORT:-${OPENCODE_PORT}}"
  (
    cd "${OPENCODE_APP_DIR}"
    if command -v setsid >/dev/null 2>&1; then
      VITE_OPENCODE_SERVER_HOST="${server_host}" \
        VITE_OPENCODE_SERVER_PORT="${server_port}" \
        CHOKIDAR_USEPOLLING="${OPENCODE_APP_POLLING}" \
        CHOKIDAR_INTERVAL="${OPENCODE_APP_POLLING_INTERVAL}" \
        setsid "${OPENCODE_APP_BIN}" "${OPENCODE_APP_BIN_ARGS[@]}" \
        --host "${OPENCODE_APP_HOST}" --port "${OPENCODE_APP_PORT}" \
        >>"${logfile}" 2>&1 &
    else
      VITE_OPENCODE_SERVER_HOST="${server_host}" \
        VITE_OPENCODE_SERVER_PORT="${server_port}" \
        CHOKIDAR_USEPOLLING="${OPENCODE_APP_POLLING}" \
        CHOKIDAR_INTERVAL="${OPENCODE_APP_POLLING_INTERVAL}" \
        "${OPENCODE_APP_BIN}" "${OPENCODE_APP_BIN_ARGS[@]}" \
        --host "${OPENCODE_APP_HOST}" --port "${OPENCODE_APP_PORT}" \
        >>"${logfile}" 2>&1 &
    fi
    echo $! > "${pidfile}"
  )
  echo "opencode-ui: started (pid $(cat "${pidfile}"))"
}

stop_service() {
  local name="$1"
  local pidfile
  pidfile="$(pidfile_for "${name}")"
  if ! [[ -f "${pidfile}" ]]; then
    echo "${name}: not running (no pidfile)"
    return 0
  fi
  local pid
  pid="$(cat "${pidfile}" 2>/dev/null || true)"
  if [[ -z "${pid}" ]]; then
    rm -f "${pidfile}"
    echo "${name}: stale pidfile removed"
    return 0
  fi
  if ! kill -0 "${pid}" 2>/dev/null; then
    rm -f "${pidfile}"
    echo "${name}: not running (stale pid ${pid})"
    return 0
  fi
  kill "${pid}" 2>/dev/null || true
  if ! wait_for_exit "${pid}" 10; then
    echo "${name}: force killing (pid ${pid})"
    kill -9 "${pid}" 2>/dev/null || true
  fi
  rm -f "${pidfile}"
  echo "${name}: stopped"
}

stop_opencode() {
  stop_service opencode
  local pids
  pids="$(find_pids_by_port "${OPENCODE_PORT}")"
  if [[ -n "${pids}" ]]; then
    echo "opencode: cleaning up by port ${OPENCODE_PORT} (pids ${pids})"
    kill ${pids} 2>/dev/null || true
    for pid in ${pids}; do
      if ! wait_for_exit "${pid}" 5; then
        kill -9 "${pid}" 2>/dev/null || true
      fi
    done
  fi
}

status_service() {
  local name="$1"
  local pidfile
  pidfile="$(pidfile_for "${name}")"
  if is_running "${pidfile}"; then
    echo "${name}: running (pid $(cat "${pidfile}"))"
  else
    echo "${name}: stopped"
  fi
}

status_backend() {
  if port_listening "${BACKEND_PORT}"; then
    echo "backend: running (port ${BACKEND_PORT})"
    return 0
  fi
  if is_running "$(pidfile_for backend)"; then
    echo "backend: error (pid $(cat "$(pidfile_for backend)"), port ${BACKEND_PORT} not listening)"
  else
    echo "backend: stopped"
  fi
}

status_frontend() {
  if port_listening "${FRONTEND_PORT}"; then
    echo "frontend: running (port ${FRONTEND_PORT})"
    return 0
  fi
  if is_running "$(pidfile_for frontend)"; then
    echo "frontend: error (pid $(cat "$(pidfile_for frontend)"), port ${FRONTEND_PORT} not listening)"
  else
    echo "frontend: stopped"
  fi
}

status_opencode() {
  if is_running "$(pidfile_for opencode)"; then
    echo "opencode: running (pid $(cat "$(pidfile_for opencode)"))"
    return 0
  fi
  local pids
  pids="$(find_pids_by_port "${OPENCODE_PORT}")"
  if [[ -n "${pids}" ]]; then
    echo "opencode: running (port ${OPENCODE_PORT}, pid ${pids})"
  else
    echo "opencode: stopped"
  fi
}

status_opencode_ui() {
  if port_listening "${OPENCODE_APP_PORT}"; then
    echo "opencode-ui: running (port ${OPENCODE_APP_PORT})"
    return 0
  fi
  if is_running "$(pidfile_for opencode_ui)"; then
    echo "opencode-ui: error (pid $(cat "$(pidfile_for opencode_ui)"), port ${OPENCODE_APP_PORT} not listening)"
  else
    echo "opencode-ui: stopped"
  fi
}

resolve_services() {
  local target="${1:-all}"
  case "${target}" in
    all|"")
      if [[ "${OPENCODE_APP_ENABLE}" == "1" || "${OPENCODE_APP_ENABLE,,}" == "true" ]]; then
        echo "backend frontend opencode opencode_ui"
      else
        echo "backend frontend opencode"
      fi
      ;;
    backend|frontend|opencode)
      echo "${target}"
      ;;
    opencode-ui|opencode_ui)
      echo "opencode_ui"
      ;;
    *)
      usage
      exit 1
      ;;
  esac
}

main() {
  local action="${1:-}"
  if [[ -z "${action}" ]]; then
    usage
    exit 1
  fi
  shift || true

  local target="all"
  local backend_port_override=""
  local backend_host_override=""
  local opencode_port_override=""
  local opencode_host_override=""
  local opencode_mode_override=""
  local opencode_bin_override=""
  local opencode_app_enable_override=""
  local opencode_app_dir_override=""
  local opencode_app_host_override=""
  local opencode_app_port_override=""
  local opencode_app_polling_override=""
  local opencode_app_polling_interval_override=""

  while [[ $# -gt 0 ]]; do
    case "$1" in
      backend|frontend|opencode|opencode-ui|opencode_ui|all)
        target="$1"
        shift
        ;;
      --backend-port)
        backend_port_override="${2:-}"
        shift 2
        ;;
      --backend-host)
        backend_host_override="${2:-}"
        shift 2
        ;;
      --opencode-port)
        opencode_port_override="${2:-}"
        shift 2
        ;;
      --opencode-host)
        opencode_host_override="${2:-}"
        shift 2
        ;;
      --opencode-mode)
        opencode_mode_override="${2:-}"
        shift 2
        ;;
      --opencode-bin)
        opencode_bin_override="${2:-}"
        shift 2
        ;;
      --opencode-app-enable)
        opencode_app_enable_override="${2:-}"
        shift 2
        ;;
      --opencode-app-dir)
        opencode_app_dir_override="${2:-}"
        shift 2
        ;;
      --opencode-app-host)
        opencode_app_host_override="${2:-}"
        shift 2
        ;;
      --opencode-app-port)
        opencode_app_port_override="${2:-}"
        shift 2
        ;;
      --opencode-app-polling)
        opencode_app_polling_override="${2:-}"
        shift 2
        ;;
      --opencode-app-polling-interval)
        opencode_app_polling_interval_override="${2:-}"
        shift 2
        ;;
      --help|-h)
        usage
        exit 0
        ;;
      *)
        if [[ "$1" =~ ^[0-9]+$ ]] && [[ -z "${backend_port_override}" ]]; then
          backend_port_override="$1"
          shift
        elif [[ "$1" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]] && [[ -z "${backend_host_override}" ]]; then
          backend_host_override="$1"
          shift
        else
          usage
          exit 1
        fi
        ;;
    esac
  done

  load_env
  FRONTEND_PORT="${FRONTEND_PORT:-${DEFAULT_FRONTEND_PORT_FALLBACK}}"
  FRONTEND_DEV="${FRONTEND_DEV:-${DEFAULT_FRONTEND_DEV_FALLBACK}}"
  BACKEND_PORT="${BACKEND_PORT:-${DEFAULT_BACKEND_PORT_FALLBACK}}"
  BACKEND_HOST="${BACKEND_HOST:-${DEFAULT_BACKEND_HOST_FALLBACK}}"
  OPENCODE_PORT="${OPENCODE_PORT:-${DEFAULT_OPENCODE_PORT_FALLBACK}}"
  OPENCODE_HOST="${OPENCODE_HOST:-${DEFAULT_OPENCODE_HOST_FALLBACK}}"
  OPENCODE_MODE="${OPENCODE_MODE:-${DEFAULT_OPENCODE_MODE_FALLBACK}}"
  OPENCODE_BIN="${OPENCODE_BIN:-${DEFAULT_OPENCODE_BIN_FALLBACK}}"
  OPENCODE_APP_ENABLE="${OPENCODE_APP_ENABLE:-${DEFAULT_OPENCODE_APP_ENABLE_FALLBACK}}"
  OPENCODE_APP_DIR="${OPENCODE_APP_DIR:-${DEFAULT_OPENCODE_APP_DIR_FALLBACK}}"
  OPENCODE_APP_HOST="${OPENCODE_APP_HOST:-${DEFAULT_OPENCODE_APP_HOST_FALLBACK}}"
  OPENCODE_APP_PORT="${OPENCODE_APP_PORT:-${DEFAULT_OPENCODE_APP_PORT_FALLBACK}}"
  OPENCODE_APP_POLLING="${OPENCODE_APP_POLLING:-${DEFAULT_OPENCODE_APP_POLLING_FALLBACK}}"
  OPENCODE_APP_POLLING_INTERVAL="${OPENCODE_APP_POLLING_INTERVAL:-${DEFAULT_OPENCODE_APP_POLLING_INTERVAL_FALLBACK}}"

  if [[ -n "${backend_port_override}" ]]; then
    BACKEND_PORT="${backend_port_override}"
  fi
  if [[ -n "${backend_host_override}" ]]; then
    BACKEND_HOST="${backend_host_override}"
  fi
  if [[ -n "${opencode_port_override}" ]]; then
    OPENCODE_PORT="${opencode_port_override}"
  fi
  if [[ -n "${opencode_host_override}" ]]; then
    OPENCODE_HOST="${opencode_host_override}"
  fi
  if [[ -n "${opencode_mode_override}" ]]; then
    OPENCODE_MODE="${opencode_mode_override}"
  fi
  if [[ -n "${opencode_bin_override}" ]]; then
    OPENCODE_BIN="${opencode_bin_override}"
  fi
  if [[ -n "${opencode_app_enable_override}" ]]; then
    OPENCODE_APP_ENABLE="${opencode_app_enable_override}"
  fi
  if [[ -n "${opencode_app_dir_override}" ]]; then
    OPENCODE_APP_DIR="${opencode_app_dir_override}"
  fi
  if [[ -n "${opencode_app_host_override}" ]]; then
    OPENCODE_APP_HOST="${opencode_app_host_override}"
  fi
  if [[ -n "${opencode_app_port_override}" ]]; then
    OPENCODE_APP_PORT="${opencode_app_port_override}"
  fi
  if [[ -n "${opencode_app_polling_override}" ]]; then
    OPENCODE_APP_POLLING="${opencode_app_polling_override}"
  fi
  if [[ -n "${opencode_app_polling_interval_override}" ]]; then
    OPENCODE_APP_POLLING_INTERVAL="${opencode_app_polling_interval_override}"
  fi

  OPENCODE_BIN_CMD="${OPENCODE_BIN}"
  OPENCODE_BIN_ARGS=()
  OPENCODE_WORKDIR="${ROOT_DIR}"
  if [[ -d "${OPENCODE_BIN}" ]]; then
    local opencode_pkg_dir="${OPENCODE_BIN}/packages/opencode"
    if [[ -d "${opencode_pkg_dir}" ]]; then
      OPENCODE_WORKDIR="${opencode_pkg_dir}"
    else
      OPENCODE_WORKDIR="${OPENCODE_BIN}"
    fi
    OPENCODE_BIN_CMD="bun"
    OPENCODE_BIN_ARGS=(run --conditions=browser src/index.ts)
  elif [[ ! -x "${OPENCODE_BIN}" ]] && command -v opencode >/dev/null 2>&1; then
    OPENCODE_BIN_CMD="opencode"
  fi

  OPENCODE_APP_BIN="bun"
  OPENCODE_APP_BIN_ARGS=(run dev --)
  if ! command -v bun >/dev/null 2>&1; then
    OPENCODE_APP_BIN="npm"
    OPENCODE_APP_BIN_ARGS=(run dev --)
  fi

  local services
  services="$(resolve_services "${target}")"

  case "${action}" in
    start)
      for svc in ${services}; do
        "start_${svc}"
      done
      echo "logs: ${LOG_DIR}"
      ;;
    stop)
      for svc in ${services}; do
        if [[ "${svc}" == "opencode" ]]; then
          stop_opencode
        else
          stop_service "${svc}"
        fi
      done
      ;;
    restart)
      for svc in ${services}; do
        if [[ "${svc}" == "opencode" ]]; then
          stop_opencode
        else
          stop_service "${svc}"
        fi
      done
      for svc in ${services}; do
        "start_${svc}"
      done
      echo "logs: ${LOG_DIR}"
      ;;
    status)
      for svc in ${services}; do
        if [[ "${svc}" == "opencode" ]]; then
          status_opencode
        elif [[ "${svc}" == "opencode_ui" ]]; then
          status_opencode_ui
        elif [[ "${svc}" == "backend" ]]; then
          status_backend
        elif [[ "${svc}" == "frontend" ]]; then
          status_frontend
        else
          status_service "${svc}"
        fi
      done
      ;;
    *)
      usage
      exit 1
      ;;
  esac
}

main "$@"
