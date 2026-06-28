import base64
from datetime import datetime, timedelta
from decimal import Decimal
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from PIL import Image
from web3.exceptions import TransactionNotFound

from app.core.exceptions.custom_exception import (
    FaceEmbeddingNotFoundException,
    PaymentRequestNotFoundException,
    UserNotFoundException,
    WalletNotPermittedException,
    WalletNotFoundException,
)
from app.models.mysql.payment_request import PaymentRequest, PaymentStatus
from app.models.responses.payment_transaction_hash_response import PaymentTransactionHashResponse
from app.models.responses.payment_verify_response import PaymentVerifyResponse
from app.services.payment_service import JST, PaymentService


class TestGetUserIdFromFaceImage:
    """PaymentService.get_user_id_from_face_image の単体テスト。"""

    def _build_base64_image(self) -> str:
        image = Image.new("RGB", (1, 1), color=(255, 255, 255))
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("ascii")

    @patch("app.services.payment_service.UserRepository")
    @patch("app.services.payment_service.FaceEmbeddingRepository")
    @patch("app.services.payment_service.FaceHelper.get_embedding_from_image")
    @patch("app.services.payment_service.S3Client")
    @patch("app.services.payment_service.SsmClient")
    def test_get_user_id_from_face_image_returns_matched_user_id(
        self,
        mock_ssm_client_class,
        mock_s3_client_class,
        mock_get_embedding_from_image,
        mock_face_embedding_repository_class,
        mock_user_repository_class,
    ) -> None:
        mysql_session = Mock()
        postgres_session = Mock()
        content = self._build_base64_image()
        threshold = 0.42
        embedding = [0.1, 0.2, 0.3]
        face_info = SimpleNamespace(user_id=123)
        user = SimpleNamespace(user_id=123)
        ssm_params = SimpleNamespace(s3_endpoint="http://s3.local")
        s3_client = Mock()

        mock_ssm_client_class.return_value = ssm_params
        mock_s3_client_class.return_value = s3_client
        mock_get_embedding_from_image.return_value = embedding
        mock_face_embedding_repository = mock_face_embedding_repository_class.return_value
        mock_face_embedding_repository.get_nearest_face_embedding.return_value = face_info
        mock_user_repository = mock_user_repository_class.return_value
        mock_user_repository.get_user_by_id.return_value = user

        result = PaymentService().get_user_id_from_face_image(
            mysql_session=mysql_session,
            postgres_session=postgres_session,
            content=content,
            threshold=threshold,
        )

        mock_ssm_client_class.assert_called_once_with()
        mock_s3_client_class.assert_called_once_with(s3_endpoint=ssm_params.s3_endpoint)
        mock_get_embedding_from_image.assert_called_once()
        embedding_kwargs = mock_get_embedding_from_image.call_args.kwargs
        assert embedding_kwargs["image"].mode == "RGB"
        assert embedding_kwargs["s3_client"] is s3_client
        assert embedding_kwargs["ssm_params"] is ssm_params
        mock_face_embedding_repository.get_nearest_face_embedding.assert_called_once_with(
            postgres_session=postgres_session,
            embedding=embedding,
            threshold=threshold,
        )
        mock_user_repository.get_user_by_id.assert_called_once_with(
            mysql_session=mysql_session,
            user_id=face_info.user_id,
        )
        assert result == user.user_id

    @patch("app.services.payment_service.TeraidPayApiLog.warning")
    @patch("app.services.payment_service.UserRepository")
    @patch("app.services.payment_service.FaceEmbeddingRepository")
    @patch("app.services.payment_service.FaceHelper.get_embedding_from_image")
    @patch("app.services.payment_service.S3Client")
    @patch("app.services.payment_service.SsmClient")
    def test_get_user_id_from_face_image_raises_when_user_not_found(
        self,
        mock_ssm_client_class,
        mock_s3_client_class,
        mock_get_embedding_from_image,
        mock_face_embedding_repository_class,
        mock_user_repository_class,
        mock_warning,
    ) -> None:
        mysql_session = Mock()
        postgres_session = Mock()
        content = self._build_base64_image()
        embedding = [0.1, 0.2, 0.3]
        face_info = SimpleNamespace(user_id=123)
        ssm_params = SimpleNamespace(s3_endpoint="http://s3.local")

        mock_ssm_client_class.return_value = ssm_params
        mock_get_embedding_from_image.return_value = embedding
        mock_face_embedding_repository = mock_face_embedding_repository_class.return_value
        mock_face_embedding_repository.get_nearest_face_embedding.return_value = face_info
        mock_user_repository = mock_user_repository_class.return_value
        mock_user_repository.get_user_by_id.return_value = None

        with pytest.raises(UserNotFoundException):
            PaymentService().get_user_id_from_face_image(
                mysql_session=mysql_session,
                postgres_session=postgres_session,
                content=content,
            )

        mock_s3_client_class.assert_called_once_with(s3_endpoint=ssm_params.s3_endpoint)
        mock_face_embedding_repository.get_nearest_face_embedding.assert_called_once_with(
            postgres_session=postgres_session,
            embedding=embedding,
            threshold=0.7,
        )
        mock_user_repository.get_user_by_id.assert_called_once_with(
            mysql_session=mysql_session,
            user_id=face_info.user_id,
        )
        mock_warning.assert_called_once()

    @patch("app.services.payment_service.TeraidPayApiLog.warning")
    @patch("app.services.payment_service.UserRepository")
    @patch("app.services.payment_service.FaceEmbeddingRepository")
    @patch("app.services.payment_service.FaceHelper.get_embedding_from_image")
    @patch("app.services.payment_service.S3Client")
    @patch("app.services.payment_service.SsmClient")
    def test_get_user_id_from_face_image_raises_when_face_embedding_not_found(
        self,
        mock_ssm_client_class,
        mock_s3_client_class,
        mock_get_embedding_from_image,
        mock_face_embedding_repository_class,
        mock_user_repository_class,
        mock_warning,
    ) -> None:
        mysql_session = Mock()
        postgres_session = Mock()
        content = self._build_base64_image()
        embedding = [0.1, 0.2, 0.3]
        ssm_params = SimpleNamespace(s3_endpoint="http://s3.local")

        mock_ssm_client_class.return_value = ssm_params
        mock_get_embedding_from_image.return_value = embedding
        mock_face_embedding_repository = mock_face_embedding_repository_class.return_value
        mock_face_embedding_repository.get_nearest_face_embedding.return_value = None

        with pytest.raises(FaceEmbeddingNotFoundException):
            PaymentService().get_user_id_from_face_image(
                mysql_session=mysql_session,
                postgres_session=postgres_session,
                content=content,
            )

        mock_s3_client_class.assert_called_once_with(s3_endpoint=ssm_params.s3_endpoint)
        mock_face_embedding_repository.get_nearest_face_embedding.assert_called_once_with(
            postgres_session=postgres_session,
            embedding=embedding,
            threshold=0.7,
        )
        mock_user_repository_class.assert_not_called()
        mock_warning.assert_called_once()


