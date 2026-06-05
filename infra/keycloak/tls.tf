# ==============================================================================
# Stage A-1: HTTPS 化用の自己署名証明書 + ACM import
#
# 目的:
#   - Keycloak `start --optimized` モード（HTTPS 強制）の挙動を検証する
#   - 本番では ACM 公開証明書 + Route 53 カスタムドメインに差し替え
#   - PoC 段階ではドメイン取得を待たずに HTTPS 経路を組み立てるため自己署名
#
# クライアント側の影響:
#   - ブラウザ: 警告画面を経由（受け入れ必要）
#   - Lambda Authorizer: NODE_TLS_REJECT_UNAUTHORIZED=0 もしくは ca_bundle 指定が必要
#   - SPA / curl: -k / rejectUnauthorized:false で接続
# ==============================================================================

# 自己署名証明書の秘密鍵
resource "tls_private_key" "self_signed" {
  algorithm = "RSA"
  rsa_bits  = 2048
}

# Public ALB と Admin ALB の DNS 名を SAN に含める自己署名証明書
# ALB DNS は apply 前に確定しないため、地域ワイルドカードを使用
resource "tls_self_signed_cert" "self_signed" {
  private_key_pem = tls_private_key.self_signed.private_key_pem

  subject {
    common_name  = "auth-poc-keycloak.poc.local"
    organization = "Auth PoC"
  }

  # AWS ELB の DNS パターンを SAN に含める（apply 前の不確定値回避のためワイルドカード）
  dns_names = [
    "auth-poc-keycloak.poc.local",
    "*.elb.amazonaws.com",
    "*.ap-northeast-1.elb.amazonaws.com",
    "localhost",
  ]

  validity_period_hours = 8760 # 1 年

  allowed_uses = [
    "key_encipherment",
    "digital_signature",
    "server_auth",
  ]
}

resource "aws_acm_certificate" "self_signed" {
  private_key      = tls_private_key.self_signed.private_key_pem
  certificate_body = tls_self_signed_cert.self_signed.cert_pem

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Name    = "${local.prefix}-self-signed"
    Purpose = "Stage A-1 HTTPS 化 PoC（本番では ACM 公開証明書に差し替え）"
  }
}
