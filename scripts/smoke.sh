#!/usr/bin/env sh
set -eu

curl -fsS http://localhost:8000/health/live
curl -fsS http://localhost:8000/health/ready
