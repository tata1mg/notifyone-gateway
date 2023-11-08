import asyncio
import os

import pytest
from sanic import Sanic
from torpedo import Host
from app.routes import blueprint_group
from app.listeners import listeners
from pytest_sanic.utils import TestClient

from app.constants import EventPriority
from app.services.event_notification import EventNotification

from tests.mock_resources.notifyone_core.mock_notifyone_core_apis import MockNotifyOneCoreApis


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
    MockNotifyOneCoreApis.mock_apis(app)
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
