# ==============================================================================
# Internal ALB for Resource Servers (VPC Lambda 等)
#
# VPC 内から Keycloak JWKS / token endpoint にプライベート到達するための ALB。
# Public ALB と同じ ECS Target Group を共有（単一 Keycloak クラスタ）。
#
# 本番では Route 53 Private Hosted Zone でカスタムドメインを関連付け、
# Split-horizon DNS で Public ALB と同じドメイン名を使う（keycloak-network-architecture.md §6.5）。
# PoC では自動生成 DNS 名をそのまま Lambda の環境変数で参照する。
# ==============================================================================

# Internal ALB 用 SG
# Ingress: VPC Lambda SG からのみ :80
resource "aws_security_group" "alb_internal" {
  name        = "${local.prefix}-alb-internal-sg"
  description = "Internal ALB for Keycloak backchannel (JWKS/token) from VPC Lambda"
  vpc_id      = aws_vpc.main.id

  egress {
    description = "To ECS (:8080)"
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }
}

# VPC Lambda SG → Internal ALB 用 Ingress（循環参照回避のため別リソース化）
resource "aws_security_group_rule" "alb_internal_from_vpc_lambda" {
  type                     = "ingress"
  from_port                = 80
  to_port                  = 80
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.vpc_lambda.id
  security_group_id        = aws_security_group.alb_internal.id
  description              = "HTTP from VPC Lambda SG"
}

# Internal ALB → ECS 用 Ingress（循環参照回避のため別リソース化）
# ECS SG に Internal ALB SG からの :8080 を許可
resource "aws_security_group_rule" "ecs_from_alb_internal" {
  type                     = "ingress"
  from_port                = 8080
  to_port                  = 8080
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.alb_internal.id
  security_group_id        = aws_security_group.ecs.id
  description              = "From Internal ALB"
}

# Internal ALB 本体
resource "aws_lb" "keycloak_internal" {
  name               = "${local.prefix}-internal-alb"
  internal           = true
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb_internal.id]
  subnets            = aws_subnet.private[*].id

  tags = {
    Name = "${local.prefix}-internal-alb"
    Role = "keycloak-backchannel"
  }
}

# Target Group (ECS Keycloak)
resource "aws_lb_target_group" "keycloak_internal" {
  name        = "${local.prefix}-internal-tg"
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

# Listener（PoC のため HTTP のみ。本番では HTTPS + ACM）
resource "aws_lb_listener" "internal_http" {
  load_balancer_arn = aws_lb.keycloak_internal.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.keycloak_internal.arn
  }
}
