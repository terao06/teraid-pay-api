-- メニューオプション構成更新API用テストデータ
INSERT INTO menu_options (
    menu_option_id,
    menu_option_group_id,
    name,
    additional_price,
    display_order,
    is_available,
    created_at,
    updated_at,
    deleted_at
) VALUES
    (27021, 27011, '通常', 0.000000, 1, TRUE, '2026-01-10 09:00:00', '2026-01-10 09:00:00', NULL),
    (27022, 27011, '削除対象オプション', 100.000000, 2, TRUE, '2026-01-10 09:00:00', '2026-01-10 09:00:00', NULL),
    (27023, 27012, 'グループごと削除対象', 50.000000, 1, TRUE, '2026-01-10 09:00:00', '2026-01-10 09:00:00', NULL);

-- fixture: delete_menu
INSERT INTO menu_options (
    menu_option_id, menu_option_group_id, name, additional_price, display_order,
    is_available, created_at, updated_at, deleted_at
) VALUES
    (840001, 840001, '削除対象の販売停止オプション', 100.000000, 0, FALSE, '2026-01-01 09:00:00', '2026-01-01 09:00:00', NULL),
    (840002, 840001, '削除済みオプション', 200.000000, 1, TRUE, '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-02-01 00:00:00'),
    (840003, 840003, '別店舗の削除対象外オプション', 300.000000, 0, TRUE, '2026-01-01 09:00:00', '2026-01-01 09:00:00', NULL),
    (840005, 840005, 'ロールバックテスト用オプション', 100.000000, 0, FALSE, '2026-01-01 09:00:00', '2026-01-01 09:00:00', NULL),
    (840006, 840006, 'Repository削除テスト用オプション', 100.000000, 0, FALSE, '2026-01-01 09:00:00', '2026-01-01 09:00:00', NULL);

-- fixture: device_menu_items
INSERT INTO menu_options (
    menu_option_id, menu_option_group_id, name, additional_price,
    display_order, is_available, created_at, updated_at, deleted_at
) VALUES
    (865211, 864111, 'ベーコン', 120.000000, 2, TRUE, NOW(), NOW(), NULL),
    (865212, 864111, 'チーズ追加', 100.500000, 1, TRUE, NOW(), NOW(), NULL),
    (865213, 864111, 'レタス', 50.000000, 1, TRUE, NOW(), NOW(), NULL),
    (865214, 864111, '選択不可オプション', 50.000000, 0, FALSE, NOW(), NOW(), NULL),
    (865215, 864111, '削除済みオプション', 50.000000, 0, TRUE, NOW(), NOW(), NOW()),
    (865216, 864112, '在庫切れのソース', 50.000000, 0, FALSE, NOW(), NOW(), NULL),
    (865217, 864115, '通常サイズ', 0.000000, 0, TRUE, NOW(), NOW(), NULL);

-- fixture: device_orders
INSERT INTO menu_options (
    menu_option_id, menu_option_group_id, name, additional_price, is_available, deleted_at
) VALUES
    (885001, 884001, '注文チーズ', 100.500000, TRUE, NULL),
    (885002, 884001, '注文ソース', 10.125000, TRUE, NULL),
    (885003, 884001, '注文削除オプション', 50.000000, TRUE, NOW());

-- fixture: device_checkout
INSERT INTO menu_options (menu_option_id, menu_option_group_id, name, additional_price, is_available) VALUES
    (906001, 905001, '現行チーズ', 120.000000, TRUE),
    (906002, 905001, '現行ソース', 80.000000, TRUE);
