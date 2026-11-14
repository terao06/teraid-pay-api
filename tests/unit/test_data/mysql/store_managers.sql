-- テスト用データ
INSERT INTO store_managers (
    store_manager_id,
    store_id,
    name,
    email,
    password_hash,
    roll_id,
    is_active,
    created_at,
    updated_at,
    deleted_at
) VALUES
    (201, 101, 'Store Manager 1', 'manager1@example.com', '$2b$12$51KjPVrKnptDeCdXPD88IOw/BL16zN7lXEgCJjl6f0BK29NXAj6s2', 1, TRUE, '2026-01-01 09:00:00', '2026-01-01 09:00:00', NULL),
    (202, 102, 'Inactive Store Manager', 'inactive-manager@example.com', '$2b$12$IxwxqU2r/nreT6rtJBLFDuGDdX4hjqDXcVBI6SN65QYd9t94YpuRG', 2, FALSE, '2026-01-02 09:00:00', '2026-01-02 09:00:00', NULL),
    (203, 102, 'Deleted Store Manager', 'deleted-manager@example.com', '$2b$12$IxwxqU2r/nreT6rtJBLFDuGDdX4hjqDXcVBI6SN65QYd9t94YpuRG', 1, TRUE, '2026-01-03 09:00:00', '2026-01-03 09:00:00', '2026-02-01 00:00:00'),
    (204, 103, 'Deleted Store Manager', 'deleted-store-manager@example.com', '$2b$12$IxwxqU2r/nreT6rtJBLFDuGDdX4hjqDXcVBI6SN65QYd9t94YpuRG', 1, TRUE, '2026-01-04 09:00:00', '2026-01-04 09:00:00', NULL),
    (205, 104, 'No Wallet Store Manager', 'no-wallet-manager@example.com', '$2b$12$51KjPVrKnptDeCdXPD88IOw/BL16zN7lXEgCJjl6f0BK29NXAj6s2', 1, TRUE, '2026-01-05 09:00:00', '2026-01-05 09:00:00', NULL);

-- API動作確認用データ
-- ログイン情報: api-manager@example.com / password123
INSERT INTO store_managers (
    store_manager_id,
    store_id,
    name,
    email,
    password_hash,
    roll_id,
    is_active,
    created_at,
    updated_at,
    deleted_at
) VALUES (
    9001,
    9001,
    'API Demo Store Manager',
    'api-manager@example.com',
    '$2b$12$51KjPVrKnptDeCdXPD88IOw/BL16zN7lXEgCJjl6f0BK29NXAj6s2',
    1,
    TRUE,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
    NULL
)
ON DUPLICATE KEY UPDATE
    store_id = VALUES(store_id),
    name = VALUES(name),
    password_hash = VALUES(password_hash),
    roll_id = VALUES(roll_id),
    is_active = TRUE,
    updated_at = CURRENT_TIMESTAMP,
    deleted_at = NULL;
