#!/bin/bash
set -e

INSTALL_DIR=/opt/kopia-exporter
SYMLINK=/usr/local/bin/kopia-exporter

case "$1" in
    remove|purge)
        # Remove virtualenv and wheel directory
        rm -rf "${INSTALL_DIR}"

        # Remove symlink
        rm -f "${SYMLINK}"

        # Reload systemd
        systemctl daemon-reload
        ;;
esac
