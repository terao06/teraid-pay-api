import base64
from decimal import Decimal
from io import BytesIO
from unittest.mock import patch

import boto3
from fastapi import HTTPException
from PIL import Image
import pytest
from sqlalchemy.orm import Session

from app.models.mysql.menu_item import MenuItem
from app.models.mysql.menu_option_group import MenuOptionGroup
from app.models.mysql.menu_option import MenuOption
from app.models.responses.menu_create_response import MenuCreateResponse
from tests.unit.test_data.s3.build_s3 import ENDPOINT_URL as S3_ENDPOINT_URL
from tests.unit.test_data.s3.build_s3 import REGION_NAME as S3_REGION_NAME
from tests.unit.test_data.ssm.build_ssm import (
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY,
)


def build_menu_image() -> str:
    """テスト用メニュー画像をBase64文字列で生成する。"""
    image = Image.new("RGB", (16, 16), color=(255, 0, 0))
    with BytesIO() as buffer:
        image.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("ascii")


MENU_REQUEST = {
    "menu_category_id": 12,
    "name": "チーズバーガー",
    "description": "チェダーチーズ入り",
    "price": "800.000000",
    "token_symbol": "JPYC",
    "menu_image": build_menu_image(),
    "image_extension": "png",
    "is_available": True,
    "display_order": 1,
    "option_groups": [
        {
            "name": "サイズ",
            "min_selections": 1,
            "max_selections": 1,
            "display_order": 1,
            "is_active": True,
            "options": [
                {
                    "name": "通常",
                    "additional_price": "0.000000",
                    "display_order": 1,
                    "is_available": True,
                },
                {
                    "name": "大盛り",
                    "additional_price": "100.000000",
                    "display_order": 2,
                    "is_available": True,
                },
            ],
        }
    ],
}

DB_MENU_REQUEST = {
    **MENU_REQUEST,
    "menu_category_id": 17,
}


