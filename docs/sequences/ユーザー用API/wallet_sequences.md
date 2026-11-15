# User API シーケンス図

この router では S3、SSM、SMS は使用しない。`permit` 更新時のみブロックチェーン RPC を使用する。

## ユーザーウォレット取得 API

```mermaid
sequenceDiagram
    autonumber
    actor Client as クライアント
    participant Server as APIサーバー
    box MySQL
        participant Users as users
        participant UserWallets as user_wallets
        participant Wallets as wallets
    end

    Client->>Server: GET /user/{user_id}/wallet
    Server->>UserWallets: ユーザーウォレット紐づけ検索<br/>user_id, deleted_at IS NULL
    UserWallets->>Users: ユーザー確認<br/>deleted_at IS NULL
    UserWallets->>Wallets: ウォレット取得<br/>deleted_at IS NULL
    Wallets-->>Server: ウォレット情報 / null
    Server-->>Client: ウォレット情報 / null
```

## ユーザーウォレット permit 情報取得 API

```mermaid
sequenceDiagram
    autonumber
    actor Client as クライアント
    participant Server as APIサーバー
    box MySQL
        participant Users as users
        participant UserWallets as user_wallets
        participant Wallets as wallets
    end

    Client->>Server: GET /user/{user_id}/wallet/permit
    Server->>UserWallets: ユーザーウォレット紐づけ検索
    UserWallets->>Users: ユーザー確認
    UserWallets->>Wallets: ウォレット取得
    Wallets-->>Server: ウォレット情報 / null

    alt ウォレットが存在しない
        Server-->>Client: 404 WALLET_NOT_FOUND_ERROR
    else ウォレットが存在する
        Server->>Server: chain_id から permit 設定取得
        Server-->>Client: wallet_address, chain_id,<br/>token_symbol, token_contract_address,<br/>spender_address
    end
```

## ユーザーウォレット permit 更新 API

```mermaid
sequenceDiagram
    autonumber
    actor Client as クライアント
    participant Server as APIサーバー
    participant Chain as ブロックチェーンRPC
    box MySQL
        participant Wallets as wallets
        participant WalletPermits as wallet_permits
    end

    Client->>Server: POST /user/{user_id}/wallet/{wallet_id}/permit<br/>allowance_value, signature_deadline, v, r, s
    Server->>Wallets: wallet_id でウォレット取得<br/>deleted_at IS NULL
    Wallets-->>Server: ウォレット情報 / 未存在

    alt ウォレットが存在しない
        Server-->>Client: 404 WALLET_NOT_FOUND_ERROR
    else ウォレットが存在する
        Server->>Server: chain_id から RPC / permit / processor 設定取得
        Server->>Chain: token / spender のコントラクト存在確認
        Chain-->>Server: code

        alt コントラクトが存在しない
            Server-->>Client: 400 WALLET_NOT_PERMITTED_ERROR
        else コントラクトが存在する
            Server->>Chain: permit トランザクション送信
            Chain-->>Server: transaction_hash
            Server->>Chain: receipt取得
            Chain-->>Server: receipt
            Server->>Chain: allowance確認
            Chain-->>Server: allowance

            alt permit または allowance 検証失敗
                Server-->>Client: 400 WALLET_NOT_PERMITTED_ERROR
            else 検証成功
                Server->>WalletPermits: permit情報登録
                WalletPermits-->>Server: 登録完了
                Server->>Wallets: is_permitted=True に更新
                Wallets-->>Server: 更新完了
                Server-->>Client: 更新完了
            end
        end
    end
```

## ユーザーウォレット nonce 発行 API

