# メニュー管理・購入履歴 DB 設計

## 1. テーブル名

| 区分 | テーブル名 |
| --- | --- |
| 追加 | store_managers |
| 追加 | devices |
| 追加 | visit_sessions |
| 追加 | menu_categories |
| 追加 | menu_items |
| 追加 | menu_option_groups |
| 追加 | menu_options |
| 追加 | menu_orders |
| 追加 | menu_order_items |
| 追加 | menu_order_item_options |
| 変更 | payment_requests |

## 2. テーブルの用途

| テーブル名 | 用途 |
| --- | --- |
| store_managers | 店舗管理画面を利用する管理者の所属店舗、メールアドレス、利用可否を管理する。 |
| devices | 店舗に常設するAndroid端末の登録、有効化、認証情報、利用可否を管理する。 |
| visit_sessions | 端末で注文を始めてから会計を終えるまでの来店単位を管理し、注文と追加注文をまとめる。 |
| menu_categories | 店舗ごとのメニューカテゴリ、カテゴリー画像の拡張子、表示可否を管理する。 |
| menu_items | 商品名、基本価格、画像、販売可否を管理する。 |
| menu_option_groups | サイズやトッピングなど、商品ごとの選択グループを管理する。 |
| menu_options | 選択可能なオプションと追加料金を管理する。 |
| menu_orders | 1回の注文について、購入者、店舗、合計金額、決済状態、提供完了日時を管理する。 |
| menu_order_items | 注文した商品と購入時点の商品名・基本単価を管理する。 |
| menu_order_item_options | 注文時に選択したオプションと購入時点の追加料金を管理する。 |
| payment_requests | menu_order_idを追加し、注文に対する決済試行を管理する。 |

## 3. テーブル定義

### 3.1 store_managers

| カラム | 型 | NULL | デフォルト | キー | 説明 |
| --- | --- | --- | --- | --- | --- |
| store_manager_id | BIGINT | NO | AUTO_INCREMENT | PK | 店舗管理者ID |
| store_id | BIGINT | NO | - | FK → stores.store_id | 所属店舗ID |
| name | VARCHAR(255) | NO | - | - | 管理者名 |
| email | VARCHAR(255) | NO | - | UK | ログイン・連絡用メールアドレス |
| password_hash | VARCHAR(255) | NO | - | - | パスワードハッシュ。平文は保存しない |
| roll_id | BIGINT | NO | - | - | 店舗管理者の権限ロールID |
| is_active | BOOLEAN | NO | TRUE | - | 利用可能フラグ |
| created_at | DATETIME | NO | CURRENT_TIMESTAMP | - | 作成日時 |
| updated_at | DATETIME | NO | CURRENT_TIMESTAMP | - | 更新日時 |
| deleted_at | DATETIME | YES | NULL | - | 論理削除日時 |

### 3.2 menu_categories

| カラム | 型 | NULL | デフォルト | キー | 説明 |
| --- | --- | --- | --- | --- | --- |
| menu_category_id | BIGINT | NO | AUTO_INCREMENT | PK | カテゴリID |
| store_id | BIGINT | NO | - | FK → stores.store_id | 店舗ID |
| name | VARCHAR(100) | NO | - | - | カテゴリ名 |
| image_extension | VARCHAR(10) | NO | - | - | カテゴリー画像の拡張子 |
| display_order | INT UNSIGNED | NO | 0 | - | 表示順 |
| is_active | BOOLEAN | NO | TRUE | - | 有効フラグ |
| created_at | DATETIME | NO | CURRENT_TIMESTAMP | - | 作成日時 |
| updated_at | DATETIME | NO | CURRENT_TIMESTAMP | - | 更新日時 |
| deleted_at | DATETIME | YES | NULL | - | 論理削除日時 |

カテゴリー画像本体はS3の `category_image_bucket` に保存し、オブジェクトキーは `{store_id}/{menu_category_id}.{image_extension}` とする。DBには画像本体および署名付きURLを保存しない。

### 3.3 menu_items

| カラム | 型 | NULL | デフォルト | キー | 説明 |
| --- | --- | --- | --- | --- | --- |
| menu_item_id | BIGINT | NO | AUTO_INCREMENT | PK | 商品ID |
| store_id | BIGINT | NO | - | FK → stores.store_id | 店舗ID |
| menu_category_id | BIGINT | YES | NULL | FK → menu_categories.menu_category_id | カテゴリID |
| name | VARCHAR(255) | NO | - | - | 商品名 |
| description | TEXT | YES | NULL | - | 商品説明 |
| price | DECIMAL(20, 6) | NO | - | - | 基本価格 |
| token_symbol | VARCHAR(20) | NO | JPYC | - | トークンシンボル |
| image_extension | VARCHAR(10) | NO | - | - | 商品画像の拡張子 |
| is_available | BOOLEAN | NO | TRUE | - | 販売可能フラグ |
| display_order | INT UNSIGNED | NO | 0 | - | 表示順 |
| created_at | DATETIME | NO | CURRENT_TIMESTAMP | - | 作成日時 |
| updated_at | DATETIME | NO | CURRENT_TIMESTAMP | - | 更新日時 |
| deleted_at | DATETIME | YES | NULL | - | 論理削除日時 |

