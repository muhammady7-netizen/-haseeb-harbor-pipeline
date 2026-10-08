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
# behind a build-time secret the agent cannot read.
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
ENV RUBRIC_TRACE_RESULT_CHARS=25000

WORKDIR /workspace

USER root
CMD ["sleep", "infinity"]
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