class TestCreatePaymentRequest:
    """PaymentService.create_payment_request の単体テスト。"""

    @patch("app.services.payment_service.PaymentRepository")
    @patch("app.services.payment_service.UserRepository")
    @patch("app.services.payment_service.StoreRepository")
    @patch("app.services.payment_service.datetime")
    def test_create_payment_request(
        self,
        mock_datetime,
        mock_store_repository_class,
        mock_user_repository_class,
        mock_payment_repository_class,
    ) -> None:
        """wallet 情報から決済リクエストを作成し、repository に保存できることを検証する。"""
        mysql_session = Mock()
        store_id = 101
        user_id = 102
        amount = 1500
        fixed_now = datetime(2026, 4, 12, 12, 0, 0, tzinfo=JST)
        store_wallet = SimpleNamespace(
            wallet_address="0x1111111111111111111111111111111111111111",
            token_symbol="JPYC",
            chain_id=11155111,
        )
        user_wallet = SimpleNamespace(
            wallet_address="0x2222222222222222222222222222222222222222",
            token_symbol="JPYC",
            chain_id=11155111,
            is_permitted=True,
        )

        mock_datetime.now.return_value = fixed_now
        mock_store_repository = mock_store_repository_class.return_value
        mock_store_repository.get_store_wallet.return_value = store_wallet
        mock_user_repository = mock_user_repository_class.return_value
        mock_user_repository.get_user_wallet.return_value = user_wallet
        mock_payment_repository = mock_payment_repository_class.return_value
        saved_payment_request_id = 501

        def create_payment_request(mysql_session, payment_request):
            payment_request.payment_request_id = saved_payment_request_id
            return payment_request

        mock_payment_repository.create_payment_request.side_effect = create_payment_request

        result = PaymentService().create_payment_request(
            mysql_session=mysql_session,
            store_id=store_id,
            user_id=user_id,
            amount=amount,
        )

        mock_store_repository.get_store_wallet.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=store_id,
        )
        mock_user_repository.get_user_wallet.assert_called_once_with(
            mysql_session=mysql_session,
            user_id=user_id,
        )
        mock_payment_repository.create_payment_request.assert_called_once()

        payment_request_kwargs = mock_payment_repository.create_payment_request.call_args.kwargs
        assert payment_request_kwargs["mysql_session"] is mysql_session
        created_payment_request = payment_request_kwargs["payment_request"]
        assert isinstance(created_payment_request, PaymentRequest)
        assert created_payment_request.store_id == store_id
        assert created_payment_request.user_id == user_id
        assert created_payment_request.store_wallet_address == store_wallet.wallet_address
        assert created_payment_request.user_wallet_address == user_wallet.wallet_address
        assert created_payment_request.amount == amount
        assert created_payment_request.token_symbol == store_wallet.token_symbol
        assert created_payment_request.chain_id == store_wallet.chain_id
        assert created_payment_request.status is None
        assert created_payment_request.transaction_hash is None
        assert created_payment_request.expires_at == fixed_now + timedelta(minutes=10)
        assert result == saved_payment_request_id

    @pytest.mark.parametrize(
        ("store_wallet", "user_wallet"),
        [
            (
                None,
                SimpleNamespace(
                    wallet_address="0x2222222222222222222222222222222222222222",
                    token_symbol="JPYC",
                    chain_id=11155111,
                    is_permitted=True,
                ),
            ),
            (
                SimpleNamespace(
                    wallet_address="0x1111111111111111111111111111111111111111",
                    token_symbol="JPYC",
                    chain_id=11155111,
                ),
                None,
            ),
        ],
        ids=["store-wallet-not-found", "user-wallet-not-found"],
    )
    @patch("app.services.payment_service.PaymentRepository")
    @patch("app.services.payment_service.UserRepository")
    @patch("app.services.payment_service.StoreRepository")
    def test_create_payment_request_raises_when_wallet_not_found(
        self,
        mock_store_repository_class,
        mock_user_repository_class,
        mock_payment_repository_class,
        store_wallet,
        user_wallet,
    ) -> None:
        """store/user の wallet が取得できない場合は WalletNotFoundException を送出する。"""
        mysql_session = Mock()

        mock_store_repository = mock_store_repository_class.return_value
        mock_store_repository.get_store_wallet.return_value = store_wallet
        mock_user_repository = mock_user_repository_class.return_value
        mock_user_repository.get_user_wallet.return_value = user_wallet

        with pytest.raises(WalletNotFoundException):
            PaymentService().create_payment_request(
                mysql_session=mysql_session,
                store_id=101,
                user_id=102,
                amount=1500,
            )

        mock_store_repository.get_store_wallet.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=101,
        )
        if store_wallet is None:
            mock_user_repository.get_user_wallet.assert_not_called()
        else:
            mock_user_repository.get_user_wallet.assert_called_once_with(
                mysql_session=mysql_session,
                user_id=102,
            )
        mock_payment_repository_class.assert_not_called()

    @pytest.mark.parametrize(
        "user_wallet",
        [
            SimpleNamespace(
                wallet_address="0x2222222222222222222222222222222222222222",
                token_symbol="USDC",
                chain_id=11155111,
                is_permitted=True,
            ),
            SimpleNamespace(
                wallet_address="0x2222222222222222222222222222222222222222",
                token_symbol="JPYC",
                chain_id=137,
                is_permitted=True,
            ),
        ],
        ids=["token-mismatch", "chain-mismatch"],
    )
    @patch("app.services.payment_service.PaymentRepository")
    @patch("app.services.payment_service.UserRepository")
    @patch("app.services.payment_service.StoreRepository")
    def test_create_payment_request_raises_when_wallet_values_mismatch(
        self,
        mock_store_repository_class,
        mock_user_repository_class,
        mock_payment_repository_class,
        user_wallet,
    ) -> None:
        """store/user の token または chain が一致しない場合は ValueError を送出する。"""
        mysql_session = Mock()
        store_wallet = SimpleNamespace(
            wallet_address="0x1111111111111111111111111111111111111111",
            token_symbol="JPYC",
            chain_id=11155111,
        )

        mock_store_repository = mock_store_repository_class.return_value
        mock_store_repository.get_store_wallet.return_value = store_wallet
        mock_user_repository = mock_user_repository_class.return_value
        mock_user_repository.get_user_wallet.return_value = user_wallet

        with pytest.raises(ValueError):
            PaymentService().create_payment_request(
                mysql_session=mysql_session,
                store_id=101,
                user_id=102,
                amount=1500,
            )

        mock_store_repository.get_store_wallet.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=101,
        )
        mock_user_repository.get_user_wallet.assert_called_once_with(
            mysql_session=mysql_session,
            user_id=102,
        )
        mock_payment_repository_class.assert_not_called()

    @patch("app.services.payment_service.PaymentRepository")
    @patch("app.services.payment_service.UserRepository")
    @patch("app.services.payment_service.StoreRepository")
    def test_create_payment_request_raises_when_user_wallet_permit_is_incomplete(
        self,
        mock_store_repository_class,
        mock_user_repository_class,
        mock_payment_repository_class,
    ) -> None:
        """user wallet の permit 許可が未完了の場合は payment request を作成しないことを検証する。"""
        mysql_session = Mock()
        store_wallet = SimpleNamespace(
            wallet_address="0x1111111111111111111111111111111111111111",
            token_symbol="JPYC",
            chain_id=11155111,
        )
        user_wallet = SimpleNamespace(
            wallet_address="0x2222222222222222222222222222222222222222",
            token_symbol="JPYC",
            chain_id=11155111,
            is_permitted=False,
        )

        mock_store_repository = mock_store_repository_class.return_value
        mock_store_repository.get_store_wallet.return_value = store_wallet
        mock_user_repository = mock_user_repository_class.return_value
        mock_user_repository.get_user_wallet.return_value = user_wallet

        with pytest.raises(WalletNotPermittedException):
            PaymentService().create_payment_request(
                mysql_session=mysql_session,
                store_id=101,
                user_id=102,
                amount=1500,
            )

        mock_store_repository.get_store_wallet.assert_called_once_with(
            mysql_session=mysql_session,
            store_id=101,
        )
        mock_user_repository.get_user_wallet.assert_called_once_with(
            mysql_session=mysql_session,
            user_id=102,
        )
        mock_payment_repository_class.assert_not_called()


