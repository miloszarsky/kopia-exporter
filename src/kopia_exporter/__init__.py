import json
import click
import subprocess
import logging
from typing import Dict, List
import time
import yaml
from datetime import datetime

from kopia_exporter.metrics import Metrics

# Configuring logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def refresh_data(config_file: str) -> List[Dict[str, any]]:
    command = "kopia snapshot list -n 1 --json"

    if config_file:
        command += f" --config-file {config_file}"

    logging.info(f"Running command: {command}")

    start_time = datetime.now()

    # Run the command and capture the output
    result = subprocess.run(
        command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    logging.info(f"Finished refreshing data. Duration: {duration:.2f} seconds")

    # Decode the output from bytes to string
    output = result.stdout.decode("utf-8")
    error = result.stderr.decode("utf-8")

    # Load the string as a JSON object
    try:
        json_output = json.loads(output)
        return json_output
    except json.JSONDecodeError as e:
        logging.error(f"Failed to decode JSON: {e}")
        logging.error(f"Output was: {error}")


# Example JSON data
# data = [
#     {
#         "id": "618f83d08a9938351e8d385a24aca252",
#         "source": {
#             "host": "freenas",
#             "userName": "root",
#             "path": "/mnt/fsrevolution/media/pictures",
#         },
#         "description": "",
#         "startTime": "2023-10-05T09:01:36.265095891Z",
#         "endTime": "2023-10-05T09:01:55.028680144Z",
#         "stats": {
#             "totalSize": 162291781350,
#             "excludedTotalSize": 0,
#             "fileCount": 8054,
#             "cachedFiles": 42506,
#             "nonCachedFiles": 8054,
#             "dirCount": 221,
#             "excludedFileCount": 0,
#             "excludedDirCount": 0,
#             "ignoredErrorCount": 0,
#             "errorCount": 0,
#         },
#         "rootEntry": {
#             "name": "pictures",
#             "type": "d",
#             "mode": "0775",
#             "mtime": "2023-10-05T07:01:44.583769857Z",
#             "obj": "kd4656c46f03377cbc01c2a7843f28b44",
#             "summ": {
#                 "size": 162291781350,
#                 "files": 50560,
#                 "symlinks": 0,
#                 "dirs": 221,
#                 "maxTime": "2023-10-05T07:01:18.627015144Z",
#                 "numFailed": 0,
#             },
#         },
#         "retentionReason": [
#             "latest-1",
#             "hourly-1",
#             "daily-1",
#             "weekly-1",
#             "monthly-1",
#             "annual-1",
#         ],
#     }
#     # Add other JSON objects here
# ]


def load_config(config_file: str) -> Dict:
    with open(config_file, "r") as f:
        return yaml.safe_load(f)


@click.group()
@click.option(
    "--conf", type=click.Path(exists=True), help="Path to the YAML configuration file"
)
@click.pass_context
def main(ctx, conf):
    ctx.ensure_object(dict)
    if conf:
        ctx.obj["config"] = load_config(conf)
    else:
        ctx.obj["config"] = {}


@main.command()
@click.option("--port", default=9884, help="The port to listen on.")
@click.option(
    "--config-file", default="", help="The kopia config file to use.", type=click.Path()
)
@click.option(
    "--refresh-interval", default=600, help="Refresh interval in seconds.", type=int
)
def server(port, config_file, refresh_interval):
    """Run in server mode.

    This will run th exporter in server mode and will pull data from kopia repository
    """
    # Start the HTTP server to expose metrics
    logging.info(f"Listening on port {port}")

    metrics = Metrics()
    metrics.start_http_server(port)

    while True:
        data = refresh_data(config_file)
        for entry in data:
            metrics.update_metrics(entry)

        # Sleep for the specified refresh interval before the next update
        time.sleep(refresh_interval)


@main.command()
@click.argument("path", type=click.Path())
@click.option("--zfs", "-z", help="Zfs snapshot to create.")
@click.option("--override-source", "-o", help="Override source path", type=click.Path())
@click.option("--job", help="Job name for the pushgateway")
@click.option("--pushgateway", help="Pushgateway host URL")
@click.pass_context
def snapshot(
    ctx, path: str, zfs: str, override_source: str, job: str, pushgateway: str
):
    config = ctx.obj["config"]
    job = job or config.get("job", "kopia")
    pushgateway = pushgateway or config.get("pushgateway")

    if not pushgateway:
        click.echo(
            "Pushgateway URL is required. Provide it via --pushgateway or in the config file.",
            err=True,
        )
        exit(1)
    """Create a kopia snapshot.

    This will run kopia snapshot and send metrics to prometheus pushgateway
    :return:
    """

    if zfs:
        click.echo(f"Creating zfs snapshot {zfs}...")
        command = f"zfs snapshot {zfs}"
        result = subprocess.run(command, shell=True, capture_output=True)

        if result.returncode != 0:
            click.echo(
                f"Failed to create zfs snapshot: {result.stderr.decode('utf-8')}",
                err=True,
            )
            exit(1)

    click.echo("Creating kopia snapshot...")
    command = "kopia snapshot create --json"

    if override_source:
        command += f" --override-source {override_source}"

    command += f" {path}"

    result = subprocess.run(command, shell=True, capture_output=True)

    # Decode the output from bytes to string
    output = result.stdout.decode("utf-8")
    error = result.stderr.decode("utf-8")

    if result.returncode != 0:
        click.echo(f"Failed to create snapshot: {error}", err=True)
        exit(1)

    click.echo("Finished creating kopia snapshot")

    if zfs:
        click.echo(f"Destroying zfs snapshot {zfs}...")
        command = f"zfs destroy {zfs}"
        result = subprocess.run(command, shell=True, capture_output=True)

        if result.returncode != 0:
            click.echo(
                f"Failed to destroy zfs snapshot: {result.stderr.decode('utf-8')}",
                err=True,
            )

    # Load the string as a JSON object
    try:
        json_output = json.loads(output)
    except json.JSONDecodeError as e:
        click.echo(f"Failed to decode JSON: {e}", err=True)
        click.echo(f"Output was: {error}", err=True)
        exit(1)

    metrics = Metrics(default_registry=False)
    metrics.update_and_push(json_output, pushgateway, job)

    click.echo("Pushed metrics to pushgateway")
