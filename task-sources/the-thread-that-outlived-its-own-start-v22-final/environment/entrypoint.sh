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

# Real, confirmed-live finding (see consistency/shortcut_audit.md): the proxy's
# own /raw/{name}/state route accepts an arbitrary `verify_queries` SQL string
# with no authentication, on the SAME localhost:7000 the agent's own MCP client
# uses -- an agent could compute every gold value directly against the gym's
# backing database without ever calling a sanctioned tool. /raw/{name}/step
# forwarded a tool_name straight upstream with no allowlist check at all,
# unlike the normal MCP call path.
#
# Fix: raw_step now enforces the same allowed_tools check the normal MCP path
# already does (see task.toml's allowed_tools list), which does not affect
# solve.py's oracle replay since the golden trajectory only ever names real
# allowlisted tools. raw_state is gated behind a per-boot secret written here,
# under /app -- already chmod go-rwx for exactly this reason -- so the verifier
# (which runs with access to /app, same as the tests/ and solution/ it already
# reads) can read it directly off disk, while the agent (rlgymagent, no access
# under /app) cannot read, forge or discover it. Neither solve.py nor any real
# agent tool call ever needs /raw/{name}/state, so this cannot break legitimate
# grading.
RAW_STATE_SECRET="$(head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n')"
echo -n "$RAW_STATE_SECRET" > /app/.raw_state_secret
chmod 600 /app/.raw_state_secret
export RAW_STATE_SECRET

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
