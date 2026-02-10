#!/bin/bash
set -e

# Stop and disable the service (ignore errors if not running)
systemctl stop kopia-exporter.service 2>/dev/null || true
systemctl disable kopia-exporter.service 2>/dev/null || true
