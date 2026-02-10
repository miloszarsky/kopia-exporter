from datetime import datetime, timezone
from typing import Tuple
from prometheus_client import (
    CollectorRegistry,
    Gauge,
    REGISTRY,
    push_to_gateway,
    start_http_server,
)


def to_struct_time(ts: str) -> datetime:
    d = datetime.strptime(ts[:-4], "%Y-%m-%dT%H:%M:%S.%f")
    return d.replace(tzinfo=timezone.utc)


class Metrics:
    def __init__(self, default_registry: bool = True):
        self.registry = REGISTRY if default_registry else CollectorRegistry()
        self.total_size_gauge = Gauge(
            "total_size",
            "Total size of the backup",
            ["host", "path", "user"],
            registry=self.registry,
        )
        self.file_count_gauge = Gauge(
            "file_count",
            "Number of files in the backup",
            ["host", "path", "user"],
            registry=self.registry,
        )
        self.dir_count_gauge = Gauge(
            "dir_count",
            "Number of directories in the backup",
            ["host", "path", "user"],
            registry=self.registry,
        )
        self.error_count_gauge = Gauge(
            "error_count",
            "Number of errors in the backup",
            ["host", "path", "user"],
            registry=self.registry,
        )
        self.backup_duration_gauge = Gauge(
            "backup_duration",
            "Duration of the backup",
            ["host", "path", "user"],
            registry=self.registry,
        )
        self.backup_start_time_gauge = Gauge(
            "backup_start_time",
            "Start time of the backup",
            ["host", "path", "user"],
            registry=self.registry,
        )
        self.backup_end_time_gauge = Gauge(
            "backup_end_time",
            "End time of the backup",
            ["host", "path", "user"],
            registry=self.registry,
        )

    def start_http_server(self, port: int):
        start_http_server(port, registry=self.registry)

    def update_metrics(self, entry) -> Tuple[str, str, str]:
        # Extract data
        host = entry["source"]["host"]
        path = entry["source"]["path"]
        user = entry["source"]["userName"]

        if "stats" in entry:
            total_size = entry["stats"]["totalSize"]
            file_count = entry["stats"]["fileCount"]
            dir_count = entry["stats"]["dirCount"]
            error_count = entry["stats"]["errorCount"]
        else:
            total_size = entry["rootEntry"]["summ"]["size"]
            file_count = entry["rootEntry"]["summ"]["files"]
            dir_count = entry["rootEntry"]["summ"]["dirs"]
            error_count = entry["rootEntry"]["summ"]["numFailed"]

        # Calculate backup duration
        start_time = to_struct_time(entry["startTime"])
        end_time = to_struct_time(entry["endTime"])

        duration = (end_time - start_time).seconds

        # Update Prometheus metrics
        self.total_size_gauge.labels(host=host, path=path, user=user).set(total_size)
        self.file_count_gauge.labels(host=host, path=path, user=user).set(file_count)
        self.dir_count_gauge.labels(host=host, path=path, user=user).set(dir_count)
        self.error_count_gauge.labels(host=host, path=path, user=user).set(error_count)
        self.backup_duration_gauge.labels(host=host, path=path, user=user).set(duration)
        self.backup_start_time_gauge.labels(host=host, path=path, user=user).set(
            start_time.timestamp()
        )
        self.backup_end_time_gauge.labels(host=host, path=path, user=user).set(
            end_time.timestamp()
        )

        return host, path, user

    def push_to_gateway(
        self, gateway_url: str, job: str, host: str, path: str, user: str
    ):
        push_to_gateway(
            gateway_url,
            job=job,
            registry=self.registry,
            grouping_key={"host": host, "path": path, "user": user},
        )

    def update_and_push(self, entry, gateway_url: str, job: str):
        host, path, user = self.update_metrics(entry)
        self.push_to_gateway(gateway_url, job=job, host=host, path=path, user=user)
