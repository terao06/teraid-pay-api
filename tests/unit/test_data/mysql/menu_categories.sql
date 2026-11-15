-- テスト用データ
INSERT INTO menu_categories (
    menu_category_id,
    store_id,
    name,
    image_extension,
    display_order,
    is_active,
    created_at,
    updated_at,
    deleted_at
) VALUES
    (11, 101, 'ドリンク', 'png', 2, TRUE, '2026-01-01 09:00:00', '2026-01-01 09:00:00', NULL),
    (12, 101, 'フード', 'png', 1, TRUE, '2026-01-02 09:00:00', '2026-01-02 09:00:00', NULL),
    (13, 101, 'デザート', 'png', 1, TRUE, '2026-01-03 09:00:00', '2026-01-03 09:00:00', NULL),
    (14, 101, '無効カテゴリー', 'png', 0, FALSE, '2026-01-04 09:00:00', '2026-01-04 09:00:00', NULL),
    (15, 101, '削除済みカテゴリー', 'png', 0, TRUE, '2026-01-05 09:00:00', '2026-01-05 09:00:00', '2026-02-01 00:00:00'),
    (16, 102, '別店舗カテゴリー', 'png', 0, TRUE, '2026-01-06 09:00:00', '2026-01-06 09:00:00', NULL),
    (17, 106, 'メニュー登録テスト用カテゴリー', 'png', 1, TRUE, '2026-01-07 09:00:00', '2026-01-07 09:00:00', NULL);

-- API動作確認用データ
INSERT INTO menu_categories (
    menu_category_id,
    store_id,
    name,
    image_extension,
    display_order,
    is_active,
    created_at,
    updated_at,
    deleted_at
) VALUES (
    9001,
    9001,
    'API Demo Category',
    'png',
    1,
    TRUE,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
    NULL
);
