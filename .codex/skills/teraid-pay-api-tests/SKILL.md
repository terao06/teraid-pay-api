---
name: teraid-pay-api-tests
description: teraid-pay-apiのAPI・DBテストを追加または変更するときに、既存のpytest fixtureとテーブル単位SQLに合わせて実装・検証する。
---

# teraid-pay-api tests

このリポジトリでAPIのテストを実装するときの確認事項。着手前に対象APIと隣接するEndpoint・Controller・Service・Repositoryテスト、`tests/unit/conftest.py`、`tests/unit/app/endpoints/conftest.py`、`tests/unit/test_data/mysql/build_local_db.py` を確認する。

各層のテスト方針には、ユーザー共通スキル `repository-test-conventions` を適用する。

## DBテスト

- DBの読み書きを伴うAPI変更では、Endpointの `Test...` に実DBを使う `test_with_db...` があるか確認する。新規APIや変更したDB動作を既存テストが検証しない場合は追加する。正常系に加え、対象未存在、店舗境界、論理削除、状態制約など変更に関係する分岐を選ぶ。
- Repositoryのテストは実DBのfixtureを使う。テスト名は `test_<検証する振る舞い>` 形式とする。`test_with_db...` はEndpointの実DBテストで使う。排他ロックが要件の場合は、`tests/unit/app/repositories/mysql/store/test_get_menu_category_detail.py` に倣い、別セッションでロックの取得が拒否され、トランザクション終了後に取得できることを確認する。
- モックだけのテストを実DB検証の代わりにしない。DBテストが実行できない環境では、テストを残して未実行の理由を報告する。
- MySQLの初期化はテストセッション開始時に1回行う。各テストで永続的に変更する行を分け、一覧や件数に影響する専用データは店舗などの検索範囲も分ける。

## テストデータと配置

- MySQLの投入SQLは `tests/unit/test_data/mysql/<テーブル名>.sql` にテーブル単位で置く。API名やテスト名でSQLファイルを分割しない。同じテーブルの専用行は既存ファイルに追加し、重複しないID・UUIDを使う。
- SQLの読み込み関数は `tests/unit/test_data/mysql/build_local_db.py`、投入fixtureは `tests/unit/conftest.py` に置く。EndpointのDBテストでは `@pytest.mark.usefixtures("insert_<テーブル名>")` 等で使う。テスト関数内にSQL読み込みやfixtureを独自実装しない。
- 専用データは、必要とするテストのsessionスコープのfixtureで1回投入する。テスト終了後の行削除は行わない。既存fixtureとの依存関係と、テストの実行順に依存せず検証できることを確認する。
- 新規テストを書く前に、同じ層の複数の類似操作を確認し、配置、`Test<操作>` クラス、fixture、実DBの使い方を揃える。ユーザーが指定した配置と形式を優先する。Endpointでは認証クライアントとレスポンス形式も既存テストに揃える。
- 新規MySQL Repositoryテストは `tests/unit/app/repositories/mysql/<対象>/test_<操作>.py` の `Test<操作>` クラスに置く。デバイス用の対象ディレクトリは `mysql/device/` とする。対象の既存テストが直下の単一ファイルにある場合も、対象別ディレクトリと操作別ファイルの既存パターンに揃える。

## 完了前

- 差分で新規テストのディレクトリとクラス名を、pytestの収集結果で対象の実DBテスト名を確認する。
- 対象テストと影響しうる隣接APIテストを実行し、SQL投入とテストデータの分離を確認する。`git diff --check` と、変更したPython定義のdocstring確認も行う。
