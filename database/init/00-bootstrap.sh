#!/bin/sh
set -eu

# psql imports secrets from its environment; they are never echoed or CLI arguments.
psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  --set ON_ERROR_STOP=1 --file /opt/minishop/database/migrations/001_schema.sql
