"""
Pre Token Generation Lambda V2 (Cognito trigger)

目的:
- Auth0 フェデレーション経由ユーザーと Cognito ローカル作成ユーザーの
  JWT を同じ形に揃える。
- `tenant_id` / `roles` をトップレベルクレームとして発行する。
- `custom:roles`（カンマ区切り文字列）を Cognito Group 形式の配列に変換する。
- Cognito が自動付与するフェデレーション内部グループ（例: <pool-id>_Auth0）を除外する。

トリガー種別: Pre Token Generation V2_0
V2 では idToken と accessToken の両方にカスタムクレームを追加できる。
V1 は ID トークン限定のため、API Gateway Authorizer に Access Token を
投げる構成では V2 が必須。
"""

import json
import logging
import os
import re
from typing import Any

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Cognito が自動付与するフェデレーション由来の内部グループ名を除外
# 例: "ap-northeast-1_sGalveybF_Auth0"
_INTERNAL_GROUP_PATTERN = re.compile(r"^[a-z]{2}-[a-z]+-\d_[A-Za-z0-9]+_.+$")


def handler(event: dict, context: Any) -> dict:
    user_attrs = event.get("request", {}).get("userAttributes", {}) or {}
    existing_groups = (
        event.get("request", {}).get("groupConfiguration", {}).get("groupsToOverride")
        or []
    )

    tenant_id = user_attrs.get("custom:tenant_id", "")
    roles_raw = user_attrs.get("custom:roles", "")
    email = user_attrs.get("email", "")

    # custom:roles は "manager,employee" のようなカンマ区切り文字列を想定
    roles = [r.strip() for r in roles_raw.split(",") if r.strip()]

    # 既存の cognito:groups と custom:roles を合成し、内部グループを除外
    merged_groups = list({*existing_groups, *roles})
    merged_groups = [g for g in merged_groups if not _INTERNAL_GROUP_PATTERN.match(g)]

    claims_to_add = {}
    if tenant_id:
        claims_to_add["tenant_id"] = tenant_id
    if merged_groups:
        claims_to_add["roles"] = ",".join(merged_groups)
    # Access Token には既定で email が入らないので Authorizer 向けに注入
    if email:
        claims_to_add["email"] = email

    logger.info(
        json.dumps(
            {
                "event": "pre_token_generation_v2",
                "userName": event.get("userName"),
                "triggerSource": event.get("triggerSource"),
                "tenant_id": tenant_id,
                "roles": merged_groups,
            }
        )
    )

    # V2: idToken と accessToken それぞれに追加する
    event["response"] = {
        "claimsAndScopeOverrideDetails": {
            "idTokenGeneration": {
                "claimsToAddOrOverride": claims_to_add,
            },
            "accessTokenGeneration": {
                "claimsToAddOrOverride": claims_to_add,
            },
            "groupOverrideDetails": {
                "groupsToOverride": merged_groups,
            },
        }
    }

    return event
