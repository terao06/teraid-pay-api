"""メニューカテゴリー更新エンドポイントのテスト。"""

import base64
from io import BytesIO
from unittest.mock import patch

import boto3
from botocore.exceptions import ClientError
from fastapi import HTTPException
from PIL import Image
import pytest
from sqlalchemy.orm import Session

from app.models.mysql.menu_category import MenuCategory
from app.models.responses.menu_category_response import MenuCategoryUpdateResponse
from tests.unit.test_data.s3.build_s3 import ENDPOINT_URL as S3_ENDPOINT_URL
from tests.unit.test_data.s3.build_s3 import REGION_NAME as S3_REGION_NAME
from tests.unit.test_data.ssm.build_ssm import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY


CATEGORY_UPDATE_REQUEST = {
    "name": "更新カテゴリー",
    "display_order": 2,
    "is_active": True,
}


def build_category_image(format: str) -> tuple[str, bytes]:
    """テスト用カテゴリー画像のBase64文字列とバイト列を生成する。

    Args:
        format: 生成する画像形式。

    Returns:
        Base64文字列と元画像データの組み合わせ。
    """
    image = Image.new("RGB", (16, 16), color=(0, 128, 255))
    with BytesIO() as buffer:
        image.save(buffer, format=format)
        image_bytes = buffer.getvalue()
    return base64.b64encode(image_bytes).decode("ascii"), image_bytes


def set_category_state(
    mysql_session: Session,
    menu_category_id: int,
    name: str,
    image_extension: str,
    display_order: int,
    is_active: bool,
) -> None:
    """共有テストDBのカテゴリーを指定した状態へ更新する。

    Args:
        mysql_session: 更新に使用するSQLAlchemyのセッション。
        menu_category_id: 更新対象のメニューカテゴリーID。
        name: 設定するカテゴリー名。
        image_extension: 設定する画像拡張子。
        display_order: 設定する表示順。
        is_active: 設定する有効状態。

    Returns:
        なし。
    """
    category = (
        mysql_session.query(MenuCategory)
        .filter(MenuCategory.menu_category_id == menu_category_id)
        .one()
    )
    category.name = name
    category.image_extension = image_extension
    category.display_order = display_order
    category.is_active = is_active
    mysql_session.commit()


