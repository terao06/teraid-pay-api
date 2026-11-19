---
name: teraid-pay-api-tests
description: teraid-pay-apiのAPI・DBテストを追加または変更するときに、既存のpytest fixtureとテーブル単位SQLに合わせて実装・検証する。
---

# teraid-pay-api tests

このリポジトリでAPIのテストを実装するときの確認事項。着手前に対象APIと隣接するEndpoint・Controller・Service・Repositoryテスト、`tests/unit/conftest.py`、`tests/unit/app/endpoints/conftest.py`、`tests/unit/test_data/mysql/build_local_db.py` を確認する。

## DBテスト

- DBの読み書きを伴うAPI変更では、Endpointの `Test...` に実DBを使う `test_with_db...` があるか確認する。新規APIや変更したDB動作を既存テストが検証しない場合は追加する。正常系に加え、対象未存在、店舗境界、論理削除、状態制約など変更に関係する分岐を選ぶ。
- モックだけのテストを実DB検証の代わりにしない。DBテストが実行できない環境では、テストを残して未実行の理由を報告する。
- 更新・削除APIのDBテストでは共有行を変更しない。専用行を用意し、テスト後にその行だけを除去する。

## テストデータと配置

- MySQLの投入SQLは `tests/unit/test_data/mysql/<テーブル名>.sql` にテーブル単位で置く。API名やテスト名でSQLファイルを分割しない。同じテーブルの専用行は既存ファイルに追加し、重複しないID・UUIDを使う。
- SQLの読み込み関数は `tests/unit/test_data/mysql/build_local_db.py`、投入と後片付けを行うfixtureは `tests/unit/conftest.py` に置く。EndpointのDBテストでは `@pytest.mark.usefixtures("insert_<テーブル名>")` 等で使う。テスト関数内にSQL読み込みやfixtureを独自実装しない。
- 他のテストへ影響するデータを `insert_sample_data` に無条件で追加しない。必要なテストだけで投入し、固定IDを指定して後片付けする。既存fixtureの依存関係と実行順序も確認する。
- 新規テストの配置は既存の `tests/unit/app/{endpoints,controllers,services,repositories}/.../test_<操作>.py` に合わせる。既存のテスト名、認証クライアント、レスポンス形式を参照する。

## 完了前

- 対象テストと影響しうる隣接APIテストを実行し、SQL投入・後片付けを含めて確認する。`git diff --check` と、変更したPython定義のdocstring確認も行う。
