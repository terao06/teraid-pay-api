import base64
from io import BytesIO
from unittest.mock import patch

import boto3
from fastapi import HTTPException
from PIL import Image
import pytest
from sqlalchemy.orm import Session

from app.models.mysql.menu_category import MenuCategory
from app.models.responses.menu_category_response import MenuCategoryCreateResponse
from tests.unit.test_data.s3.build_s3 import ENDPOINT_URL as S3_ENDPOINT_URL
from tests.unit.test_data.s3.build_s3 import REGION_NAME as S3_REGION_NAME
from tests.unit.test_data.ssm.build_ssm import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY


def build_category_image() -> str:
    image = Image.new("RGB", (16, 16), color=(0, 128, 255))
    with BytesIO() as buffer:
        image.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("ascii")


CATEGORY_REQUEST = {
    "name": "ハンバーガー",
    "category_image": build_category_image(),
    "image_extension": "png",
    "display_order": 1,
    "is_active": True,
}


class TestCreateMenuCategory:
    @patch("app.endpoints.store.StoreController.create_menu_category")
    def test_returns_wrapped_created_category(
        self,
        mock_create_menu_category,
        client,
    ) -> None:
        mock_create_menu_category.return_value = MenuCategoryCreateResponse(
            menu_category_id=18,
            name="ハンバーガー",
            display_order=1,
            is_active=True,
        )

        response = client.post("/store/menu/categories", json=CATEGORY_REQUEST)

        assert response.status_code == 201
        assert response.json() == {
            "status": "success",
            "data": {
                "menu_category_id": 18,
                "name": "ハンバーガー",
                "display_order": 1,
                "is_active": True,
            },
        }
        request = mock_create_menu_category.call_args.kwargs["request"]
        assert mock_create_menu_category.call_args.kwargs["store_id"] == 101
        assert request.name == "ハンバーガー"
        assert request.image_extension.value == "png"

    @patch("app.endpoints.store.StoreController.create_menu_category")
    def test_returns_http_exception_from_controller(
        self,
        mock_create_menu_category,
        client,
    ) -> None:
        mock_create_menu_category.side_effect = HTTPException(
            status_code=500,
            detail={"status": "error", "message": "server error"},
        )

        response = client.post("/store/menu/categories", json=CATEGORY_REQUEST)

        assert response.status_code == 500
        assert response.json() == {
            "detail": {"status": "error", "message": "server error"}
        }

    @pytest.mark.parametrize(
        "request_json",
        [
            {**CATEGORY_REQUEST, "name": ""},
            {**CATEGORY_REQUEST, "name": "a" * 101},
            {**CATEGORY_REQUEST, "display_order": -1},
            {**CATEGORY_REQUEST, "image_extension": "gif"},
        ],
    )
    def test_returns_validation_error(self, request_json, client) -> None:
        response = client.post("/store/menu/categories", json=request_json)

        assert response.status_code == 422

    @pytest.mark.usefixtures(
        "initialize_s3",
        "initialize_ssm",
        "use_local_s3_endpoint",
    )
    def test_with_db_and_s3(
        self,
        store_client_with_db_for_menu_create,
        mysql_session: Session,
    ) -> None:
        response = store_client_with_db_for_menu_create.post(
            "/store/menu/categories",
            json={**CATEGORY_REQUEST, "name": "カテゴリー登録APIテスト"},
        )

        assert response.status_code == 201
        response_data = response.json()["data"]
        menu_category = (
            mysql_session.query(MenuCategory)
            .filter(MenuCategory.menu_category_id == response_data["menu_category_id"])
            .one()
        )
        assert menu_category.store_id == 106
        assert menu_category.name == "カテゴリー登録APIテスト"
        assert menu_category.image_extension == "png"

        s3_client = boto3.client(
            "s3",
            endpoint_url=S3_ENDPOINT_URL,
            region_name=S3_REGION_NAME,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        )
        s3_response = s3_client.get_object(
            Bucket="categories",
            Key=f"106/{menu_category.menu_category_id}.png",
        )
        assert s3_response["Body"].read() != b""
