-- 注文時のオプション名と商品1個当たりの数量を検証する。
INSERT INTO menu_order_item_options (
    menu_order_item_option_id, menu_order_item_id, menu_option_id, option_group_name,
    option_name, additional_price, option_quantity, display_order
) VALUES
    (872101, 871102, 865212, 'トッピング', '追加チーズ', 100.000000, 1, 2),
    (872102, 871102, 865211, 'トッピング', '追加ベーコン', 120.000000, 1, 1);
