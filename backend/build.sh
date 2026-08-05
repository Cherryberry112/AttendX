#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status
set -o errexit

echo "==> Upgrading pip and build tools..."
pip install --upgrade pip setuptools wheel

echo "==> Installing dependencies..."
pip install -r requirements.txt

echo "==> Build complete!"
