#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status
set -o errexit

# Force single-threaded C++ compilation for dlib to stay within 512MB RAM
export CMAKE_BUILD_PARALLEL_LEVEL=1
export MAKEFLAGS="-j1"

echo "==> Upgrading pip and build tools..."
pip install --upgrade pip setuptools wheel

if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
elif [ -f "backend/requirements.txt" ]; then
    pip install -r backend/requirements.txt
fi

echo "==> Build complete!"
