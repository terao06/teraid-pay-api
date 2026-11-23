# 別会計API改修リスト

`menu_checkout_items` を新設する方式では、**既存の端末向けAPI 3本を改修**します。最初に未払い分の会計を作成して明細と合計金額を表示し、その後で決済方式を選びます。「まとめて支払う」なら最初の `checkout_id` を使い、「別々に支払う」なら選んだ明細と数量で同じ会計作成APIを再度呼びます。

| API | 必要な改修 |
| --- | --- |
| **会計作成** `POST /device/visit-sessions/{visit_session_id}/checkouts` | 初回は未払い分をすべて対象にし、各明細の `menu_order_items.menu_order_item_id`、未払い数量、金額を返します。別会計では `menu_order_item_id` と今回支払う `quantity` を受け取り、未払い数量の範囲内かを確認します。どちらの場合も、対象の明細・数量・金額を `menu_checkout_items` に保存し、合計を `menu_checkouts.total_amount` に記録します。 |
| **顔認証決済開始** `POST /device/checkouts/{checkout_id}/payments/face` | `menu_checkout_items.menu_order_item_id`、`menu_checkout_items.quantity`、`menu_checkout_items.line_amount` を使い、対象数量がまだ未払いで、金額の合計が `menu_checkouts.total_amount` と一致することを確認します。まとめ払いでは、会計作成後に追加注文が入っていないかも確認します。リクエストは既存の形式を使えます。 |
| **決済結果確認** `POST /device/checkouts/{checkout_id}/payments/{payment_request_id}/verify` | 成功時に `payment_requests.status` と `menu_checkouts.status` を `paid` に更新します。その会計の `menu_checkout_items.quantity` が支払済み数量に含まれます。注文内の全明細が支払済みになった時点で `menu_orders.status` を `PAID` にし、`menu_orders.paid_at` を記録します。レスポンスには、セッションに未払い分が残っているかを追加します。 |
