# AdaFace weight

顔認証の特徴量抽出で使用する AdaFace の PyTorch checkpoint を配置します。

## 配置ファイル

```text
adaface_ir50_ms1mv2.ckpt
```

## 取得方法

1. Hugging Face の VishalMishraTss/AdaFace から `adaface_ir50_ms1mv2.ckpt` を取得します。
   - https://huggingface.co/VishalMishraTss/AdaFace/tree/main
2. ダウンロードした checkpoint を `adaface_ir50_ms1mv2.ckpt` という名前でこのディレクトリへ配置します。
3. モデルを差し替える場合は、ファイル名と SSM 設定の `adaface_weight` を同じパスに揃えます。

## SSM設定

[tests/unit/test_data/ssm/teraid_pay_api_setting.json](../../../../ssm/teraid_pay_api_setting.json) では以下のキーで参照されます。

```json
{
  "llm_weight_bucket": "weights",
  "adaface_weight": "adaface/adaface_ir50_ms1mv2.ckpt"
}
```
