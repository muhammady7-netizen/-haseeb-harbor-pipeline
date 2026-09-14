# ATTRIBUTION: lifted from rl-harbor-platform/harbor-task-template/environment/mcp/proxy/server.py
# (FROZEN — do not edit; mirror upstream).
#
# HARBOR-LOCAL DIVERGENCES (intentional, narrow):
#   * Tool allowlist enforcement. Each ``mcp_servers_extended`` entry may
#     carry an ``allowed_tools`` list (configured via the Tool Config tab
#     on a HarborBatch). When present, ``list_tools()`` returns only the
#     named tools and ``call_tool()`` raises before issuing the upstream
#     /step ToolCallAction for anything outside the allowlist. Look for
#     `# HARBOR-LOCAL` markers below — every divergence is at most a
#     handful of lines, so re-syncing from upstream stays mechanical.
"""
Harbor task template — MCP proxy (FROZEN).

Presents a native MCP (streamable-http) interface to the agent, and translates
every call into the upstream OpenEnv HTTP API (POST /step, POST /reset).

Responsibilities:
  * Read task.toml at startup from $TASK_DIR (default: /app).
  * For every [[metadata.mcp_servers_extended]] entry:
      - Pick upstream URL based on $HARBOR_MCP_MODE (docker | daytona).
      - Generate a unique x-database-id per trial.
      - Read the seed .sql file and POST /reset with sql_content (never
        falling back to the server's internal default database).
      - Fetch the tool catalog via POST /step {action_type: ListToolsAction}.
  * Serve native MCP at /mcp/<server_name>.
  * Inject the configured auth header when present, plus x-database-id on every upstream call.

Fail-loud policy: any missing/invalid config or failed /reset exits non-zero,
which makes Harbor's healthcheck fail and the trial abort cleanly.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import secrets
import sys
import time
import tomllib
from pathlib import Path
from typing import Any

import httpx
import uvicorn
from mcp import types
from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

logger = logging.getLogger("harbor-mcp-proxy")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

TASK_DIR = Path(os.environ.get("TASK_DIR", "/app"))
MODE = os.environ.get("HARBOR_MCP_MODE", "docker").lower()
PROXY_HOST = os.environ.get("PROXY_HOST", "0.0.0.0")
PROXY_PORT = int(os.environ.get("PROXY_PORT", "7000"))
HTTP_TIMEOUT = float(os.environ.get("PROXY_HTTP_TIMEOUT", "180.0"))
SNAPSHOT_DIR = Path(os.environ.get("SNAPSHOT_DIR", "/logs/verifier/snapshots"))
SNAPSHOT_EXCLUDE = {"sqlite_sequence", "sqlite_stat1"}

STATE: dict[str, dict[str, Any]] = {}
READY: bool = False


def die(msg: str) -> None:
    logger.error("FATAL: %s", msg)
    sys.exit(1)


def load_task_config() -> dict[str, Any]:
    path = TASK_DIR / "task.toml"
    if not path.exists():
        die(f"task.toml not found at {path} (set TASK_DIR to override)")
    return tomllib.loads(path.read_text())


# OpenAI's chat/completions API hard-caps the ``tools`` array at 128 entries.
OPENAI_TOOL_LIMIT = 128


def _is_openai_family(model: str) -> bool:
    """True for OpenAI-routed model names (gpt-*/o1/o3/o4/openai-*). Mirrors the
    worker's ``_is_openai_model`` — DashScope's ``openai/qwen…`` normalization is
    NOT OpenAI, so it's excluded. Used only to decide whether the 128-tool cap
    applies; on anything else we never block."""
    if not model:
        return False
    m = model.lower()
    base = m.split("/", 1)[1] if "/" in m else m
    if base.startswith("qwen"):
        return False
    if m.startswith("openai/"):
        return True
    return base.startswith(("gpt-", "gpt3", "gpt4", "o1-", "o3-", "o4-")) or base in ("o1", "o3", "o4")


def _run_model_from_cfg(cfg: dict) -> str:
    """Resolve the agent's run model from a parsed task.toml.

    Prefers ``metadata.run_model`` (the actual agent model stamped at dispatch).
    Falls back to ``metadata.verifier_judge.model`` for task.toml files
    generated before run_model existed — those pre-date the configurable judge,
    when the judge model was derived from the run model, so the fallback keeps
    legacy behavior unchanged.
    """
    meta = cfg.get("metadata") or {}
    run_model = meta.get("run_model")
    if isinstance(run_model, str) and run_model.strip():
        return run_model
    return (meta.get("verifier_judge") or {}).get("model") or ""


def _is_fireworks_family(model: str) -> bool:
    """True for Fireworks-routed models (GLM, DeepSeek, Llama, Kimi, etc.).

    Harbor stores these as ``fireworks/…``; LiteLLM uses ``fireworks_ai/…``.
    Both prefixes are accepted here because the proxy reads the run model
    from task.toml before OpenHands normalization rewrites the name.
    """
    if not model:
        return False
    m = model.lower()
    return m.startswith(("fireworks/", "fireworks_ai/")) or "accounts/fireworks/models/" in m


def new_db_id() -> str:
    return f"db_{int(time.time() * 1000)}_{secrets.token_hex(4)}"


def upstream_for(entry: dict[str, Any]) -> str:
    name = entry["name"]
    if MODE == "docker":
        local_url = entry.get("local_url")
        if local_url:
            return str(local_url).rstrip("/")
        port = entry.get("container_port")
        if not port:
            die(f"server '{name}': container_port or local_url is required in docker mode")
        return f"http://127.0.0.1:{port}"
    if MODE == "daytona":
        var = entry.get("remote_url_env")
        if not var:
            die(f"server '{name}': remote_url_env missing in task.toml")
        url = os.environ.get(var)
        if not url:
            die(f"server '{name}': env var {var} is unset (daytona mode)")
        return url.rstrip("/")
    die(f"Unknown HARBOR_MCP_MODE: {MODE!r}")


async def wait_for_upstream(client: httpx.AsyncClient, name: str, upstream: str) -> None:
    """Wait for the configured gym rather than relying on fixed entrypoint ports."""
    last_error: Exception | None = None
    for attempt in range(60):
        try:
            response = await client.get(f"{upstream}/health", timeout=5.0)
            response.raise_for_status()
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt < 59:
                await asyncio.sleep(2)
    die(f"server '{name}': {upstream}/health unavailable after 60 attempts: {last_error}")


def build_headers(state: dict[str, Any]) -> dict[str, str]:
    headers: dict[str, str] = {}
    # db_id / db_id_header_name are None when reset_on_run=False — the gym
    # operates on its own built-in state and no per-run database is provisioned.
    db_id = state.get("db_id")
    db_id_header = state.get("db_id_header_name")
    if db_id and db_id_header:
        headers[db_id_header] = db_id
    if state["token"]:
        headers[state["auth_header_name"]] = state["token"]
    # Daytona preview URLs are token-gated by default — the worker passes
    # the token in via ``<remote_url_env>_TOKEN`` and we send it as
    # ``x-daytona-preview-token`` on every upstream request.
    preview_token = state.get("preview_token")
    if preview_token:
        headers["x-daytona-preview-token"] = preview_token
    return headers


async def do_reset(
    client: httpx.AsyncClient,
    upstream: str,
    headers: dict[str, str],
    sql: str | None,
    db_id: str,
) -> None:
    """Reset the upstream gym's database.

    When *sql* is None we POST ``/reset`` with an empty body so the gym falls
    back to its built-in ``get_seed_data_function()`` default (every rl-gym's
    custom_http_server.py treats ``sql_content`` as optional). When *sql* is
    a string, we try the modern ``{"sql_content": ...}`` path and fall back
    to the older reset+/api/seed-database flow for compatibility.
    """
    if sql is None:
        r = await client.post(f"{upstream}/reset", headers=headers, json={})
        r.raise_for_status()
        return

    errors: list[str] = []

    # Newer OpenEnv runtimes can seed directly through /reset.
    try:
        r = await client.post(
            f"{upstream}/reset",
            headers=headers,
            json={"sql_content": sql},
        )
        r.raise_for_status()
        body = r.json() or {}
        obs = body.get("observation") or {}
        reset_result = (obs.get("metadata") or {}).get("database_reset_result")
        if isinstance(reset_result, dict) and reset_result.get("success") is False:
            errors.append(
                "/reset sql_content reported failed seed: "
                f"{reset_result.get('message') or reset_result}"
            )
        elif obs.get("success") or body.get("success"):
            return
        errors.append(f"/reset sql_content returned no success marker: {body}")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"/reset sql_content failed: {exc}")

    # Older direct-mode gym images reset first, then seed through /api/seed-database.
    try:
        reset = await client.post(f"{upstream}/reset", headers=headers, json={})
        reset.raise_for_status()
        seed = await client.post(
            f"{upstream}/api/seed-database",
            headers=headers,
            json={"database_id": db_id, "sql_content": sql},
        )
        seed.raise_for_status()
        return
    except Exception as exc:  # noqa: BLE001
        errors.append(f"/reset + /api/seed-database failed: {exc}")

    raise RuntimeError("; ".join(errors))


async def do_step(
    client: httpx.AsyncClient,
    upstream: str,
    headers: dict[str, str],
    action: dict[str, Any],
) -> dict[str, Any]:
    r = await client.post(
        f"{upstream}/step",
        headers=headers,
        json=action,
    )
    r.raise_for_status()
    return r.json() or {}


async def do_state(
    client: httpx.AsyncClient,
    upstream: str,
    headers: dict[str, str],
    verify_queries: list[str] | None = None,
) -> dict[str, Any]:
    params = [("verify_queries", q) for q in (verify_queries or [])]
    r = await client.get(f"{upstream}/state", headers=headers, params=params)
    r.raise_for_status()
    return r.json() or {}


async def snapshot_full_db(
    client: httpx.AsyncClient, upstream: str, headers: dict[str, str]
) -> dict[str, list[dict[str, Any]]]:
    tables_resp = await do_state(
        client, upstream, headers,
        ["SELECT name FROM sqlite_master WHERE type='table'"],
    )
    tables = [
        row["name"]
        for row in (tables_resp.get("verification_results", [{}])[0].get("result") or [])
        if row.get("name") and row["name"] not in SNAPSHOT_EXCLUDE
    ]
    dump: dict[str, list[dict[str, Any]]] = {}
    for t in tables:
        resp = await do_state(
            client, upstream, headers,
            [f"SELECT * FROM {t} ORDER BY rowid"],
        )
        dump[t] = resp.get("verification_results", [{}])[0].get("result") or []
    return dump


async def bootstrap() -> None:
    global READY
    cfg = load_task_config()
    entries = (cfg.get("metadata") or {}).get("mcp_servers_extended") or []
    if not entries:
        die("task.toml: [[metadata.mcp_servers_extended]] has no entries")

    # HARBOR-LOCAL: the before-agent full-DB snapshot (snapshot_full_db) is
    # consumed ONLY by the JSON State verifier axis. When that axis is
    # disabled for the run (metadata.state_snapshot_enabled = false, plumbed
    # from the batch's allowed_verifier_types) we skip the snapshot entirely.
    # This avoids a SELECT * over every table — essential for gyms with very
    # large tables that would otherwise OOM the gym during the dump. A
    # missing key defaults to True so legacy task.toml files are unchanged.
    state_snapshot_enabled = bool(
        (cfg.get("metadata") or {}).get("state_snapshot_enabled", True)
    )
    # HARBOR-LOCAL: provider-aware schema warnings key off the agent's run
    # model. Prefer ``metadata.run_model`` (the actual agent model); fall back
    # to ``verifier_judge.model`` for task.toml files dispatched before
    # run_model was stamped. NB: after the configurable-judge change the judge
    # is no longer a reliable proxy for the run model, so run_model is required
    # to correctly detect Fireworks/GLM (or OpenAI) agent runs.
    run_model = _run_model_from_cfg(cfg)

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        for entry in entries:
            name = entry.get("name")
            token = entry.get("access_token", "")
            seed_file = entry.get("seed_file")
            auth_header_name = entry.get("auth_header_name")
            db_id_header_name = entry.get("db_id_header_name")

            # Read early so required-field validation and db_id generation
            # can both branch on it. Absent key → False so older task.toml
            # files (pre-feature) preserve the new opt-in semantics.
            reset_on_run: bool = bool(entry.get("reset_on_run", False))

            # db_id_header_name is only required when we're actually calling
            # /reset and provisioning a per-run database. When reset is
            # disabled the gym operates on its own built-in state and no
            # database-id header is sent on any request.
            # ``auth_header_name`` is only required when this gym actually
            # uses auth (a non-empty access_token). Gyms with no auth send
            # both empty — build_headers() then skips the auth header
            # entirely, so the header name is irrelevant. Requiring it only
            # when ``token`` is present keeps auth-less gyms dispatchable
            # while still catching a token-without-header misconfiguration.
            required_fields = [
                ("name", name),
                *([("auth_header_name", auth_header_name)] if token else []),
                *([("db_id_header_name", db_id_header_name)] if reset_on_run else []),
            ]
            missing = [k for k, v in required_fields if not v]
            if missing:
                die(
                    "metadata.mcp_servers_extended entry missing required "
                    f"fields {missing}: {entry!r}"
                )

            sql: str | None
            if seed_file:
                seed_path = (TASK_DIR / seed_file).resolve()
                if not seed_path.exists():
                    die(f"server '{name}': seed file not found: {seed_path}")
                sql = seed_path.read_text()
                if not sql.strip():
                    die(f"server '{name}': seed file is empty: {seed_path}")
            else:
                sql = None

            upstream = upstream_for(entry)

            # Only mint a db_id when we're resetting — no /reset means no
            # per-run database is provisioned, so there's nothing to identify.
            db_id: str | None = new_db_id() if reset_on_run else None

            preview_token: str | None = None
            if MODE == "daytona":
                token_env = entry.get("remote_url_env")
                if token_env:
                    preview_token = os.environ.get(f"{token_env}_TOKEN") or None

            # HARBOR-LOCAL: tool allowlist (None = no restriction; empty
            # set = block all; non-empty set = only those tool names).
            # Coerce here once so list_tools / call_tool stay branch-free.
            raw_allowed = entry.get("allowed_tools")
            allowed_tools: set[str] | None
            if isinstance(raw_allowed, list):
                allowed_tools = {
                    str(t) for t in raw_allowed if isinstance(t, str)
                }
            else:
                allowed_tools = None

            state = {
                "upstream": upstream,
                # None when reset_on_run=False — build_headers skips the
                # db_id header in that case.
                "db_id": db_id,
                "token": token,
                "auth_header_name": auth_header_name,
                "db_id_header_name": db_id_header_name if reset_on_run else None,
                "preview_token": preview_token,
                "tools": [],
                # HARBOR-LOCAL: optional tool-name allowlist (batch Tool Config,
                # or the OpenAI-only golden tool-name cap resolved server-side).
                # We never carry golden *arguments* here — leaking them would let
                # the agent copy the golden solution.
                "allowed_tools": allowed_tools,
            }
            headers = build_headers(state)

            logger.info(
                "server '%s' upstream=%s db_id=%s auth_hdr=%s db_hdr=%s seed=%s reset_on_run=%s",
                name, upstream, db_id or "<none>", auth_header_name,
                db_id_header_name if reset_on_run else "<none>",
                seed_file or "<gym default>", reset_on_run,
            )
            await wait_for_upstream(client, name, upstream)
            if reset_on_run:
                try:
                    await do_reset(client, upstream, headers, sql, db_id)
                except Exception as exc:
                    die(f"server '{name}': /reset failed: {exc}")
            else:
                logger.info(
                    "server '%s': /reset skipped, db_id not generated (reset_on_run=False)", name
                )

            try:
                resp = await do_step(
                    client, upstream, headers,
                    {"action_type": "ListToolsAction"},
                )
            except Exception as exc:
                die(f"server '{name}': initial ListToolsAction failed: {exc}")

            state["tools"] = (resp.get("observation") or {}).get("tools_list") or []
            logger.info("server '%s' ready with %d tool(s)", name, len(state["tools"]))
            # HARBOR-LOCAL: warn loudly when any tool carries a schema that
            # LLM providers are known to reject hard. These patterns were
            # previously silently rewritten by a sanitizer; now that the
            # sanitizer is removed the gym must supply valid schemas directly.
            # The warning appears in harbor-mcp-proxy.log and is surfaced by
            # the frontend diagnostic banner.
            _warn_schema_issues(name, state["tools"], run_model)
            # HARBOR-LOCAL: surface allowlist size at startup so a missing
            # / wrongly-named tool is obvious in the run logs (the proxy
            # otherwise silently filters it out).
            if state["allowed_tools"] is not None:
                visible = sum(
                    1
                    for t in state["tools"]
                    if t.get("name") in state["allowed_tools"]
                )
                logger.info(
                    "server '%s' tool allowlist active: %d/%d tools visible "
                    "(allowlist size=%d)",
                    name, visible, len(state["tools"]),
                    len(state["allowed_tools"]),
                )

            # Capture before-agent DB snapshot for the verifier.
            # HARBOR-LOCAL: only when the JSON State axis is enabled — see
            # state_snapshot_enabled above. Skipping leaves no *.before.json,
            # and the verifier (test_outputs.py) only dumps the after-state
            # for servers that have a before-snapshot, so the heavy SELECT *
            # is avoided on both sides when state checking is off.
            if state_snapshot_enabled:
                try:
                    before = await snapshot_full_db(client, upstream, headers)
                    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
                    (SNAPSHOT_DIR / f"{name}.before.json").write_text(
                        json.dumps(before, indent=2, default=str)
                    )
                    logger.info(
                        "server '%s' before-snapshot saved (%d tables)",
                        name, len(before),
                    )
                except Exception as exc:
                    die(f"server '{name}': before-snapshot failed: {exc}")
            else:
                logger.info(
                    "server '%s': before-snapshot skipped (JSON State verifier disabled)",
                    name,
                )

            STATE[name] = state

    # HARBOR-LOCAL: provider-aware aggregate tool-count guard. When several
    # gyms are combined, their catalogs can exceed OpenAI's 128-tool array cap,
    # and the agent then dies on its FIRST completion with an opaque
    # "Invalid 'tools': array too long" 400 — which the platform otherwise
    # records as a low-scoring "completed" run. Fail fast here with an explicit
    # message instead. Trips ONLY for OpenAI-family models AND only when the gym
    # tools ALONE already exceed the cap, so a run that could actually fit
    # (<=128) is never blocked. The run's model is read from
    # metadata.run_model (falling back to verifier_judge.model for task.toml
    # files dispatched before run_model was stamped).
    run_model = _run_model_from_cfg(cfg)
    if _is_openai_family(run_model):
        total_visible = 0
        for nm, st in STATE.items():
            allowed = st.get("allowed_tools")
            catalog = st.get("tools") or []
            total_visible += sum(
                1 for t in catalog if allowed is None or t.get("name") in allowed
            )
        logger.info(
            "aggregate tool count across %d gym(s): %d (OpenAI limit %d)",
            len(STATE), total_visible, OPENAI_TOOL_LIMIT,
        )
        if total_visible > OPENAI_TOOL_LIMIT:
            die(
                f"HARBOR TOOL-LIMIT ABORT: this run exposes {total_visible} MCP tools "
                f"across {len(STATE)} gym(s) [{', '.join(STATE)}], but model "
                f"'{run_model}' (OpenAI-family) allows at most {OPENAI_TOOL_LIMIT} "
                f"tools per request. Reduce the number of gyms on this task, switch to "
                f"a model without the 128-tool cap (e.g. Claude), or set a batch Tool "
                f"Config allowlist to trim the toolset to <= {OPENAI_TOOL_LIMIT}."
            )

    READY = True


def _extract_tool_payload(tool_result: Any) -> str:
    """OpenEnv /step responses wrap the tool payload in one of three shapes:

    * ``tool_result.content[0].text`` — MCP-standard text block (some servers).
    * ``tool_result.data``            — flat data field (Teams).
    * ``tool_result`` itself is the payload — raw JSON object/array/scalar
      (Freshdesk). Serialize it so the agent sees real content, not "".

    The agent-facing response is always a string.
    """
    if isinstance(tool_result, dict):
        content = tool_result.get("content")
        if isinstance(content, list) and content:
            first = content[0]
            if isinstance(first, dict) and first.get("type") == "text":
                text = first.get("text")
                if isinstance(text, str):
                    return text
        data = tool_result.get("data")
        if isinstance(data, str):
            return data
        if data is not None:
            return json.dumps(data, default=str)
        text = tool_result.get("text")
        if isinstance(text, str):
            return text
        # Freshdesk shape: the whole tool_result IS the payload.
        return json.dumps(tool_result, default=str)
    if isinstance(tool_result, str):
        return tool_result
    if tool_result is None:
        return ""
    return json.dumps(tool_result, default=str)


# HARBOR-LOCAL: OpenAI function-calling schema compatibility.
#
# OpenAI's tool/function API rejects a tool whose top-level parameters schema
# is not ``type: "object"`` or that uses ``oneOf``/``anyOf``/``allOf``/``enum``/
# ``not`` at the root ("Invalid schema for function 'X': schema must have type
# 'object' and not have 'oneOf'/'anyOf'/'allOf'/'enum'/'not' at the top
# level."). Anthropic accepts these, so gyms authored/validated against Claude
# (e.g. obi-email-v1's ``import_message``, which expresses "exactly one of raw
# | payload" as a root ``anyOf``) ship schemas that crash every GPT/OpenAI run
# on the agent's FIRST completion — before any assistant text or tool call is
# emitted. The trajectory then contains only the user turn, with no error
# surfaced to the platform.
#
# We normalize the ROOT schema only (the documented OpenAI restriction;
# nested combinators are accepted in non-strict function calling). Member
# subschemas of a root ``anyOf``/``oneOf``/``allOf`` have their ``properties``
# merged into a single object so the agent still sees every callable field;
# the structural XOR constraint is preserved in the tool ``description`` prose
# and enforced upstream by the gym at call time, so verifier correctness is
# unaffected.




# Keywords that LLM providers reject in tool schemas. Presence of any of
# these at any depth is a strong signal the gym's schema will cause a hard
# 400 on the very first agent completion.
_SCHEMA_PROBLEM_KEYS = frozenset({
    # Root combinators — OpenAI hard-rejects these at the root level.
    "anyOf", "oneOf", "allOf", "not",
    # Unresolved JSON-Schema refs — every provider requires inline schemas.
    "$ref",
    # OpenAPI / extended keys — Gemini 400s on these; OpenAI strict mode
    # also rejects several. Fireworks/GLM tolerates additionalProperties
    # and title (see _schema_problem_keys_for_model).
    "additionalProperties", "title", "$defs", "definitions",
    "unevaluatedProperties", "patternProperties", "dependentSchemas",
    "if", "then", "else",
})

# Keys tolerated by Fireworks-hosted models (GLM, DeepSeek, Llama, etc.).
_FIREWORKS_TOLERATED_SCHEMA_KEYS = frozenset({"additionalProperties", "title"})


def _schema_problem_keys_for_model(model: str) -> frozenset[str]:
    """Return schema keys that should trigger BAD GYM SCHEMA for this run."""
    if _is_fireworks_family(model):
        return _SCHEMA_PROBLEM_KEYS - _FIREWORKS_TOLERATED_SCHEMA_KEYS
    return _SCHEMA_PROBLEM_KEYS


def _check_node(
    node: Any, depth: int = 0, *, problem_keys: frozenset[str] | None = None,
) -> list[str]:
    """Return a list of problematic keys found anywhere in the schema node."""
    keys = problem_keys if problem_keys is not None else _SCHEMA_PROBLEM_KEYS
    if depth > 32 or not isinstance(node, dict):
        return []
    found: list[str] = []
    for k, v in node.items():
        if k in keys:
            found.append(k)
        elif isinstance(v, dict):
            found.extend(_check_node(v, depth + 1, problem_keys=keys))
        elif isinstance(v, list):
            for item in v:
                found.extend(_check_node(item, depth + 1, problem_keys=keys))
    return found


def _warn_schema_issues(
    gym_name: str, tools: list[dict[str, Any]], model: str = "",
) -> None:
    """Log a prominent warning for every tool that carries a schema LLM
    providers are known to reject, so the issue is immediately visible in
    harbor-mcp-proxy.log and the frontend diagnostic banner."""
    problem_keys = _schema_problem_keys_for_model(model)
    for tool in tools:
        tool_name = tool.get("name", "<unknown>")
        schema = tool.get("inputSchema") or {}
        problems = list(dict.fromkeys(
            _check_node(schema, problem_keys=problem_keys)
        ))  # unique, ordered
        if not problems:
            # Also warn if root is not type:object (required by all providers).
            if schema.get("type") not in ("object", None, ""):
                problems = [f"root type is {schema['type']!r} (must be object)"]
        if problems:
            logger.warning(
                "BAD GYM SCHEMA [%s/%s]: schema contains problematic "
                "keys/patterns that LLM providers reject — %s. "
                "Fix the gym's schema before sharing or the run will fail "
                "on the first completion.",
                gym_name, tool_name, ", ".join(f"'{p}'" for p in problems),
            )


def build_mcp_server(name: str) -> Server:
    state = STATE[name]
    srv = Server(name)

    @srv.list_tools()
    async def _list_tools() -> list[types.Tool]:
        # HARBOR-LOCAL: filter by allowlist when configured. None means
        # "no restriction" — preserve the upstream behavior of exposing
        # every tool the gym returned at bootstrap.
        allowed = state.get("allowed_tools")
        catalog = state["tools"]
        if allowed is not None:
            catalog = [t for t in catalog if t.get("name") in allowed]
        out: list[types.Tool] = []
        for t in catalog:
            # Expose the upstream tool verbatim. No golden-trajectory content is
            # ever appended to descriptions — that would bias/leak the answer.
            out.append(
                types.Tool(
                    name=t["name"],
                    description=t.get("description") or "",
                    inputSchema=(
                        t.get("inputSchema") or {"type": "object", "properties": {}}
                    ),
                )
            )
        return out

    @srv.call_tool()
    async def _call_tool(
        tool_name: str, arguments: dict[str, Any] | None
    ) -> list[types.TextContent]:
        # HARBOR-LOCAL: reject calls outside the allowlist before any HTTP
        # work. Raising here surfaces a clear MCP error to the agent
        # ("tool 'x' is not allowed for this batch") instead of relying
        # on a 4xx from upstream that may or may not be routed cleanly.
        allowed = state.get("allowed_tools")
        if allowed is not None and tool_name not in allowed:
            raise RuntimeError(
                f"tool {tool_name!r} is not allowed for this batch"
            )
        headers = build_headers(state)
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            # HARBOR-LOCAL: pass the agent's call straight through to upstream.
            # We never substitute or "replay" golden-trajectory arguments — if a
            # call is missing a required argument, upstream returns its normal
            # error and the agent self-corrects. Injecting golden arguments here
            # would leak the reference solution into the run.
            resp = await do_step(
                client,
                state["upstream"],
                headers,
                {
                    "action_type": "ToolCallAction",
                    "tool_name": tool_name,
                    "arguments": arguments or {},
                },
            )
        obs = resp.get("observation") or {}
        if not obs.get("success"):
            raise RuntimeError(obs.get("error_message") or "upstream /step failed")
        result = obs.get("tool_result")
        payload = _extract_tool_payload(result)
        is_error = obs.get("is_error") or (
            isinstance(result, dict) and result.get("isError")
        )
        if is_error:
            # Surface the error message (Duplicate entry …, Validation failed …)
            # so the agent can correct course.
            raise RuntimeError(payload or "tool error")
        return [types.TextContent(type="text", text=payload)]

    return srv


async def health(_request: Request) -> JSONResponse:
    if READY:
        return JSONResponse(
            {"status": "ok", "servers": list(STATE.keys())}, status_code=200
        )
    return JSONResponse({"status": "starting"}, status_code=503)


def build_app() -> Starlette:
    mcp_servers = {name: build_mcp_server(name) for name in STATE}
    session_managers: dict[str, StreamableHTTPSessionManager] = {
        name: StreamableHTTPSessionManager(
            app=srv, event_store=None, json_response=False
        )
        for name, srv in mcp_servers.items()
    }

    def asgi_for(name: str):
        sm = session_managers[name]

        async def handler(scope, receive, send):
            await sm.handle_request(scope, receive, send)

        return handler

    @contextlib.asynccontextmanager
    async def lifespan(_app):
        async with contextlib.AsyncExitStack() as stack:
            for sm in session_managers.values():
                await stack.enter_async_context(sm.run())
            yield

    # Raw OpenEnv passthrough (used by the verifier to dump after-agent state,
    # and by solve.py in oracle mode to drive /reset + /step directly). Headers
    # are injected from STATE[name], identical to native-MCP side.
    async def raw_state(request: Request) -> JSONResponse:
        name = request.path_params["name"]
        if name not in STATE:
            return JSONResponse({"error": f"unknown server {name}"}, status_code=404)
        s = STATE[name]
        qs = [v for k, v in request.query_params.multi_items() if k == "verify_queries"]
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            data = await do_state(client, s["upstream"], build_headers(s), qs)
        return JSONResponse(data)

    async def raw_step(request: Request) -> JSONResponse:
        name = request.path_params["name"]
        if name not in STATE:
            return JSONResponse({"error": f"unknown server {name}"}, status_code=404)
        s = STATE[name]
        body = await request.json()
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            data = await do_step(client, s["upstream"], build_headers(s), body)
        return JSONResponse(data)

    routes: list = [
        Route("/health", health, methods=["GET"]),
        Route("/raw/{name}/state", raw_state, methods=["GET"]),
        Route("/raw/{name}/step", raw_step, methods=["POST"]),
    ]
    for name in STATE:
        routes.append(Mount(f"/mcp/{name}", app=asgi_for(name)))

    return Starlette(routes=routes, lifespan=lifespan)


def main() -> None:
    try:
        asyncio.run(bootstrap())
    except SystemExit:
        raise
    except Exception as exc:
        die(f"bootstrap failed: {exc}")

    app = build_app()
    logger.info(
        "proxy listening on %s:%d — routes: %s",
        PROXY_HOST, PROXY_PORT, ["/health"] + [f"/mcp/{n}" for n in STATE],
    )
    uvicorn.run(app, host=PROXY_HOST, port=PROXY_PORT, log_level="info")


if __name__ == "__main__":
    main()