class TestExecutePayment:
    """PaymentService.execute_payment の単体テスト。"""

    @patch("app.services.payment_service.Web3")
    @patch("app.services.payment_service.HTTPProvider")
    @patch("app.services.payment_service.get_payment_processor_config")
    @patch("app.services.payment_service.get_chain_config")
    @patch("app.services.payment_service.PaymentRepository")
    def test_execute_payment(self,
                             mock_payment_repository_class,
                             mock_get_chain_config,
                             mock_get_payment_processor_config,
                             mock_http_provider_class,
                             mock_web3_class) -> None:
        """REQUESTED の payment を PaymentProcessor で実行し、transaction_hash を保存することを検証する。"""
        mysql_session = Mock()
        payment_request_id = 501
        transaction_hash = "0xabcdef1234567890"
        target_payment_request = SimpleNamespace(
            payment_request_id=payment_request_id,
            status=PaymentStatus.REQUESTED,
            transaction_hash=None,
            amount=1500,
            chain_id=11155111,
            user_wallet_address="0x2222222222222222222222222222222222222222",
            store_wallet_address="0x1111111111111111111111111111111111111111",
            expires_at=datetime(2026, 4, 12, 12, 10, 0),
        )
        mock_payment_repository = mock_payment_repository_class.return_value
        mock_payment_repository.get_payment_by_id.return_value = target_payment_request
        mock_payment_repository.update_payment_request.return_value = target_payment_request
        mock_get_chain_config.return_value = SimpleNamespace(rpc_url="https://example.invalid")
        mock_get_payment_processor_config.return_value = SimpleNamespace(
            token_contract_address="0x3333333333333333333333333333333333333333",
            payment_processor_address="0x4444444444444444444444444444444444444444",
            operator_private_key="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        )
        mock_http_provider_class.return_value = "provider"
        mock_web3 = mock_web3_class.return_value
        mock_web3.to_checksum_address.side_effect = lambda address: address
        mock_account = SimpleNamespace(
            address="0x5555555555555555555555555555555555555555",
            sign_transaction=Mock(return_value=SimpleNamespace(raw_transaction=b"signed")),
        )
        mock_web3.eth.account.from_key.return_value = mock_account
        mock_web3.eth.get_transaction_count.return_value = 7
        mock_sent_hash = Mock()
        mock_sent_hash.hex.return_value = transaction_hash
        mock_web3.eth.send_raw_transaction.return_value = mock_sent_hash
        mock_payment_processor = Mock()
        mock_pay_call = Mock()
        mock_pay_call.build_transaction.return_value = {"nonce": 7}
        mock_payment_processor.functions.pay.return_value = mock_pay_call
        mock_web3.eth.contract.return_value = mock_payment_processor

        result = PaymentService().execute_payment(
            mysql_session=mysql_session,
            payment_request_id=payment_request_id,
        )

        mock_payment_repository.get_payment_by_id.assert_called_once_with(
            mysql_session=mysql_session,
            payment_request_id=payment_request_id,
            status=PaymentStatus.REQUESTED,
        )
        mock_get_chain_config.assert_called_once_with(chain_id=target_payment_request.chain_id)
        mock_get_payment_processor_config.assert_called_once_with(chain_id=target_payment_request.chain_id)
        mock_http_provider_class.assert_called_once_with("https://example.invalid")
        mock_web3_class.assert_called_once_with("provider")
        mock_web3.eth.contract.assert_called_once()
        mock_payment_processor.functions.pay.assert_called_once_with(
            PaymentService._build_payment_id(target_payment_request),
            "0x3333333333333333333333333333333333333333",
            target_payment_request.user_wallet_address,
            target_payment_request.store_wallet_address,
            int(Decimal(str(target_payment_request.amount)) * (Decimal(10) ** 18)),
        )
        mock_pay_call.build_transaction.assert_called_once_with({
            "from": mock_account.address,
            "nonce": 7,
            "chainId": target_payment_request.chain_id,
        })
        mock_web3.eth.send_raw_transaction.assert_called_once_with(b"signed")
        mock_payment_repository.update_payment_request.assert_called_once_with(
            mysql_session=mysql_session,
            payment_request=target_payment_request,
        )
        assert target_payment_request.transaction_hash == transaction_hash
        assert target_payment_request.status == PaymentStatus.SUBMITTED
        assert result == PaymentTransactionHashResponse(
            payment_request_id=payment_request_id,
            transaction_hash=transaction_hash)

    @patch("app.services.payment_service.PaymentRepository")
    def test_execute_payment_raises_when_payment_request_not_found(
        self,
        mock_payment_repository_class,
    ) -> None:
        """REQUESTED の payment が取得できない場合は PaymentRequestNotFoundException を送出する。"""
        mysql_session = Mock()
        payment_request_id = 501
        mock_payment_repository = mock_payment_repository_class.return_value
        mock_payment_repository.get_payment_by_id.return_value = None

        with pytest.raises(PaymentRequestNotFoundException):
            PaymentService().execute_payment(
                mysql_session=mysql_session,
                payment_request_id=payment_request_id,
            )

        mock_payment_repository.get_payment_by_id.assert_called_once_with(
            mysql_session=mysql_session,
            payment_request_id=payment_request_id,
            status=PaymentStatus.REQUESTED,
        )
        mock_payment_repository.update_payment_request.assert_not_called()


class TestVerifyTransactionHash:
    """PaymentService.verify_transaction_hash の単体テスト。"""

    @patch("app.services.payment_service.Web3")
    @patch("app.services.payment_service.HTTPProvider")
    @patch("app.services.payment_service.get_chain_config")
    @patch("app.services.payment_service.PaymentRepository")
    def test_verify_transaction_hash_returns_confirming_when_receipt_not_found(
        self,
        mock_payment_repository_class,
        mock_get_chain_config,
        mock_http_provider_class,
        mock_web3_class,
    ) -> None:
        """receipt が取得できない場合は CONFIRMING に更新することを検証する。"""
        mysql_session = Mock()
        payment_request_id = 501
        transaction_hash = "0xabcdef1234567890"
        target_payment_request = SimpleNamespace(
            payment_request_id=payment_request_id,
            transaction_hash=transaction_hash,
            chain_id=11155111,
            status=PaymentStatus.SUBMITTED,
        )
        mock_payment_repository = mock_payment_repository_class.return_value
        mock_payment_repository.get_payment_by_id.return_value = target_payment_request
        mock_chain_config = SimpleNamespace(
            rpc_url="https://example.test",
            token_contract_address="0x1111111111111111111111111111111111111111",
        )
        mock_get_chain_config.return_value = mock_chain_config
        mock_http_provider = mock_http_provider_class.return_value
        mock_web3 = mock_web3_class.return_value
        mock_web3.eth.get_transaction_receipt.return_value = None

        result = PaymentService().verify_transaction_hash(
            mysql_session=mysql_session,
            payment_request_id=payment_request_id,
        )

        mock_payment_repository.get_payment_by_id.assert_called_once_with(
            mysql_session=mysql_session,
            payment_request_id=payment_request_id,
        )
        mock_get_chain_config.assert_called_once_with(chain_id=target_payment_request.chain_id)
        mock_http_provider_class.assert_called_once_with(mock_chain_config.rpc_url)
        mock_web3_class.assert_called_once_with(mock_http_provider)
        mock_web3.eth.get_transaction_receipt.assert_called_once_with(
            transaction_hash=transaction_hash,
        )
        mock_web3.eth.get_transaction.assert_not_called()
        mock_payment_repository.update_payment_request.assert_called_once_with(
            mysql_session=mysql_session,
            payment_request=target_payment_request,
        )
        assert target_payment_request.status == PaymentStatus.CONFIRMING
        assert result == PaymentVerifyResponse(
            payment_request_id=payment_request_id,
            status=PaymentStatus.CONFIRMING.value,
        )

    @patch("app.services.payment_service.Web3")
    @patch("app.services.payment_service.HTTPProvider")
    @patch("app.services.payment_service.get_chain_config")
    @patch("app.services.payment_service.PaymentRepository")
    def test_verify_transaction_hash_returns_confirming_when_transaction_not_found(
        self,
        mock_payment_repository_class,
        mock_get_chain_config,
        mock_http_provider_class,
        mock_web3_class,
    ) -> None:
        """transaction がまだ RPC で見つからない場合は CONFIRMING に更新することを検証する。"""
        mysql_session = Mock()
        payment_request_id = 501
        transaction_hash = "0xabcdef1234567890"
        target_payment_request = SimpleNamespace(
            payment_request_id=payment_request_id,
            transaction_hash=transaction_hash,
            chain_id=11155111,
            status=PaymentStatus.SUBMITTED,
        )
        mock_payment_repository = mock_payment_repository_class.return_value
        mock_payment_repository.get_payment_by_id.return_value = target_payment_request
        mock_chain_config = SimpleNamespace(
            rpc_url="https://example.test",
            token_contract_address="0x1111111111111111111111111111111111111111",
        )
        mock_get_chain_config.return_value = mock_chain_config
        mock_http_provider = mock_http_provider_class.return_value
        mock_web3 = mock_web3_class.return_value
        mock_web3.eth.get_transaction_receipt.side_effect = TransactionNotFound(
            f"Transaction with hash: {transaction_hash} not found."
        )

        result = PaymentService().verify_transaction_hash(
            mysql_session=mysql_session,
            payment_request_id=payment_request_id,
        )

        mock_payment_repository.get_payment_by_id.assert_called_once_with(
            mysql_session=mysql_session,
            payment_request_id=payment_request_id,
        )
        mock_get_chain_config.assert_called_once_with(chain_id=target_payment_request.chain_id)
        mock_http_provider_class.assert_called_once_with(mock_chain_config.rpc_url)
        mock_web3_class.assert_called_once_with(mock_http_provider)
        mock_web3.eth.get_transaction_receipt.assert_called_once_with(
            transaction_hash=transaction_hash,
        )
        mock_web3.eth.get_transaction.assert_not_called()
        mock_payment_repository.update_payment_request.assert_called_once_with(
            mysql_session=mysql_session,
            payment_request=target_payment_request,
        )
        assert target_payment_request.status == PaymentStatus.CONFIRMING
        assert result == PaymentVerifyResponse(
            payment_request_id=payment_request_id,
            status=PaymentStatus.CONFIRMING.value,
        )

    @patch("app.services.payment_service.Web3")
    @patch("app.services.payment_service.HTTPProvider")
    @patch("app.services.payment_service.get_chain_config")
    @patch("app.services.payment_service.PaymentRepository")
    def test_verify_transaction_hash_returns_tx_failed_when_receipt_status_is_zero(
        self,
        mock_payment_repository_class,
        mock_get_chain_config,
        mock_http_provider_class,
        mock_web3_class,
    ) -> None:
        """receipt.status が 0 の場合は TX_FAILED に更新することを検証する。"""
        mysql_session = Mock()
        payment_request_id = 501
        transaction_hash = "0xabcdef1234567890"
        target_payment_request = SimpleNamespace(
            payment_request_id=payment_request_id,
            transaction_hash=transaction_hash,
            chain_id=11155111,
            status=PaymentStatus.SUBMITTED,
        )
        mock_payment_repository = mock_payment_repository_class.return_value
        mock_payment_repository.get_payment_by_id.return_value = target_payment_request
        mock_get_chain_config.return_value = SimpleNamespace(
            rpc_url="https://example.test",
            token_contract_address="0x1111111111111111111111111111111111111111",
        )
        mock_web3 = mock_web3_class.return_value
        mock_web3.eth.get_transaction_receipt.return_value = SimpleNamespace(status=0)

        result = PaymentService().verify_transaction_hash(
            mysql_session=mysql_session,
            payment_request_id=payment_request_id,
        )

        mock_web3.eth.get_transaction_receipt.assert_called_once_with(
            transaction_hash=transaction_hash,
        )
        mock_web3.eth.get_transaction.assert_not_called()
        mock_payment_repository.update_payment_request.assert_called_once_with(
            mysql_session=mysql_session,
            payment_request=target_payment_request,
        )
        assert target_payment_request.status == PaymentStatus.TX_FAILED
        assert result == PaymentVerifyResponse(
            payment_request_id=payment_request_id,
            status=PaymentStatus.TX_FAILED.value,
        )
        mock_http_provider_class.assert_called_once()

    @pytest.mark.parametrize(
        ("is_validate", "expected_status"),
        [
            (True, PaymentStatus.PAID),
            (False, PaymentStatus.VERIFY_FAILED),
        ],
        ids=["valid-contract", "invalid-contract"],
    )
    @patch("app.services.payment_service.PaymentService._validate_payment_processed_event")
    @patch("app.services.payment_service.Web3")
    @patch("app.services.payment_service.HTTPProvider")
    @patch("app.services.payment_service.get_payment_processor_config")
    @patch("app.services.payment_service.get_chain_config")
    @patch("app.services.payment_service.PaymentRepository")
    def test_verify_transaction_hash_updates_status_by_contract_validation(
        self,
        mock_payment_repository_class,
        mock_get_chain_config,
        mock_get_payment_processor_config,
        mock_http_provider_class,
        mock_web3_class,
        mock_validate_payment_processed_event,
        is_validate,
        expected_status,
    ) -> None:
        """transaction の検証結果に応じて PAID/VERIFY_FAILED に更新することを検証する。"""
        mysql_session = Mock()
        payment_request_id = 501
        transaction_hash = "0xabcdef1234567890"
        target_payment_request = SimpleNamespace(
            payment_request_id=payment_request_id,
            transaction_hash=transaction_hash,
            chain_id=11155111,
            status=PaymentStatus.SUBMITTED,
            amount=1500,
            user_wallet_address="0x2222222222222222222222222222222222222222",
            store_wallet_address="0x3333333333333333333333333333333333333333",
        )
        mock_payment_repository = mock_payment_repository_class.return_value
        mock_payment_repository.get_payment_by_id.return_value = target_payment_request
        mock_chain_config = SimpleNamespace(
            rpc_url="https://example.test",
            token_contract_address="0x1111111111111111111111111111111111111111",
        )
        mock_get_chain_config.return_value = mock_chain_config
        mock_get_payment_processor_config.return_value = SimpleNamespace(
            token_contract_address="0x1111111111111111111111111111111111111111",
            payment_processor_address="0x4444444444444444444444444444444444444444",
            operator_private_key="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        )
        mock_web3 = mock_web3_class.return_value
        receipt = SimpleNamespace(status=1)
        mock_web3.eth.get_transaction_receipt.return_value = receipt
        mock_web3.to_checksum_address.side_effect = lambda address: address
        payment_processor = mock_web3.eth.contract.return_value
        mock_validate_payment_processed_event.return_value = is_validate

        result = PaymentService().verify_transaction_hash(
            mysql_session=mysql_session,
            payment_request_id=payment_request_id,
        )

        mock_web3.eth.get_transaction_receipt.assert_called_once_with(
            transaction_hash=transaction_hash,
        )
        mock_web3.eth.get_transaction.assert_not_called()
        mock_get_payment_processor_config.assert_called_once_with(chain_id=target_payment_request.chain_id)
        mock_web3.eth.contract.assert_called_once()
        mock_validate_payment_processed_event.assert_called_once_with(
            payment_request=target_payment_request,
            receipt=receipt,
            payment_processor=payment_processor,
            token_contract_address="0x1111111111111111111111111111111111111111",
        )
        mock_payment_repository.update_payment_request.assert_called_once_with(
            mysql_session=mysql_session,
            payment_request=target_payment_request,
        )
        assert target_payment_request.status == expected_status
        assert result == PaymentVerifyResponse(
            payment_request_id=payment_request_id,
            status=expected_status.value,
        )
        mock_http_provider_class.assert_called_once()

    @pytest.mark.parametrize(
        "target_payment_request",
        [
            None,
            SimpleNamespace(
                payment_request_id=501,
                transaction_hash=None,
                chain_id=11155111,
                status=PaymentStatus.SUBMITTED,
            ),
            SimpleNamespace(
                payment_request_id=501,
                transaction_hash="",
                chain_id=11155111,
                status=PaymentStatus.SUBMITTED,
            ),
        ],
        ids=["payment-request-not-found", "transaction-hash-not-found", "transaction-hash-empty"],
    )
    @patch("app.services.payment_service.Web3")
    @patch("app.services.payment_service.HTTPProvider")
    @patch("app.services.payment_service.get_chain_config")
    @patch("app.services.payment_service.PaymentRepository")
    def test_verify_transaction_hash_raises_when_payment_request_is_invalid(
        self,
        mock_payment_repository_class,
        mock_get_chain_config,
        mock_http_provider_class,
        mock_web3_class,
        target_payment_request,
    ) -> None:
        """payment または transaction_hash が取得できない場合は例外を送出する。"""
        mysql_session = Mock()
        payment_request_id = 501
        mock_payment_repository = mock_payment_repository_class.return_value
        mock_payment_repository.get_payment_by_id.return_value = target_payment_request

        with pytest.raises(PaymentRequestNotFoundException):
            PaymentService().verify_transaction_hash(
                mysql_session=mysql_session,
                payment_request_id=payment_request_id,
            )

        mock_payment_repository.get_payment_by_id.assert_called_once_with(
            mysql_session=mysql_session,
            payment_request_id=payment_request_id,
        )
        mock_payment_repository.update_payment_request.assert_not_called()
        mock_get_chain_config.assert_not_called()
        mock_http_provider_class.assert_not_called()
        mock_web3_class.assert_not_called()


class TestValidatePaymentProcessedEvent:
    """PaymentService._validate_payment_processed_event tests."""

    token_contract_address = "0x1111111111111111111111111111111111111111"
    user_wallet_address = "0x2222222222222222222222222222222222222222"
    store_wallet_address = "0x3333333333333333333333333333333333333333"

    def _build_payment_request(self, payment_request_id=501, amount=1500):
        return SimpleNamespace(
            payment_request_id=payment_request_id,
            chain_id=11155111,
            user_wallet_address=self.user_wallet_address,
            store_wallet_address=self.store_wallet_address,
            amount=amount,
            expires_at=datetime(2026, 4, 12, 12, 10, 0),
        )

    def _build_payment_processor(self, events):
        payment_processor = Mock()
        payment_processor.events.PaymentProcessed.return_value.process_receipt.return_value = events
        return payment_processor

    def _build_event(self, **overrides):
        args = {
            "paymentId": int(501).to_bytes(32, byteorder="big"),
            "token": self.token_contract_address,
            "from": self.user_wallet_address,
            "to": self.store_wallet_address,
            "amount": 1500 * 10**18,
            "operator": "0x4444444444444444444444444444444444444444",
        }
        args.update(overrides)
        return {"args": args}

    def test_validate_payment_processed_event_returns_true_when_event_matches_payment_request(self) -> None:
        """transaction の contract/from/input が payment_request と一致する場合 True を返す。"""
        payment_request = self._build_payment_request()
        receipt = SimpleNamespace()
        payment_processor = self._build_payment_processor([self._build_event()])

        result = PaymentService()._validate_payment_processed_event(
            payment_request=payment_request,
            receipt=receipt,
            payment_processor=payment_processor,
            token_contract_address=self.token_contract_address,
        )

        assert result is True

    @pytest.mark.parametrize(
        ("payment_request_overrides", "event_overrides", "token_contract_address"),
        [
            ({"payment_request_id": 502}, {}, token_contract_address),
            ({}, {"token": "0x4444444444444444444444444444444444444444"}, token_contract_address),
            ({}, {"from": "0x5555555555555555555555555555555555555555"}, token_contract_address),
            ({}, {"to": "0x6666666666666666666666666666666666666666"}, token_contract_address),
            ({"amount": 1501}, {}, token_contract_address),
        ],
        ids=[
            "payment-id-mismatch",
            "token-address-mismatch",
            "from-address-mismatch",
            "to-address-mismatch",
            "amount-mismatch",
        ],
    )
    def test_validate_payment_processed_event_returns_false_when_event_does_not_match_payment_request(
        self,
        payment_request_overrides,
        event_overrides,
        token_contract_address,
    ) -> None:
        """transaction の検証対象値が一致しない場合 False を返す。"""
        payment_request = self._build_payment_request(**payment_request_overrides)
        receipt = SimpleNamespace()
        payment_processor = self._build_payment_processor([self._build_event(**event_overrides)])

        result = PaymentService()._validate_payment_processed_event(
            payment_request=payment_request,
            receipt=receipt,
            payment_processor=payment_processor,
            token_contract_address=token_contract_address,
        )

        assert result is False
