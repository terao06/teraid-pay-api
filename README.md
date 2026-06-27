# teraid-pay-api

Teraid Pay の決済 API です。FastAPI、MySQL、AWS Secrets Manager 互換の LocalStack、Ethereum 系ウォレット署名検証、JPYC 決済用コントラクト連携を扱います。

この API は、ユーザーと店舗のウォレット登録、署名用 nonce の発行、JPYC approve 状態の管理、決済リクエスト作成、PaymentProcessor コントラクト経由の決済実行を提供します。

## 主な機能

- FastAPI による REST API
- ユーザーウォレットと店舗ウォレットの管理
- ウォレット署名用 nonce の発行と署名検証
- JPYC approve に必要なコントラクト情報の返却
- 決済リクエストの作成、実行、トランザクション検証
- MySQL による永続化
- LocalStack Secrets Manager を使ったローカル Secret 管理
- Docker Compose によるローカル開発環境
- pytest によるユニットテスト

## 技術スタック

- Python 3.10
- FastAPI
- Uvicorn
- SQLAlchemy
- PyMySQL
- boto3
- eth-account
- web3.py
- MySQL
- LocalStack
- Docker / Docker Compose

## ディレクトリ構成

```text
app/
  core/             # 設定、DB、AWS、例外、ユーティリティ
  controllers/      # エンドポイントから呼ばれるアプリケーション制御
  endpoints/        # FastAPI ルーター
  middlewares/      # リクエスト、レスポンス、トランザクションのラッパー
  models/           # リクエスト、レスポンス、MySQL モデル
  repositories/     # DB アクセス層
  services/         # ビジネスロジック
contract_deploy/    # PaymentProcessor コントラクトのデプロイ
docs/               # Swagger YAML
docker/             # ローカル API Dockerfile
local_setting/      # ローカル MySQL 設定
tests/              # pytest
```

## 前提条件

- Docker Desktop
- Docker Compose
- Python 3.10 以上

ローカルを Docker Compose で起動する場合、Python は主にテストや Secret 登録スクリプトの実行で使います。

## セットアップ

リポジトリを取得します。

```powershell
git clone https://github.com/terao06/teraid-pay-api.git
cd teraid-pay-api
```

ローカル環境を起動します。

```powershell
docker compose up -d --build
```

API は以下で起動します。

```text
http://localhost:8005
```

FastAPI の自動生成ドキュメントは以下です。

```text
http://localhost:8005/docs
```

phpMyAdmin は以下で確認できます。

```text
http://localhost:8014
```

## ローカルシークレット

API は MySQL 接続情報やコントラクト情報を Secrets Manager から取得します。ローカルでは LocalStack の Secrets Manager を使います。

サンプルをコピーして、必要に応じて値を編集します。まず API を起動してウォレット登録系の動作確認だけを行う場合は、サンプル値のままでも構いません。ただし、JPYC の approve 情報取得や決済実行まで動かす場合は、コントラクトデプロイ後の値に差し替える必要があります。

```powershell
copy tests\unit\test_data\secret\secret.sample.json tests\unit\test_data\secret\secret.json
```

Secret の主な項目は以下です。

```json
{
  "mysql_database": "db_local",
  "mysql_user": "teraid_pay_admin_user",
  "mysql_password": "password",
  "mysql_host": "teraid-pay-api-db",
  "mysql_port": 3306,
  "chain_11155111_rpc_url": "https://sepolia.infura.io/v3/your-infura-api-key",
  "chain_11155111_jpyc_token_address": "0x...",
  "chain_11155111_payment_processor_address": "0x...",
  "chain_11155111_payment_operator_private_key": "0x..."
}
```

各項目の意味は以下です。

