"""端末と来店セッションによるカテゴリー参照条件を検証する。"""

from datetime import datetime
from unittest.mock import Mock, call, patch

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions.custom_exception import UnauthorizedException, VisitSessionNotFoundException
from app.models.mysql.device import Device
from app.models.mysql.menu_category import MenuCategory
from app.services.device_service import DeviceService


DEVICE_UUID = "81006600-0000-4000-8000-000000000066"
DEVICE_ID = 810066
VISIT_SESSION_ID = 820066
STORE_ID = 110
ACTIVATED_AT = datetime(2026, 1, 1)


class TestGetMenuCategories:
    """認証済み端末の状態、セッション、店舗の照合を検証する。

    Args:
        なし。

    Returns:
        なし。
    """

    @pytest.mark.parametrize("session_is_active", [True, False])
    @patch("app.helpers.menu_category_image_helper.S3Client")
    @patch("app.helpers.menu_category_image_helper.SsmClient")
    @patch("app.services.device_service.StoreMenuCategoryRepository")
    @patch("app.services.device_service.VisitSessionRepository")
    @patch("app.services.device_service.DeviceRepository")
    def test_requires_active_session_for_authenticated_device(
        self, devices, visits, categories, ssm_class, s3_class, session_is_active,
    ) -> None:
        """端末に属する注文受付中セッションがある場合だけ所属店舗の一覧を取得する。

        Args:
            devices: 端末Repositoryのモック。
            visits: 来店セッションRepositoryのモック。
            categories: 店舗カテゴリーRepositoryのモック。
            ssm_class: 画像設定クライアントのモック。
            s3_class: S3クライアントのモック。
            session_is_active: 指定セッションが端末に属して注文受付中か。

        Returns:
            なし。
        """
        session = Mock(spec=Session)
        devices.return_value.get_device_by_uuid.return_value = Device(
            device_id=DEVICE_ID, store_id=STORE_ID, activated_at=ACTIVATED_AT, is_active=True,
        )
        visits.return_value.has_active_visit_session.return_value = session_is_active
        list_categories = categories.return_value.get_menu_categories
        list_categories.return_value = []
        service = DeviceService()
        arguments = {"mysql_session": session, "device_uuid": DEVICE_UUID, "visit_session_id": VISIT_SESSION_ID}

        if session_is_active:
            assert service.get_menu_categories(**arguments).model_dump() == {"menu_categories": []}
            list_categories.assert_called_once_with(mysql_session=session, store_id=STORE_ID, is_active=True)
        else:
            with pytest.raises(VisitSessionNotFoundException):
                service.get_menu_categories(**arguments)
            categories.assert_not_called()

        ssm_class.assert_not_called()
        s3_class.assert_not_called()
        devices.return_value.get_device_by_uuid.assert_called_once_with(mysql_session=session, device_uuid=DEVICE_UUID)
        visits.return_value.has_active_visit_session.assert_called_once_with(
            mysql_session=session, device_id=DEVICE_ID, visit_session_id=VISIT_SESSION_ID,
        )

    @pytest.mark.parametrize(
        "device",
        [None, Device(activated_at=None, is_active=True), Device(activated_at=ACTIVATED_AT, is_active=False)],
        ids=["missing", "unactivated", "stopped"],
    )
    @patch("app.services.device_service.StoreMenuCategoryRepository")
    @patch("app.services.device_service.VisitSessionRepository")
    @patch("app.services.device_service.DeviceRepository")
    def test_rejects_unavailable_device(self, devices, visits, categories, device) -> None:
        """利用不可の端末を拒否し、来店セッションやカテゴリーを参照しない。

        Args:
            devices: 端末Repositoryのモック。
            visits: 来店セッションRepositoryのモック。
            categories: 店舗カテゴリーRepositoryのモック。
            device: 取得結果として使う利用不可の端末情報。

        Returns:
            なし。
        """
        devices.return_value.get_device_by_uuid.return_value = device

        with pytest.raises(UnauthorizedException):
            DeviceService().get_menu_categories(
                mysql_session=Mock(spec=Session), device_uuid=DEVICE_UUID, visit_session_id=VISIT_SESSION_ID,
            )

        visits.assert_not_called()
        categories.assert_not_called()

    @patch("app.helpers.menu_category_image_helper.S3Client")
    @patch("app.helpers.menu_category_image_helper.SsmClient")
    @patch("app.services.device_service.StoreMenuCategoryRepository")
    @patch("app.services.device_service.VisitSessionRepository")
    @patch("app.services.device_service.DeviceRepository")
    def test_returns_ordered_categories_with_signed_urls(self, devices, visits, categories, ssm_class, s3_class) -> None:
        """端末の所属店舗のカテゴリーを表示順で取得し、既存設定で画像URLを署名する。

        Args:
            devices: 端末Repositoryのモック。
            visits: 来店セッションRepositoryのモック。
            categories: 店舗カテゴリーRepositoryのモック。
            ssm_class: 画像設定クライアントのモック。
            s3_class: 署名付きURLを生成するクライアントのモック。

        Returns:
            なし。
        """
        session = Mock(spec=Session)
        devices.return_value.get_device_by_uuid.return_value = Device(
            device_id=DEVICE_ID, store_id=STORE_ID, activated_at=ACTIVATED_AT, is_active=True,
        )
        visits.return_value.has_active_visit_session.return_value = True
        params = ssm_class.return_value
        params.s3_endpoint = "http://s3.example.com"
        params.category_image_bucket = "categories"
        params.menu_image_url_expires_in = 3600
        categories.return_value.get_menu_categories.return_value = [
            MenuCategory(menu_category_id=2, name="フード", image_extension="jpg", display_order=1),
            MenuCategory(menu_category_id=1, name="ドリンク", image_extension="png", display_order=2),
        ]
        sign = s3_class.return_value.generate_presigned_get_url
        sign.side_effect = ["https://example.com/2.jpg", "https://example.com/1.png"]

        result = DeviceService().get_menu_categories(
            mysql_session=session, device_uuid=DEVICE_UUID, visit_session_id=VISIT_SESSION_ID,
        )

        assert result.model_dump() == {
            "menu_categories": [
                {"menu_category_id": 2, "name": "フード", "image_url": "https://example.com/2.jpg", "display_order": 1},
                {"menu_category_id": 1, "name": "ドリンク", "image_url": "https://example.com/1.png", "display_order": 2},
            ],
        }
        categories.return_value.get_menu_categories.assert_called_once_with(
            mysql_session=session, store_id=STORE_ID, is_active=True,
        )
        categories.return_value.count_menu_categories.assert_not_called()
        ssm_class.assert_called_once_with()
        s3_class.assert_called_once_with(s3_endpoint=params.s3_endpoint)
        assert sign.call_args_list == [
            call(bucket_name="categories", file_name="110/2.jpg", expires_in=3600),
            call(bucket_name="categories", file_name="110/1.png", expires_in=3600),
        ]
