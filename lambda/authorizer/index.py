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
COGNITO_REGION = os.environ.get("COGNITO_REGION", "ap-northeast-1")

# 集約 Cognito（共通認証基盤）
CENTRAL_POOL_ID = os.environ["COGNITO_USER_POOL_ID"]
CENTRAL_CLIENT_ID = os.environ["COGNITO_CLIENT_ID"]
CENTRAL_ISSUER = f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{CENTRAL_POOL_ID}"

# ローカル Cognito（各サービスアカウント相当）
LOCAL_POOL_ID = os.environ.get("LOCAL_COGNITO_USER_POOL_ID", "")
LOCAL_CLIENT_ID = os.environ.get("LOCAL_COGNITO_CLIENT_ID", "")
LOCAL_ISSUER = f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{LOCAL_POOL_ID}" if LOCAL_POOL_ID else ""

# DR Cognito（大阪リージョン）
DR_REGION = os.environ.get("DR_COGNITO_REGION", "ap-northeast-3")
DR_POOL_ID = os.environ.get("DR_COGNITO_USER_POOL_ID", "")
DR_CLIENT_ID = os.environ.get("DR_COGNITO_CLIENT_ID", "")
DR_ISSUER = f"https://cognito-idp.{DR_REGION}.amazonaws.com/{DR_POOL_ID}" if DR_POOL_ID else ""

# Keycloak (PoC の ALB 経由)
KEYCLOAK_ISSUER = os.environ.get("KEYCLOAK_ISSUER", "")
KEYCLOAK_CLIENT_ID = os.environ.get("KEYCLOAK_CLIENT_ID", "")

# 許可する issuer のリスト（マルチissuer対応）
# skip_client_check=True の場合、 aud/client_id 検証をスキップする
# (Keycloak の access token は aud が "account" で client_id はトップレベルに
#  azp として入るなど、検証が柔軟になるため)
ALLOWED_ISSUERS: dict[str, dict[str, Any]] = {
    CENTRAL_ISSUER: {
        "client_id": CENTRAL_CLIENT_ID,
        "type": "central",
    }
}

if LOCAL_ISSUER and LOCAL_POOL_ID:
    ALLOWED_ISSUERS[LOCAL_ISSUER] = {
        "client_id": LOCAL_CLIENT_ID,
        "type": "local",
    }

if DR_ISSUER and DR_POOL_ID:
    ALLOWED_ISSUERS[DR_ISSUER] = {
        "client_id": DR_CLIENT_ID,
        "type": "dr",
    }

if KEYCLOAK_ISSUER:
    ALLOWED_ISSUERS[KEYCLOAK_ISSUER] = {
        "client_id": KEYCLOAK_CLIENT_ID,
        "type": "keycloak",
    }

logger.info(f"Allowed issuers: {list(ALLOWED_ISSUERS.keys())}")

# JWKS キャッシュ
_jwks_cache: dict[str, Any] = {}
_jwks_uri_cache: dict[str, str] = {}
JWKS_CACHE_TTL = 3600  # 1時間


def get_jwks_uri(issuer: str) -> str:
    """OIDC Discovery から jwks_uri を取得（キャッシュ付き）。
    Cognito: {issuer}/.well-known/jwks.json
    Keycloak: {issuer}/protocol/openid-connect/certs
    IdP ごとに JWKS パスが異なるため、Discovery で動的に取得する。
    """
    if issuer in _jwks_uri_cache:
        return _jwks_uri_cache[issuer]

    discovery_url = f"{issuer}/.well-known/openid-configuration"
    try:
        with urllib.request.urlopen(discovery_url, timeout=5) as response:
            config = json.loads(response.read())
            jwks_uri = config.get("jwks_uri", "")
            if jwks_uri:
                _jwks_uri_cache[issuer] = jwks_uri
                return jwks_uri
    except Exception as e:
        logger.warning(f"OIDC Discovery failed for {issuer}: {e}")

    # フォールバック: Cognito 互換パス
    fallback = f"{issuer}/.well-known/jwks.json"
    _jwks_uri_cache[issuer] = fallback
    return fallback


def get_jwks(issuer: str) -> dict:
    """指定された issuer の JWKS を取得（キャッシュ付き）"""
    now = time.time()

    if issuer in _jwks_cache:
        cached = _jwks_cache[issuer]
        if now - cached["time"] < JWKS_CACHE_TTL:
            return cached["jwks"]

    jwks_url = get_jwks_uri(issuer)
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

    # client_id / azp / aud のいずれかで Client 検証
    # - Cognito Access Token: client_id
    # - Cognito ID Token: aud
    # - Keycloak Access Token: azp（aud は "account"）
    token_client_candidates = [
        payload.get("client_id"),
        payload.get("azp"),
    ]
    aud = payload.get("aud")
    if isinstance(aud, list):
        token_client_candidates.extend(aud)
    elif aud:
        token_client_candidates.append(aud)

    expected_client_id = issuer_config["client_id"]
    if expected_client_id and expected_client_id not in token_client_candidates:
        raise ValueError(
            f"Client ID mismatch: expected={expected_client_id}, got={token_client_candidates}"
        )

    # issuer タイプを追加
    payload["_issuer_type"] = issuer_config["type"]

    return payload


def extract_user_context(payload: dict) -> dict:
    """JWT ペイロードからユーザー情報を抽出（Context として Backend に渡す）

    Pre Token Generation Lambda で注入された tenant_id / roles クレームを取り出す。
    - tenant_id: Auth0 フェデレーションユーザーは attribute_mapping 経由、
                 ローカルユーザーは custom:tenant_id で設定済み。
    - roles: cognito:groups と custom:roles を合成したカンマ区切り文字列。
    """
    # roles: Cognito (Pre Token Lambda) はカンマ区切り文字列、Keycloak は配列で来る。
    # どちらも受けられるよう両対応。
    # fallback: cognito:groups / realm_access.roles
    # IdP内部ロール（Keycloak デフォルト等）を除外するセット
    _INTERNAL_ROLES = {
        "offline_access", "uma_authorization", "default-roles-auth-poc",
        "manage-account", "manage-account-links", "view-profile",
    }

    roles_claim = payload.get("roles")
    if isinstance(roles_claim, list):
        roles = [str(r).strip() for r in roles_claim if str(r).strip()]
    elif isinstance(roles_claim, str) and roles_claim:
        roles = [r.strip() for r in roles_claim.split(",") if r.strip()]
    else:
        groups = payload.get("cognito:groups") or payload.get("realm_access", {}).get("roles", [])
        roles = groups if isinstance(groups, list) else [groups]

    # IdP内部ロールを除外
    roles = [r for r in roles if r not in _INTERNAL_ROLES]

    # tenant_id: トップレベル（Pre Token Lambda 注入）優先、無ければ custom属性
    tenant_id = payload.get("tenant_id") or payload.get("custom:tenant_id", "")

    # identities からフェデレーション情報を取得
    identities = payload.get("identities", [])
    idp_name = identities[0]["providerName"] if identities else "local"

    return {
        "userId": payload.get("sub", ""),
        "email": payload.get("email", ""),
        "tenantId": tenant_id,
        "roles": ",".join(roles),
        "groups": ",".join(roles),  # 後方互換
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
            "tenantId": user_context["tenantId"],
            "roles": user_context["roles"],
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
