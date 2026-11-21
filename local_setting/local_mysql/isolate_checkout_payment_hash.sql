-- add_checkout_payment_fields.sql の適用後に一度実行する。
ALTER TABLE payment_requests
    ADD COLUMN checkout_transaction_hash VARCHAR(66) NULL COMMENT '端末の会計決済で送信前に確定するトランザクションハッシュ';

UPDATE payment_requests
SET checkout_transaction_hash = transaction_hash, transaction_hash = NULL
WHERE checkout_id IS NOT NULL AND transaction_hash IS NOT NULL;

ALTER TABLE payment_requests
    ADD CONSTRAINT ck_payment_requests_transaction_hash_scope CHECK (
        (checkout_id IS NULL AND checkout_transaction_hash IS NULL)
        OR (checkout_id IS NOT NULL AND transaction_hash IS NULL)
    );
