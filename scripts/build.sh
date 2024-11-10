#!/bin/sh
# Local build

set -e

cd "$(dirname "$0")/.."

rm -rf dist
python3 setup.py sdist
