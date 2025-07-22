from sanic import Blueprint
from torpedo import Request, send_response

from app.service_clients import NotifyOneCoreClient

event_update_blueprint = Blueprint("event_update", version=4)


@event_update_blueprint.route(
    "/handle-email-template-update", methods=["POST"], name="handle_email_template_update"
)
async def handle_email_template_update(request: Request):
    """
    Endpoint to trigger event based notifications
    """
    request_payload = request.custom_json()
    data = await NotifyOneCoreClient.handle_email_template_update(request_payload)
    return send_response(data=data)
