from sanic import Blueprint

from app.routes.notifications.notification import event_notification_blueprint
from .get_config import config_bp
from .event_update import event_update_blueprint

blueprint_group = Blueprint.group(
    event_notification_blueprint,
    config_bp,
    event_update_blueprint
)