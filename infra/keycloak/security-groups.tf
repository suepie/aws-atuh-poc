# ==============================================================================
# Security Groups
# 本番理想形: ECS は Private Subnet、Egress は VPC 内の必要ポートのみに絞る。
# ==============================================================================

# Public ALB SG
# L4 では :80 を全開し、L7 Listener Rule（alb.tf）でパスベースの IP 制限を行う。
resource "aws_security_group" "alb" {
  name        = "${local.prefix}-alb-sg"
  description = "Public ALB for Keycloak OIDC endpoints"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTP from anywhere (OIDC public endpoints, L7 rules restrict)"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "To ECS (:8080)"
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }
}

# Admin ALB SG（管理者 IP 限定）
# 本番では internal ALB にして VPN/DirectConnect 経由のアクセスに変更する想定。
resource "aws_security_group" "alb_admin" {
  name        = "${local.prefix}-alb-admin-sg"
  description = "Admin ALB for Keycloak Admin Console (IP restricted)"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTP from admin IPs only"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = distinct(concat([local.my_ip_cidr], var.allowed_cidr_blocks))
  }

  egress {
    description = "To ECS (:8080)"
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }
}

# ECS SG
# - Ingress: ALB SG 経由のみ :8080
# - Egress:  VPC Endpoint (:443) + RDS (:5432) + VPC DNS (:53) のみ
#            → インターネット直接到達を完全に排除
resource "aws_security_group" "ecs" {
  name        = "${local.prefix}-ecs-sg"
  description = "ECS Fargate for Keycloak (Private Subnet)"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "From Public ALB"
    from_port       = 8080
    to_port         = 8080
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  ingress {
    description     = "From Admin ALB"
    from_port       = 8080
    to_port         = 8080
    protocol        = "tcp"
    security_groups = [aws_security_group.alb_admin.id]
  }

  egress {
    description = "HTTPS to VPC Endpoints (ECR / CloudWatch Logs / S3)"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  egress {
    description = "PostgreSQL to RDS"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  egress {
    description = "DNS (UDP) to VPC Resolver"
    from_port   = 53
    to_port     = 53
    protocol    = "udp"
    cidr_blocks = [var.vpc_cidr]
  }

  egress {
    description = "DNS (TCP) to VPC Resolver"
    from_port   = 53
    to_port     = 53
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }
}

# S3 Gateway Endpoint 経由の S3 アクセスは、destination が S3 のパブリック IP
# のまま（ルートテーブルで VPC 内に閉じ込められる）なので、SG では
# S3 prefix list を指定する必要がある。
# ECR DKR が image layer を S3 から pull するのに必要。
resource "aws_security_group_rule" "ecs_egress_s3" {
  type              = "egress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  prefix_list_ids   = [aws_vpc_endpoint.s3.prefix_list_id]
  security_group_id = aws_security_group.ecs.id
  description       = "HTTPS to S3 via Gateway Endpoint (ECR image layers)"
}

# RDS SG
# - Ingress: ECS SG のみ
# - 過去にあったメンテ用 my_ip 許可は本番理想形のため削除。
#   一時的に DB にアクセスしたい場合は Bastion / SSM Session Manager 経由で接続する。
resource "aws_security_group" "rds" {
  name        = "${local.prefix}-rds-sg"
  description = "RDS PostgreSQL for Keycloak (Private Subnet)"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "From ECS"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
