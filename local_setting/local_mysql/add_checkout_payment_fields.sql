-- menu_checkouts 作成後に、既存DBに一度だけ適用する。
ALTER TABLE payment_requests
    MODIFY COLUMN amount DECIMAL(28, 6) NOT NULL COMMENT '送金額',
    ADD COLUMN checkout_id BIGINT NULL,
    ADD COLUMN idempotency_key_hash BINARY(32) NULL,
    ADD CONSTRAINT fk_payment_requests_checkout FOREIGN KEY (checkout_id) REFERENCES menu_checkouts (checkout_id),
    ADD CONSTRAINT uq_payment_requests_checkout_key UNIQUE (checkout_id, idempotency_key_hash);
