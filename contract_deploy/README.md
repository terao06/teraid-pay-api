# Teraid Pay コントラクトデプロイ

`PaymentProcessor` コントラクトを Python でコンパイル、デプロイするためのディレクトリです。

## 役割

`PaymentProcessor` は、JPYC の `approve` 先になる決済用コントラクトです。

決済フローは以下です。

1. ユーザーが JPYC コントラクトに対して `approve(PaymentProcessor, amount)` を実行する
2. バックエンドの operator が `pay(paymentId, token, from, to, amount)` を呼び出す
3. `PaymentProcessor` が `JPYC.transferFrom(from, to, amount)` を実行する
4. `PaymentProcessed` イベントが発火する

## 対象ネットワーク

このディレクトリでは、以下のテストネットへのデプロイを想定しています。

| ネットワーク | chain ID | ガス代に使う通貨 | env ファイル例 |
| --- | ---: | --- | --- |
| Avalanche Fuji C-Chain | `43113` | Fuji testnet AVAX | `.env.avalanche` |
| Ethereum Sepolia | `11155111` | Sepolia testnet ETH | `.env.sepolia` |
| Polygon Amoy | `80002` | Amoy testnet POL | `.env.polygon` |

どのネットワークでも、デプロイ用ウォレットにテスト用のガス代が必要です。ガス代がない状態で `python deploy.py` を実行すると、トランザクションを送信できません。

## セットアップ

```powershell
cd contract_deploy
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## 共通パラメータ

各ネットワークの env ファイルには、以下の値を設定します。

| 変数名 | どこから取得するか | 設定する値 |
| --- | --- | --- |
| `RPC_URL` | RPC プロバイダー、または各チェーンの公開 RPC | 対象チェーンの HTTPS RPC URL |
| `DEPLOYER_PRIVATE_KEY` | MetaMask などのウォレットアプリ | デプロイ用ウォレットの秘密鍵 |
| `JPYC_TOKEN_ADDRESS` | JPYC 公式ドキュメント、公式案内、または対象チェーンのブロックエクスプローラー | 対象チェーン上の JPYC トークンコントラクトアドレス |
| `CONTRACT_OWNER_ADDRESS` | MetaMask などのウォレットアプリ | コントラクト管理者にしたいウォレットアドレス |
| `PAYMENT_OPERATOR_ADDRESS` | MetaMask などのウォレットアプリ | API から決済トランザクションを実行する operator ウォレットアドレス |

`CONTRACT_OWNER_ADDRESS` と `PAYMENT_OPERATOR_ADDRESS` は任意です。未設定の場合は、`DEPLOYER_PRIVATE_KEY` に対応するデプロイ用ウォレットのアドレスが使われます。

`PAYMENT_OPERATOR_ADDRESS` をデプロイ用ウォレットと別にした場合は、API 側の Secret Manager またはローカルシークレットに、この operator アドレスに対応する秘密鍵を設定してください。

## Avalanche Fuji 用 `.env.avalanche`

Avalanche Fuji C-Chain にデプロイする場合は、`.env.avalanche` を作成します。

```powershell
copy .env.example .env.avalanche
```

`.env.avalanche` の例です。

```text
RPC_URL=https://api.avax-test.network/ext/bc/C/rpc
DEPLOYER_PRIVATE_KEY=0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
JPYC_TOKEN_ADDRESS=0xAvalancheFuji上のJPYCトークンアドレス
CONTRACT_OWNER_ADDRESS=0x管理者ウォレットアドレス
PAYMENT_OPERATOR_ADDRESS=0xoperatorウォレットアドレス
GAS_MULTIPLIER=1.2
MAX_PRIORITY_FEE_GWEI=2
```

### Avalanche Fuji の取得元

| 値 | 取得元 |
| --- | --- |
| `RPC_URL` | Avalanche Fuji C-Chain の公開 RPC。上記の `https://api.avax-test.network/ext/bc/C/rpc` を使用できます。 |
| `DEPLOYER_PRIVATE_KEY` | MetaMask などで作成した Fuji 用ウォレットの秘密鍵 |
| `JPYC_TOKEN_ADDRESS` | Avalanche Fuji 上の JPYC トークンコントラクトアドレス |
| ガス代 | Fuji testnet AVAX |

Fuji のガス代は、Avalanche Builder Hub の手順で取得できます。

https://build.avax.network/academy/avalanche-l1/avalanche-fundamentals/04-creating-an-l1/02a-claim-testnet-tokens

このページでは、Core wallet を接続して C-Chain / P-Chain の testnet AVAX を受け取る手順が案内されています。Builder Hub アカウントを作らない場合は、外部 Avalanche Faucet と coupon code を使う方法も案内されています。

## Sepolia 用 `.env.sepolia`

Ethereum Sepolia にデプロイする場合は、`.env.sepolia` を作成します。

```powershell
copy .env.example .env.sepolia
```

`.env.sepolia` の例です。

```text
RPC_URL=https://sepolia.infura.io/v3/YOUR_PROJECT_ID
DEPLOYER_PRIVATE_KEY=0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
JPYC_TOKEN_ADDRESS=0xSepolia上のJPYCトークンアドレス
CONTRACT_OWNER_ADDRESS=0x管理者ウォレットアドレス
PAYMENT_OPERATOR_ADDRESS=0xoperatorウォレットアドレス
GAS_MULTIPLIER=1.2
MAX_PRIORITY_FEE_GWEI=2
```

### Sepolia の取得元

