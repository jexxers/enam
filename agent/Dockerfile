FROM python:3.12-alpine

WORKDIR /app

ENV PYTHONUNBUFFERED=1

RUN apk add --no-cache nodejs npm
RUN npm install -g @anthropic-ai/claude-code

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock /app/
RUN uv sync --frozen --no-dev --no-install-project

COPY . /app
CMD ["uv", "run", "python", "-m", "agent.main"]
