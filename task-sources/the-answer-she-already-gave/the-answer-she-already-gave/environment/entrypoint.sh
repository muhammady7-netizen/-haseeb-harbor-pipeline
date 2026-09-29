#!/bin/sh
set -eu

mkdir -p /logs/agent
PROXY_LOG_FILE="${PROXY_LOG_FILE:-/logs/agent/harbor-mcp-proxy.log}"
SERVICES_LOG_FILE="/logs/agent/supervisord.log"
ENV_DUMP_FILE="/logs/agent/entrypoint-env.log"
PROXY_PYTHON="${PROXY_PYTHON:-python3}"

{
    echo "=== entrypoint env (filtered) ==="
    env | grep -E "HARBOR_MCP_MODE|MCP_REMOTE_URL|TASK_DIR|PROXY_" | sort
    echo "=== entrypoint args ==="
    echo "$@"
    echo "=== task.toml mcp_servers_extended (secrets redacted) ==="
    # /logs/agent is agent-readable; a leaked access_token lets the agent hit
    # a gym directly, bypassing the proxy.
    test -f "${TASK_DIR:-/app}/task.toml" && \
        sed -n '/\[\[metadata\.mcp_servers_extended\]\]/,/^$/p' \
            "${TASK_DIR:-/app}/task.toml" \
        | sed -E 's/^(access_token[[:space:]]*=[[:space:]]*).*/\1"<redacted>"/' \
        || echo '(no task.toml)'
} > "${ENV_DUMP_FILE}" 2>&1

/usr/bin/supervisord -n -c /etc/supervisor/conf.d/supervisord.conf >>"${SERVICES_LOG_FILE}" 2>&1 &
SUPERVISORD_PID=$!

"${PROXY_PYTHON}" /opt/proxy/server.py >>"${PROXY_LOG_FILE}" 2>&1 &
PROXY_PID=$!

cleanup() {
    kill -TERM "${PROXY_PID}" 2>/dev/null || true
    kill -TERM "${SUPERVISORD_PID}" 2>/dev/null || true
    wait "${PROXY_PID}" 2>/dev/null || true
    wait "${SUPERVISORD_PID}" 2>/dev/null || true
}
trap cleanup TERM INT EXIT

# Daytona passes no command and overrides CMD; without this the script ends,
# the EXIT trap fires and the container dies before the proxy binds :7000.
if [ "$#" -eq 0 ]; then
    set -- sleep infinity
fi

exec "$@"
