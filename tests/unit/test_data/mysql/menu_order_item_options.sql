-- 注文時のオプション名と商品1個当たりの数量を検証する。
INSERT INTO menu_order_item_options (
    menu_order_item_option_id, menu_order_item_id, menu_option_id, option_group_name,
    option_name, additional_price, option_quantity, display_order
) VALUES
    (872101, 871102, 865212, 'トッピング', '追加チーズ', 100.000000, 1, 2),
    (872102, 871102, 865211, 'トッピング', '追加ベーコン', 120.000000, 1, 1);

-- fixture: device_order_history
INSERT INTO menu_order_item_options (
    menu_order_item_option_id, menu_order_item_id, menu_option_id, option_group_name,
    option_name, additional_price, option_quantity, display_order
) VALUES
    (895001, 894002, 885001, '注文時のトッピング', '注文時のチーズ', 80.000000, 1, 2),
    (895002, 894002, 885002, '注文時のトッピング', '注文時のソース', 10.000000, 2, 1);

-- fixture: device_checkout
INSERT INTO menu_order_item_options (
    menu_order_item_option_id, menu_order_item_id, menu_option_id, option_group_name,
    option_name, additional_price, option_quantity, display_order
) VALUES
    (908001, 907001, 906001, '注文時のトッピング', '注文時のチーズ', 80.000000, 1, 1),
    (908002, 907001, 906002, '注文時のトッピング', '注文時のソース', 20.000000, 1, 2),
    (908003, 907005, 906002, '注文時のトッピング', '注文時のソース', 25.000000, 2, 1);
