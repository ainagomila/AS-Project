# Scanner image: one container that holds every scanning tool.
# It is NOT the application image, so nothing here ships with the banking app.

# Versions of the two Go-based scanners. "latest" keeps vulnerability rules fresh;
# once everything works you can pin them (e.g. --build-arg TRIVY_VERSION=0.xx.x).
ARG TRIVY_VERSION=latest
ARG GITLEAKS_VERSION=latest

# Stages that only exist to borrow the official static binaries.
FROM aquasec/trivy:${TRIVY_VERSION} AS trivy
FROM ghcr.io/gitleaks/gitleaks:${GITLEAKS_VERSION} AS gitleaks

FROM python:3.12-slim

# Don't write .pyc files: the repo is mounted read-only at /src.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# git        -> gitleaks scans the commit history
# nodejs/npm -> `npm audit` for the Vue.js frontend
RUN apt-get update \
    && apt-get install -y --no-install-recommends git nodejs npm ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Each Python tool gets its own virtualenv so their dependencies can never
# conflict with each other (semgrep pins many libraries). Binaries are
# symlinked onto the PATH.
RUN for tool in pip-audit bandit semgrep uv; do \
        python -m venv "/opt/venvs/$tool" \
        && "/opt/venvs/$tool/bin/pip" install --no-cache-dir "$tool" \
        && ln -s "/opt/venvs/$tool/bin/$tool" "/usr/local/bin/$tool"; \
    done

COPY --from=trivy    /usr/local/bin/trivy /usr/local/bin/trivy
COPY --from=gitleaks /usr/bin/gitleaks    /usr/local/bin/gitleaks

# The repo is mounted here (read-only) by docker-compose.security.yml.
WORKDIR /src
CMD ["bash", "/src/scripts/vulnscan/scan.sh"]