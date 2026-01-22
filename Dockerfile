FROM python:3.13-slim

LABEL org.opencontainers.image.source="https://github.com/adamtheturtle/doccmd"
LABEL org.opencontainers.image.description="Run commands against code blocks in documentation"
LABEL org.opencontainers.image.licenses="MIT"

ARG DOCCMD_VERSION

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install the package from PyPI with pinned version
RUN uv pip install --system --no-cache "doccmd==${DOCCMD_VERSION}"

ENTRYPOINT ["doccmd"]
