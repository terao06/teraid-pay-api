-- メニューオプション構成更新API用テストデータ
INSERT INTO menu_option_groups (
    menu_option_group_id,
    menu_item_id,
    name,
    min_selections,
    max_selections,
    display_order,
    is_active,
    created_at,
    updated_at,
    deleted_at
) VALUES
    (27011, 24, 'サイズ', 1, 1, 1, TRUE, '2026-01-10 09:00:00', '2026-01-10 09:00:00', NULL),
    (27012, 24, '削除対象グループ', 0, 1, 2, TRUE, '2026-01-10 09:00:00', '2026-01-10 09:00:00', NULL);

-- fixture: delete_menu
INSERT INTO menu_option_groups (
    menu_option_group_id, menu_item_id, name, min_selections, max_selections,
    display_order, is_active, created_at, updated_at, deleted_at
) VALUES
    (840001, 840001, '削除対象の無効グループ', 0, 1, 0, FALSE, '2026-01-01 09:00:00', '2026-01-01 09:00:00', NULL),
    (840002, 840001, '削除済みグループ', 0, 1, 1, TRUE, '2026-01-01 09:00:00', '2026-01-01 09:00:00', '2026-02-01 00:00:00'),
    (840003, 840003, '別店舗の削除対象外グループ', 0, 1, 0, TRUE, '2026-01-01 09:00:00', '2026-01-01 09:00:00', NULL);
