"""検知されるべきでない健全コード（3 ルールを回避）。
Phase 4 P4-1: semgrep が false positive を出さないかの検証用。"""

import jwt
from fastapi import FastAPI

# --- P6 回避: auth middleware を追加 ---------------------------------------
app = FastAPI(title="clean")
app.add_middleware(AuthMiddleware, issuer="https://auth.example.com")  # noqa: F821


@app.get("/api/users")
def list_users():
    return {"users": []}


# --- P5 回避: 鍵 + アルゴリズム指定で署名検証 -------------------------------
def decode_verified(token, public_key):
    return jwt.decode(token, key=public_key, algorithms=["ES256"], audience="api")


# --- P3 回避: path の tenant_id を JWT クレームと照合 ------------------------
def handler(event, context):
    tenant_id = event['pathParameters'].get('tenant_id')
    jwt_tenant = event['requestContext']['authorizer']['tenant_id']
    if tenant_id != jwt_tenant:
        return {"statusCode": 403, "body": "Cross-tenant access denied"}
    return {"statusCode": 200, "body": tenant_id}
