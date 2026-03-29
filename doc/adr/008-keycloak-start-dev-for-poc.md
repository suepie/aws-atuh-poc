---
title: PoCでKeycloak start-devモードを使用
status: Accepted
date: 2026-03-25
---

# ADR-008: PoCでKeycloak start-devモードを使用

## ステータス
Accepted

## コンテキスト
Keycloak 26.xをECS Fargate + ALB（HTTP）で稼働させる際、DB内の`sslRequired=EXTERNAL`設定によりAdmin Consoleにアクセスできなくなった。`start --optimized`モードでは環境変数でDB内のSSL設定を上書きできない。

## 決定
PoCでは`start-dev`モードを使用する。

## 根拠
- `start-dev`はSSL設定に関係なくHTTPを許可する
- PoCでは起動速度やパフォーマンスの最適化は不要
- ALBにACM証明書（HTTPS）を設定すれば`start --optimized`に移行可能だが、PoCの範囲外

## 影響
- CPU使用率が高い（リクエストごとに設定を動的評価）→ 2 vCPU / 4 GBに増強で対応
- 本番では`start --optimized` + HTTPS構成が必須
- 設定変更がビルドなしで即反映される（開発には便利だが、変更管理が必要）
