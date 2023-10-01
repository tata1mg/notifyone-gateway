from sanic import Blueprint

from app.routes.notifications.notification import event_notification_blueprint

blueprint_group = Blueprint.group(
    event_notification_blueprint
)