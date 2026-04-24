# ==============================================================================
# VPC Interface Endpoint for Cognito IDP
#
# VPC Lambda Authorizer が Cognito JWKS を VPC 内経路で取得するための Endpoint。
# Private DNS を有効化することで、cognito-idp.ap-northeast-1.amazonaws.com が
# VPC 内 Private IP に解決される。
# これにより NAT Gateway 不要で Cognito アクセスが可能になる。
# ==============================================================================

# VPC Endpoint SG（VPC Lambda SG からの :443 を許可）
# vpc-endpoints.tf の SG は ECS 用なので、ここでは Lambda 用に別 SG を用意する
resource "aws_security_group" "vpc_endpoint_cognito" {
  name        = "${local.prefix}-vpce-cognito-sg"
  description = "VPC Endpoint for Cognito IDP (accessed from VPC Lambda)"
  vpc_id      = aws_vpc.main.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group_rule" "vpce_cognito_from_vpc_lambda" {
  type                     = "ingress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.vpc_lambda.id
  security_group_id        = aws_security_group.vpc_endpoint_cognito.id
  description              = "HTTPS from VPC Lambda SG"
}

# Cognito IDP Interface Endpoint
resource "aws_vpc_endpoint" "cognito_idp" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.${var.aws_region}.cognito-idp"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = aws_subnet.private[*].id
  security_group_ids  = [aws_security_group.vpc_endpoint_cognito.id]
  private_dns_enabled = true

  tags = {
    Name = "${local.prefix}-vpce-cognito-idp"
  }
}
