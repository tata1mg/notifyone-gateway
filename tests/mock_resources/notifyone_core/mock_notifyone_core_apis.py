from sanic import Sanic
from torpedo import send_response
from torpedo.exceptions import HTTPRequestException


class MockNotifyOneCoreApis:

    @classmethod
    def mock_apis(cls, app:Sanic):
        cls._mock_get_custom_event_api(app)
        cls._mock_get_notifications_api(app)
        cls._mock_prepare_notifications_api(app)

    @classmethod
    def _mock_get_custom_event_api(cls, app: Sanic):

        @app.route("/events/custom", methods=["GET"])
        async def get_events_custom(request):
            # header variable based api response body and status control
            success_data = [
                {
                    "id": 101,
                    "event_name": "order_placed",
                    "app_name": "off",
                    "actions": {
                        "sms": 0,
                        "email": 0
                    },
                    "meta_info": {"priority": "low"}
                },
                {
                    "id": 102,
                    "event_name": "order_delivered",
                    "app_name": "off",
                    "actions": {
                        "sms": 1,
                        "email": 1
                    },
                    "meta_info": {"priority": "high"}
                },
                {
                    "id": 103,
                    "event_name": "send_otp",
                    "app_name": "off",
                    "actions": {
                        "sms": 1,
                        "email": 1
                    },
                    "meta_info": {"priority": "critical"}
                }
            ]
            return send_response(data=success_data)
        return

    @classmethod
    def _mock_get_notifications_api(cls, app: Sanic):
        @app.route("/notifications/<notification_request_id:str>", methods=["GET"])
        async def get_notifications(request, notification_request_id: str):
            # header variable based api response body and status control
            if notification_request_id == "identifier_for_no_data":
                data = {
                    "notifications": []
                }
            elif notification_request_id == "identifier_for_data_exists":
                data = {
                    "notifications": [
                        {
                            "id": 2,
                            "event_id": 1,
                            "notification_request_id": "5873e3ec-08d3-4f0f-b298-05422df9cf1d",
                            "channel": "email",
                            "sent_to": "abc@gmail.com",
                            "source_identifier": "ID1212122",
                            "operator": "AWS_SES",
                            "operator_event_id": None,
                            "message": "Error case",
                            "metadata": "Unable to locate credentials",
                            "created": 1698405253,
                            "updated": 1698405258,
                            "status": "FAILED"
                        }
                    ]
                }
            else:
                raise HTTPRequestException("Something went wrong")
            return send_response(data=data)
        return

    @classmethod
    def _mock_prepare_notifications_api(cls, app: Sanic):
        @app.route("/prepare-notification", methods=["POST"])
        async def send_notification_sync(request):
            request_data = request.custom_json()
            if request_data["source_identifier"] == "raise_500":
                raise HTTPRequestException("Intentional 500 error raised")
            data = {
                "channels": {}
            }
            return send_response(data=data)
        return
