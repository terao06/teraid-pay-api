-- 来店セッション開始APIの状態分岐と端末ごとの検索範囲を検証する。
INSERT INTO visit_sessions (
    visit_session_id, device_id, start_request_id, status, started_at, ended_at
) VALUES
    (820062, 810062, 'closed-request', 'closed', '2026-11-16 10:00:00', '2026-11-16 11:00:00'),
    (820065, 810065, 'checkout-request', 'checkout_processing', '2026-11-16 10:00:00', NULL),
    (820066, 810066, 'start-request', 'active', '2026-11-16 10:00:00', NULL);
