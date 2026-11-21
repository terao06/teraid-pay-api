# 顔認証メニュー注文・決済シーケンス図

## 前提

- 既存の POST /payment/request/with/face をメニュー注文対応へ拡張する。
- リクエストは amount ではなく、商品、数量、オプション、idempotency_keyを受け取る。
- APIがDB上の商品価格とオプション追加料金から決済金額を計算する。
- メニュー情報はmenu_items、menu_option_groups、menu_optionsをJOINして一括取得する。
- 店舗・利用者のウォレット情報も、それぞれ関連テーブルをJOINして取得する。
- オンチェーンのpaymentIdはmenu_order_idを基に生成する。
- 決済送信後、画面は検証APIを決済終了まで繰り返し呼び出す。

## 顔認証メニュー注文・決済作成・実行 API

~~~mermaid
sequenceDiagram
    autonumber
    actor User as 利用者
    participant Client as 注文・顔認証画面
    participant API as APIサーバー
    participant SSM as AWS SSM Parameter Store
    participant S3 as S3
    participant ML as 顔特徴量抽出処理
    participant Chain as ブロックチェーンRPC

    box PostgreSQL
        participant FaceEmbeddings as face_embeddings
    end

    box MySQL
        participant Users as users
        participant Stores as stores
        participant MenuItems as menu_items
        participant OptionGroups as menu_option_groups
        participant Options as menu_options
        participant StoreWallets as store_wallets
        participant UserWallets as user_wallets
        participant Wallets as wallets
        participant Orders as menu_orders
        participant OrderItems as menu_order_items
        participant OrderItemOptions as menu_order_item_options
        participant Payments as payment_requests
    end

    User->>Client: 注文を確定して顔を撮影
    Client->>API: POST /payment/request/with/face<br/>store_id, items, content, idempotency_key

    API->>SSM: S3 endpoint・bucket・モデルキー取得
    SSM-->>API: パラメータ
    API->>S3: SCRFD・AdaFaceモデル取得
    S3-->>API: モデルデータ
    API->>ML: 顔画像から特徴量抽出
    ML-->>API: embedding
    API->>FaceEmbeddings: 類似顔検索<br/>threshold=0.7
    FaceEmbeddings-->>API: user_id / 未一致

    alt 顔が一致しない
        API-->>Client: 404 FACE_NOT_REGISTERED_ERROR
    else 顔が一致する
        API->>Users: ユーザー存在確認
        Users-->>API: ユーザー / 未存在

        alt ユーザーが存在しない
            API-->>Client: 404 USER_NOT_FOUND_ERROR
        else ユーザーが存在する
            API->>Orders: user_id・idempotency_keyで既存注文確認
            Orders-->>API: 既存注文 / 未存在

            alt 同じ注文が作成済み
                API-->>Client: 既存のmenu_order_idと決済状態
            else 新規注文
                API->>MenuItems: メニュー情報をJOIN検索<br/>商品ID・店舗ID・販売状態で絞り込み
                Note over MenuItems,Options: menu_items<br/>LEFT JOIN menu_option_groups<br/>LEFT JOIN menu_options
                MenuItems-->>API: 商品・基本価格・選択数ルール<br/>オプション・追加料金・販売状態
                API->>API: 商品・オプション検証<br/>明細金額・合計金額計算

                alt 商品またはオプションが無効
                    API-->>Client: 400 注文内容エラー
                else 注文内容が有効
                    API->>StoreWallets: 店舗ウォレットをJOIN検索<br/>store_idで絞り込み
                    Note right of StoreWallets: stores<br/>JOIN store_wallets<br/>JOIN wallets
                    StoreWallets-->>API: 店舗ウォレット / 未存在
                    API->>UserWallets: 利用者ウォレットをJOIN検索<br/>user_idで絞り込み
                    Note right of UserWallets: users<br/>JOIN user_wallets<br/>JOIN wallets
                    UserWallets-->>API: 利用者ウォレット / 未存在

                    alt ウォレットなし・不一致・permit未許可
                        API-->>Client: 404または400エラー
                    else 決済可能
                        critical 注文と決済リクエストを登録
                            API->>Orders: 注文登録<br/>status=1（PENDING_PAYMENT）
                            Orders-->>API: menu_order_id
                            API->>OrderItems: 商品明細・商品名・基本単価登録
                            API->>OrderItemOptions: 選択オプション・追加料金登録
                            API->>Payments: 決済リクエスト登録<br/>menu_order_id, amount, status=requested
                            Payments-->>API: payment_request_id
                            API->>Orders: status=2（PAYMENT_PROCESSING）
                        end

                        API->>Payments: REQUESTEDの決済リクエスト取得
                        Payments-->>API: 決済リクエスト
                        API->>API: menu_order_idからpaymentId生成
                        API->>Chain: 残高確認・PaymentProcessor.pay送信

                        alt 送信失敗
                            API->>Payments: status=error
                            API->>Orders: status=4（PAYMENT_FAILED）
                            API-->>Client: 決済失敗
                        else 送信成功
                            Chain-->>API: transaction_hash
                            API->>Payments: transaction_hash保存<br/>status=submitted
                            API-->>Client: menu_order_id, payment_request_id, transaction_hash
                        end
                    end
                end
            end
        end
    end
~~~

## 決済トランザクション検証 API

~~~mermaid
sequenceDiagram
    autonumber
    actor Client as 注文・顔認証画面
    participant API as APIサーバー
    participant Chain as ブロックチェーンRPC

    box MySQL
        participant Orders as menu_orders
        participant Payments as payment_requests
    end

    Client->>API: POST /payment/request/{payment_request_id}/verify
    API->>Payments: 決済リクエスト取得<br/>payment_request_id, deleted_at IS NULL
    Payments-->>API: 決済リクエスト / 未存在

    alt 決済リクエストまたはtransaction_hashが存在しない
        API-->>Client: 404 PAYMENT_ERROR
    else transaction_hashが存在する
        API->>Chain: transaction receipt取得
        Chain-->>API: receipt / 未確定 / 失敗

        alt receipt未取得
            API->>Payments: status=confirming
            API-->>Client: confirming
        else receipt.status == 0
            API->>Payments: status=tx_failed
            API->>Orders: status=4（PAYMENT_FAILED）
            API-->>Client: tx_failed（決済終了）
        else receipt.status == 1
            API->>Chain: PaymentProcessedイベント検証<br/>menu_order_id基準のpaymentId
            Chain-->>API: 検証結果

            alt イベント検証失敗
                API->>Payments: status=verify_failed
                API->>Orders: status=4（PAYMENT_FAILED）
                API-->>Client: verify_failed（決済終了）
            else イベント検証成功
                API->>Payments: status=paid
                API->>Orders: status=3（PAID）, paid_at設定
                API-->>Client: paid（決済終了）
            end
        end
    end
~~~

## 未確認事項

- itemsの正式なリクエスト形式
- 決済失敗後の再決済APIと状態遷移