class TestUpdateMenuCategory:
    """メニューカテゴリー更新エンドポイントを検証する。"""

    @patch("app.endpoints.store.StoreController.update_menu_category")
    def test_returns_wrapped_updated_category(
        self,
        mock_update_menu_category,
        client,
    ) -> None:
        """Controllerの更新結果を共通レスポンス形式で返す。"""
        mock_update_menu_category.return_value = MenuCategoryUpdateResponse(
            menu_category_id=14,
        )

        response = client.put(
            "/store/menu/categories/14",
            json=CATEGORY_UPDATE_REQUEST,
        )

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "data": {
                "menu_category_id": 14,
            },
        }
        request = mock_update_menu_category.call_args.kwargs["request"]
        assert mock_update_menu_category.call_args.kwargs["store_id"] == 101
        assert mock_update_menu_category.call_args.kwargs["menu_category_id"] == 14
        assert request.name == "更新カテゴリー"
        assert request.category_image is None
        assert request.image_extension is None

    @patch("app.endpoints.store.StoreController.update_menu_category")
    def test_returns_http_exception_from_controller(
        self,
        mock_update_menu_category,
        client,
    ) -> None:
        """Controllerが送出したHTTPExceptionをそのまま返す。"""
        mock_update_menu_category.side_effect = HTTPException(
            status_code=404,
            detail={"status": "error", "message": "not found"},
        )

        response = client.put(
            "/store/menu/categories/999",
            json=CATEGORY_UPDATE_REQUEST,
        )

        assert response.status_code == 404
        assert response.json() == {
            "detail": {"status": "error", "message": "not found"}
        }

    @pytest.mark.parametrize(
        ("menu_category_id", "request_json"),
        [
            (0, CATEGORY_UPDATE_REQUEST),
            (14, {**CATEGORY_UPDATE_REQUEST, "name": ""}),
            (14, {**CATEGORY_UPDATE_REQUEST, "display_order": -1}),
            (14, {**CATEGORY_UPDATE_REQUEST, "category_image": "image"}),
            (14, {**CATEGORY_UPDATE_REQUEST, "image_extension": "png"}),
            (
                14,
                {
                    **CATEGORY_UPDATE_REQUEST,
                    "category_image": "image",
                    "image_extension": "gif",
                },
            ),
        ],
    )
    def test_returns_validation_error(
        self,
        client,
        menu_category_id,
        request_json,
    ) -> None:
        """不正なパスまたはリクエストに422を返す。"""
        response = client.put(
            f"/store/menu/categories/{menu_category_id}",
            json=request_json,
        )

        assert response.status_code == 422

    @pytest.mark.usefixtures("insert_menu_categories")
    def test_with_db_updates_inactive_category(
        self,
        store_client_with_db,
        mysql_session: Session,
    ) -> None:
        """認証店舗の無効カテゴリーを画像なしで更新できる。"""
        set_category_state(
            mysql_session=mysql_session,
            menu_category_id=14,
            name="無効カテゴリー",
            image_extension="png",
            display_order=0,
            is_active=False,
        )
        try:
            response = store_client_with_db.put(
                "/store/menu/categories/14",
                json=CATEGORY_UPDATE_REQUEST,
            )

            assert response.status_code == 200
            assert response.json()["data"] == {
                "menu_category_id": 14,
            }
            mysql_session.expire_all()
            category = (
                mysql_session.query(MenuCategory)
                .filter(MenuCategory.menu_category_id == 14)
                .one()
            )
            assert category.name == "更新カテゴリー"
            assert category.image_extension == "png"
            assert category.display_order == 2
            assert category.is_active is True
        finally:
            set_category_state(
                mysql_session=mysql_session,
                menu_category_id=14,
                name="無効カテゴリー",
                image_extension="png",
                display_order=0,
                is_active=False,
            )

    @pytest.mark.usefixtures(
        "insert_menu_categories",
        "initialize_s3",
        "initialize_ssm",
        "use_local_s3_endpoint",
    )
    def test_with_db_and_s3_replaces_category_image(
        self,
        store_client_with_db,
        mysql_session: Session,
    ) -> None:
        """画像拡張子を変更し、S3の旧画像を新画像へ置き換える。"""
        set_category_state(
            mysql_session=mysql_session,
            menu_category_id=12,
            name="フード",
            image_extension="png",
            display_order=1,
            is_active=True,
        )
        s3_client = boto3.client(
            "s3",
            endpoint_url=S3_ENDPOINT_URL,
            region_name=S3_REGION_NAME,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        )
        try:
            s3_client.create_bucket(
                Bucket="categories",
                CreateBucketConfiguration={"LocationConstraint": S3_REGION_NAME},
            )
        except ClientError as exc:
            if exc.response["Error"]["Code"] not in {
                "BucketAlreadyOwnedByYou",
                "BucketAlreadyExists",
            }:
                raise

        _, old_image_bytes = build_category_image(format="PNG")
        new_image_base64, new_image_bytes = build_category_image(format="JPEG")
        old_key = "101/12.png"
        new_key = "101/12.jpg"
        s3_client.put_object(Bucket="categories", Key=old_key, Body=old_image_bytes)

        try:
            response = store_client_with_db.put(
                "/store/menu/categories/12",
                json={
                    **CATEGORY_UPDATE_REQUEST,
                    "category_image": new_image_base64,
                    "image_extension": "jpg",
                },
            )

            assert response.status_code == 200
            mysql_session.expire_all()
            category = (
                mysql_session.query(MenuCategory)
                .filter(MenuCategory.menu_category_id == 12)
                .one()
            )
            assert category.image_extension == "jpg"
            stored_new_image = s3_client.get_object(
                Bucket="categories",
                Key=new_key,
            )["Body"].read()
            assert stored_new_image == new_image_bytes
            with pytest.raises(ClientError):
                s3_client.get_object(Bucket="categories", Key=old_key)
        finally:
            s3_client.delete_object(Bucket="categories", Key=old_key)
            s3_client.delete_object(Bucket="categories", Key=new_key)
            set_category_state(
                mysql_session=mysql_session,
                menu_category_id=12,
                name="フード",
                image_extension="png",
                display_order=1,
                is_active=True,
            )

    @pytest.mark.usefixtures("insert_menu_categories")
    @pytest.mark.parametrize("menu_category_id", [15, 16, 999])
    def test_with_db_returns_not_found(
        self,
        store_client_with_db,
        menu_category_id,
    ) -> None:
        """削除済み、他店舗、未存在のカテゴリーに404を返す。"""
        response = store_client_with_db.put(
            f"/store/menu/categories/{menu_category_id}",
            json=CATEGORY_UPDATE_REQUEST,
        )

        assert response.status_code == 404
