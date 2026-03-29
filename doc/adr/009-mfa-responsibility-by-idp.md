---
title: MFA責任はパスワード管理側に帰属させる
status: Accepted
date: 2026-03-28
---

# ADR-009: MFA責任はパスワード管理側に帰属させる

## ステータス
Accepted

## コンテキスト
Keycloak + Auth0構成で、Auth0経由のフェデレーションユーザーにもKeycloakのMFA（TOTP）が要求され、二重MFAが発生した。

## 決定
MFAは**パスワードを管理している側**が提供する。

- ローカルユーザー → Keycloak（またはCognito）がMFA提供
- フェデレーションユーザー → 外部IdP（Auth0 / Entra ID）がMFA提供、Keycloak/CognitoはMFAスキップ

## 実装
Keycloakの `browser` 認証フローで `Conditional OTP` + `Condition - User Configured` を使用。フェデレーションユーザーのOTPクレデンシャルを削除することで、OTP未設定=スキップとなる。

## 根拠
- 二重MFAはユーザー体験を著しく損なう
- 外部IdPのMFAポリシーはIdP管理者の責任範囲
- Keycloak/CognitoはIdPの認証結果全体を信頼する設計

## 影響
- フェデレーションユーザーのMFAレベルは外部IdPに依存する
- 外部IdPがMFAを無効にしている場合、パスワードのみで認証される
- 必要に応じてKeycloak側で`amr`クレーム（Auth0が返す認証メソッド情報）を検証する拡張が可能
