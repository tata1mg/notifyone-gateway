import asyncio
import copy
import logging

from app.models import Event
from app.service_clients import NotifyOneCoreClient

logger = logging.getLogger()


class Notifications:

    _lock = asyncio.Lock()
    _sync_delay = 10
    _event_attributes = ['actions', 'event_type', 'meta_info']

    # In-memory cache of app events mapping
    _APP_EVENTS = dict()

    @classmethod
    async def app_events(cls):
        """
        Return app-events mapping from in-memory
        If the mapping is not already initialized, initialize it and return
        As initialization is costly, use asyncio lock to prevent concurrent initializations
        """
        if not cls._APP_EVENTS:
            # Initialize app events mapping
            async with cls._lock:
                if not cls._APP_EVENTS:
                    await cls.initialize_app_events()
                return cls._APP_EVENTS
        else:
            return cls._APP_EVENTS

    @classmethod
    async def refresh_app_events_periodically(cls):
        # sleep for cls._sync_delay seconds
        await asyncio.shield(asyncio.sleep(cls._sync_delay))
        logger.info('Syncing app events after {} seconds'.format(cls._sync_delay))
        # refresh connections list
        try:
            await cls.initialize_app_events()
        except Exception as e:
            logger.error('refresh_app_events_periodically failed with error - {}'.format(str(e)))
        finally:
            # recursive call
            asyncio.create_task(cls.refresh_app_events_periodically())

    @classmethod
    async def initialize_app_events(cls):
        """
        Fetch app events from the downstream, format and load in-memory
        """
        app_events = cls._APP_EVENTS
        all_events = await NotifyOneCoreClient.get_events_custom(
            attributes=cls._event_attributes
        )
        if all_events:
            app_events = cls._create_app_events_mapping(all_events)
        cls._APP_EVENTS = app_events

    @staticmethod
    def _create_app_events_mapping(events: list) -> dict:
        app_event_mapping = dict()
        for event in events:
            app_event_mapping[str(event['id'])] = copy.deepcopy(event)
        return app_event_mapping

    @classmethod
    async def validate_event(cls, app_name, event_name) -> bool:
        app_events = await cls.app_events()
        if app_name in app_events and event_name in app_events[app_name]:
            return True
        return False

    @classmethod
    async def get_event_by_id(cls, event_id:str) -> Event:
        event = None
        app_events = await cls.app_events()
        if event_id in app_events:
            event = Event(app_events[event_id])
        return event

    @classmethod
    async def get_event(cls, app_name, event_name) -> Event:
        event = None
        app_events = await cls.app_events()
        if app_name in app_events and event_name in app_events[app_name]:
            event = Event(app_events[app_name][event_name])
        return event

    @classmethod
    async def get_event_notification(cls, notification_request_id):
        return await NotifyOneCoreClient.get_sent_notifications_by_notification_request_id(notification_request_id)
