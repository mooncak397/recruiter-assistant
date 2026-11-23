# Hugging Face Spaces (Docker SDK): the Space runs the container as user 1000 and routes to port 7860.
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /bin/uv
RUN useradd -m -u 1000 user
USER user
WORKDIR /home/user/app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PATH="/home/user/app/.venv/bin:$PATH"
COPY --chown=user pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY --chown=user app ./app
COPY --chown=user profile ./profile
COPY --chown=user prompts ./prompts
EXPOSE 7860
# exactly 1 worker: chat sessions live in process memory (ADR-010)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]
