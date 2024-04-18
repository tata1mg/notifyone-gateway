import pytest
from app.constants import ErrorMessages
from app.utilities import json_dumps
from app.utilities.pubsub.sqs import SQSWrapper


class TestSendNotification:

    @pytest.mark.parametrize(
        "event_id, source_identifier, to",
        [
            (
                # missing event id case
                None,
                "PO1211212121",
                {
                    "email": [],
                    "mobile":[],
                    "device": []
                }
            ),
            (
                # missing source_identifier case
                101,
                None,
                {
                    "email": [],
                    "mobile":[],
                    "device": []
                }
            ),
            (
                # Invalid email case
                101,
                "PO12121212",
                {
                    "email": ["wrong.email.com"],
                    "mobile": [],
                    "device": []
                }
            ),
            (
                # Invalid mobile case
                101,
                "PO12121212",
                {
                    "email": [],
                    "mobile": ["787211212221"],
                    "device": []
                }
            ),
            (
                # Invalid mobile case
                101,
                "PO12121212",
                {
                    "email": ["abc@mail.com"],
                    "mobile": ["7800000000"],
                    "device": []
                }
            ),
            (
                # Async processing
                102,
                "PO12121212",
                {
                    "email": ["abc@mail.com"],
                    "mobile": ["7800000000"],
                    "device": []
                }
            ),
            (
                # Sync processing - 200OK case
                103,
                "PO12121212",
                {
                    "email": ["abc@mail.com"],
                    "mobile": ["7800000000"],
                    "device": []
                }
            ),
            (
                # Sync processing - non 200 case
                103,
                "raise_500",
                {
                    "email": ["abc@mail.com"],
                    "mobile": ["7800000000"],
                    "device": []
                }
            )
        ],
    )
    async def test_send_notification(
        self, test_cli, event_id, source_identifier, to
    ):
        """
        test the send-notification endpoint
        """
        data = {
            "event_id": event_id,
            "source_identifier": source_identifier,
            "to": to,
            "channels": {
                "email": {
                    "sender": {
                        "name": "Tata 1mg",
                        "address": "xyz@1mg.com"
                    },
                    "reply_to": "string"
                }
            },
            "attachments": [
                {
                    "url": "https://1mg-odin-production.s3.ap-south-1.amazonaws.com/upload/sales_orders/42550349/6f55151e-adb5-4171-8fe2-5eb6599eafb7.pdf",
                    "filename": "report.pdf"
                }
            ],
            "body": {
                "order": {
                    "order_id": "PO21212121"
                }
            }
        }
        response_object = await test_cli.post(
            "/send-notification",
            headers={"Content-Type": "application/json"},
            data=json_dumps(data)
        )
        result = response_object.json()
        if not (event_id and source_identifier):
            assert response_object.status_code == 400
            assert result["error"]["message"] in [ErrorMessages.MISSING_REQUIRED_PARAMS.value.format("event_id"), ErrorMessages.MISSING_REQUIRED_PARAMS.value.format("source_identifier")]
        elif to.get("email") and to.get("email")[0] == "wrong.email.com":
            assert response_object.status_code == 400
            assert result["error"]["message"] == ErrorMessages.INVALID_EMAIL_FORMAT.value
        elif to.get("mobile") and to.get("mobile")[0] == "787211212221":
            assert response_object.status_code == 400
            assert result["error"]["message"] == ErrorMessages.INVALID_MOBILE_FORMAT.value
        elif event_id == 101:
            assert response_object.status_code == 400
            assert result["error"]["message"] == ErrorMessages.NO_CHANNEL_ACTIVE.value

        if event_id == 102:
            assert response_object.status_code == 200

        elif event_id == 103 and source_identifier == "PO12121212":
            assert response_object.status_code == 200
            assert result["data"]["processing_type"] == "SYNC"
            assert result["data"].get("request_id")
            assert result["data"].get("message")
        elif event_id == 103 and source_identifier == "raise_500":
            assert response_object.status_code == 400
            # assert result["data"]["processing_type"] == "SYNC"
            # assert result["data"].get("request_id")
            # assert result["data"].get("message")

    async def test_send_notification_large_payload(
            self, test_cli
    ):
        """
        test the send-notification endpoint for large payloads
        """
        data = {
            "event_id": 103,
            "source_identifier": "PO12121212121",
            "to": {
                    "email": ["abc@mail.com"],
                    "mobile": ["7800000000"],
                    "device": []
                },
            "channels": {
                "email": {
                    "sender": {
                        "name": "Tata 1mg",
                        "address": "xyz@1mg.com"
                    },
                    "reply_to": "string"
                }
            },
            "attachments": [
                {
                    "url": "https://1mg-odin-production.s3.ap-south-1.amazonaws.com/upload/sales_orders/42550349/6f55151e-adb5-4171-8fe2-5eb6599eafb7.pdf",
                    "filename": "report.pdf"
                }
            ],
            "body": {
                "order": {
                    "order_id": "PO21212121"
                }
            }
        }

        counter = 0
        while not SQSWrapper.check_if_compression_needed(json_dumps(data)):
            counter += 1
            for i in range(100000):
                data['body']['order'][str(counter) + 'order_id' + str(i)] = 'PO21212121' + str(i)

        response_object = await test_cli.post(
            "/send-notification",
            headers={"Content-Type": "application/json"},
            data=json_dumps(data)
        )
        result = response_object.json()
        assert response_object.status_code == 200
