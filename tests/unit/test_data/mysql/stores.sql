-- テスト用データ
INSERT INTO stores (store_id, name, email, created_at, updated_at, deleted_at) VALUES (101, 'Sample Store 1', 'store1@example.com', NOW(), NOW(), NULL);
INSERT INTO stores (store_id, name, email, created_at, updated_at, deleted_at) VALUES (102, 'Sample Store 2', 'store2@example.com', NOW(), NOW(), NULL);
INSERT INTO stores (store_id, name, email, created_at, updated_at, deleted_at) VALUES (103, 'Deleted Store', 'deleted-store@example.com', NOW(), NOW(), '2023-01-01 00:00:00');
INSERT INTO stores (store_id, name, email, created_at, updated_at, deleted_at) VALUES (104, 'Deleted Store', 'deleted-store@example.com', NOW(), NOW(), NULL);
INSERT INTO stores (store_id, name, email, created_at, updated_at, deleted_at) VALUES (105, 'Wallet Create Test Store', 'wallet-create-store@example.com', NOW(), NOW(), NULL);
INSERT INTO stores (store_id, name, email, created_at, updated_at, deleted_at) VALUES (106, 'Menu Create Test Store', 'menu-create-store@example.com', NOW(), NOW(), NULL);

-- API動作確認用データ
INSERT INTO stores (
    store_id,
    name,
    email,
    created_at,
    updated_at,
    deleted_at
) VALUES (
    9001,
    'API Demo Store',
    'api-demo-store@example.com',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
    NULL
);

-- fixture: menu_mutations
INSERT INTO stores (store_id, name, email, created_at, updated_at, deleted_at) VALUES
    (107, 'Menu Mutation Test Store', 'menu-mutations-store@example.com', NOW(), NOW(), NULL),
    (108, 'Other Menu Mutation Test Store', 'other-menu-mutations-store@example.com', NOW(), NOW(), NULL);

-- fixture: start_visit_session
INSERT INTO stores (store_id, name, email, created_at, updated_at, deleted_at) VALUES
    (109, 'Visit Session Test Store', 'visit-session-store@example.com', NOW(), NOW(), NULL),
    (110, 'Other Visit Session Test Store', 'other-visit-session-store@example.com', NOW(), NOW(), NULL);

-- fixture: device_menu_items
INSERT INTO stores (store_id, name, email, created_at, updated_at, deleted_at) VALUES
    (111, 'Device Menu Items Test Store', 'device-menu-items-store@example.com', NOW(), NOW(), NULL),
    (112, 'Device Menu Items Other Store', 'device-menu-items-other-store@example.com', NOW(), NOW(), NULL);

-- fixture: device_orders
INSERT INTO stores (store_id, name, email, created_at, updated_at) VALUES
    (113, 'Device Order Test Store', 'device-order-store@example.com', NOW(), NOW());

-- fixture: device_checkout
INSERT INTO stores (store_id, name, email, created_at, updated_at) VALUES
    (9101, 'Device Checkout Test Store', 'device-checkout-store@example.com', NOW(), NOW());

-- fixture: face_checkout_payment
INSERT INTO stores (store_id, name, email, created_at, updated_at) VALUES
    (9201, 'Face Checkout Store', 'face-checkout@example.com', NOW(), NOW());

-- fixture: complete_visit_session
INSERT INTO stores (store_id, name, email, created_at, updated_at) VALUES
    (9301, 'Visit Completion Test Store', 'visit-completion@example.com', NOW(), NOW()),
    (9302, 'Visit Completion Other Store', 'visit-completion-other@example.com', NOW(), NOW());
