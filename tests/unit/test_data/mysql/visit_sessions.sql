-- 来店セッションの状態分岐と端末ごとの検索範囲を検証する。
INSERT INTO visit_sessions (
    visit_session_id, device_id, start_request_id, status, started_at, ended_at
) VALUES
    (820062, 810062, 'closed-request', 'closed', '2026-11-16 10:00:00', '2026-11-16 11:00:00'),
    (820065, 810065, 'checkout-request', 'checkout_processing', '2026-11-16 10:00:00', NULL),
    (820066, 810066, 'start-request', 'active', '2026-11-16 10:00:00', NULL),
    (820068, 810068, 'category-list-empty', 'active', '2026-11-16 10:00:00', NULL);

-- fixture: device_menu_items
INSERT INTO visit_sessions (
    visit_session_id, device_id, start_request_id, status, started_at, ended_at
) VALUES
    (862001, 861001, 'device-menu-items', 'active', '2026-11-16 10:00:00', NULL),
    (862002, 861002, 'device-menu-items-other-device', 'active', '2026-11-16 10:00:00', NULL);

-- fixture: device_orders
INSERT INTO visit_sessions (visit_session_id, device_id, start_request_id, status, started_at, ended_at) VALUES
    (882001, 881001, 'order-active', 'active', NOW(), NULL),
    (882002, 881001, 'order-closed', 'closed', NOW(), NOW());

-- fixture: device_order_history
INSERT INTO visit_sessions (visit_session_id, device_id, start_request_id, status, started_at, ended_at) VALUES
    (892001, 891001, 'history-active', 'active', '2026-11-21 02:00:00', NULL),
    (892002, 891001, 'history-closed', 'closed', '2026-11-21 01:00:00', '2026-11-21 01:30:00'),
    (892003, 891002, 'history-checkout', 'checkout_processing', '2026-11-21 02:00:00', NULL),
    (892004, 891003, 'history-other-device', 'active', '2026-11-21 02:00:00', NULL);

-- fixture: device_checkout
INSERT INTO visit_sessions (visit_session_id, device_id, start_request_id, status, started_at, ended_at) VALUES
    (902001, 901001, 'checkout-active', 'active', '2026-11-21 02:00:00', NULL),
    (902002, 901001, 'checkout-closed', 'closed', '2026-11-21 01:00:00', '2026-11-21 01:30:00'),
    (902003, 901002, 'checkout-processing', 'checkout_processing', '2026-11-21 02:00:00', NULL),
    (902004, 901003, 'checkout-empty', 'active', '2026-11-21 02:00:00', NULL),
    (902005, 901004, 'checkout-mixed', 'active', '2026-11-21 02:00:00', NULL);
