# kopia-exporter

Kopia Exporter for Prometheus

## Description

kopia-exporter is a tool that exports metrics from Kopia backups to Prometheus. It can run in server mode to continuously update metrics or in snapshot mode to create backups and push metrics to a Prometheus Pushgateway.

## Installation

### Option 1: Docker (Recommended)

The easiest way to run kopia-exporter is with Docker. Pre-built images are available on GitHub Container Registry.

1. Create a `docker-compose.yml` (or clone the repository for the included one):
   ```
   git clone https://github.com/miloszarsky/kopia-exporter.git
   cd kopia-exporter
   ```

2. Start with Docker Compose:
   ```
   docker compose up -d
   ```

This will pull the image from `ghcr.io/miloszarsky/kopia-exporter`, mount your host's kopia config from `~/.config/kopia`, and expose metrics on port `9884`.

You can also pull the image directly:
```
docker pull ghcr.io/miloszarsky/kopia-exporter:latest
```

#### Custom kopia config location

If your kopia config is in a non-default location:
```
KOPIA_CONFIG_DIR=/root/.config/kopia docker compose up -d
```

#### Passing the config file explicitly to the exporter

Override the default command in `docker-compose.yml`:
```yaml
command: ["server", "--port", "9884", "--config-file", "/root/.config/kopia/repository.config", "--refresh-interval", "300"]
```

#### Local filesystem repositories

If your kopia repository is stored on a local filesystem (not S3/B2/cloud), you also need to mount the repository path. Uncomment and adjust the volume in `docker-compose.yml`:
```yaml
volumes:
  - /path/to/kopia/repo:/path/to/kopia/repo:ro
```

#### Environment variables

| Variable | Default | Description |
|---|---|---|
| `KOPIA_CONFIG_DIR` | `~/.config/kopia` | Host path to kopia config directory |
| `KOPIA_CACHE_DIR` | `~/.cache/kopia` | Host path to kopia cache directory |
| `EXPORTER_PORT` | `9884` | Port to expose metrics on |
| `REFRESH_INTERVAL` | `600` | Refresh interval in seconds |

#### Building the image manually

```
docker build -t kopia-exporter .
docker run -d --name kopia-exporter \
  -p 9884:9884 \
  -v ~/.config/kopia:/root/.config/kopia:ro \
  -v ~/.cache/kopia:/root/.cache/kopia \
  kopia-exporter
```

### Option 2: Using pipx

1. Ensure you have pipx installed on your system. If not, you can install it using pip:
   ```
   pip install pipx
   pipx ensurepath
   ```

2. Install kopia-exporter using pipx:
   ```
   pipx install git+https://github.com/alvistar/kopia-exporter.git
   ```

This method installs kopia-exporter in an isolated environment and makes it available globally.

### Option 3: Manual Installation

1. Ensure you have Python 3.7+ installed on your system.

2. Clone the repository:
   ```
   git clone https://github.com/yourusername/kopia-exporter.git
   cd kopia-exporter
   ```

3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

kopia-exporter can be used in two modes: server mode and snapshot mode.

### Server Mode

In server mode, kopia-exporter continuously updates metrics and exposes them via an HTTP server.

```
python -m kopia_exporter server [OPTIONS]
```

Options:
- `--port INTEGER`: The port to listen on (default: 9884)
- `--config-file FILE`: The Kopia config file to use
- `--refresh-interval INTEGER`: Refresh interval in seconds (default: 600)

Example:
```
python -m kopia_exporter server --port 8080 --config-file /path/to/kopia.config --refresh-interval 300
```

### Snapshot Mode

In snapshot mode, kopia-exporter creates a Kopia snapshot and pushes metrics to a Prometheus Pushgateway.

```
python -m kopia_exporter snapshot [OPTIONS] PATH
```

Options:
- `--zfs, -z TEXT`: ZFS snapshot to create
- `--override-source, -o PATH`: Override source path
- `--job TEXT`: Job name for the Pushgateway
- `--pushgateway TEXT`: Pushgateway host URL
- `--conf FILE`: Path to the YAML configuration file

Example:
```
python -m kopia_exporter snapshot /path/to/backup --zfs tank/data@snapshot1 --job kopia-backup --pushgateway http://pushgateway:9091
```

## Configuration

You can use a YAML configuration file to set default values for the Pushgateway URL and job name. Create a file named `config.yaml` with the following content:

```yaml
pushgateway: "http://pushgateway:9091"
job: "kopia-backup"
```

Then use the `--conf` option to specify the configuration file:

```
python -m kopia_exporter --conf config.yaml snapshot /path/to/backup
```

## Metrics

kopia-exporter exports[metrics.py](src%2Fkopia_exporter%2Fmetrics.py) the following metrics:

- `total_size`: Total size of the backup
- `file_count`: Number of files in the backup
- `dir_count`: Number of directories in the backup
- `error_count`: Number of errors in the backup
- `backup_duration`: Duration of the backup in seconds
- `backup_start_time`: Start time of the backup (Unix timestamp)
- `backup_end_time`: End time of the backup (Unix timestamp)

These metrics are labeled with `host`, `path`, and `user` to identify the source of the backup.

## Requirements

**Docker:**
- Docker and Docker Compose

**Native:**
- Python 3.8+
- Kopia backup tool installed and configured
- Prometheus server (for server mode)
- Prometheus Pushgateway (for snapshot mode)

## Systemd Service Installation

To run kopia-exporter as a systemd service, follow these steps:

1. Copy the systemd unit file to the systemd directory:
   ```
   sudo cp utils/kopia-exporter.service /etc/systemd/system/
   ```

2. Edit the unit file to match your configuration:
   ```
   sudo nano /etc/systemd/system/kopia-exporter.service
   ```
   Update the `ExecStart` line with the correct path to kopia-exporter and your desired options.

3. Reload the systemd daemon:
   ```
   sudo systemctl daemon-reload
   ```

4. Enable the service to start on boot:
   ```
   sudo systemctl enable kopia-exporter.service
   ```

5. Start the service:
   ```
   sudo systemctl start kopia-exporter.service
   ```

6. Check the status of the service:
   ```
   sudo systemctl status kopia-exporter.service
   ```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License.
