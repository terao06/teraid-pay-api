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
    (840003, 840003, '別店舗の削除対象外オプション', 300.000000, 0, TRUE, '2026-01-01 09:00:00', '2026-01-01 09:00:00', NULL);
