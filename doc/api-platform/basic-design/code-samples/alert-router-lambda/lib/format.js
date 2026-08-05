'use strict';

/**
 * 通知メッセージ整形（severity 別 SLA 文言付与）。
 * README §2.5 / §2.6 準拠。canary 側 lib/classify.js が出力した severity を受ける。
 *
 * severity → priority / 通知先 / SLA の対応（§2.5 4x4 真偽値表）:
 *   CRITICAL → P1 / Security オンコール / 即時（page）
 *   WARN     → P2 / Platform          / 24h 以内
 *   INFO     → P3 / App team          / 通常（次営業日）
 */

// severity → ルーティングメタ情報の SSOT
const SEVERITY_META = {
  CRITICAL: {
    priority: 'P1',
    routingKey: 'p1',
    target: 'Security オンコール',
    sla: '即時対応（page / 15 分以内に確認）',
    emoji: '🔥',
  },
  WARN: {
    priority: 'P2',
    routingKey: 'p2',
    target: 'Platform チーム',
    sla: '24 時間以内に調査',
    emoji: '⚠',
  },
  INFO: {
    priority: 'P3',
    routingKey: 'p3',
    target: 'App チーム',
    sla: '通常対応（次営業日）',
    emoji: 'ℹ',
  },
};

/**
 * severity からルーティングメタを取得。未知 severity は WARN(P2) に fallback。
 */
function metaFor(severity) {
  return SEVERITY_META[severity] || SEVERITY_META.WARN;
}

/**
 * SNS 通知の Subject（最大 100 文字、ASCII 推奨だが SNS は UTF-8 許容）。
 */
function formatSubject(event) {
  const meta = metaFor(event.severity);
  const subject = `[${meta.priority}] AuthCheck ${event.severity} - ${event.appId}/${event.env} ${event.method} ${event.path}`;
  // SNS Subject は 100 文字上限
  return subject.length > 100 ? subject.slice(0, 100) : subject;
}

/**
 * 人間可読の本文。どのアプリのどの endpoint で何が起きたか + 対応 SLA。
 */
function formatBody(event) {
  const meta = metaFor(event.severity);
  const lines = [
    `${meta.emoji} 中央認証チェック Alert`,
    '',
    `重大度   : ${event.severity} (${meta.priority})`,
    `通知先   : ${meta.target}`,
    `対応 SLA : ${meta.sla}`,
    '',
    `アプリ   : ${event.appId} (${event.env})`,
    `認証方式 : ${event.authPattern}`,
    `対象     : ${event.method} ${event.path}`,
    '',
    `Negative probe (認証ヘッダなし) の応答 : ${fmtStatus(event.negStatus)}`,
    `Positive probe (有効 token)     の応答 : ${fmtStatus(event.posStatus)}`,
    '',
    `理由     : ${event.reason || '(reason 未指定)'}`,
    `発生時刻 : ${event.timestamp || '(timestamp 未指定)'}`,
  ];

  // CRITICAL は認証漏れ/逆転なので初動を明示
  if (event.severity === 'CRITICAL') {
    lines.push(
      '',
      '── 初動 ──',
      '1. 該当 endpoint の Authorizer / 認証設定を即確認',
      '2. 認証漏れが確認できた場合は当該 endpoint を遮断（WAF / API GW disable）',
      '3. Security インシデント起票',
    );
  }

  return lines.join('\n');
}

function fmtStatus(status) {
  if (status === null) return 'null (skip / public endpoint)';
  if (status === undefined) return '(未実施)';
  return String(status);
}

module.exports = { SEVERITY_META, metaFor, formatSubject, formatBody };
