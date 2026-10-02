FROM us-central1-docker.pkg.dev/delivery-g-obi/connectors-rl-gym/connectors-harness@sha256:b1374cd8a392ea66f9a649e700a1498e8fcb03ee35776362db7cc15dc3049b89

# Own venv so these pins can't shift a version out from under the gym servers,
# which run on this image's system python3.
RUN python3 -m venv /opt/proxy-venv && \
    /opt/proxy-venv/bin/pip install --no-cache-dir \
        pytest \
        mcp==1.26.0 \
        httpx==0.28.1 \
        "uvicorn[standard]==0.41.0" \
        starlette==0.52.1 \
        litellm==1.82.0

WORKDIR /app

# Build context is environment/ (some remote builders upload only that), so
# these come from the _app/ mirror - keep in sync via sync_app_mirror.sh.
COPY _app/task.toml _app/instruction.md /app/
COPY _app/tests/ /app/tests/

COPY mcp/proxy/ /opt/proxy/

# HARBOR-LOCAL: gate the trusted /raw/{gym}/state and /raw/{gym}/step passthroughs
# (used by the verifier for SQL-backed checks) behind a build-time secret the
# agent (rlgymagent) cannot read, so it cannot reach them directly over the same
# localhost:7000 it is given for the sanctioned MCP interface.
# Fixed (not build-time-random) because the ORACLE replay (solution/solve.py)
# needs the identical value via [solution.env] in task.toml - see solve.py's own
# comment for why an env var, not this file, is what it reads: the oracle replay
# runs as the same non-root rlgymagent user as a real agent turn (confirmed live,
# uid 1000 either way), so file permissions cannot distinguish the two - only the
# scoped env var harbor injects specifically around the oracle exec can.
RUN python3 -c "import pathlib; pathlib.Path('/opt/proxy/internal_verifier_secret.txt').write_text('7b1c9f0a4e6d2c8b5a3f1e9d7c6b4a2f0e8d6c4b2a9f7e5d3c1b0a9f8e7d6c5b')" && \
    chown root:root /opt/proxy/internal_verifier_secret.txt && \
    chmod 600 /opt/proxy/internal_verifier_secret.txt

# E2B boots this image under systemd, which would start the packaged
# supervisor.service with an EMPTY environment and lose GYM_DATASET. Removing
# the unit hands supervisord back to entrypoint.sh. Inert under Docker/Modal.
RUN rm -f /etc/systemd/system/multi-user.target.wants/supervisor.service

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# /app root-only so the agent reaches gym state through MCP, not off disk.
RUN id rlgymagent >/dev/null 2>&1 || useradd --create-home --shell /bin/bash rlgymagent; \
    chmod -R go-rwx /app; \
    mkdir -p /workspace && chown rlgymagent:rlgymagent /workspace

ENV TASK_DIR=/app
ENV HARBOR_MCP_MODE=docker
ENV PROXY_HOST=0.0.0.0
ENV PROXY_PORT=7000
ENV SNAPSHOT_DIR=/logs/verifier/snapshots
ENV PROXY_PYTHON=/opt/proxy-venv/bin/python3
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV GYM_DATASET=synthetic
# LOCAL FIX (judge_context_truncation): the default per-call trace-evidence clip
# (_TRACE_RESULT_MAX_CHARS=4000 in tests/verifier_engine.py) truncates this
# task's single-window search_calendar result (~15.5k chars for the real
# 9-event 2026-05-19..05-26 window) down to ~25% before a trace rubric_check
# ever sees it, silently dropping most events' organizer/eventType/status
# fields the rubric is graded on. Raised to comfortably clear that payload
# with margin for a real agent making extra exploratory calls.
ENV RUBRIC_TRACE_RESULT_CHARS=25000

WORKDIR /workspace

USER root
CMD ["sleep", "infinity"]
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