### 3.4 menu_option_groups

| カラム | 型 | NULL | デフォルト | キー | 説明 |
| --- | --- | --- | --- | --- | --- |
| menu_option_group_id | BIGINT | NO | AUTO_INCREMENT | PK | オプショングループID |
| menu_item_id | BIGINT | NO | - | FK → menu_items.menu_item_id | 対象商品ID |
| name | VARCHAR(100) | NO | - | - | サイズ、トッピングなどのグループ名 |
| min_selections | INT UNSIGNED | NO | 0 | - | 最小選択数 |
| max_selections | INT UNSIGNED | NO | 1 | - | 最大選択数 |
| display_order | INT UNSIGNED | NO | 0 | - | 表示順 |
| is_active | BOOLEAN | NO | TRUE | - | 有効フラグ |
| created_at | DATETIME | NO | CURRENT_TIMESTAMP | - | 作成日時 |
| updated_at | DATETIME | NO | CURRENT_TIMESTAMP | - | 更新日時 |
| deleted_at | DATETIME | YES | NULL | - | 論理削除日時 |

制約: min_selections <= max_selections、max_selections > 0

### 3.5 menu_options

| カラム | 型 | NULL | デフォルト | キー | 説明 |
| --- | --- | --- | --- | --- | --- |
| menu_option_id | BIGINT | NO | AUTO_INCREMENT | PK | オプションID |
| menu_option_group_id | BIGINT | NO | - | FK → menu_option_groups.menu_option_group_id | グループID |
| name | VARCHAR(100) | NO | - | - | 大盛り、チーズなどのオプション名 |
| additional_price | DECIMAL(20, 6) | NO | 0 | - | 追加料金 |
| display_order | INT UNSIGNED | NO | 0 | - | 表示順 |
| is_available | BOOLEAN | NO | TRUE | - | 選択可能フラグ |
| created_at | DATETIME | NO | CURRENT_TIMESTAMP | - | 作成日時 |
| updated_at | DATETIME | NO | CURRENT_TIMESTAMP | - | 更新日時 |
| deleted_at | DATETIME | YES | NULL | - | 論理削除日時 |

制約: additional_price >= 0

### 3.6 menu_orders

| カラム | 型 | NULL | デフォルト | キー | 説明 |
| --- | --- | --- | --- | --- | --- |
| menu_order_id | BIGINT | NO | AUTO_INCREMENT | PK | 注文ID |
| idempotency_key | VARCHAR(64) | NO | - | UK | 二重注文防止キー |
| visit_session_id | BIGINT | YES | NULL | FK → visit_sessions.visit_session_id | 店内端末での来店セッションID。端末注文の場合は設定する |
| store_id | BIGINT | NO | - | FK → stores.store_id | 店舗ID |
| user_id | BIGINT | YES | NULL | FK → users.user_id | 購入者ID。購入者未特定の端末注文は `NULL` |
| total_amount | DECIMAL(20, 6) | NO | - | - | 注文合計金額 |
| token_symbol | VARCHAR(20) | NO | JPYC | - | トークンシンボル |
| status | TINYINT UNSIGNED | NO | 1 | - | オーダー状態。`OrderStatus` の整数コードを保存 |
| paid_at | DATETIME | YES | NULL | - | 決済完了日時 |
| served_at | DATETIME | YES | NULL | - | 提供完了日時（UTC）。`NULL` は未提供 |
| created_at | DATETIME | NO | UTC_TIMESTAMP() | - | 注文受付日時（UTC） |
| updated_at | DATETIME | NO | UTC_TIMESTAMP() | - | 更新日時（UTC） |
| deleted_at | DATETIME | YES | NULL | - | 論理削除日時 |

`OrderStatus` は Python の `IntEnum` とし、以下の固定コードを DB と API で使う。

| コード | `OrderStatus` | 意味 |
| --- | --- | --- |
| `1` | `PENDING_PAYMENT` | 支払い待ち |
| `2` | `PAYMENT_PROCESSING` | 決済処理中 |
| `3` | `PAID` | 支払済み |
| `4` | `PAYMENT_FAILED` | 決済失敗 |
| `5` | `CANCELED` | キャンセル |

