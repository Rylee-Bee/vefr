FROM python:3.12-slim
WORKDIR /app
ENV VEFR_HOME=/app \
    VEFR_VAULT=/app/data/vault.json \
    VEFR_JOURNAL=/app/data/journal.json

# git is needed by `ratatoskr volumes export` to init a host-style
# repo. alpine-style `apk add` would be smaller; on debian-slim
# it's `apt-get install -y --no-install-recommends git` + cleanup.
# We layer the install before the source COPYs so the git layer
# caches independently of the source code.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Engine-owned templates ship INSIDE the image at /app/worlds-template/.
# At runtime, the deploy host bind-mounts a read-only Docker volume
# (vefr-template) on top of this path, so a `ferry deploy` can update
# the templates without rebuilding the image. The image's copy is
# the offline boot fallback: if the volume is empty (first run, after
# a `volume rm`), the engine still has lore/ and sample-world/ to load
# from. Author-imported packs (whatever `ferry fetch --pack <name>`
# lands) live at /app/worlds/ on a separate read-write volume.
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir .
COPY web ./web
COPY worlds ./worlds-template

# The three runtime data roots. Declared as VOLUME so any Docker
# tooling (docker run -v, Compose, the quadlet's Volume=) knows
# they're meant to be mount points. The image is still bootable
# without any of them mounted - the loader falls back to the
# baked-in template at /app/worlds-template/ and an empty /app/data/.
RUN mkdir -p /app/worlds /app/data
VOLUME ["/app/worlds-template", "/app/worlds", "/app/data"]

# Run as non-root. The engine only writes to /app/data/ and
# /app/worlds/ (both volumes); no root privileges are needed.
RUN useradd --system --no-create-home --shell /usr/sbin/nologin vefr \
    && chown -R vefr:vefr /app/data /app/worlds
USER vefr

# Stamp the build with the engine source SHA so `ratatoskr ferry deploy`
# can skip a no-op `podman build` when the remote image already matches
# the checkout HEAD. Falls back to a build-time `git rev-parse`; if the
# repo metadata is missing (a packaged tarball, an export that stripped
# .git) the label is the literal string "unknown".
ARG ENGINE_SHA=unknown
LABEL vefr.engine_sha=${ENGINE_SHA}

CMD ["uvicorn", "vefr.main:app", "--host", "0.0.0.0", "--port", "8820"]
