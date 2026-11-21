-- 注文時の商品名、数量、表示順を検証する。
INSERT INTO menu_order_items (
    menu_order_item_id, menu_order_id, menu_item_id, menu_item_name,
    unit_price, quantity, line_amount, display_order
) VALUES
    (871101, 870101, 863011, 'フライドポテト', 300.000000, 1, 300.000000, 2),
    (871102, 870101, 863012, '特製チーズバーガー', 650.000000, 2, 1740.000000, 1),
    (871103, 870102, 863011, 'フライドポテト', 300.000000, 1, 300.000000, 0),
    (871104, 870103, 863011, 'フライドポテト', 300.000000, 1, 300.000000, 0),
    (871105, 870107, 863014, '他店舗商品', 500.000000, 1, 500.000000, 0),
    (871106, 870104, 863011, 'フライドポテト', 300.000000, 1, 300.000000, 0),
    (871107, 870108, 863011, 'フライドポテト', 300.000000, 1, 300.000000, 0);

-- fixture: device_order_history
INSERT INTO menu_order_items (
    menu_order_item_id, menu_order_id, menu_item_id, menu_item_name,
    unit_price, quantity, line_amount, display_order
) VALUES
    (894001, 893001, 883002, '注文時のポテト', 300.000000, 1, 300.000000, 2),
    (894002, 893001, 883001, '注文時のバーガー', 600.000000, 2, 1400.000000, 1);

-- fixture: device_checkout
INSERT INTO menu_order_items (
    menu_order_item_id, menu_order_id, menu_item_id, menu_item_name, unit_price, quantity, line_amount, display_order
) VALUES
    (907001, 903001, 904001, '注文時のカレー', 600.000000, 2, 1400.000000, 1),
    (907002, 903002, 904001, '注文時のポテト', 300.000000, 1, 300.000000, 1),
    (907003, 903006, 904001, '注文時の飲み物', 400.000000, 1, 400.000000, 1),
    (907004, 903007, 904002, '注文時のケーキ', 300.000000, 1, 300.000000, 1);