`status` の有効値は `1`〜`5` とする。状態を追加するときは新しいコードを割り当てる。

### 3.7 menu_order_items

| カラム | 型 | NULL | デフォルト | キー | 説明 |
| --- | --- | --- | --- | --- | --- |
| menu_order_item_id | BIGINT | NO | AUTO_INCREMENT | PK | 注文明細ID |
| menu_order_id | BIGINT | NO | - | FK → menu_orders.menu_order_id | 注文ID |
| menu_item_id | BIGINT | NO | - | FK → menu_items.menu_item_id | 商品ID |
| menu_item_name | VARCHAR(255) | NO | - | - | 購入時点の商品名 |
| unit_price | DECIMAL(20, 6) | NO | - | - | 購入時点の商品基本単価 |
| quantity | INT UNSIGNED | NO | - | - | 数量 |
| line_amount | DECIMAL(20, 6) | NO | - | - | オプション料金を含む明細金額 |
| display_order | INT UNSIGNED | NO | 0 | - | 表示順 |
| created_at | DATETIME | NO | UTC_TIMESTAMP() | - | 作成日時（UTC） |

### 3.8 menu_order_item_options

| カラム | 型 | NULL | デフォルト | キー | 説明 |
| --- | --- | --- | --- | --- | --- |
| menu_order_item_option_id | BIGINT | NO | AUTO_INCREMENT | PK | 注文オプション明細ID |
| menu_order_item_id | BIGINT | NO | - | FK → menu_order_items.menu_order_item_id | 注文明細ID |
| menu_option_id | BIGINT | NO | - | FK → menu_options.menu_option_id | 選択元オプションID |
| option_group_name | VARCHAR(100) | NO | - | - | 購入時点のグループ名 |
| option_name | VARCHAR(100) | NO | - | - | 購入時点のオプション名 |
| additional_price | DECIMAL(20, 6) | NO | 0 | - | 購入時点の追加料金 |
| option_quantity | INT UNSIGNED | NO | 1 | - | 商品1個当たりのオプション数量 |
| display_order | INT UNSIGNED | NO | 0 | - | 表示順 |
| created_at | DATETIME | NO | UTC_TIMESTAMP() | - | 作成日時（UTC） |

### 3.9 payment_requestsへの追加カラム

| カラム | 型 | NULL | デフォルト | キー | 説明 |
| --- | --- | --- | --- | --- | --- |
| menu_order_id | BIGINT | YES | NULL | FK → menu_orders.menu_order_id | 関連する注文ID。既存の自由金額決済ではNULL |

### 3.10 devices

| カラム | 型 | NULL | デフォルト | キー | 説明 |
| --- | --- | --- | --- | --- | --- |
| device_id | BIGINT | NO | AUTO_INCREMENT | PK | デバイスID |
| store_id | BIGINT | NO | - | FK → stores.store_id | 設置店舗ID |
| device_name | VARCHAR(100) | NO | - | - | 店舗管理者が設定するデバイス名 |
| device_uuid | VARCHAR(36) | NO | - | UK | デバイス登録時に発行するUUID |
| activation_code_hash | VARCHAR(64) | YES | NULL | UK | 初回有効化コードのSHA-256ハッシュ値 |
| activation_expires_at | DATETIME | YES | NULL | - | 有効化コードの有効期限 |
| device_credential_hash | VARCHAR(255) | YES | NULL | - | 有効化後の長期端末認証情報のハッシュ値 |
| activated_at | DATETIME | YES | NULL | - | 初回有効化日時 |
| last_authenticated_at | DATETIME | YES | NULL | - | 最終認証日時 |
| is_active | BOOLEAN | NO | FALSE | - | 利用可能フラグ。初回有効化後にTRUE |
| created_at | DATETIME | NO | CURRENT_TIMESTAMP | - | 作成日時 |
| updated_at | DATETIME | NO | CURRENT_TIMESTAMP | - | 更新日時 |
| deleted_at | DATETIME | YES | NULL | - | 論理削除日時 |

有効化成功後は `activation_code_hash` と `activation_expires_at` をNULLに更新する。有効化コードと端末認証情報の平文はDBに保存しない。

### 3.11 visit_sessions

