from app.constants import NotificationChannels, EventPriority


class Event:

    def __init__(self, event_dict: dict):
        self.id = event_dict['id']
        self.app_name = event_dict['app_name']
        self.event_name = event_dict['event_name']
        self.actions = event_dict['actions'] or dict()
        self.meta_info = event_dict['meta_info'] or dict()
        self.priority = EventPriority(self.meta_info.get('priority'))

    def any_channel_active(self) -> bool:
        return bool(sum(self.actions.values()))

    def is_email_mandatory(self) -> bool:
        return bool(sum([self.actions.get(channel, 0) for channel in NotificationChannels.email_mandatory_channels()]))

    def is_mobile_mandatory(self) -> bool:
        return bool(sum([self.actions.get(channel, 0) for channel in NotificationChannels.mobile_mandatory_channels()]))

    def get_active_channels(self):
        return [key for key in self.actions if self.actions[key] == 1]

    @property
    def dynamic_channel_allowed(self):
        return self.meta_info.get("dynamic_channels", False)
    