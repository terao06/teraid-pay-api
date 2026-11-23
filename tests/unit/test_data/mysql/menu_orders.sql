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

-- fixture: device_checkout
INSERT INTO menu_orders (
    menu_order_id, idempotency_key, visit_session_id, store_id, total_amount, token_symbol,
    status, paid_at, created_at, deleted_at
) VALUES
    (903001, 'checkout-pending', 902001, 9101, 1400.000000, 'JPYC', 1, NULL, '2026-11-21 03:00:00', NULL),
    (903002, 'checkout-failed', 902001, 9101, 300.000000, 'JPYC', 4, NULL, '2026-11-21 02:30:00', NULL),
    (903003, 'checkout-paid', 902001, 9101, 300.000000, 'JPYC', 3, NOW(), '2026-11-21 02:30:00', NULL),
    (903004, 'checkout-deleted', 902001, 9101, 300.000000, 'JPYC', 1, NULL, '2026-11-21 02:30:00', NOW()),
    (903005, 'checkout-other-store', 902001, 102, 300.000000, 'JPYC', 1, NULL, '2026-11-21 02:30:00', NULL),
    (903006, 'checkout-mixed-jpyc', 902005, 9101, 400.000000, 'JPYC', 1, NULL, '2026-11-21 02:30:00', NULL),
    (903007, 'checkout-mixed-other', 902005, 9101, 300.000000, 'OTHER', 1, NULL, '2026-11-21 02:30:00', NULL),
    (903008, 'checkout-canceled', 902001, 9101, 300.000000, 'JPYC', 5, NULL, '2026-11-21 02:30:00', NULL),
    (903009, 'checkout-order-processing', 902001, 9101, 300.000000, 'JPYC', 2, NULL, '2026-11-21 02:30:00', NULL),
    (903010, 'checkout-paid-at', 902001, 9101, 300.000000, 'JPYC', 1, NOW(), '2026-11-21 02:30:00', NULL),
    (903011, 'checkout-partial-order', 902006, 9101, 2900.000000, 'JPYC', 1, NULL, '2026-11-21 04:00:00', NULL);

-- fixture: face_checkout_payment
INSERT INTO menu_orders (
    menu_order_id, idempotency_key, visit_session_id, store_id, total_amount, status, deleted_at
) VALUES
    (913001, 'face-checkout-first', 912001, 9201, 1200.125000, 1, NULL),
    (913002, 'face-checkout-second', 912001, 9201, 300.250000, 4, NULL),
    (913003, 'face-checkout-timeout', 912002, 9201, 700.125000, 1, NULL),
    (913004, 'face-checkout-insufficient', 912003, 9201, 900.125000, 1, NULL),
    (913005, 'face-checkout-changed', 912004, 9201, 300.000000, 1, NULL),
    (913006, 'face-checkout-added', 912004, 9201, 50.000000, 1, NULL),
    (913007, 'face-checkout-other-store', 912001, 102, 10.000000, 1, NULL),
    (913008, 'face-checkout-deleted', 912001, 9201, 10.000000, 1, NOW()),
    (913009, 'face-checkout-canceled', 912001, 9201, 10.000000, 5, NULL),
    (913010, 'face-checkout-timeout-extra', 912002, 9201, 20.000000, 1, NULL),
    (913011, 'face-checkout-update-failure', 912006, 9201, 600.175000, 1, NULL),
    (913012, 'face-checkout-partly-paid', 912009, 9201, 400.000000, 1, NULL),
    (913013, 'face-checkout-unselected', 912009, 9201, 50.000000, 1, NULL),
    (913021, 'payment-result-1', 912021, 9201, 100.125000, 1, NULL),
    (913022, 'payment-result-2', 912022, 9201, 100.125000, 1, NULL),
    (913023, 'payment-result-3', 912023, 9201, 100.125000, 1, NULL),
    (913024, 'payment-result-4', 912024, 9201, 100.125000, 1, NULL),
    (913025, 'payment-result-1-unselected', 912021, 9201, 50.250000, 1, NULL);

-- fixture: complete_visit_session
INSERT INTO menu_orders (
    menu_order_id, idempotency_key, visit_session_id, store_id, total_amount, status, paid_at, deleted_at
) VALUES
    (933001, 'complete-order-paid', 932001, 9301, 300.000000, 3, UTC_TIMESTAMP(), NULL),
    (933002, 'complete-order-canceled', 932001, 9301, 300.000000, 5, NULL, NULL),
    (933003, 'complete-order-deleted', 932001, 9301, 300.000000, 1, NULL, UTC_TIMESTAMP()),
    (933004, 'complete-order-other-store', 932001, 9302, 300.000000, 1, NULL, NULL),
    (933005, 'complete-order-paid-at', 932001, 9301, 300.000000, 1, UTC_TIMESTAMP(), NULL),
    (933006, 'complete-order-unpaid', 932002, 9301, 300.000000, 1, NULL, NULL),
    (933007, 'complete-order-payment-failed', 932004, 9301, 300.000000, 4, NULL, NULL);