class TestCreateMenu:
    """メニュー登録エンドポイントの単体テスト。"""

    @patch("app.endpoints.store.StoreController.create_menu")
    def test_returns_wrapped_created_menu(
        self,
        mock_create_menu,
        client,
    ) -> None:
        """controllerの登録結果を201の共通レスポンス形式で返すことを確認する。"""
        mock_create_menu.return_value = MenuCreateResponse(menu_item_id=10)

        response = client.post("/store/menu", json=MENU_REQUEST)

        assert response.status_code == 201
        assert response.json() == {
            "status": "success",
            "data": {"menu_item_id": 10},
        }
        mock_create_menu.assert_called_once()
        assert mock_create_menu.call_args.kwargs["store_id"] == 101
        request = mock_create_menu.call_args.kwargs["request"]
        assert request.menu_category_id == 12
        assert request.name == "チーズバーガー"
        assert request.price == Decimal("800.000000")
        assert request.menu_image == MENU_REQUEST["menu_image"]
        assert request.image_extension.value == "png"
        assert len(request.option_groups) == 1
        assert len(request.option_groups[0].options) == 2

    @patch("app.endpoints.store.StoreController.create_menu")
    @pytest.mark.parametrize(
        ("status_code", "message"),
        [
            (404, "menu category not found"),
            (500, "server error"),
        ],
    )
    def test_returns_http_exception_from_controller(
        self,
        mock_create_menu,
        status_code,
        message,
        client,
    ) -> None:
        """controllerが送出したHTTPExceptionをそのまま返すことを確認する。"""
        mock_create_menu.side_effect = HTTPException(
            status_code=status_code,
            detail={"status": "error", "message": message},
        )

        response = client.post("/store/menu", json=MENU_REQUEST)

        assert response.status_code == status_code
        assert response.json() == {
            "detail": {"status": "error", "message": message}
        }

    @pytest.mark.parametrize(
        "request_json",
        [
            {**MENU_REQUEST, "price": "-1.000000"},
            {
                **MENU_REQUEST,
                "option_groups": [
                    {
                        **MENU_REQUEST["option_groups"][0],
                        "min_selections": 2,
                        "max_selections": 1,
                    }
                ],
            },
            {
                **MENU_REQUEST,
                "option_groups": [
                    {
                        **MENU_REQUEST["option_groups"][0],
                        "options": [
                            {
                                **MENU_REQUEST["option_groups"][0]["options"][0],
                                "additional_price": "-1.000000",
                            }
                        ],
                    }
                ],
            },
            {**MENU_REQUEST, "display_order": -1},
            {**MENU_REQUEST, "image_extension": "gif"},
        ],
    )
    def test_returns_validation_error(
        self,
        request_json,
        client,
    ) -> None:
        """メニュー登録の入力値が不正な場合に422を返すことを確認する。"""
        response = client.post("/store/menu", json=request_json)

        assert response.status_code == 422

    @pytest.mark.usefixtures(
        "insert_menu_categories",
        "initialize_s3",
        "initialize_ssm",
        "use_local_s3_endpoint",
    )
    def test_with_db(
        self,
        store_client_with_db_for_menu_create,
        mysql_session: Session,
    ) -> None:
        """DB 連携で商品、オプショングループ、オプションを登録することを確認する。"""
        response = store_client_with_db_for_menu_create.post(
            "/store/menu",
            json=DB_MENU_REQUEST,
        )

        assert response.status_code == 201
        response_data = response.json()["data"]
        menu_item_id = response_data["menu_item_id"]

        menu_item = (
            mysql_session.query(MenuItem)
            .filter(MenuItem.menu_item_id == menu_item_id)
            .one()
        )
        menu_option_group = (
            mysql_session.query(MenuOptionGroup)
            .filter(
                MenuOptionGroup.menu_item_id == menu_item_id
            )
            .one()
        )
        menu_options = (
            mysql_session.query(MenuOption)
            .filter(
                MenuOption.menu_option_group_id
                == menu_option_group.menu_option_group_id
            )
            .order_by(MenuOption.display_order.asc())
            .all()
        )

        assert menu_item.store_id == 106
        assert menu_item.menu_category_id == 17
        assert menu_item.name == "チーズバーガー"
        assert menu_item.price == Decimal("800.000000")
        assert menu_item.image_extension == "png"
        assert menu_option_group.menu_item_id == menu_item_id
        assert menu_option_group.name == "サイズ"
        assert [menu_option.name for menu_option in menu_options] == [
            "通常",
            "大盛り",
        ]
        assert [menu_option.additional_price for menu_option in menu_options] == [
            Decimal("0.000000"),
            Decimal("100.000000"),
        ]

        s3_client = boto3.client(
            "s3",
            endpoint_url=S3_ENDPOINT_URL,
            region_name=S3_REGION_NAME,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        )
        s3_response = s3_client.get_object(
            Bucket="menus",
            Key=f"106/{menu_item_id}.png",
        )
        assert s3_response["Body"].read() != b""

    @pytest.mark.usefixtures("insert_menu_categories")
    def test_with_db_returns_not_found_for_other_store_category(
        self,
        store_client_with_db,
    ) -> None:
        """DB連携で別店舗のカテゴリーを指定した場合に404を返すことを確認する。"""
        request_json = {**MENU_REQUEST, "menu_category_id": 16}

        response = store_client_with_db.post("/store/menu", json=request_json)

        assert response.status_code == 404
        assert response.json() == {
            "detail": {
                "status": "error",
                "message": "メニューカテゴリーが存在しません。",
            }
        }

    @pytest.mark.usefixtures("insert_menu_categories")
    def test_with_db_returns_unprocessable_for_invalid_menu_image(
        self,
        store_client_with_db,
        mysql_session: Session,
    ) -> None:
        """DB連携で画像形式と拡張子が不一致の場合に422を返すことを確認する。"""
        request_json = {
            **MENU_REQUEST,
            "name": "画像不正商品",
            "image_extension": "jpeg",
        }

        response = store_client_with_db.post("/store/menu", json=request_json)

        assert response.status_code == 422
        assert response.json() == {
            "detail": {
                "status": "error",
                "message": "メニュー画像が正しくありません。",
            }
        }
        assert (
            mysql_session.query(MenuItem)
            .filter(MenuItem.name == "画像不正商品")
            .count()
            == 0
        )

    @pytest.mark.usefixtures(
        "insert_menu_categories",
        "initialize_ssm",
        "use_local_s3_endpoint",
    )
    @patch("app.services.store_menu_service.S3Client")
    def test_with_db_rolls_back_when_s3_upload_fails(
        self,
        mock_s3_client_class,
        store_client_with_db,
        mysql_session: Session,
    ) -> None:
        """S3アップロード失敗時に全テーブルへの登録をロールバックすることを確認する。"""
        mock_s3_client_class.return_value.upload_object.side_effect = Exception(
            "S3 error"
        )
        request_json = {**MENU_REQUEST, "name": "S3失敗確認商品"}

        response = store_client_with_db.post("/store/menu", json=request_json)

        assert response.status_code == 500
        assert (
            mysql_session.query(MenuItem)
            .filter(MenuItem.name == "S3失敗確認商品")
            .count()
            == 0
        )
        mock_s3_client_class.return_value.delete_object.assert_not_called()

    @pytest.mark.usefixtures("insert_menu_categories")
    @patch(
        "app.repositories.mysql.store_menu_repository.StoreMenuRepository.create_menu_option",
        side_effect=Exception("DB error"),
    )
    def test_with_db_rolls_back_when_option_registration_fails(
        self,
        mock_create_menu_option,
        store_client_with_db,
        mysql_session: Session,
    ) -> None:
        """オプション登録失敗時に商品を含む全登録をロールバックすることを確認する。"""
        request_json = {**MENU_REQUEST, "name": "ロールバック確認商品"}

        response = store_client_with_db.post("/store/menu", json=request_json)

        assert response.status_code == 500
        assert mock_create_menu_option.called
        assert (
            mysql_session.query(MenuItem)
            .filter(MenuItem.name == "ロールバック確認商品")
            .count()
            == 0
        )
