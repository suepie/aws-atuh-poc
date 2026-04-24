"""
Backend Lambda - 経費精算サンプルAPI

Lambda Authorizer が付与した Context (tenantId, roles) を使って
ロールベース・テナントスコープの認可を実装する。

エンドポイント:
- GET    /v1/test                        : 既存の動作確認用（Authorizer Context を返す）
- GET    /v1/expenses                    : 自テナントの申請一覧
- POST   /v1/expenses                    : 申請作成
- GET    /v1/expenses/{id}               : 申請詳細
- POST   /v1/expenses/{id}/approve       : 申請承認 (manager+)
- DELETE /v1/expenses/{id}               : 申請削除 (admin)
- GET    /v1/tenants/{tenantId}/expenses : 同テナントの全申請 (manager+)
"""

import json
import logging
from typing import Any

logger = logging.getLogger()
logger.setLevel(logging.INFO)


# ---------------------------------------------------------------------------
# インメモリのダミーデータ（PoCではLambdaコンテナ生存中のみ保持）
# 本番では DynamoDB or RDS の tenant_id 条件付きクエリに置換する。
# ---------------------------------------------------------------------------
EXPENSES: dict[str, dict] = {
    "exp-001": {"id": "exp-001", "tenant_id": "acme-corp", "owner": "alice@acme.com", "amount": 1200, "status": "pending"},
    "exp-002": {"id": "exp-002", "tenant_id": "acme-corp", "owner": "bob@acme.com", "amount": 3400, "status": "approved"},
    "exp-003": {"id": "exp-003", "tenant_id": "globex-inc", "owner": "dave@globex.com", "amount": 5600, "status": "pending"},
    "exp-004": {"id": "exp-004", "tenant_id": "partner-co", "owner": "eve@partner.com", "amount": 800, "status": "pending"},
}


# ---------------------------------------------------------------------------
# 認可ユーティリティ
# ---------------------------------------------------------------------------
ROLE_RANK = {"employee": 1, "manager": 2, "admin": 3}


def parse_roles(roles_str: str) -> list[str]:
    return [r.strip() for r in (roles_str or "").split(",") if r.strip()]


def has_min_role(roles: list[str], required: str) -> bool:
    required_rank = ROLE_RANK.get(required, 99)
    return any(ROLE_RANK.get(r, 0) >= required_rank for r in roles)


def response(status: int, body: dict | list) -> dict:
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,DELETE,OPTIONS",
        },
        "body": json.dumps(body, ensure_ascii=False),
    }


def deny(reason: str, status: int = 403) -> dict:
    logger.info(json.dumps({"event": "access_denied", "reason": reason, "status": status}))
    return response(status, {"error": reason})


# ---------------------------------------------------------------------------
# ルーティング
# ---------------------------------------------------------------------------
def handler(event: dict, context: Any) -> dict:
    authz = event.get("requestContext", {}).get("authorizer", {}) or {}
    path = event.get("resource") or event.get("path", "")
    method = event.get("httpMethod", "")
    path_params = event.get("pathParameters") or {}

    caller = {
        "userId": authz.get("userId", ""),
        "email": authz.get("email", ""),
        "tenantId": authz.get("tenantId", ""),
        "roles": parse_roles(authz.get("roles", "")),
    }

    logger.info(json.dumps({
        "event": "api_request", "method": method, "path": path,
        "userId": caller["userId"], "tenantId": caller["tenantId"], "roles": caller["roles"],
    }))

    # tenant_id が無いユーザーは認可不能としてすべて拒否
    if not caller["tenantId"]:
        return deny("tenant_id claim missing", 403)

    # /v1/* と /v2/* はどちらも同じビジネスロジック（Authorizer のみ違う）
    # ルーティング判定のため先頭の /vN/ プレフィックスを除去して正規化する
    normalized = path
    for prefix in ("/v1/", "/v2/"):
        if path.startswith(prefix):
            normalized = "/" + path[len(prefix):]
            break

    # ルーティング
    try:
        if normalized in ("/test",) and method == "GET":
            return handle_debug(event, authz)

        if normalized == "/expenses" and method == "GET":
            return handle_list_my(caller)

        if normalized == "/expenses" and method == "POST":
            return handle_create(event, caller)

        if normalized == "/expenses/{id}" and method == "GET":
            return handle_get(path_params.get("id", ""), caller)

        if normalized == "/expenses/{id}/approve" and method == "POST":
            return handle_approve(path_params.get("id", ""), caller)

        if normalized == "/expenses/{id}" and method == "DELETE":
            return handle_delete(path_params.get("id", ""), caller)

        if normalized == "/tenants/{tenantId}/expenses" and method == "GET":
            return handle_list_tenant(path_params.get("tenantId", ""), caller)

        return response(404, {"error": f"Not found: {method} {path}"})
    except Exception as e:
        logger.exception("handler error")
        return response(500, {"error": str(e)})


