class TestExecutePayment:
    def test_execute_payment_endpoint_is_not_public(
        self,
        client,
    ) -> None:
        response = client.post("/payment/request/501/execute")

        assert response.status_code == 404
