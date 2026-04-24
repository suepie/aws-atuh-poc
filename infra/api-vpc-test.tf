# ==============================================================================
# ADR-012: VPC Lambda Authorizer 検証用 /v2/* エンドポイント
#
# 既存 /v1/* は非VPC Authorizer を使用（インターネット経由で JWKS 取得）。
# /v2/* は VPC Lambda Authorizer を使用（Internal ALB / VPC Endpoint 経由）。
#
# 両方並列に稼働させて比較検証する。VPC Lambda は infra/keycloak スタックで
# 作成されるため、ここでは data source で参照する。
# ==============================================================================

# data source: Keycloak スタックで作成された VPC Lambda
data "aws_lambda_function" "vpc_authorizer" {
  function_name = "auth-poc-kc-vpc-authorizer"
}

# ------------------------------------------------------------------------------
# API Gateway Authorizer (VPC Lambda)
# ------------------------------------------------------------------------------
resource "aws_api_gateway_authorizer" "jwt_vpc" {
  name                             = "jwt-authorizer-vpc"
  rest_api_id                      = aws_api_gateway_rest_api.main.id
  authorizer_uri                   = data.aws_lambda_function.vpc_authorizer.invoke_arn
  type                             = "TOKEN"
  identity_source                  = "method.request.header.Authorization"
  authorizer_result_ttl_in_seconds = 0 # 検証時は毎回 Lambda を呼ぶためキャッシュ無効
}

resource "aws_lambda_permission" "api_gw_invoke_vpc_authorizer" {
  statement_id  = "AllowAPIGatewayInvokeVPC"
  action        = "lambda:InvokeFunction"
  function_name = data.aws_lambda_function.vpc_authorizer.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/authorizers/${aws_api_gateway_authorizer.jwt_vpc.id}"
}

# ------------------------------------------------------------------------------
# /v2 リソース階層（/v1 のミラー、Authorizer のみ異なる）
# ------------------------------------------------------------------------------
resource "aws_api_gateway_resource" "v2" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "v2"
}

resource "aws_api_gateway_resource" "v2_test" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.v2.id
  path_part   = "test"
}

resource "aws_api_gateway_resource" "v2_expenses" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.v2.id
  path_part   = "expenses"
}

resource "aws_api_gateway_resource" "v2_expense_item" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.v2_expenses.id
  path_part   = "{id}"
}

resource "aws_api_gateway_resource" "v2_expense_approve" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.v2_expense_item.id
  path_part   = "approve"
}

resource "aws_api_gateway_resource" "v2_tenants" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.v2.id
  path_part   = "tenants"
}

resource "aws_api_gateway_resource" "v2_tenant_item" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.v2_tenants.id
  path_part   = "{tenantId}"
}

resource "aws_api_gateway_resource" "v2_tenant_expenses" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.v2_tenant_item.id
  path_part   = "expenses"
}

locals {
  v2_methods = {
    v2_test            = { resource = aws_api_gateway_resource.v2_test.id,            method = "GET" }
    v2_expenses_get    = { resource = aws_api_gateway_resource.v2_expenses.id,        method = "GET" }
    v2_expenses_post   = { resource = aws_api_gateway_resource.v2_expenses.id,        method = "POST" }
    v2_expense_get     = { resource = aws_api_gateway_resource.v2_expense_item.id,    method = "GET" }
    v2_expense_delete  = { resource = aws_api_gateway_resource.v2_expense_item.id,    method = "DELETE" }
    v2_expense_approve = { resource = aws_api_gateway_resource.v2_expense_approve.id, method = "POST" }
    v2_tenant_expenses = { resource = aws_api_gateway_resource.v2_tenant_expenses.id, method = "GET" }
  }

  v2_cors_resources = {
    v2_test            = aws_api_gateway_resource.v2_test.id
    v2_expenses        = aws_api_gateway_resource.v2_expenses.id
    v2_expense_item    = aws_api_gateway_resource.v2_expense_item.id
    v2_expense_approve = aws_api_gateway_resource.v2_expense_approve.id
    v2_tenant_expenses = aws_api_gateway_resource.v2_tenant_expenses.id
  }
}

# ------------------------------------------------------------------------------
# /v2/* 認可メソッド + Backend統合
# ------------------------------------------------------------------------------
resource "aws_api_gateway_method" "v2" {
  for_each      = local.v2_methods
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = each.value.resource
  http_method   = each.value.method
  authorization = "CUSTOM"
  authorizer_id = aws_api_gateway_authorizer.jwt_vpc.id
}

resource "aws_api_gateway_integration" "v2" {
  for_each                = local.v2_methods
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = each.value.resource
  http_method             = aws_api_gateway_method.v2[each.key].http_method
  type                    = "AWS_PROXY"
  integration_http_method = "POST"
  uri                     = aws_lambda_function.backend.invoke_arn
}

# ------------------------------------------------------------------------------
# CORS (OPTIONS)
# ------------------------------------------------------------------------------
resource "aws_api_gateway_method" "v2_options" {
  for_each      = local.v2_cors_resources
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = each.value
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "v2_options" {
  for_each    = local.v2_cors_resources
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = each.value
  http_method = aws_api_gateway_method.v2_options[each.key].http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = jsonencode({ statusCode = 200 })
  }
}

resource "aws_api_gateway_method_response" "v2_options" {
  for_each    = local.v2_cors_resources
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = each.value
  http_method = aws_api_gateway_method.v2_options[each.key].http_method
  status_code = "200"
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "v2_options" {
  for_each    = local.v2_cors_resources
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = each.value
  http_method = aws_api_gateway_method.v2_options[each.key].http_method
  status_code = "200"
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,Authorization'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,POST,DELETE,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
  depends_on = [
    aws_api_gateway_integration.v2_options,
    aws_api_gateway_method_response.v2_options,
  ]
}
