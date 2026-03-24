#!/bin/bash
# Keycloak Realm設定をインポートする（既存Realmを上書き）
# Usage: bash import-realm.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONTAINER_NAME="keycloak-keycloak-1"
REALM_FILE="$SCRIPT_DIR/realm-export.json"

if [ ! -f "$REALM_FILE" ]; then
  echo "Error: $REALM_FILE not found"
  exit 1
fi

echo "Importing realm from: $REALM_FILE"

docker cp "$REALM_FILE" "$CONTAINER_NAME:/tmp/realm-import.json"

docker exec "$CONTAINER_NAME" \
  /opt/keycloak/bin/kc.sh import \
  --file /tmp/realm-import.json \
  --override true

echo "Import complete. Restart Keycloak to apply changes."
echo "docker compose restart keycloak"
