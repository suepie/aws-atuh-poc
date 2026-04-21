# Application Load Balancer
resource "aws_lb" "keycloak" {
  name               = "${local.prefix}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = data.aws_subnets.default.ids
}

# Target Group
resource "aws_lb_target_group" "keycloak" {
  name        = "${local.prefix}-tg"
  port        = 8080
  protocol    = "HTTP"
  vpc_id      = data.aws_vpc.default.id
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

# Public ALB Listener（OIDC公開エンドポイント用）
# /realms/* 等の認証エンドポイントをパブリックに公開
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.keycloak.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.keycloak.arn
  }
}

# ==============================================================================
# Admin Console 用 Internal ALB（管理者IP限定）
# 本番では VPN / 社内NW 経由のみアクセス可能にする。
# PoC では internet-facing + SG の IP 制限で代替。
# ==============================================================================

resource "aws_lb" "keycloak_admin" {
  name               = "${local.prefix}-admin-alb"
  internal           = false # 本番では true（VPN/DirectConnect経由）
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb_admin.id]
  subnets            = data.aws_subnets.default.ids
}

resource "aws_lb_target_group" "keycloak_admin" {
  name        = "${local.prefix}-admin-tg"
  port        = 8080
  protocol    = "HTTP"
  vpc_id      = data.aws_vpc.default.id
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
    type             = "forward"
    target_group_arn = aws_lb_target_group.keycloak_admin.arn
  }
}
