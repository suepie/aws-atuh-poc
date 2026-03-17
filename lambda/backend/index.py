"""
Backend Lambda - サンプルAPI

Lambda Authorizer が付与した Context 情報を返す。
認可フローの動作確認用。
"""

import json
import logging
from typing import Any

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event: dict, context: Any) -> dict:
    """サンプルAPIハンドラー"""
    # Lambda Authorizer が付与した Context を取得
    authorizer_context = event.get("requestContext", {}).get("authorizer", {})

    logger.info(json.dumps({
        "event": "api_request",
        "path": event.get("path"),
        "method": event.get("httpMethod"),
        "userId": authorizer_context.get("userId"),
        "email": authorizer_context.get("email"),
    }))

    # レスポンス: 認可情報をそのまま返す（デバッグ用）
    body = {
        "message": "API呼び出し成功",
        "path": event.get("path"),
        "method": event.get("httpMethod"),
        "authorizer": {
            "userId": authorizer_context.get("userId", ""),
            "email": authorizer_context.get("email", ""),
            "groups": authorizer_context.get("groups", ""),
            "issuerType": authorizer_context.get("issuerType", ""),
            "idpName": authorizer_context.get("idpName", ""),
            "tokenUse": authorizer_context.get("tokenUse", ""),
            "principalId": authorizer_context.get("principalId", ""),
        },
        "requestContext": {
            "requestId": event.get("requestContext", {}).get("requestId", ""),
            "sourceIp": event.get("requestContext", {}).get("identity", {}).get("sourceIp", ""),
            "stage": event.get("requestContext", {}).get("stage", ""),
        },
    }

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,OPTIONS",
        },
        "body": json.dumps(body, ensure_ascii=False),
    }
