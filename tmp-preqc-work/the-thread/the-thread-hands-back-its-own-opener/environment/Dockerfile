FROM us-central1-docker.pkg.dev/delivery-g-obi/connectors-rl-gym/connectors-harness@sha256:1cb77ee036676d6789a086919dfa3d1023df4f4b718d2f8fd443663ee2d87db4

# No corpus patching here on purpose: this image already ships the client's full
# synthetic slack delivery and the gyms resolve it with GYM_DATASET=synthetic.
# Gold was computed against that same snapshot, so any repair step here would be
# an oracle-side data fix and would hide a real defect.

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

# E2B boots this image under systemd, which would start the packaged
# supervisor.service with an EMPTY environment - GYM_DATASET would never reach
# the gyms and they would fall back to a corpus this image does not ship.
# Removing the unit hands supervisord back to entrypoint.sh, which inherits the
# image ENV. Docker never runs systemd, so this line is inert there.
RUN rm -f /etc/systemd/system/multi-user.target.wants/supervisor.service

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# /app root-only so the agent reaches gym state through MCP, not off disk.
RUN id rlgymagent >/dev/null 2>&1 || useradd --create-home --shell /bin/bash rlgymagent; \
    chmod -R go-rwx /app; \
    mkdir -p /workspace && chown rlgymagent:rlgymagent /workspace

# One ENV per line: E2B's parser keeps continuation whitespace inside the value.
ENV TASK_DIR=/app
ENV HARBOR_MCP_MODE=docker
ENV GYM_DATASET=synthetic
ENV PROXY_HOST=0.0.0.0
ENV PROXY_PORT=7000
ENV SNAPSHOT_DIR=/logs/verifier/snapshots
ENV PROXY_PYTHON=/opt/proxy-venv/bin/python3
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /workspace

USER root
CMD ["sleep", "infinity"]
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
