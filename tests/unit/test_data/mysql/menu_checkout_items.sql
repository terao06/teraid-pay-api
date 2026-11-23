-- 部分支払い後の会計明細。

-- fixture: device_checkout
INSERT INTO menu_checkout_items (checkout_id, menu_order_item_id, quantity, line_amount) VALUES
    (909001, 907005, 1, 650.000000),
    (909001, 907006, 1, 300.000000),
    (909002, 907005, 1, 650.000000),
    (909003, 907005, 1, 650.000000),
    (909004, 907005, 1, 650.000000);
