# Application Load Balancer（Public Subnet 配置）
resource "aws_lb" "keycloak" {
  name               = "${local.prefix}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id
}

# Target Group
resource "aws_lb_target_group" "keycloak" {
  name        = "${local.prefix}-tg"
  port        = 8080
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 5
    timeout             = 10
    interval            = 30
    path                = "/realms/master"
    matcher             = "200"
  }

  deregistration_delay = 30
}

# Public ALB Listener (HTTP:80)
# Stage A-1 以降は 80 → 443 へ permanent redirect。HTTPS Listener が正規の入口。
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.keycloak.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "redirect"
    redirect {
      protocol    = "HTTPS"
      port        = "443"
      status_code = "HTTP_301"
    }
  }
}

# Stage A-1: Public ALB HTTPS Listener (443)
# 自己署名証明書（tls.tf）で TLS 終端、バックエンドは HTTP:8080 のまま
resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.keycloak.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate.self_signed.arn

  default_action {
    type = "fixed-response"
    fixed_response {
      content_type = "text/plain"
      message_body = "Forbidden"
      status_code  = "403"
    }
  }
}

# Stage A-1 以降、Listener Rules は HTTPS Listener (443) に紐づける。
# HTTP:80 は redirect default のみ（Rules 不要）。

# Rule 1: JWKS / OIDC Discovery エンドポイントは全IP許可（Lambda 等の Resource Server 用）
resource "aws_lb_listener_rule" "public_oidc_endpoints" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 100

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.keycloak.arn
  }

  condition {
    path_pattern {
      values = [
        "/realms/*/.well-known/*",
        "/realms/*/protocol/openid-connect/certs",
      ]
    }
  }
}

# Rule 2: ログイン画面 / token endpoint 等は IP制限（ブラウザユーザーの IP のみ）
resource "aws_lb_listener_rule" "browser_endpoints_ip_restricted" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 200

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.keycloak.arn
  }

  condition {
    source_ip {
      values = distinct(concat([local.my_ip_cidr], var.allowed_cidr_blocks))
    }
  }
}

# ==============================================================================
# Admin Console 用 Internal ALB（管理者IP限定）
# 本番では VPN / 社内NW 経由のみアクセス可能にする。
# PoC では internet-facing + SG の IP 制限で代替。
# ==============================================================================

resource "aws_lb" "keycloak_admin" {
  name               = "${local.prefix}-admin-alb"
  internal           = false # 本番では true（VPN/DirectConnect経由）に変更する（N2）
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb_admin.id]
  subnets            = aws_subnet.public[*].id
}

resource "aws_lb_target_group" "keycloak_admin" {
  name        = "${local.prefix}-admin-tg"
  port        = 8080
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 5
    timeout             = 10
    interval            = 30
    path                = "/realms/master"
    matcher             = "200"
  }

  deregistration_delay = 30
}

resource "aws_lb_listener" "admin_http" {
  load_balancer_arn = aws_lb.keycloak_admin.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "redirect"
    redirect {
      protocol    = "HTTPS"
      port        = "443"
      status_code = "HTTP_301"
    }
  }
}

# Stage A-1: Admin ALB HTTPS Listener (443)
resource "aws_lb_listener" "admin_https" {
  load_balancer_arn = aws_lb.keycloak_admin.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate.self_signed.arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.keycloak_admin.arn
  }
}
