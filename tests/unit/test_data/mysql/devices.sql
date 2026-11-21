-- devicesテーブル用。デバイス一覧・詳細・更新・削除APIのDBテストで投入する。
INSERT INTO devices (device_id, store_id, device_name, device_uuid, is_active, created_at, updated_at, deleted_at) VALUES
    (810001, 101, '削除対象端末', '81000100-0000-4000-8000-000000000001', FALSE, NOW(), NOW(), NULL),
    (810002, 102, '別店舗端末', '81000200-0000-4000-8000-000000000002', FALSE, NOW(), NOW(), NULL),
    (810003, 101, '削除済み端末', '81000300-0000-4000-8000-000000000003', FALSE, NOW(), NOW(), '2026-01-01 00:00:00'),
    (810011, 101, '一覧DBテスト-1', '81001100-0000-4000-8000-000000000011', FALSE, '2026-11-16 10:00:00', '2026-11-16 10:00:00', NULL),
    (810012, 101, '一覧DBテスト-2', '81001200-0000-4000-8000-000000000012', FALSE, '2026-11-16 10:00:00', '2026-11-16 10:00:00', NULL),
    (810021, 101, '更新DBテスト', '81002100-0000-4000-8000-000000000021', FALSE, NOW(), NOW(), NULL),
    (810022, 101, '未有効化DBテスト', '81002200-0000-4000-8000-000000000022', FALSE, NOW(), NOW(), NULL),
    (810031, 101, '詳細DBテスト', '81003100-0000-4000-8000-000000000031', FALSE, NOW(), NOW(), NULL);

-- fixture: activate_device
INSERT INTO devices (
    device_id, store_id, device_name, device_uuid, activation_code_hash,
    activation_expires_at, is_active, created_at, updated_at, deleted_at
) VALUES
    (810041, 101, '有効化対象端末', '81004100-0000-4000-8000-000000000041', SHA2('ABCD-EFGH-JKLM', 256),
        DATE_ADD(UTC_TIMESTAMP(), INTERVAL 33 HOUR), FALSE, UTC_TIMESTAMP(), UTC_TIMESTAMP(), NULL),
    (810042, 101, '有効化コード期限切れ端末', '81004200-0000-4000-8000-000000000042', SHA2('NPQR-STUV-WXYZ', 256),
        UTC_TIMESTAMP(), FALSE, UTC_TIMESTAMP(), UTC_TIMESTAMP(), NULL),
    (810043, 101, '有効化前に削除済みの端末', '81004300-0000-4000-8000-000000000043', SHA2('2345-6789-ABCD', 256),
        DATE_ADD(UTC_TIMESTAMP(), INTERVAL 33 HOUR), FALSE, UTC_TIMESTAMP(), UTC_TIMESTAMP(), UTC_TIMESTAMP()),
    (810044, 101, '並行有効化対象端末', '81004400-0000-4000-8000-000000000044', SHA2('JKLM-NPQR-STUV', 256),
        DATE_ADD(UTC_TIMESTAMP(), INTERVAL 33 HOUR), FALSE, UTC_TIMESTAMP(), UTC_TIMESTAMP(), NULL);

-- fixture: issue_device_access_token
INSERT INTO devices (
    device_id, store_id, device_name, device_uuid, device_credential_hash,
    activated_at, is_active, created_at, updated_at, deleted_at
) VALUES
    (810051, 101, '認証対象端末', '81005100-0000-4000-8000-000000000051', SHA2('test-device-access-credential', 256),
        NOW(), TRUE, NOW(), NOW(), NULL),
    (810052, 101, '停止済みの端末', '81005200-0000-4000-8000-000000000052', SHA2('test-device-access-credential', 256),
        NOW(), FALSE, NOW(), NOW(), NULL),
    (810053, 101, '削除済みの端末', '81005300-0000-4000-8000-000000000053', SHA2('test-device-access-credential', 256),
        NOW(), TRUE, NOW(), NOW(), NOW()),
    (810054, 101, '有効化されていない端末', '81005400-0000-4000-8000-000000000054', SHA2('test-device-access-credential', 256),
        NULL, TRUE, NOW(), NOW(), NULL),
    (810055, 101, '端末認証情報がない端末', '81005500-0000-4000-8000-000000000055', NULL,
        NOW(), TRUE, NOW(), NOW(), NULL),
    (810056, 101, '資格情報不一致のテスト用端末', '81005600-0000-4000-8000-000000000056', SHA2('test-device-access-credential', 256),
        NOW(), TRUE, NOW(), NOW(), NULL);

