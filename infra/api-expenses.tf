# ==============================================================================
# 経費精算API - 認可検証用エンドポイント
#
# /v1/expenses              (GET/POST)
# /v1/expenses/{id}         (GET/DELETE)
# /v1/expenses/{id}/approve (POST)
# /v1/tenants/{tenantId}/expenses (GET)
# ==============================================================================

# --- /v1/expenses ------------------------------------------------------------
resource "aws_api_gateway_resource" "expenses" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.v1.id
  path_part   = "expenses"
}

resource "aws_api_gateway_resource" "expense_item" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.expenses.id
  path_part   = "{id}"
}

resource "aws_api_gateway_resource" "expense_approve" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.expense_item.id
  path_part   = "approve"
}

# --- /v1/tenants/{tenantId}/expenses ----------------------------------------
resource "aws_api_gateway_resource" "tenants" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.v1.id
  path_part   = "tenants"
}

resource "aws_api_gateway_resource" "tenant_item" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.tenants.id
  path_part   = "{tenantId}"
}

resource "aws_api_gateway_resource" "tenant_expenses" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.tenant_item.id
  path_part   = "expenses"
}

# ---------------------------------------------------------------------------
# ヘルパ: メソッド + Backend統合を作成するためのlocals
# ---------------------------------------------------------------------------
locals {
  expense_methods = {
    expenses_get      = { resource = aws_api_gateway_resource.expenses.id,        method = "GET" }
    expenses_post     = { resource = aws_api_gateway_resource.expenses.id,        method = "POST" }
    expense_get       = { resource = aws_api_gateway_resource.expense_item.id,    method = "GET" }
    expense_delete    = { resource = aws_api_gateway_resource.expense_item.id,    method = "DELETE" }
    expense_approve   = { resource = aws_api_gateway_resource.expense_approve.id, method = "POST" }
    tenant_expenses   = { resource = aws_api_gateway_resource.tenant_expenses.id, method = "GET" }
  }

  expense_cors_resources = {
    expenses        = aws_api_gateway_resource.expenses.id
    expense_item    = aws_api_gateway_resource.expense_item.id
    expense_approve = aws_api_gateway_resource.expense_approve.id
    tenant_expenses = aws_api_gateway_resource.tenant_expenses.id
  }
}

# ---------------------------------------------------------------------------
# 認可付きメソッド + Backend統合
# ---------------------------------------------------------------------------
resource "aws_api_gateway_method" "expense" {
  for_each      = local.expense_methods
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = each.value.resource
  http_method   = each.value.method
  authorization = "CUSTOM"
  authorizer_id = aws_api_gateway_authorizer.jwt.id
}

resource "aws_api_gateway_integration" "expense" {
  for_each                = local.expense_methods
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = each.value.resource
  http_method             = aws_api_gateway_method.expense[each.key].http_method
  type                    = "AWS_PROXY"
  integration_http_method = "POST"
  uri                     = aws_lambda_function.backend.invoke_arn
}

# ---------------------------------------------------------------------------
# CORS (OPTIONS) - 各リソース用
# ---------------------------------------------------------------------------
resource "aws_api_gateway_method" "expense_options" {
  for_each      = local.expense_cors_resources
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = each.value
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "expense_options" {
  for_each    = local.expense_cors_resources
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = each.value
  http_method = aws_api_gateway_method.expense_options[each.key].http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = jsonencode({ statusCode = 200 })
  }
}

resource "aws_api_gateway_method_response" "expense_options" {
  for_each    = local.expense_cors_resources
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = each.value
  http_method = aws_api_gateway_method.expense_options[each.key].http_method
  status_code = "200"
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "expense_options" {
  for_each    = local.expense_cors_resources
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = each.value
  http_method = aws_api_gateway_method.expense_options[each.key].http_method
  status_code = "200"
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,Authorization'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,POST,DELETE,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
  depends_on = [aws_api_gateway_integration.expense_options]
}
