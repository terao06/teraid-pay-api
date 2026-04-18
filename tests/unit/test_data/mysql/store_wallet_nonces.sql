INSERT INTO store_wallet_nonces (
    store_wallet_nonce_id,
    store_id,
    wallet_address,
    chain_type,
    network_name,
    nonce,
    expires_at,
    used_at,
    created_at,
    updated_at
) VALUES (
    1,
    101,
    '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
    'ethereum',
    'sepolia',
    'available-older',
    '2026-04-13 12:00:00',
    NULL,
    '2026-04-13 11:00:00',
    '2026-04-13 11:00:00'
);

INSERT INTO store_wallet_nonces (
    store_wallet_nonce_id,
    store_id,
    wallet_address,
    chain_type,
    network_name,
    nonce,
    expires_at,
    used_at,
    created_at,
    updated_at
) VALUES (
    2,
    101,
    '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
    'ethereum',
    'sepolia',
    'available-latest',
    '2026-04-13 12:05:00',
    NULL,
    '2026-04-13 11:05:00',
    '2026-04-13 11:05:00'
);

INSERT INTO store_wallet_nonces (
    store_wallet_nonce_id,
    store_id,
    wallet_address,
    chain_type,
    network_name,
    nonce,
    expires_at,
    used_at,
    created_at,
    updated_at
) VALUES (
    3,
    101,
    '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
    'ethereum',
    'sepolia',
    'already-used',
    '2026-04-13 12:10:00',
    '2026-04-13 11:55:00',
    '2026-04-13 11:10:00',
    '2026-04-13 11:55:00'
);

INSERT INTO store_wallet_nonces (
    store_wallet_nonce_id,
    store_id,
    wallet_address,
    chain_type,
    network_name,
    nonce,
    expires_at,
    used_at,
    created_at,
    updated_at
) VALUES (
    4,
    101,
    '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
    'ethereum',
    'sepolia',
    'expired',
    '2026-04-13 11:59:59',
    NULL,
    '2026-04-13 10:59:00',
    '2026-04-13 10:59:00'
);

INSERT INTO store_wallet_nonces (
    store_wallet_nonce_id,
    store_id,
    wallet_address,
    chain_type,
    network_name,
    nonce,
    expires_at,
    used_at,
    created_at,
    updated_at
) VALUES (
    5,
    101,
    '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
    'ethereum',
    'sepolia',
    'different-wallet',
    '2026-04-13 12:15:00',
    NULL,
    '2026-04-13 11:15:00',
    '2026-04-13 11:15:00'
);
