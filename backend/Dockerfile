FROM python:3.13
COPY --from=ghcr.io/astral-sh/uv:0.12.24 /uv /uvx /bin/

ENV UV_NO_DEV=1
# Run as an unprivileged user. It owns only /app (the start command may create
# .env.d/oidc.key there) and the virtualenv; the code is read-only to it.
# UID should match the owner of the bind-mounted backend/.certs (the start scripts pass it).
ARG UID=1000
RUN useradd --create-home --uid "$UID" kofre
WORKDIR /app
RUN chown kofre:kofre /app
USER kofre

# Install dependencies first so code changes don't invalidate this layer
COPY pyproject.toml uv.lock ./
RUN uv sync --locked

COPY . .

EXPOSE 8080


CMD ["sh", "-c", "mkdir -p .env.d && { [ -f .env.d/oidc.key ] || { openssl genrsa -out .env.d/oidc.key 2048 && chmod 600 .env.d/oidc.key; }; } && uv run python manage.py migrate && uv run python manage.py create_oauth_client && uv run python manage.py runserver_https 0.0.0.0:8080"]
