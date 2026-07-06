#!/bin/sh
set -eu

APP_DIR="${APP_DIR:-/opt/tendersystems}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
BACKUP_DIR="${BACKUP_DIR:-$APP_DIR/backups/postgres}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"

mkdir -p "$BACKUP_DIR"
umask 077

timestamp="$(date +%Y%m%d-%H%M%S)"
tmp_file="$BACKUP_DIR/.postgres-$timestamp.sql.gz.tmp"
backup_file="$BACKUP_DIR/postgres-$timestamp.sql.gz"

cd "$APP_DIR"
docker compose -f "$COMPOSE_FILE" exec -T postgres \
  pg_dump -U tenderuser -d tenderdb | gzip -9 > "$tmp_file"

mv "$tmp_file" "$backup_file"
find "$BACKUP_DIR" -type f -name 'postgres-*.sql.gz' -mtime +"$RETENTION_DAYS" -delete

echo "$backup_file"
