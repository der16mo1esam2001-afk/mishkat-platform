#!/bin/sh
set -eu
: "${MISHKAT_DB_PASSWORD:?MISHKAT_DB_PASSWORD is required}"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --set=app_password="$MISHKAT_DB_PASSWORD" --set=database_name="$POSTGRES_DB" <<'SQL'
SELECT format(
  'CREATE ROLE mishkat_app LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS',
  :'app_password'
) WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mishkat_app')
\gexec
SELECT format(
  'ALTER ROLE mishkat_app WITH LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS',
  :'app_password'
)
\gexec
GRANT CONNECT ON DATABASE :"database_name" TO mishkat_app;
SQL
