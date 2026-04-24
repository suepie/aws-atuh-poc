# ==============================================================================
# VPC Lambda Authorizer (本番想定 PoC 検証用)
#
# 既存の Lambda Authorizer (infra/) と同じコード (lambda/authorizer/package.zip)
# を使用し、VPC 内配置に切り替えたバージョン。
#
# 狙い:
# - Private Subnet 配置で、NAT Gateway を使わず Internal ALB 経由で Keycloak JWKS を取得
# - VPC Endpoint (cognito-idp) 経由で Cognito JWKS を取得
# - API Gateway の /v2/* エンドポイントから呼ばれる（infra/api-vpc-test.tf）
#
# 実行時の動作差:
# - 既存 Lambda: 環境変数 KEYCLOAK_INTERNAL_JWKS_URL 未設定 → OIDC Discovery で Public ALB から JWKS 取得
# - VPC Lambda: 環境変数 KEYCLOAK_INTERNAL_JWKS_URL 設定 → Internal ALB から JWKS 取得
# - コードは全く同じ（lambda/authorizer/index.py）
# ==============================================================================

# VPC Lambda 用 SG (Egress のみ、全許可)
resource "aws_security_group" "vpc_lambda" {
  name        = "${local.prefix}-vpc-lambda-sg"
  description = "VPC Lambda Authorizer for Keycloak JWKS via Internal ALB"
  vpc_id      = aws_vpc.main.id

  egress {
    description = "All outbound (to Internal ALB / VPC Endpoints)"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Lambda IAM Role
resource "aws_iam_role" "vpc_lambda" {
  name = "${local.prefix}-vpc-authorizer-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "vpc_lambda_basic" {
  role       = aws_iam_role.vpc_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "vpc_lambda_vpc_access" {
  role       = aws_iam_role.vpc_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "vpc_authorizer" {
  name              = "/aws/lambda/${local.prefix}-vpc-authorizer"
  retention_in_days = 7
}

# Lambda Function (VPC config 付き)
# 既存 Authorizer と同じ package.zip を使用
resource "aws_lambda_function" "vpc_authorizer" {
  function_name = "${local.prefix}-vpc-authorizer"
  role          = aws_iam_role.vpc_lambda.arn
  handler       = "index.handler"
  runtime       = "python3.11"
  timeout       = 30
  memory_size   = 256

  filename         = "${path.module}/../../lambda/authorizer/package.zip"
  source_code_hash = filebase64sha256("${path.module}/../../lambda/authorizer/package.zip")

  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.vpc_lambda.id]
  }

  environment {
    variables = {
      # Keycloak Issuer は Public ALB の URL (JWT の iss クレームと一致させる)
      KEYCLOAK_ISSUER    = "http://${aws_lb.keycloak.dns_name}/realms/auth-poc"
      KEYCLOAK_CLIENT_ID = "auth-poc-spa"

      # VPC Lambda 専用: JWKS 取得先を Internal ALB に差し替える
      # (JWT の iss は Public ALB URL のまま、JWKS のみ Internal ALB から取得)
      KEYCLOAK_INTERNAL_JWKS_URL = "http://${aws_lb.keycloak_internal.dns_name}/realms/auth-poc/protocol/openid-connect/certs"

      # Cognito 設定 (API Gateway 側の既存 Authorizer と同じ値を使う)
      # VPC Endpoint (cognito-idp) 経由で取得される
      COGNITO_USER_POOL_ID       = var.central_cognito_user_pool_id
      COGNITO_REGION             = var.aws_region
      COGNITO_CLIENT_ID          = var.central_cognito_client_id
      LOCAL_COGNITO_USER_POOL_ID = var.local_cognito_user_pool_id
      LOCAL_COGNITO_CLIENT_ID    = var.local_cognito_client_id
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.vpc_lambda_basic,
    aws_iam_role_policy_attachment.vpc_lambda_vpc_access,
    aws_cloudwatch_log_group.vpc_authorizer,
  ]

  tags = {
    Role = "vpc-authorizer"
  }
}
