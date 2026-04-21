# ALB Security Group
resource "aws_security_group" "alb" {
  name        = "${local.prefix}-alb-sg"
  description = "ALB for Keycloak"
  vpc_id      = data.aws_vpc.default.id

  # OIDC公開エンドポイント用（JWKS, authorize, token 等はパブリックアクセス必須）
  ingress {
    description = "HTTP from anywhere (OIDC public endpoints)"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Admin ALB Security Group（管理者IP限定）
resource "aws_security_group" "alb_admin" {
  name        = "${local.prefix}-alb-admin-sg"
  description = "Internal ALB for Keycloak Admin Console"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "HTTP from admin IPs only"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = distinct(concat([local.my_ip_cidr], var.allowed_cidr_blocks))
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ECS Security Group
resource "aws_security_group" "ecs" {
  name        = "${local.prefix}-ecs-sg"
  description = "ECS Fargate for Keycloak"
  vpc_id      = data.aws_vpc.default.id

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
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# RDS Security Group
resource "aws_security_group" "rds" {
  name        = "${local.prefix}-rds-sg"
  description = "RDS PostgreSQL for Keycloak"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description     = "From ECS"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs.id]
  }

  ingress {
    description = "Temporary: from my IP for DB maintenance"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [local.my_ip_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
