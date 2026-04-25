INSERT INTO nonces (
    nonce_id,
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
    '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
    'ethereum',
    'sepolia',
    'available-older',
    '2026-04-13 12:00:00',
    NULL,
    '2026-04-13 11:00:00',
    '2026-04-13 11:00:00'
);

INSERT INTO nonces (
    nonce_id,
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
    '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
    'ethereum',
    'sepolia',
    'available-latest',
    '2026-04-13 12:05:00',
    NULL,
    '2026-04-13 11:05:00',
    '2026-04-13 11:05:00'
);

INSERT INTO nonces (
    nonce_id,
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
    '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
    'ethereum',
    'sepolia',
    'already-used',
    '2026-04-13 12:10:00',
    '2026-04-13 11:55:00',
    '2026-04-13 11:10:00',
    '2026-04-13 11:55:00'
);

INSERT INTO nonces (
    nonce_id,
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
    '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
    'ethereum',
    'sepolia',
    'expired',
    '2026-04-13 11:59:59',
    NULL,
    '2026-04-13 10:59:00',
    '2026-04-13 10:59:00'
);

INSERT INTO nonces (
    nonce_id,
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
    '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
    'ethereum',
    'sepolia',
    'different-wallet',
    '2026-04-13 12:15:00',
    NULL,
    '2026-04-13 11:15:00',
    '2026-04-13 11:15:00'
);

INSERT INTO nonces (
    nonce_id,
    wallet_address,
    chain_type,
    network_name,
    nonce,
    expires_at,
    used_at,
    created_at,
    updated_at
) VALUES (
    6,
    '0x7d5e89df8eaf8872895865aef6de2d9373a159de',
    'ethereum',
    'sepolia',
    'available-latest',
    '2026-04-13 12:20:00',
    NULL,
    '2026-04-13 11:20:00',
    '2026-04-13 11:20:00'
);

INSERT INTO nonces (
    nonce_id,
    wallet_address,
    chain_type,
    network_name,
    nonce,
    expires_at,
    used_at,
    created_at,
    updated_at
) VALUES (
    7,
    '0x7d5e89df8eaf8872895865aef6de2d9373a159de',
    'ethereum',
    'sepolia',
    'store-available-latest',
    '2026-04-13 12:25:00',
    NULL,
    '2026-04-13 11:25:00',
    '2026-04-13 11:25:00'
);
