FROM python:3.12-slim

WORKDIR /app

# Copy Python project files
COPY pyproject.toml ./
COPY server/ ./server/
COPY README.md ./
COPY web/ ./web/
COPY assets/ ./assets/

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && apt-get install -y nodejs npm \
    && rm -rf /var/lib/apt/lists/* \
    && pip install uv

RUN cd /app/server  \
    && pip install -r /app/server/requirements.txt \
    && cd /app/web/ \
    && npm install

COPY run_in_docker.sh ./

# Expose ports
EXPOSE 5173 8022


CMD ["/bin/bash", "run_in_docker.sh"]