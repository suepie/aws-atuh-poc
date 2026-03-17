"""
Lambda Authorizer - JWT検証 + 認可判定

doc/old/authentication-authorization-detail.md の設計に基づく実装:
1. トークン抽出
2. JWTデコード（署名検証なし）→ issuer取得
3. issuer判定（集約Cognito / ローカルCognito）
4. JWKS取得 → 署名検証
5. クレーム検証（exp, iss, aud）
6. ユーザー情報抽出
7. IAM Policy生成 + Context返却
"""

import json
import logging
import os
import time
import urllib.request
from typing import Any

import jwt  # PyJWT (lambda layer or bundled)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 環境変数から許可する issuer を構築
COGNITO_USER_POOL_ID = os.environ["COGNITO_USER_POOL_ID"]
COGNITO_REGION = os.environ.get("COGNITO_REGION", "ap-northeast-1")
COGNITO_CLIENT_ID = os.environ["COGNITO_CLIENT_ID"]

COGNITO_ISSUER = f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}"

# 許可する issuer のリスト（Phase 4 でローカルCognito追加時に拡張）
ALLOWED_ISSUERS = {
    COGNITO_ISSUER: {
        "client_id": COGNITO_CLIENT_ID,
        "type": "central",
    }
}

# JWKS キャッシュ
_jwks_cache: dict[str, Any] = {}
JWKS_CACHE_TTL = 3600  # 1時間


def get_jwks(issuer: str) -> dict:
    """指定された issuer の JWKS を取得（キャッシュ付き）"""
    now = time.time()

    if issuer in _jwks_cache:
        cached = _jwks_cache[issuer]
        if now - cached["time"] < JWKS_CACHE_TTL:
            return cached["jwks"]

    jwks_url = f"{issuer}/.well-known/jwks.json"
    logger.info(f"Fetching JWKS from: {jwks_url}")

    with urllib.request.urlopen(jwks_url, timeout=5) as response:
        jwks = json.loads(response.read())

    _jwks_cache[issuer] = {"jwks": jwks, "time": now}
    return jwks


def find_public_key(jwks: dict, kid: str) -> dict | None:
    """JWKS から kid が一致する公開鍵を取得"""
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key
    return None


def verify_token(token: str) -> dict:
    """JWT を検証し、ペイロードを返す"""
    # ① デコード（署名検証なし）で issuer を取得
    unverified_header = jwt.get_unverified_header(token)
    unverified_payload = jwt.decode(token, options={"verify_signature": False})

    issuer = unverified_payload.get("iss")
    kid = unverified_header.get("kid")

    logger.info(f"Token issuer: {issuer}, kid: {kid}")

    # ② issuer が許可リストにあるか確認
    if issuer not in ALLOWED_ISSUERS:
        raise ValueError(f"Unknown issuer: {issuer}")

    issuer_config = ALLOWED_ISSUERS[issuer]

    # ③ JWKS を取得
    jwks = get_jwks(issuer)

    # ④ kid が一致する公開鍵を取得
    key_data = find_public_key(jwks, kid)
    if not key_data:
        # キャッシュが古い可能性 → リフレッシュ
        if issuer in _jwks_cache:
            del _jwks_cache[issuer]
        jwks = get_jwks(issuer)
        key_data = find_public_key(jwks, kid)
        if not key_data:
            raise ValueError(f"Public key not found for kid: {kid}")

    # ⑤ 公開鍵を構築して署名検証 + クレーム検証
    # Cognito アクセストークンは "aud" クレームを持たず "client_id" を使う
    # そのため PyJWT の audience 検証をスキップし、手動で client_id を検証する
    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key_data))
    payload = jwt.decode(
        token,
        public_key,
        algorithms=["RS256"],
        issuer=issuer,
        options={"verify_aud": False},
    )

    # client_id または aud でクライアント検証（アクセストークン/IDトークン両対応）
    token_client_id = payload.get("client_id") or payload.get("aud")
    expected_client_id = issuer_config["client_id"]
    if token_client_id != expected_client_id:
        raise ValueError(
            f"Client ID mismatch: expected={expected_client_id}, got={token_client_id}"
        )

    # issuer タイプを追加
    payload["_issuer_type"] = issuer_config["type"]

    return payload


def extract_user_context(payload: dict) -> dict:
    """JWT ペイロードからユーザー情報を抽出（Context として Backend に渡す）"""
    # cognito:groups からテナント・グループ情報を取得
    groups = payload.get("cognito:groups", [])

    # identities からフェデレーション情報を取得
    identities = payload.get("identities", [])
    idp_name = identities[0]["providerName"] if identities else "local"

    return {
        "userId": payload.get("sub", ""),
        "email": payload.get("email", ""),
        "groups": ",".join(groups) if isinstance(groups, list) else str(groups),
        "issuerType": payload.get("_issuer_type", "unknown"),
        "idpName": idp_name,
        "tokenUse": payload.get("token_use", ""),
    }


def generate_policy(principal_id: str, effect: str, resource: str, context: dict) -> dict:
    """IAM Policy を生成"""
    # resource の末尾を * にして同一API内の全リソースを許可
    # 例: arn:aws:execute-api:region:account:api-id/stage/GET/v1/test
    #   → arn:aws:execute-api:region:account:api-id/stage/*
    parts = resource.split("/")
    if len(parts) >= 2:
        resource_prefix = "/".join(parts[:2]) + "/*"
    else:
        resource_prefix = resource

    return {
        "principalId": principal_id,
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "execute-api:Invoke",
                    "Effect": effect,
                    "Resource": resource_prefix,
                }
            ],
        },
        "context": context,
    }


def handler(event: dict, context: Any) -> dict:
    """Lambda Authorizer ハンドラー"""
    logger.info(f"Authorizer invoked. methodArn: {event.get('methodArn')}")

    token_str = event.get("authorizationToken", "")
    method_arn = event.get("methodArn", "")

    # Bearer プレフィックスを除去
    if token_str.startswith("Bearer "):
        token_str = token_str[7:]
    elif token_str.startswith("bearer "):
        token_str = token_str[7:]

    if not token_str:
        logger.warning("No token provided")
        raise Exception("Unauthorized")  # API Gateway が 401 を返す

    try:
        # JWT 検証
        payload = verify_token(token_str)
        logger.info(f"Token verified. sub: {payload.get('sub')}")

        # ユーザー情報抽出
        user_context = extract_user_context(payload)

        # 認可: Allow（Phase 3 ではすべて許可、Phase 4 でグループベース認可追加）
        policy = generate_policy(
            principal_id=payload.get("sub", "unknown"),
            effect="Allow",
            resource=method_arn,
            context=user_context,
        )

        logger.info(json.dumps({
            "event": "authorization_success",
            "userId": user_context["userId"],
            "email": user_context["email"],
            "groups": user_context["groups"],
            "issuerType": user_context["issuerType"],
            "idpName": user_context["idpName"],
        }))

        return policy

    except ValueError as e:
        logger.warning(f"Token validation failed: {e}")
        raise Exception("Unauthorized")
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        raise Exception("Unauthorized")
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        raise Exception("Unauthorized")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise Exception("Unauthorized")