| 項目 | 設定する値 | いつ必要か |
| --- | --- | --- |
| `mysql_database` | MySQL のデータベース名。ローカル Docker Compose では `db_local` | API 起動時 |
| `mysql_user` | MySQL のユーザー名。ローカル Docker Compose では `teraid_pay_admin_user` | API 起動時 |
| `mysql_password` | MySQL のパスワード。ローカル Docker Compose では `password` | API 起動時 |
| `mysql_host` | MySQL のホスト名。API コンテナから接続するため、ローカル Docker Compose では `teraid-pay-api-db` | API 起動時 |
| `mysql_port` | MySQL のポート。API コンテナからは `3306` | API 起動時 |
| `chain_11155111_rpc_url` | 対象チェーンの RPC URL。Sepolia で Infura を使う場合は API key を含めた `https://sepolia.infura.io/v3/{api_key}` | approve 情報取得、決済実行、トランザクション検証 |
| `chain_11155111_jpyc_token_address` | 対象チェーン上の JPYC トークンコントラクトアドレス。`contract_deploy/.env` の `JPYC_TOKEN_ADDRESS` と同じ値、またはデプロイ結果 `deployment.json` の `token` | approve 情報取得、決済実行 |
| `chain_11155111_payment_processor_address` | デプロイ済み `PaymentProcessor` のコントラクトアドレス。`contract_deploy/build/deployment.json` の `payment_processor` | approve 情報取得、決済実行 |
| `chain_11155111_payment_operator_private_key` | `PaymentProcessor` の operator として登録したウォレットの秘密鍵。`contract_deploy/.env` の `PAYMENT_OPERATOR_ADDRESS` に対応する秘密鍵 | 決済実行 |

`chain_11155111_...` の `11155111` は Sepolia の chain ID です。他のチェーンを使う場合は、実装側が参照する chain ID に合わせてキー名と値を用意してください。

### コントラクトデプロイ後に差し替える値

JPYC 決済まで動かす場合は、先に `PaymentProcessor` をデプロイします。手順は [contract_deploy/README.md](contract_deploy/README.md) を参照してください。

デプロイ時の `.env` には最低限以下を設定します。

```text
RPC_URL=https://sepolia.infura.io/v3/YOUR_PROJECT_ID
DEPLOYER_PRIVATE_KEY=0xデプロイ用ウォレット秘密鍵
JPYC_TOKEN_ADDRESS=0x対象チェーン上のJPYCトークンアドレス
PAYMENT_OPERATOR_ADDRESS=0x決済実行用operatorウォレットアドレス
```

`PAYMENT_OPERATOR_ADDRESS` を省略した場合は、デプロイ用ウォレットが operator になります。その場合、API 側の `chain_11155111_payment_operator_private_key` には `DEPLOYER_PRIVATE_KEY` と同じ秘密鍵を設定します。運用上は、デプロイ用ウォレットと operator ウォレットは分けることを推奨します。

デプロイに成功すると、`contract_deploy/build/deployment.json` に以下のような結果が保存されます。

```json
{
  "network_chain_id": 11155111,
  "deployer": "0x...",
  "owner": "0x...",
  "operator": "0x...",
  "token": "0x...",
  "payment_processor": "0x...",
  "transaction_hash": "0x...",
  "block_number": 123456
}
```

この結果を `tests\unit\test_data\secret\secret.json` に反映します。

```json
{
  "chain_11155111_rpc_url": "https://sepolia.infura.io/v3/YOUR_PROJECT_ID",
  "chain_11155111_jpyc_token_address": "deployment.json の token",
  "chain_11155111_payment_processor_address": "deployment.json の payment_processor",
  "chain_11155111_payment_operator_private_key": "deployment.json の operator に対応する秘密鍵"
}
```

注意点:

- `payment_processor` は JPYC の `approve` 先です。フロントエンドでも同じアドレスを使います。
- `token` は `PaymentProcessor` デプロイ時に指定した JPYC トークンアドレスです。
- `operator` は公開アドレスです。Secret に入れるのは、その operator アドレスに対応する秘密鍵です。
- 秘密鍵や実際の API key はコミットしないでください。

LocalStack に Secret を登録します。

```powershell
python tests\unit\test_data\secret\insert_secret.py
```

`secret.json` を編集したあとは、この登録コマンドを再実行してください。既存の `secret` がある場合は更新されます。

Docker Compose 内の API コンテナからは、`SECRETS_MANAGER_ENDPOINT=http://localstack:4566` が使われます。ホスト側からスクリプトを実行する場合は、既定値として `http://localhost:4566` が使われます。

初回に決済実行まで確認する場合の流れは以下です。

