#!/usr/bin/env bash
set -euo pipefail

# Clean prior reports
rm -f output/*.md

# Stage all sample inputs
mkdir -p drop-zone output
cp -R sample-data/. drop-zone/

# Run the agent once (expects api-server available via compose network)
docker compose run --rm agent


# messy report has an empty description, should we be compensating for that?