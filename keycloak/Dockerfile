FROM quay.io/keycloak/keycloak:26.0

# Realm設定を自動インポート
COPY config/realm-export.json /opt/keycloak/data/import/

# ヘルスチェック有効化
ENV KC_HEALTH_ENABLED=true
ENV KC_METRICS_ENABLED=true

ENTRYPOINT ["/opt/keycloak/bin/kc.sh"]
