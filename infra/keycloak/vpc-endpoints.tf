# ==============================================================================
# VPC Endpoints
# ECS Task が VPC 外に出ずに AWS サービスへアクセスするための出口。
# NAT Gateway ($32+/月) の代わりに Interface Endpoint (3 個) + Gateway Endpoint (S3)
# でコスト削減しつつプライベート化する。
# ==============================================================================

# VPC Endpoint 用 SG（ECS から :443 許可）
resource "aws_security_group" "vpc_endpoints" {
  name        = "${local.prefix}-vpce-sg"
  description = "VPC Endpoints for Keycloak (ECR / Logs)"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "HTTPS from ECS"
    from_port       = 443
    to_port         = 443
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

# ECR API Endpoint（docker pull の認証・メタデータ）
resource "aws_vpc_endpoint" "ecr_api" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.ecr.api"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true

  tags = {
    Name = "${local.prefix}-vpce-ecr-api"
  }
}

# ECR DKR Endpoint（docker pull の image レイヤー取得）
resource "aws_vpc_endpoint" "ecr_dkr" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.ecr.dkr"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true

  tags = {
    Name = "${local.prefix}-vpce-ecr-dkr"
  }
}

# S3 Gateway Endpoint（ECR image レイヤーの実体は S3 上にあるため必須）
# Gateway Endpoint は無料。
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.private.id]

  tags = {
    Name = "${local.prefix}-vpce-s3"
  }
}

# CloudWatch Logs Endpoint（ECS タスクログ出力用）
resource "aws_vpc_endpoint" "logs" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.logs"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true

  tags = {
    Name = "${local.prefix}-vpce-logs"
  }
}
