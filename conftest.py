import asyncio
import os

import pytest
from sanic import Sanic
from torpedo import Host, send_response
from torpedo.exceptions import HTTPRequestException
from app.routes import blueprint_group
from app.listeners import listeners
from pytest_sanic.utils import TestClient

from app.constants import EventPriority
from app.services.event_notification import EventNotification


@pytest.fixture(scope="session")
def loop():
    """
    Default event loop, you should only use this event loop in your tests.
    """
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def sanic_client(loop):
    """
    Create a TestClient instance for test easy use.
    test_client(app, **kwargs)
    """
    clients = []

    async def create_client(app, **kwargs):
        client = TestClient(app, **kwargs)
        await client.start_server()
        clients.append(client)
        return client

    yield create_client

    # Clean up
    if clients:
        for cli in clients:
            loop.run_until_complete(cli.close())


@pytest.fixture(scope="session")
async def app():
    """
    Create an app for tests
    This app works as a dummy app used to mock the outbound http calls (be it inter-service calls or calls to 3rd party applications)
    Add all the external routes you want to mock with request and response
    """
    app = Sanic("notification_gateway")

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

    @app.route("/prepare-notification", methods=["POST"])
    async def send_notification_sync(request):
        request_data = request.custom_json()
        if request_data["source_identifier"] == "raise_500":
            raise HTTPRequestException("Intentional 500 error raised")
        data = {
            "channels": {}
        }
        return send_response(data=data)

    yield app


@pytest.fixture(scope="session")
def test_cli(loop, app, sanic_client):
    """Setup a test sanic app"""
    Host._listeners = listeners
    client = Host.test_setup(
        loop,
        sanic_client,
        "app.service_clients",
        app,
        blueprint_group,
        gen_schemas=False,
        db_config=None
    )
    # Update host for critical priority publisher
    EventNotification.HANDLERS[EventPriority.CRITICAL]._host = "http://localhost:{}".format(client.port)

    # Mock SQS queues
    from tests.mock_resources.aws.mock_sqs import mock_sqs_queues
    mock_sqs_queues(os.getcwd())

    return client
