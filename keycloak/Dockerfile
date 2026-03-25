FROM quay.io/keycloak/keycloak:26.0

# Realm設定を自動インポート
COPY config/realm-export.json /opt/keycloak/data/import/

ENTRYPOINT ["/opt/keycloak/bin/kc.sh"]
