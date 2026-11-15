"""メニューオプション構成更新エンドポイントのテスト。"""

from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.models.mysql.menu_option import MenuOption
from app.models.mysql.menu_option_group import MenuOptionGroup
from app.models.responses.menu_option_groups_update_response import (
    MenuOptionGroupsUpdateResponse,
    MenuOptionGroupUpdateResult,
)


MENU_OPTION_GROUPS_UPDATE_REQUEST = {
    "option_groups": [
        {
            "menu_option_group_id": 20,
            "name": "サイズ",
            "min_selections": 1,
            "max_selections": 1,
            "display_order": 1,
            "is_active": True,
            "options": [
                {
                    "menu_option_id": 30,
                    "name": "通常",
                    "additional_price": "0.000000",
                    "display_order": 1,
                    "is_available": True,
                }
            ],
        }
    ]
}

MENU_OPTION_GROUPS_UPDATE_DB_REQUEST = {
    "option_groups": [
        {
            "menu_option_group_id": 27011,
            "name": "更新サイズ",
            "min_selections": 1,
            "max_selections": 1,
            "display_order": 1,
            "is_active": True,
            "options": [
                {
                    "menu_option_id": 27021,
                    "name": "更新通常",
                    "additional_price": "50.000000",
                    "display_order": 1,
                    "is_available": False,
                },
                {
                    "name": "特大",
                    "additional_price": "200.000000",
                    "display_order": 2,
                    "is_available": True,
                },
            ],
        },
        {
            "name": "トッピング",
            "min_selections": 0,
            "max_selections": 2,
            "display_order": 2,
            "is_active": True,
            "options": [
                {
                    "name": "チーズ",
                    "additional_price": "100.000000",
                    "display_order": 1,
                    "is_available": True,
                }
            ],
        },
    ]
}


class TestUpdateMenuOptionGroups:
    """メニューオプション構成更新エンドポイントを検証する。"""

    @patch("app.endpoints.store.StoreController.update_menu_option_groups")
    def test_returns_wrapped_updated_ids(
        self,
        mock_update_menu_option_groups,
        client,
    ) -> None:
        """Controllerの更新結果を共通レスポンス形式で返す。"""
        mock_update_menu_option_groups.return_value = (
            MenuOptionGroupsUpdateResponse(
                menu_item_id=10,
                menu_option_groups=[
                    MenuOptionGroupUpdateResult(
                        menu_option_group_id=20,
                        menu_option_ids=[30],
                    )
                ],
            )
        )

        response = client.put(
            "/store/menu/10/option-groups",
            json=MENU_OPTION_GROUPS_UPDATE_REQUEST,
        )

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "data": {
                "menu_item_id": 10,
                "menu_option_groups": [
                    {
                        "menu_option_group_id": 20,
                        "menu_option_ids": [30],
                    }
                ],
            },
        }
        assert mock_update_menu_option_groups.call_args.kwargs["store_id"] == 101
        request = mock_update_menu_option_groups.call_args.kwargs["request"]
        assert request.option_groups[0].options[0].menu_option_id == 30

    @pytest.mark.parametrize(
        "request_json",
        [
            {},
            {"option_groups": [{**MENU_OPTION_GROUPS_UPDATE_REQUEST["option_groups"][0], "min_selections": 2}]},
            {
                "option_groups": [
                    MENU_OPTION_GROUPS_UPDATE_REQUEST["option_groups"][0],
                    MENU_OPTION_GROUPS_UPDATE_REQUEST["option_groups"][0],
                ]
            },
        ],
    )
    def test_returns_validation_error(self, client, request_json) -> None:
        """必須項目、選択数、重複IDが不正な場合に422を返す。"""
        response = client.put(
            "/store/menu/10/option-groups",
            json=request_json,
        )

        assert response.status_code == 422

    @pytest.mark.usefixtures("insert_menu_option_groups_update")
    def test_with_db_synchronizes_option_groups(
        self,
        store_client_with_db,
        mysql_session: Session,
    ) -> None:
        """実DBで更新・追加・論理削除を含むオプション構成を同期する。"""
        response = store_client_with_db.put(
            "/store/menu/24/option-groups",
            json=MENU_OPTION_GROUPS_UPDATE_DB_REQUEST,
        )

        assert response.status_code == 200
        response_data = response.json()["data"]
        assert response_data["menu_item_id"] == 24
        assert len(response_data["menu_option_groups"]) == 2
        assert response_data["menu_option_groups"][0][
            "menu_option_group_id"
        ] == 27011
        assert response_data["menu_option_groups"][0][
            "menu_option_ids"
        ][0] == 27021

        mysql_session.rollback()
        mysql_session.expire_all()
        groups = (
            mysql_session.query(MenuOptionGroup)
            .filter(MenuOptionGroup.menu_item_id == 24)
            .all()
        )
        group_by_id = {group.menu_option_group_id: group for group in groups}
        group_by_name = {group.name: group for group in groups}

        assert group_by_id[27011].name == "更新サイズ"
        assert group_by_id[27011].deleted_at is None
        assert group_by_id[27012].deleted_at is not None
        assert group_by_name["トッピング"].deleted_at is None

        options = (
            mysql_session.query(MenuOption)
            .filter(
                MenuOption.menu_option_group_id.in_(list(group_by_id))
            )
            .all()
        )
        option_by_id = {
            option.menu_option_id: option for option in options
        }
        option_by_name = {option.name: option for option in options}

        assert option_by_id[27021].name == "更新通常"
        assert str(option_by_id[27021].additional_price) == "50.000000"
        assert option_by_id[27021].is_available is False
        assert option_by_id[27021].deleted_at is None
        assert option_by_id[27022].deleted_at is not None
        assert option_by_id[27023].deleted_at is not None
        assert option_by_name["特大"].menu_option_group_id == 27011
        assert option_by_name["チーズ"].menu_option_group_id == (
            group_by_name["トッピング"].menu_option_group_id
        )
