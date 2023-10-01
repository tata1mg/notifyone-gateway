import json
import uuid


def generate_uuid():
    return str(uuid.uuid4())


def json_dumps(data):
    return json.dumps(data)


def json_loads(data_str):
    return json.loads(data_str)