1. `docker compose up -d --build` で MySQL と LocalStack を起動する
2. `contract_deploy/.env` を作成し、RPC、JPYC トークン、デプロイ用秘密鍵、operator アドレスを設定する
3. `cd contract_deploy` して `python deploy.py` を実行する
4. `contract_deploy/build/deployment.json` の `token` と `payment_processor` を `secret.json` に反映する
5. `operator` に対応する秘密鍵を `chain_11155111_payment_operator_private_key` に設定する
6. リポジトリルートに戻り、`python tests\unit\test_data\secret\insert_secret.py` で LocalStack に登録する
7. API の `/docs` またはフロントエンドからウォレット登録、approve、決済作成、決済実行を確認する

## 起動

Docker Compose で起動済みの場合、API は `http://localhost:8005` で待ち受けます。

手元の Python 環境で直接起動する場合は、依存関係をインストールして Uvicorn を起動します。

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8005 --reload
```

## API 概要

すべての成功レスポンスは基本的に以下の共通形式で返ります。

```json
{
  "status": "success",
  "data": {}
}
```

### ユーザー

| メソッド | パス | 説明 |
| --- | --- | --- |
| GET | `/user/{user_id}/wallet` | ユーザーのウォレット情報を取得 |
| GET | `/user/{user_id}/wallet/approval` | JPYC approve に必要な情報を取得 |
| POST | `/user/{user_id}/wallet/{wallet_id}/approval` | ユーザーウォレットの approve 状態を更新 |
| POST | `/user/{user_id}/wallet/nonce` | ウォレット署名用 nonce を作成 |
| POST | `/user/{user_id}/wallet` | 署名検証後にウォレットを作成 |
| DELETE | `/user/{user_id}/wallet/{wallet_id}` | ユーザーウォレットを削除 |

### 店舗

| メソッド | パス | 説明 |
| --- | --- | --- |
| GET | `/store/{store_id}/wallet` | 店舗のウォレット情報を取得 |
| POST | `/store/{store_id}/wallet/nonce` | ウォレット署名用 nonce を作成 |
| POST | `/store/{store_id}/wallet` | 署名検証後にウォレットを作成 |
| DELETE | `/store/{store_id}/wallet/{wallet_id}` | 店舗ウォレットを削除 |

### 決済

| メソッド | パス | 説明 |
| --- | --- | --- |
| POST | `/payment/request` | 決済リクエストを作成し、決済を実行 |
| POST | `/payment/request/{payment_request_id}/verify` | トランザクションを検証 |

## リクエスト例

ウォレット署名用 nonce を作成します。

```http
POST /user/1/wallet/nonce
Content-Type: application/json

{
  "wallet_address": "0x0000000000000000000000000000000000000000",
  "chain_type": "ethereum",
  "network_name": "sepolia"
}
```

署名を検証してウォレットを登録します。

```http
POST /user/1/wallet
Content-Type: application/json

{
  "wallet_address": "0x0000000000000000000000000000000000000000",
  "signature": "0x...",
  "chain_type": "ethereum",
  "network_name": "sepolia",
  "token_symbol": "JPYC",
  "chain_id": 11155111
}
```

決済リクエストを作成し、PaymentProcessor コントラクト経由で決済を実行します。レスポンスには `payment_request_id` と `transaction_hash` が返ります。

```http
POST /payment/request
Content-Type: application/json

{
  "store_id": 1,
  "user_id": 1,
  "amount": 1000
}
```

## PaymentProcessor コントラクト

JPYC 決済では `PaymentProcessor` コントラクトを使用します。コントラクトのデプロイ手順は [contract_deploy/README.md](contract_deploy/README.md) を参照してください。

基本的な決済フローは以下です。

1. ユーザーが JPYC コントラクトに対して `approve(PaymentProcessor, amount)` を実行する
2. バックエンドの operator が `pay(paymentId, token, from, to, amount)` を呼び出す
3. `PaymentProcessor` が `JPYC.transferFrom(from, to, amount)` を実行する
4. `PaymentProcessed` イベントが発火する

デプロイ済みの `PaymentProcessor` アドレス、JPYC トークンアドレス、operator 秘密鍵は Secret Manager で管理します。ローカルで決済実行まで確認する場合は、`ローカルシークレット` セクションの手順に従って `secret.json` を更新してください。

## テスト

依存関係をインストールします。

```powershell
pip install -r requirements.txt
pip install pytest
```

テストを実行します。

```powershell
pytest
```
