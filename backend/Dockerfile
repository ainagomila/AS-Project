FROM python:3.13
COPY --from=ghcr.io/astral-sh/uv:0.12.24 /uv /uvx /bin/

ENV UV_NO_DEV=1
WORKDIR /app

# Install dependencies first so code changes don't invalidate this layer
COPY pyproject.toml uv.lock ./
RUN uv sync --locked

COPY . .

EXPOSE 8080

RUN uv run python manage.py migrate

CMD ["uv", "run", "python", "manage.py", "runserver", "0.0.0.0:8080"]
