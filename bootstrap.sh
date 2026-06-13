#!/usr/bin/env bash
# Deep Claw bootstrap — runs once on first start, then launches the agent.
# On Replit: set your secrets in the Secrets panel before hitting Run.

set -e

echo "=== Deep Claw Bootstrap ==="

# Create data dir
mkdir -p data

# Install Python deps (idempotent — pip skips already-installed packages)
echo "Installing dependencies..."
pip install -e ".[dashboard]" --quiet

# Warn if critical secrets are missing
if [ -z "$ANTHROPIC_API_KEY" ]; then
  echo "WARNING: ANTHROPIC_API_KEY not set — Claude qualification will be disabled"
fi
if [ -z "$DERIV_API_TOKEN" ]; then
  echo "WARNING: DERIV_API_TOKEN not set — Deriv adapter runs in MOCK mode"
fi

echo "=== Starting Deep Claw ==="
python main.py VOLATILITY_75_INDEX
