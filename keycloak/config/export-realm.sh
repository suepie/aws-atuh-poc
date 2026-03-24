#!/bin/bash
# Keycloak Realm設定をエクスポートしてGit管理用JSONに保存する
# Usage: bash export-realm.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONTAINER_NAME="keycloak-keycloak-1"
REALM_NAME="auth-poc"
OUTPUT_FILE="$SCRIPT_DIR/realm-export.json"

echo "Exporting realm '$REALM_NAME' from container '$CONTAINER_NAME'..."

docker exec "$CONTAINER_NAME" \
  /opt/keycloak/bin/kc.sh export \
  --dir /tmp/export \
  --realm "$REALM_NAME" \
  --users realm_file

docker cp "$CONTAINER_NAME:/tmp/export/${REALM_NAME}-realm.json" "$OUTPUT_FILE"

echo "Exported to: $OUTPUT_FILE"
echo "Review changes with: git diff $OUTPUT_FILE"
