#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status
set -o errexit

# Force single-threaded C++ compilation for dlib to stay within 512MB RAM
export CMAKE_BUILD_PARALLEL_LEVEL=1
export MAKEFLAGS="-j1"

echo "==> Upgrading pip and build tools..."
pip install --upgrade pip setuptools wheel

echo "==> Installing dependencies with single-threaded C++ build limit..."
pip install -r requirements.txt

echo "==> Build complete!"
