'use strict';

/**
 * 4x4 真偽値表による分類（README §2.5 準拠）。
 * canary と alert-router-lambda で同一ロジックを共有する（SSOT）。
 *
 * 入力:
 *   negStatus: Negative probe（認証ヘッダなし）の HTTP status。skip の場合は null。
 *   posStatus: Positive probe（有効 Bearer 等）の HTTP status。未実施は undefined。
 *   authPattern: 認証パターン enum（alb-cookie-monolith は Negative 期待が 302）。
 *
 * 出力: { severity, reason, priority }
 *   severity: 'OK' | 'CRITICAL' | 'WARN' | 'INFO'
 *   priority: 'P1' | 'P2' | 'P3' | null
 *   reason:   人間可読の理由
 */

// 認証拒否として正常な Negative status（authPattern 別）
function negativeIsAuthDenied(negStatus, authPattern) {
  if (authPattern === 'alb-cookie-monolith') {
    // Cookie SSR モノリスは未認証で /login へ 302 リダイレクト
    return negStatus === 302;
  }
  // JWT / IAM 系は 401 or 403
  return negStatus === 401 || negStatus === 403;
}

// Positive が「アクセス成功」とみなせる status
function positiveIsSuccess(posStatus) {
  return posStatus === 200 || posStatus === 201 || posStatus === 204;
}

// Positive が「認証拒否された」status（token 失効等）
function positiveIsAuthDenied(posStatus) {
  return posStatus === 401 || posStatus === 403;
}

function classify(negStatus, posStatus, authPattern) {
  // --- Negative が skip（public + health）--------------------------------
  if (negStatus === null || negStatus === undefined) {
    // public endpoint。Positive があり成功なら OK、それ以外は判定不要
    return { severity: 'OK', priority: null, reason: 'Public/skip endpoint (no negative probe)' };
  }

  // --- CRITICAL: 認証漏れ（Negative が通ってしまう）----------------------
  // 未認証リクエストが 2xx で通る = Authorizer 不在 / バイパス
  if (negStatus >= 200 && negStatus < 300) {
    if (positiveIsSuccess(posStatus)) {
      return {
        severity: 'CRITICAL',
        priority: 'P1',
        reason: 'Auth missing or bypassed (negative 2xx, positive 2xx)',
      };
    }
    // Negative 2xx だが Positive は拒否 = 認証逆転（設定崩壊）
    return {
      severity: 'CRITICAL',
      priority: 'P1',
      reason: 'Auth inverted (negative 2xx, positive denied)',
    };
  }

  // --- Negative が正しく認証拒否している場合 ------------------------------
  if (negativeIsAuthDenied(negStatus, authPattern)) {
    // Positive 未実施（Negative のみ）→ OK
    if (posStatus === undefined || posStatus === null) {
      return { severity: 'OK', priority: null, reason: 'Negative denied, no positive test' };
    }
    // Positive 成功 → OK（正常系）
    if (positiveIsSuccess(posStatus)) {
      return { severity: 'OK', priority: null, reason: 'Auth enforced correctly' };
    }
    // Positive も拒否 → token 失効の疑い（WARN / P2）
    if (positiveIsAuthDenied(posStatus)) {
      return {
        severity: 'WARN',
        priority: 'P2',
        reason: 'Test token expired or invalid (negative denied, positive denied)',
      };
    }
    // Positive 404 → endpoint 不在 / 構成ミス（WARN / P2）
    if (posStatus === 404) {
      return {
        severity: 'WARN',
        priority: 'P2',
        reason: 'Endpoint not found on positive probe (config drift)',
      };
    }
    // Positive 5xx → Backend バグ（INFO / P3）
    if (posStatus >= 500) {
      return {
        severity: 'INFO',
        priority: 'P3',
        reason: 'Backend error on positive probe (5xx)',
      };
    }
    // その他 status → WARN として拾う
    return {
      severity: 'WARN',
      priority: 'P2',
      reason: `Unexpected positive status ${posStatus} (negative denied)`,
    };
  }

  // --- Negative 404 → probe 構成ミス（WARN / P2）------------------------
  if (negStatus === 404) {
    return {
      severity: 'WARN',
      priority: 'P2',
      reason: 'Negative probe returned 404 (config error / wrong path)',
    };
  }

  // --- その他の Negative status（想定外）→ WARN -------------------------
  return {
    severity: 'WARN',
    priority: 'P2',
    reason: `Unexpected negative status ${negStatus}`,
  };
}

module.exports = { classify, negativeIsAuthDenied, positiveIsSuccess, positiveIsAuthDenied };