| カラム | 型 | NULL | デフォルト | キー | 説明 |
| --- | --- | --- | --- | --- | --- |
| visit_session_id | BIGINT | NO | AUTO_INCREMENT | PK | 来店セッションID |
| device_id | BIGINT | NO | - | FK → devices.device_id | 注文を受け付ける端末ID |
| start_request_id | VARCHAR(64) | NO | - | - | 注文開始要求の再送を識別するID |
| status | ENUM | NO | active | - | active（注文受付中）、checkout_processing（決済処理中）、closed（終了済み） |
| started_at | DATETIME | NO | CURRENT_TIMESTAMP | - | セッション開始日時 |
| ended_at | DATETIME | YES | NULL | - | セッション終了日時 |

- 同じ端末からの開始要求を識別するため、`(device_id, start_request_id)` を一意とする。
- 端末1台につき、`active` または `checkout_processing` のセッションは合計1件までとする。終了済みのセッションは履歴として保持する。

## 4. ER図

~~~mermaid
erDiagram
    STORES ||--o{ STORE_MANAGERS : employs
    STORES ||--o{ DEVICES : has
    DEVICES ||--o{ VISIT_SESSIONS : hosts
    STORES ||--o{ MENU_CATEGORIES : has
    STORES ||--o{ MENU_ITEMS : offers
    MENU_CATEGORIES o|--o{ MENU_ITEMS : classifies

    MENU_ITEMS ||--o{ MENU_OPTION_GROUPS : has
    MENU_OPTION_GROUPS ||--o{ MENU_OPTIONS : contains

    STORES ||--o{ MENU_ORDERS : receives
    USERS ||--o{ MENU_ORDERS : places
    VISIT_SESSIONS o|--o{ MENU_ORDERS : groups
    MENU_ORDERS ||--|{ MENU_ORDER_ITEMS : contains
    MENU_ITEMS ||--o{ MENU_ORDER_ITEMS : snapshot_of

    MENU_ORDER_ITEMS ||--o{ MENU_ORDER_ITEM_OPTIONS : selected
    MENU_OPTIONS ||--o{ MENU_ORDER_ITEM_OPTIONS : snapshot_of

    STORES ||--o{ PAYMENT_REQUESTS : receives
    USERS ||--o{ PAYMENT_REQUESTS : pays
    MENU_ORDERS o|--o{ PAYMENT_REQUESTS : attempts

    STORES {
        bigint store_id PK
    }

    STORE_MANAGERS {
        bigint store_manager_id PK
        bigint store_id FK
        varchar name
        varchar email UK
        varchar password_hash
        bigint roll_id
        boolean is_active
        datetime deleted_at
    }

    DEVICES {
        bigint device_id PK
        bigint store_id FK
        varchar device_name
        varchar device_uuid UK
        varchar activation_code_hash UK
        datetime activation_expires_at
        varchar device_credential_hash
        datetime activated_at
        datetime last_authenticated_at
        boolean is_active
        datetime deleted_at
    }

    VISIT_SESSIONS {
        bigint visit_session_id PK
        bigint device_id FK
        varchar start_request_id
        enum status
        datetime started_at
        datetime ended_at
    }

    USERS {
        bigint user_id PK
    }

    MENU_CATEGORIES {
        bigint menu_category_id PK
        bigint store_id FK
        varchar name
        varchar image_extension
        int display_order
        boolean is_active
    }

    MENU_ITEMS {
        bigint menu_item_id PK
        bigint store_id FK
        bigint menu_category_id FK
        varchar name
        decimal price
        varchar token_symbol
        varchar image_extension
        boolean is_available
    }

    MENU_OPTION_GROUPS {
        bigint menu_option_group_id PK
        bigint menu_item_id FK
        varchar name
        int min_selections
        int max_selections
        boolean is_active
    }

    MENU_OPTIONS {
        bigint menu_option_id PK
        bigint menu_option_group_id FK
        varchar name
        decimal additional_price
        boolean is_available
    }

    MENU_ORDERS {
        bigint menu_order_id PK
        varchar idempotency_key UK
        bigint visit_session_id FK
        bigint store_id FK
        bigint user_id FK
        decimal total_amount
        varchar token_symbol
        tinyint status
        datetime paid_at
        datetime served_at
    }

    MENU_ORDER_ITEMS {
        bigint menu_order_item_id PK
        bigint menu_order_id FK
        bigint menu_item_id FK
        varchar menu_item_name
        decimal unit_price
        int quantity
        decimal line_amount
    }

    MENU_ORDER_ITEM_OPTIONS {
        bigint menu_order_item_option_id PK
        bigint menu_order_item_id FK
        bigint menu_option_id FK
        varchar option_group_name
        varchar option_name
        decimal additional_price
        int option_quantity
    }

    PAYMENT_REQUESTS {
        bigint payment_request_id PK
        bigint menu_order_id FK
        bigint store_id FK
        bigint user_id FK
        decimal amount
        varchar token_symbol
        enum status
    }
~~~
