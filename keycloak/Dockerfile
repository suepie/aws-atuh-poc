# ==============================================================================
# Keycloak 26.2 multi-stage build
# Stage A-1: start --optimized 化（ADR-008 上書き）
# Stage A-3: Token Exchange v2 (RFC 8693) feature flag 有効化
#
# 旧構成: start-dev + --import-realm（HTTP 許可、起動毎に build フェーズが走る）
# 新構成: kc.sh build (DB / features を image に焼き付け) → start --optimized
#         初回起動が高速化、本番想定の HTTPS + proxy-headers 構成。
# ==============================================================================

# ----- Build stage: kc.sh build で機能フラグを焼き付け -----
FROM quay.io/keycloak/keycloak:26.2 AS builder

# ビルド時に有効化する機能（v26.2 系の名称）
# - token-exchange: legacy v1 (Deprecated 扱いだが互換性のため保持)
# - token-exchange-standard: RFC 8693 standard v2 GA (Stage A-3 検証対象)
# - admin-fine-grained-authz: Realm/Client 単位の管理権限委譲
# - dpop: 将来検証用（DPoP RFC 9449、現時点は読み込みのみ）
ENV KC_DB=postgres
ENV KC_HEALTH_ENABLED=true
ENV KC_METRICS_ENABLED=true
ENV KC_FEATURES=token-exchange,token-exchange-standard,admin-fine-grained-authz

# 本ビルドで Quarkus の augmentation が走り、起動時の build フェーズが不要になる
RUN /opt/keycloak/bin/kc.sh build

# ----- Runtime stage: build 成果物 + realm import を配置 -----
FROM quay.io/keycloak/keycloak:26.2

COPY --from=builder /opt/keycloak/ /opt/keycloak/
COPY config/realm-export.json /opt/keycloak/data/import/

# 自己署名証明書を使わずに ALB の TLS 終端を信頼する構成のため、
# ECS 側は HTTP のままで動作（KC_PROXY_HEADERS=xforwarded で X-Forwarded-* を読む）。
# 本番でカスタムドメイン化したら KC_HOSTNAME を https://auth.<domain> に固定する。

ENTRYPOINT ["/opt/keycloak/bin/kc.sh"]