# ---------------------------------------------------------------------------
# ハンドラ
# ---------------------------------------------------------------------------
def handle_debug(event: dict, authz: dict) -> dict:
    """既存の動作確認用エンドポイント互換"""
    body = {
        "message": "API呼び出し成功",
        "path": event.get("path"),
        "method": event.get("httpMethod"),
        "authorizer": {
            "userId": authz.get("userId", ""),
            "email": authz.get("email", ""),
            "tenantId": authz.get("tenantId", ""),
            "roles": authz.get("roles", ""),
            "issuerType": authz.get("issuerType", ""),
            "idpName": authz.get("idpName", ""),
        },
    }
    return response(200, body)


def handle_list_my(caller: dict) -> dict:
    """自分の申請一覧（employee以上）"""
    if not has_min_role(caller["roles"], "employee"):
        return deny("employee role required")
    items = [
        e for e in EXPENSES.values()
        if e["tenant_id"] == caller["tenantId"] and e["owner"] == caller["email"]
    ]
    return response(200, {"items": items})


def handle_create(event: dict, caller: dict) -> dict:
    if not has_min_role(caller["roles"], "employee"):
        return deny("employee role required")
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return response(400, {"error": "Invalid JSON"})
    amount = body.get("amount", 0)
    new_id = f"exp-{len(EXPENSES) + 1:03d}"
    item = {
        "id": new_id,
        "tenant_id": caller["tenantId"],  # JWT から自動付与（body からは受け取らない）
        "owner": caller["email"],
        "amount": amount,
        "status": "pending",
    }
    EXPENSES[new_id] = item
    return response(201, item)


def handle_get(expense_id: str, caller: dict) -> dict:
    item = EXPENSES.get(expense_id)
    if not item:
        return response(404, {"error": "Expense not found"})
    # 別テナントなら見せない
    if item["tenant_id"] != caller["tenantId"]:
        return deny("cross-tenant access forbidden")
    # 自分の申請なら OK、他人のは manager+ 必要
    if item["owner"] == caller["email"]:
        return response(200, item)
    if has_min_role(caller["roles"], "manager"):
        return response(200, item)
    return deny("manager role required to view others' expenses")


def handle_approve(expense_id: str, caller: dict) -> dict:
    item = EXPENSES.get(expense_id)
    if not item:
        return response(404, {"error": "Expense not found"})
    if item["tenant_id"] != caller["tenantId"]:
        return deny("cross-tenant access forbidden")
    if not has_min_role(caller["roles"], "manager"):
        return deny("manager role required")
    item["status"] = "approved"
    return response(200, item)


def handle_delete(expense_id: str, caller: dict) -> dict:
    item = EXPENSES.get(expense_id)
    if not item:
        return response(404, {"error": "Expense not found"})
    if item["tenant_id"] != caller["tenantId"]:
        return deny("cross-tenant access forbidden")
    if not has_min_role(caller["roles"], "admin"):
        return deny("admin role required")
    del EXPENSES[expense_id]
    return response(200, {"id": expense_id, "deleted": True})


def handle_list_tenant(tenant_id: str, caller: dict) -> dict:
    if tenant_id != caller["tenantId"]:
        return deny("cross-tenant access forbidden")
    if not has_min_role(caller["roles"], "manager"):
        return deny("manager role required")
    items = [e for e in EXPENSES.values() if e["tenant_id"] == tenant_id]
    return response(200, {"items": items})