| 値 | 取得元 |
| --- | --- |
| `RPC_URL` | Infura: https://app.infura.io/ または Alchemy: https://dashboard.alchemy.com/ |
| `YOUR_PROJECT_ID` | Infura: https://app.infura.io/ で取得する Project ID または API Key |
| `DEPLOYER_PRIVATE_KEY` | MetaMask などで作成した Sepolia 用ウォレットの秘密鍵 |
| `JPYC_TOKEN_ADDRESS` | Sepolia 上の JPYC トークンコントラクトアドレス |
| ガス代 | Sepolia testnet ETH |

Infura を使う場合は、以下の手順で `RPC_URL` を作成します。

1. https://app.infura.io/ にログインします。
2. 新しい API Key または Project を作成します。
3. ネットワークで `Ethereum Sepolia` を選びます。
4. 表示された HTTPS エンドポイントをコピーします。
5. `https://sepolia.infura.io/v3/YOUR_PROJECT_ID` の `YOUR_PROJECT_ID` 部分を、自分の Project ID/API Key に置き換えます。

`YOUR_PROJECT_ID` は https://app.infura.io/ で取得します。Infura の画面で `API Key` または `Project ID` と表示されている文字列が、`YOUR_PROJECT_ID` に入れる値です。

Alchemy を使う場合は、Alchemy の App 作成画面で `Ethereum` と `Sepolia` を選び、表示された HTTPS URL 全体を `RPC_URL` に設定します。

Sepolia のガス代は、Sepolia testnet ETH faucet で取得できます。

- Chainlink Faucet: https://faucets.chain.link/sepolia
- Alchemy Faucet: https://www.alchemy.com/faucets/ethereum-sepolia

Chainlink Faucet では Ethereum Sepolia の ETH を取得できます。Alchemy Faucet では Ethereum Sepolia 向けに 24 時間ごとに 0.1 ETH をリクエストできます。

## Polygon Amoy 用 `.env.polygon`

Polygon Amoy にデプロイする場合は、`.env.polygon` を作成します。

```powershell
copy .env.example .env.polygon
```

`.env.polygon` の例です。

```text
RPC_URL=https://rpc-amoy.polygon.technology
DEPLOYER_PRIVATE_KEY=0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
JPYC_TOKEN_ADDRESS=0xPolygonAmoy上のJPYCトークンアドレス
CONTRACT_OWNER_ADDRESS=0x管理者ウォレットアドレス
PAYMENT_OPERATOR_ADDRESS=0xoperatorウォレットアドレス
GAS_MULTIPLIER=1.2
MAX_PRIORITY_FEE_GWEI=30
```

### Polygon Amoy の取得元

| 値 | 取得元 |
| --- | --- |
| `RPC_URL` | Polygon Amoy の公開 RPC。上記の `https://rpc-amoy.polygon.technology` を使用できます。 |
| `DEPLOYER_PRIVATE_KEY` | MetaMask などで作成した Amoy 用ウォレットの秘密鍵 |
| `JPYC_TOKEN_ADDRESS` | Polygon Amoy 上の JPYC トークンコントラクトアドレス |
| ガス代 | Amoy testnet POL |

Polygon Amoy のガス代は、Polygon Faucet で取得できます。

https://faucet.polygon.technology/

Polygon Faucet では、ネットワークに `Polygon Amoy` を選び、デプロイ用ウォレットアドレスを入力して testnet POL をリクエストします。受け取った POL は `DEPLOYER_PRIVATE_KEY` に対応するウォレットに入っている必要があります。

Polygon Amoy では、RPC が要求する最小 priority fee が高い場合があります。`transaction gas price below minimum` が出る場合は、`.env.polygon` の `MAX_PRIORITY_FEE_GWEI` を `30`、`40`、`50` のように上げてから再実行してください。

## JPYC トークンアドレスの確認

`JPYC_TOKEN_ADDRESS` はチェーンごとに異なります。Avalanche Fuji、Sepolia、Polygon Amoy で同じアドレスとは限らないため、必ずデプロイ先ネットワーク上の JPYC トークンコントラクトアドレスを設定してください。

確認方法の例です。

1. JPYC の公式ドキュメントまたは公式案内で、対象ネットワークのコントラクトアドレスを確認します。
2. 対象ネットワークのブロックエクスプローラーで同じアドレスを検索します。
3. 表示内容が JPYC のトークンコントラクトであることを確認してから env ファイルに設定します。

## 任意の gas 設定

通常の動作確認では `.env.example` のままで構いません。

```text
GAS_MULTIPLIER=1.2
MAX_PRIORITY_FEE_GWEI=2
```

## デプロイ

`deploy.py` はデフォルトで `.env` を読み込みます。ネットワーク別の env ファイルを使う場合は、`ENV_FILE` を指定します。

Avalanche Fuji にデプロイする場合:

```powershell
$env:ENV_FILE=".env.avalanche"
python deploy.py
```

Sepolia にデプロイする場合:

```powershell
$env:ENV_FILE=".env.sepolia"
python deploy.py
```

Polygon Amoy にデプロイする場合:

```powershell
$env:ENV_FILE=".env.polygon"
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
- `.env`, `.env.avalanche`, `.env.sepolia`, `.env.polygon` は `.gitignore` の対象です。
- `approve` はコントラクトアドレス単位で行われるため、デプロイ後の `payment_processor` アドレスは環境変数または Secret Manager で管理してください。
- アプリ起動時に毎回デプロイする運用にはしません。環境ごとに一度デプロイし、そのアドレスを使い回します。