-- fixture: start_visit_session
INSERT INTO devices (
    device_id, store_id, device_name, device_uuid, device_credential_hash,
    activated_at, is_active, created_at, updated_at, deleted_at
) VALUES
    (810061, 109, 'セッション開始端末', '81006100-0000-4000-8000-000000000061',
        SHA2('test-visit-session-credential', 256), NOW(), TRUE, NOW(), NOW(), NULL),
    (810062, 109, '終了済みセッションの端末', '81006200-0000-4000-8000-000000000062',
        SHA2('test-visit-session-credential', 256), NOW(), TRUE, NOW(), NOW(), NULL),
    (810063, 109, '同じ開始要求の並行テスト端末', '81006300-0000-4000-8000-000000000063',
        SHA2('test-visit-session-credential', 256), NOW(), TRUE, NOW(), NOW(), NULL),
    (810064, 109, '別の開始要求の並行テスト端末', '81006400-0000-4000-8000-000000000064',
        SHA2('test-visit-session-credential', 256), NOW(), TRUE, NOW(), NOW(), NULL),
    (810065, 109, '決済処理中セッションの端末', '81006500-0000-4000-8000-000000000065',
        SHA2('test-visit-session-credential', 256), NOW(), TRUE, NOW(), NOW(), NULL),
    (810066, 110, '別店舗のセッション端末', '81006600-0000-4000-8000-000000000066',
        SHA2('test-visit-session-credential', 256), NOW(), TRUE, NOW(), NOW(), NULL),
    (810067, 109, '永続化テスト用端末', '81006700-0000-4000-8000-000000000067',
        SHA2('test-visit-session-credential', 256), NOW(), TRUE, NOW(), NOW(), NULL),
    (810068, 109, 'カテゴリー未登録店舗の端末', '81006800-0000-4000-8000-000000000068',
        SHA2('test-visit-session-credential', 256), NOW(), TRUE, NOW(), NOW(), NULL);

-- fixture: device_menu_items
INSERT INTO devices (
    device_id, store_id, device_name, device_uuid, device_credential_hash,
    activated_at, is_active, created_at, updated_at, deleted_at
) VALUES
    (861001, 111, 'カテゴリー別メニュー取得端末', '86100100-0000-4000-8000-000000861001',
        SHA2('test-device-menu-items-credential', 256), NOW(), TRUE, NOW(), NOW(), NULL),
    (861002, 112, 'カテゴリー別メニューの他店舗端末', '86100200-0000-4000-8000-000000861002',
        SHA2('test-device-menu-items-credential', 256), NOW(), TRUE, NOW(), NOW(), NULL);

-- fixture: device_orders
INSERT INTO devices (
    device_id, store_id, device_name, device_uuid, device_credential_hash, activated_at, is_active, created_at, updated_at
) VALUES
    (881001, 113, 'Order Device', '88100100-0000-4000-8000-000000881001',
        SHA2('test-device-order-credential', 256), NOW(), TRUE, NOW(), NOW()),
    (881002, 113, 'Disabled Order Device', '88100200-0000-4000-8000-000000881002',
        SHA2('test-device-order-credential', 256), NOW(), FALSE, NOW(), NOW());

-- fixture: device_order_history
INSERT INTO devices (
    device_id, store_id, device_name, device_uuid, is_active, activated_at, deleted_at
) VALUES
    (891001, 113, 'History Active', '89100100-0000-4000-8000-000000891001', TRUE, NOW(), NULL),
    (891002, 113, 'History Checkout', '89100200-0000-4000-8000-000000891002', TRUE, NOW(), NULL),
    (891003, 113, 'History Other', '89100300-0000-4000-8000-000000891003', TRUE, NOW(), NULL),
    (891004, 113, 'History Disabled', '89100400-0000-4000-8000-000000891004', FALSE, NOW(), NULL),
    (891005, 113, 'History Unactivated', '89100500-0000-4000-8000-000000891005', TRUE, NULL, NULL),
    (891006, 113, 'History Deleted', '89100600-0000-4000-8000-000000891006', TRUE, NOW(), NOW());

-- fixture: device_checkout
INSERT INTO devices (device_id, store_id, device_name, device_uuid, is_active, activated_at) VALUES
    (901001, 9101, 'Checkout Active', '90100100-0000-4000-8000-000000901001', TRUE, NOW()),
    (901002, 9101, 'Checkout Processing', '90100200-0000-4000-8000-000000901002', TRUE, NOW()),
    (901003, 9101, 'Checkout Empty', '90100300-0000-4000-8000-000000901003', TRUE, NOW()),
    (901004, 9101, 'Checkout Mixed', '90100400-0000-4000-8000-000000901004', TRUE, NOW()),
    (901005, 9101, 'Checkout Disabled', '90100500-0000-4000-8000-000000901005', FALSE, NOW());

-- fixture: face_checkout_payment
INSERT INTO devices (device_id, store_id, device_name, device_uuid, is_active, activated_at) VALUES
    (911001, 9201, 'Face Checkout Send', '91100100-0000-4000-8000-000000911001', TRUE, NOW()),
    (911002, 9201, 'Face Checkout Timeout', '91100200-0000-4000-8000-000000911002', TRUE, NOW()),
    (911003, 9201, 'Face Checkout Insufficient', '91100300-0000-4000-8000-000000911003', TRUE, NOW()),
    (911004, 9201, 'Face Checkout Changed', '91100400-0000-4000-8000-000000911004', TRUE, NOW()),
    (911005, 9201, 'Face Checkout Disabled', '91100500-0000-4000-8000-000000911005', FALSE, NOW()),
    (911006, 9201, 'Face Checkout Update Failure', '91100600-0000-4000-8000-000000911006', TRUE, NOW()),
    (911021, 9201, 'Payment Result 1', '91102100-0000-4000-8000-000000911021', TRUE, NOW()),
    (911022, 9201, 'Payment Result 2', '91102200-0000-4000-8000-000000911022', TRUE, NOW()),
    (911023, 9201, 'Payment Result 3', '91102300-0000-4000-8000-000000911023', TRUE, NOW()),
    (911024, 9201, 'Payment Result 4', '91102400-0000-4000-8000-000000911024', TRUE, NOW());
