import json
import logging

from torpedo import send_response
from sanic import Blueprint, Request

logger = logging.getLogger()

config_bp = Blueprint("config", url_prefix="/config")


@config_bp.get("/")
async def get_config(req: Request):
    config = req.app.config
    logger.info("logging app config for debugging %s", config)

    return send_response(data=str(config))
