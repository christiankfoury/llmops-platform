#!/bin/sh
set -eu

mkdir -p /app/node_modules /app/.next
chown -R nextjs:nodejs /app/node_modules /app/.next 2>/dev/null || true

exec su-exec nextjs "$@"
