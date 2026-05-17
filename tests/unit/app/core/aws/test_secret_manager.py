import pytest
from botocore.exceptions import ClientError

from app.core.aws.secret_manager import SecretManager


@pytest.mark.usefixtures("initialize_secret")
class TestSecretManager:
    def test_init(self) -> None:
        secret_manager = SecretManager()

        assert secret_manager.region_name == "ap-northeast-1"
        assert secret_manager.endpoint_url == "http://localhost:4566"
        assert secret_manager.client.meta.endpoint_url == "http://localhost:4566"

    def test_get_secret_returns_dict(self) -> None:
        secret = SecretManager().get_secret("secret")

        assert isinstance(secret, dict)
        assert secret["mysql_database"] == "db_local"
        assert secret["chain_11155111_payment_processor_address"] == (
            "0xf2ec38e0A2F2794e826dD0aCF5de548C45d52615"
        )

    def test_get_secret_with_client_error(self) -> None:
        secret_manager = SecretManager()

        with pytest.raises(ClientError) as exc_info:
            secret_manager.get_secret("missing-secret")

        assert exc_info.value.response["Error"]["Code"] == "ResourceNotFoundException"
