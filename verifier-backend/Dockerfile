FROM python:3.13
COPY --from=ghcr.io/astral-sh/uv:0.12.24 /uv /uvx /bin/

WORKDIR /code

COPY pyproject.toml uv.lock ./
RUN uv sync --locked

COPY . .

EXPOSE 5678

CMD ["uv", "run", "fastapi", "run", "app/main.py", "--port", "5678"]
