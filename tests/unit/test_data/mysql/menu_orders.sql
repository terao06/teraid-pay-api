-- 店舗、提供状態、決済状態、論理削除、並び順を検証する。
INSERT INTO menu_orders (
    menu_order_id, idempotency_key, visit_session_id, store_id, total_amount, status,
    paid_at, served_at, created_at, deleted_at
) VALUES
    (870101, 'unserved-pending', 862001, 111, 2040.000000, 1,
        NULL, NULL, '2026-11-16 01:00:00', NULL),
    (870102, 'unserved-paid', 862001, 111, 300.000000, 3,
        '2026-11-16 01:01:00', NULL, '2026-11-16 01:00:00', NULL),
    (870103, 'unserved-without-device', NULL, 111, 300.000000, 1,
        NULL, NULL, '2026-11-16 01:02:00', NULL),
    (870104, 'served-unpaid', 862001, 111, 300.000000, 1,
        NULL, '2026-11-16 01:30:00', '2026-11-16 00:50:00', NULL),
    (870105, 'canceled-unserved', 862001, 111, 300.000000, 5,
        NULL, NULL, '2026-11-16 00:50:00', NULL),
    (870106, 'deleted-unserved', 862001, 111, 300.000000, 1,
        NULL, NULL, '2026-11-16 00:50:00', '2026-11-16 01:00:00'),
    (870107, 'other-store-unserved', 862002, 112, 500.000000, 1,
        NULL, NULL, '2026-11-16 00:50:00', NULL),
    (870108, 'served-paid', 862001, 111, 300.000000, 3,
        '2026-11-16 01:41:00', '2026-11-16 01:40:00', '2026-11-16 01:09:00', NULL),
    (870109, 'served-later-canceled', 862001, 111, 300.000000, 5,
        NULL, '2026-11-16 01:40:00', '2026-11-16 01:08:00', NULL),
    (870110, 'served-deleted', 862001, 111, 300.000000, 3,
        '2026-11-16 01:50:00', '2026-11-16 01:50:00', '2026-11-16 01:30:00', '2026-11-16 01:51:00'),
    (870111, 'other-store-served', 862002, 112, 500.000000, 1,
        NULL, '2026-11-16 01:50:00', '2026-11-16 01:40:00', NULL);

-- fixture: device_order_history
INSERT INTO menu_orders (
    menu_order_id, idempotency_key, visit_session_id, store_id, total_amount, status, created_at, deleted_at
) VALUES
    (893001, 'history-most-recent', 892001, 113, 1700.000000, 1, '2026-11-21 03:00:00', NULL),
    (893002, 'history-earlier', 892001, 113, 300.000000, 5, '2026-11-21 02:30:00', NULL),
    (893003, 'history-same-time', 892001, 113, 300.000000, 3, '2026-11-21 02:30:00', NULL),
    (893004, 'history-deleted', 892001, 113, 300.000000, 1, '2026-11-21 03:15:00', '2026-11-21 03:20:00'),
    (893005, 'history-other-store', 892001, 102, 300.000000, 1, '2026-11-21 03:15:00', NULL),
    (893006, 'history-other-visit', 892004, 113, 300.000000, 1, '2026-11-21 03:15:00', NULL),
    (893007, 'history-checkout-deleted', 892003, 113, 300.000000, 1, '2026-11-21 03:15:00', '2026-11-21 03:20:00');
