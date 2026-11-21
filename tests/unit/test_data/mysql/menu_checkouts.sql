-- 顔認証決済開始の会計スナップショット。

-- fixture: face_checkout_payment
INSERT INTO menu_checkouts (checkout_id, visit_session_id, scope, total_amount, token_symbol) VALUES
    (914001, 912001, 'all_unpaid', 1500.375000, 'JPYC'),
    (914002, 912002, 'single_order', 700.125000, 'JPYC'),
    (914003, 912003, 'single_order', 900.125000, 'JPYC'),
    (914004, 912004, 'all_unpaid', 300.000000, 'JPYC'),
    (914005, 912001, 'single_order', 1200.125000, 'JPYC'),
    (914006, 912006, 'single_order', 600.175000, 'JPYC'),
    (914007, 912004, 'single_order', 300.000000, 'JPYC'),
    (914021, 912021, 'single_order', 100.125000, 'JPYC'),
    (914022, 912022, 'single_order', 100.125000, 'JPYC'),
    (914023, 912023, 'single_order', 100.125000, 'JPYC'),
    (914024, 912024, 'single_order', 100.125000, 'JPYC'),
    (914025, 912024, 'single_order', 100.125000, 'JPYC');
