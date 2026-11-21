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
    (830001, 107, 830001, '削除対象の有効カテゴリーの商品', 300.000000, 'JPYC', 'png', TRUE, 0, '2026-01-01 09:00:00', '2026-01-01 09:00:00'),
    (830002, 107, 830002, '削除対象の無効カテゴリーの商品', 300.000000, 'JPYC', 'png', TRUE, 0, '2026-01-01 09:00:00', '2026-01-01 09:00:00');

-- fixture: delete_menu
INSERT INTO menu_items (
    menu_item_id, store_id, menu_category_id, name, price, token_symbol, image_extension,
    is_available, display_order, created_at, updated_at, deleted_at
) VALUES
    (840001, 107, NULL, '削除対象の販売停止商品', 300.000000, 'JPYC', 'png', FALSE, 0, '2026-01-01 09:00:00', '2026-01-01 09:00:00', NULL),
    (840002, 107, NULL, '削除対象の販売中商品', 400.000000, 'JPYC', 'png', TRUE, 0, '2026-01-01 09:00:00', '2026-01-01 09:00:00', NULL),
    (840003, 108, NULL, '別店舗の削除対象外商品', 500.000000, 'JPYC', 'png', TRUE, 0, '2026-01-01 09:00:00', '2026-01-01 09:00:00', NULL),
    (840004, 107, NULL, '削除済みの削除対象外商品', 600.000000, 'JPYC', 'png', TRUE, 0, '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-02-01 00:00:00'),
    (840005, 107, NULL, 'ロールバックテスト用商品', 300.000000, 'JPYC', 'png', FALSE, 0, '2026-01-01 09:00:00', '2026-01-01 09:00:00', NULL),
    (840006, 107, NULL, 'Repository削除テスト用商品', 300.000000, 'JPYC', 'png', FALSE, 0, '2026-01-01 09:00:00', '2026-01-01 09:00:00', NULL);

-- fixture: update_menu_option_groups
INSERT INTO menu_items (
    menu_item_id, store_id, menu_category_id, name, price, token_symbol, image_extension,
    is_available, display_order, created_at, updated_at
) VALUES
    (850001, 107, NULL, 'オプション構成更新テスト用商品', 300.000000, 'JPYC', 'png', TRUE, 0, '2026-01-01 09:00:00', '2026-01-01 09:00:00');

-- fixture: device_menu_items
INSERT INTO menu_items (
    menu_item_id, store_id, menu_category_id, name, price, token_symbol, image_extension,
    is_available, display_order, created_at, updated_at, deleted_at
) VALUES
    (863011, 111, 860012, 'ポテト', 300.000000, 'JPYC', 'png', TRUE, 2, NOW(), NOW(), NULL),
    (863012, 111, 860012, 'チーズバーガー', 650.250000, 'JPYC', 'jpeg', TRUE, 1, NOW(), NOW(), NULL),
    (863013, 111, 860012, 'サンドイッチ', 450.000000, 'JPYC', 'jpg', TRUE, 1, NOW(), NOW(), NULL),
    (863014, 112, 860012, '他店舗商品', 500.000000, 'JPYC', 'png', TRUE, 0, NOW(), NOW(), NULL),
    (863015, 111, 860012, '販売停止商品', 500.000000, 'JPYC', 'png', FALSE, 0, NOW(), NOW(), NULL),
    (863016, 111, 860012, '削除済み商品', 500.000000, 'JPYC', 'png', TRUE, 0, NOW(), NOW(), NOW()),
    (863017, 111, 860013, '販売停止デザート', 300.000000, 'JPYC', 'png', FALSE, 0, NOW(), NOW(), NULL),
    (863018, 111, 860011, 'ジュース', 200.000000, 'JPYC', 'png', TRUE, 1, NOW(), NOW(), NULL);

-- fixture: device_orders
INSERT INTO menu_items (menu_item_id, store_id, name, price, token_symbol, image_extension, is_available) VALUES
    (883001, 113, '注文バーガー', 650.250000, 'JPYC', 'png', TRUE),
    (883002, 113, '注文ポテト', 300.000000, 'JPYC', 'png', TRUE),
    (883003, 113, '注文販売停止商品', 500.000000, 'JPYC', 'png', FALSE),
    (883004, 113, '注文別通貨商品', 200.000000, 'OTHER', 'png', TRUE);

-- fixture: device_checkout
INSERT INTO menu_items (menu_item_id, store_id, name, price, token_symbol, image_extension, is_available) VALUES
    (904001, 9101, '会計テストの現行商品', 900.000000, 'JPYC', 'png', TRUE),
    (904002, 9101, '会計テストの別通貨商品', 300.000000, 'OTHER', 'png', TRUE);
