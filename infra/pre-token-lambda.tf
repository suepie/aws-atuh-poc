# ==============================================================================
# Pre Token Generation Lambda
# Cognito の ID トークン発行時に tenant_id / roles クレームを注入する。
# Auth0 フェデレーションユーザーとローカル Cognito ユーザーで JWT 形を揃える。
# ==============================================================================

resource "aws_cloudwatch_log_group" "pre_token" {
  name              = "/aws/lambda/${var.project_name}-pre-token"
  retention_in_days = 7
}

data "archive_file" "pre_token" {
  type        = "zip"
  source_file = "${path.module}/../lambda/pre-token/index.py"
  output_path = "${path.module}/../lambda/pre-token/package.zip"
}

resource "aws_lambda_function" "pre_token" {
  function_name = "${var.project_name}-pre-token"
  role          = aws_iam_role.lambda_role.arn
  handler       = "index.handler"
  runtime       = "python3.11"
  timeout       = 5
  memory_size   = 128

  filename         = data.archive_file.pre_token.output_path
  source_code_hash = data.archive_file.pre_token.output_base64sha256
}

resource "aws_lambda_permission" "pre_token_central" {
  statement_id  = "AllowCognitoInvokeCentral"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.pre_token.function_name
  principal     = "cognito-idp.amazonaws.com"
  source_arn    = aws_cognito_user_pool.central.arn
}

resource "aws_lambda_permission" "pre_token_local" {
  statement_id  = "AllowCognitoInvokeLocal"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.pre_token.function_name
  principal     = "cognito-idp.amazonaws.com"
  source_arn    = aws_cognito_user_pool.local.arn
}
