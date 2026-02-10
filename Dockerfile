# Stage 1: Build
FROM python:3.12-slim AS builder

WORKDIR /build

COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN pip install --no-cache-dir build && \
    python -m build --wheel --outdir /build/dist

# Stage 2: Runtime
FROM python:3.12-slim

LABEL maintainer="kopia-exporter"
LABEL description="Kopia Prometheus Exporter"

# Install kopia and rclone (needed for rclone-based repositories)
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl gnupg ca-certificates unzip && \
    curl -s https://kopia.io/signing-key | gpg --dearmor -o /usr/share/keyrings/kopia-keyring.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/kopia-keyring.gpg] http://packages.kopia.io/apt/ stable main" > /etc/apt/sources.list.d/kopia.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends kopia && \
    curl -fsSL https://rclone.org/install.sh | bash && \
    apt-get purge -y curl gnupg unzip && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

# Install the exporter wheel from the build stage
COPY --from=builder /build/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && \
    rm -f /tmp/*.whl

# Default metrics port
EXPOSE 9884

ENTRYPOINT ["kopia-exporter"]
CMD ["server", "--port", "9884"]
