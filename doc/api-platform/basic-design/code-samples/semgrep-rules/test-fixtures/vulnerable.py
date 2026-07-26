"""検知されるべき脆弱コード（P6 / P5 / P3 の 3 ルールを踏む）。
Phase 4 P4-1: semgrep が実際に検知するかの検証用フィクスチャ。"""

import jwt
from fastapi import FastAPI

# --- P6: FastAPI に auth middleware がない ---------------------------------
app = FastAPI(title="vulnerable")


@app.get("/api/users")
def list_users():
    return {"users": []}


# --- P5: JWT を署名検証せずデコード ----------------------------------------
def decode_no_verify(token):
    # verify=False → 署名検証スキップ
    return jwt.decode(token, options={"verify_signature": False}, verify=False)


def decode_none_alg(token):
    # algorithms=["none"] → 署名なしを受容
    return jwt.decode(token, algorithms=["none"])


def decode_no_key(token):
    # 鍵未指定でデコード
    return jwt.decode(token)


# --- P3: path の tenant_id を JWT クレームと照合しない ----------------------
def handler(event, context):
    tenant_id = event['pathParameters'].get('tenant_id')
    # JWT の tenant_id と照合せずそのまま使用 → クロステナントの穴
    return {"statusCode": 200, "body": tenant_id}
