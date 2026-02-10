#!/bin/bash
set -e

INSTALL_DIR=/opt/kopia-exporter
VENV_DIR="${INSTALL_DIR}/venv"
SYMLINK=/usr/local/bin/kopia-exporter

# Create virtualenv
python3 -m venv "${VENV_DIR}"

# Install the shipped wheel
"${VENV_DIR}/bin/pip" install "${INSTALL_DIR}"/*.whl

# Create symlink
ln -sf "${VENV_DIR}/bin/kopia-exporter" "${SYMLINK}"

# Reload systemd and enable the service
systemctl daemon-reload
systemctl enable kopia-exporter.service
