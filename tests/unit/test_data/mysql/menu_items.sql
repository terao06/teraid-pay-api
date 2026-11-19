-- テスト用データ
INSERT INTO menu_items (
    menu_item_id,
    store_id,
    menu_category_id,
    name,
    description,
    price,
    token_symbol,
    image_extension,
    is_available,
    display_order,
    created_at,
    updated_at,
    deleted_at
) VALUES
    (21, 101, 12, 'チーズバーガー', 'チェダーチーズ入り', 800.000000, 'JPYC', 'jpeg', TRUE, 1, '2026-01-01 09:00:00', '2026-01-01 09:00:00', NULL),
    (22, 101, 11, 'コーラ', NULL, 200.000000, 'JPYC', 'png', FALSE, 1, '2026-01-02 09:00:00', '2026-01-02 09:00:00', NULL),
    (23, 101, 15, '旧カテゴリー商品', NULL, 500.000000, 'JPYC', 'jpg', TRUE, 2, '2026-01-03 09:00:00', '2026-01-03 09:00:00', NULL),
    (24, 101, NULL, '未分類商品', NULL, 300.000000, 'JPYC', 'png', TRUE, 3, '2026-01-04 09:00:00', '2026-01-04 09:00:00', NULL),
    (25, 101, 13, '削除済み商品', NULL, 400.000000, 'JPYC', 'png', TRUE, 0, '2026-01-05 09:00:00', '2026-01-05 09:00:00', '2026-02-01 00:00:00'),
    (26, 102, 16, '別店舗商品', NULL, 600.000000, 'JPYC', 'png', TRUE, 0, '2026-01-06 09:00:00', '2026-01-06 09:00:00', NULL);

-- fixture: delete_menu_category
INSERT INTO menu_items (
    menu_item_id, store_id, menu_category_id, name, price, token_symbol, image_extension,
    is_available, display_order, created_at, updated_at
) VALUES
    (830001, 101, 830001, '削除対象カテゴリーの商品', 300.000000, 'JPYC', 'png', TRUE, 0, '2026-01-01 09:00:00', '2026-01-01 09:00:00');

-- fixture: delete_menu
INSERT INTO menu_items (
    menu_item_id, store_id, menu_category_id, name, price, token_symbol, image_extension,
    is_available, display_order, created_at, updated_at, deleted_at
) VALUES
    (840001, 101, NULL, '削除対象の販売停止商品', 300.000000, 'JPYC', 'png', FALSE, 0, '2026-01-01 09:00:00', '2026-01-01 09:00:00', NULL),
    (840002, 101, NULL, '削除対象の販売中商品', 400.000000, 'JPYC', 'png', TRUE, 0, '2026-01-01 09:00:00', '2026-01-01 09:00:00', NULL),
    (840003, 102, NULL, '別店舗の削除対象外商品', 500.000000, 'JPYC', 'png', TRUE, 0, '2026-01-01 09:00:00', '2026-01-01 09:00:00', NULL),
    (840004, 101, NULL, '削除済みの削除対象外商品', 600.000000, 'JPYC', 'png', TRUE, 0, '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-02-01 00:00:00');