```mermaid
sequenceDiagram
    autonumber
    actor Client as クライアント
    participant Server as APIサーバー
    box MySQL
        participant Users as users
        participant Wallets as wallets
        participant Nonces as nonces
        participant UserNonces as user_nonces
    end

    Client->>Server: POST /user/{user_id}/wallet/nonce<br/>wallet_address, chain_type, network_name
    Server->>Users: ユーザー存在確認<br/>user_id, deleted_at IS NULL
    Users-->>Server: ユーザー情報 / 未存在

    alt ユーザーが存在しない
        Server-->>Client: 404 USER_NOT_FOUND_ERROR
    else ユーザーが存在する
        Server->>Wallets: ウォレットアドレス重複確認
        Wallets-->>Server: ウォレット情報 / 未存在

        alt ウォレットが既に登録済み
            Server-->>Client: 404 WALLET_IS_ALREADY_EXIST
        else 未登録
            Server->>Server: nonce生成<br/>expires_at = 現在時刻 + 10分
            Server->>Nonces: nonce登録
            Nonces-->>Server: nonce_id
            Server->>UserNonces: ユーザーとnonceの紐づけ登録
            UserNonces-->>Server: 登録完了
            Server-->>Client: nonce, expires_at
        end
    end
```

## ユーザーウォレット登録 API

```mermaid
sequenceDiagram
    autonumber
    actor Client as クライアント
    participant Server as APIサーバー
    box MySQL
        participant Users as users
        participant Wallets as wallets
        participant Nonces as nonces
        participant UserNonces as user_nonces
        participant UserWallets as user_wallets
    end

    Client->>Client: nonceに署名
    Client->>Server: POST /user/{user_id}/wallet<br/>wallet_address, signature, chain_type,<br/>network_name, token_symbol, chain_id
    Server->>Users: ユーザー存在確認
    Users-->>Server: ユーザー情報 / 未存在

    alt ユーザーが存在しない
        Server-->>Client: 404 USER_NOT_FOUND_ERROR
    else ユーザーが存在する
        Server->>UserNonces: ユーザーに紐づく最新nonce検索
        UserNonces->>Nonces: 利用可能nonce検索<br/>used_at IS NULL, expires_at >= 現在時刻
        Nonces-->>Server: nonce情報 / 未存在

        alt 有効な nonce がない
            Server-->>Client: 401 VERIFY_ERROR
        else 有効な nonce がある
            Server->>Server: nonce と signature から署名者アドレス復元

            alt 署名者アドレスが一致しない
                Server-->>Client: 401 VERIFY_ERROR
            else 署名検証成功
                Server->>UserWallets: ユーザーの既存ウォレット紐づけ確認
                UserWallets->>Wallets: 同一 chain_type / network_name / chain_id のウォレット確認
                Wallets-->>Server: 既存ウォレット / 未存在

                alt ユーザーに既存ウォレットあり
                    Server-->>Client: 409 WALLET_CONFLICT_ERROR
                else 登録可能
                    Server->>Wallets: ウォレット登録<br/>is_permitted=False
                    Wallets-->>Server: wallet_id
                    Server->>UserWallets: ユーザーとウォレットの紐づけ登録
                    UserWallets-->>Server: 登録完了
                    Server->>Nonces: nonce使用済み更新
                    Nonces-->>Server: 更新完了
                    Server->>UserNonces: ユーザーnonce紐づけ論理削除
                    UserNonces-->>Server: 更新完了
                    Server-->>Client: 登録済みウォレット情報
                end
            end
        end
    end
```

## ユーザーウォレット削除 API

```mermaid
sequenceDiagram
    autonumber
    actor Client as クライアント
    participant Server as APIサーバー
    box MySQL
        participant Wallets as wallets
        participant UserWallets as user_wallets
    end

    Client->>Server: DELETE /user/{user_id}/wallet/{wallet_id}
    Server->>Wallets: ウォレット論理削除<br/>wallet_id, deleted_at, updated_at
    Wallets-->>Server: 更新完了
    Server->>UserWallets: ユーザーウォレット紐づけ論理削除<br/>wallet_id, deleted_at, updated_at
    UserWallets-->>Server: 更新完了
    Server-->>Client: 削除完了
```
