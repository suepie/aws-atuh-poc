#!/bin/bash
# Keycloak起動前にmaster realmのSSL設定をNONEに変更する
# PoCではALBがHTTPのため必要。本番ではHTTPS + ACM証明書を使用し、このスクリプトは不要。

set -e

# DB接続情報が環境変数にあればSQLでSSL設定を更新
if [ -n "$KC_DB_URL" ] && [ -n "$KC_DB_USERNAME" ] && [ -n "$KC_DB_PASSWORD" ]; then
  # JDBC URLからホスト・ポート・DB名を抽出
  DB_HOST=$(echo "$KC_DB_URL" | sed -E 's|jdbc:postgresql://([^:/]+).*|\1|')
  DB_PORT=$(echo "$KC_DB_URL" | sed -E 's|jdbc:postgresql://[^:]+:([0-9]+)/.*|\1|')
  DB_NAME=$(echo "$KC_DB_URL" | sed -E 's|jdbc:postgresql://[^/]+/([^?]+).*|\1|')

  # psqlが使えない場合はスキップ（初回起動時はテーブルがまだない）
  if command -v psql &> /dev/null; then
    echo "Updating SSL required to NONE for all realms..."
    PGPASSWORD="$KC_DB_PASSWORD" psql -h "$DB_HOST" -p "${DB_PORT:-5432}" -U "$KC_DB_USERNAME" -d "$DB_NAME" \
      -c "UPDATE realm SET ssl_required='NONE' WHERE ssl_required != 'NONE';" 2>/dev/null || \
      echo "Note: Could not update realm SSL (table may not exist yet on first run)"
  else
    echo "psql not available, skipping SSL update"
  fi
fi

# Keycloak起動
exec /opt/keycloak/bin/kc.sh "$@"
