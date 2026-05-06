# Teraid Pay コントラクトデプロイ

`PaymentProcessor` コントラクトを Python でコンパイル、デプロイするためのディレクトリです。

## 役割

`PaymentProcessor` は、JPYC の `approve` 先になる決済用コントラクトです。

決済フローは以下です。

1. ユーザーが JPYC コントラクトに対して `approve(PaymentProcessor, amount)` を実行する
2. バックエンドの operator が `pay(paymentId, token, from, to, amount)` を呼び出す
3. `PaymentProcessor` が `JPYC.transferFrom(from, to, amount)` を実行する
4. `PaymentProcessed` イベントが発火する

## セットアップ

```powershell
cd contract_deploy
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

`.env` に以下を設定します。

```text
RPC_URL=対象チェーンのRPC URL
DEPLOYER_PRIVATE_KEY=デプロイに使うウォレットの秘密鍵
JPYC_TOKEN_ADDRESS=対象チェーン上のJPYCトークンアドレス
```

必要に応じて以下も設定します。未設定の場合はデプロイアカウントが使われます。

```text
CONTRACT_OWNER_ADDRESS=コントラクト管理者アドレス
PAYMENT_OPERATOR_ADDRESS=決済実行を許可するoperatorアドレス
```

## デプロイ

```powershell
python deploy.py
```

デプロイに成功すると、結果がコンソールに表示され、`build/deployment.json` に保存されます。

重要なのは以下の値です。

```text
payment_processor
```

この値がデプロイ済み `PaymentProcessor` のコントラクトアドレスです。API とフロントでは、このアドレスを JPYC の `approve` 先として使用します。

## 注意点

- `DEPLOYER_PRIVATE_KEY` はコミットしないでください。
- `.env` は `.gitignore` の対象です。
- `approve` はコントラクトアドレス単位で行われるため、デプロイ後の `payment_processor` アドレスは環境変数または Secret Manager で管理してください。
- アプリ起動時に毎回デプロイする運用にはしません。環境ごとに一度デプロイし、そのアドレスを使い回します。
