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
