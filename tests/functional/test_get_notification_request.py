import datetime

import pytest



class TestGetNotification:

    @pytest.mark.parametrize(
        "notification_request_id, source_identifier",
        [
            (
                "identifier_for_data_exists",
                ""
            ),
            (
                "identifier_for_no_data",
                ""
            ),
            (
                "identifier_for_http_request_exception",
                ""
            ),
            (
                "",
                ""
            ),
        ],
    )
    async def test_get_notification(
        self,
        test_cli,
        notification_request_id,
        source_identifier
    ):
        """
        Test the get-notification endpoint
        """
        response_object = await test_cli.get(
            "/get-notification",
            headers={"Content-Type": "application/json"},
            params={
                "notification_request_id": notification_request_id,
                "source_identifier": source_identifier
            }
        )
        result = response_object.json()

        if notification_request_id == "identifier_for_http_request_exception":
            response_object.status_code == 500
        elif notification_request_id or source_identifier:
            assert response_object.status_code == 200
        else:
            assert response_object.status_code == 400

        if notification_request_id == "identifier_for_data_exists":
            assert len(result["data"]["notifications"]) >= 1
        elif notification_request_id == "identifier_for_no_data":
            assert len(result["data"]["notifications"]) == 0