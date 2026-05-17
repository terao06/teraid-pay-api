import pytest
from botocore.exceptions import ClientError

from app.core.aws.ssm_manager import SsmClient


@pytest.mark.usefixtures("initialize_ssm")
class TestSsmClient:
    def test_init(self) -> None:
        ssm_client = SsmClient()

        assert ssm_client.region_name == "ap-northeast-1"
        assert ssm_client.endpoint_url == "http://localhost:4566"
        assert ssm_client.client.meta.endpoint_url == "http://localhost:4566"

    def test_get_parameter_returns_string(self) -> None:
        value = SsmClient()._get_parameter("s3_endpoint")

        assert value == "http://teraid-pay-api-s3:9000"

    def test_get_parameter_returns_dict_when_value_is_json(self) -> None:
        value = SsmClient()._get_parameter("llm_weight_bucket")

        assert value == "weights"

    def test_get_parameter_with_client_error(self) -> None:
        ssm_client = SsmClient()

        with pytest.raises(ClientError) as exc_info:
            ssm_client._get_parameter(name="/missing-parameter")

        assert exc_info.value.response["Error"]["Code"] == "ParameterNotFound"
