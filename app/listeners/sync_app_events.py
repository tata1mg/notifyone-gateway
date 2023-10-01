import asyncio

from torpedo.constants import ListenerEventTypes

from app.services import Notifications


async def load_app_events(app, loop):
    asyncio.create_task(Notifications.app_events())


async def setup_app_events_periodic_refresh(app, loop):
    # Refresh app events mapping periodically
    asyncio.create_task(Notifications.refresh_app_events_periodically())

sync_app_events_listeners = [
    (setup_app_events_periodic_refresh, ListenerEventTypes.AFTER_SERVER_START.value),
    (load_app_events, ListenerEventTypes.AFTER_SERVER_START.value)
]
