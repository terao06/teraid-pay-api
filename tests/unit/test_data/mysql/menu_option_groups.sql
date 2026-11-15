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
