import json
import uuid


def generate_uuid():
    return str(uuid.uuid4())


def json_dumps(data):
    return json.dumps(data)
