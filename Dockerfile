# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base

COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH=/opt/venv/bin:$PATH

WORKDIR /app

# Ambiente de desenvolvimento: o código entra por bind mount e o venv fica num volume,
# para que `uv run` mantenha as dependências em dia com o uv.lock sem reconstruir a imagem.
FROM base AS dev

ARG UID=1000
ARG GID=1000
RUN groupadd --gid "$GID" dev \
    && useradd --uid "$UID" --gid "$GID" --create-home dev \
    && mkdir -p /opt/venv /home/dev/.cache/uv \
    && chown -R dev:dev /opt/venv /home/dev /app

USER dev
ENV UV_CACHE_DIR=/home/dev/.cache/uv

COPY --chown=dev:dev pyproject.toml uv.lock* ./
RUN uv sync --no-install-project
