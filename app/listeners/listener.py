import asyncio

from torpedo.constants import ListenerEventTypes

from app.services import EventNotification


async def setup_dispatch_notification(app, loop):
    EventNotification.setup()


other_listeners = [
    (setup_dispatch_notification, ListenerEventTypes.AFTER_SERVER_START.value)
]
