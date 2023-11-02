from urllib.parse import urlparse
from tests.mock_resources.aws.moto_server import MockServers

from torpedo.common_utils import json_file_to_dict


def mock_sqs_queues(path:str):
    config_file_path = path + "/config.json"
    service_config = json_file_to_dict(config_file_path)

    trigger_notifications_conf = service_config["TRIGGER_NOTIFICATIONS"]
    sqs_config = trigger_notifications_conf["SQS"]
    config_endpoint_url = sqs_config["SQS_ENDPOINT_URL"]
    parsed_url = urlparse(config_endpoint_url)

    endpoint_url = MockServers.setup_server(parsed_url.hostname, parsed_url.port)

    high_priority_queue = trigger_notifications_conf["HIGH_PRIORITY"]["QUEUE_NAME"]
    medium_priority_queue = trigger_notifications_conf["MEDIUM_PRIORITY"]["QUEUE_NAME"]
    low_priority_queue = trigger_notifications_conf["LOW_PRIORITY"]["QUEUE_NAME"]

    create_queue(high_priority_queue, sqs_config["SQS_REGION"], endpoint_url)
    create_queue(medium_priority_queue, sqs_config["SQS_REGION"], endpoint_url)
    create_queue(low_priority_queue, sqs_config["SQS_REGION"], endpoint_url)

    return


def create_queue(name, region, endpoint_url):
    import boto3
    sqs_resource = boto3.resource(
        "sqs",
        endpoint_url=endpoint_url,
        region_name=region,
        aws_access_key_id="",
        aws_secret_access_key=""
    )
    sqs_resource.create_queue(QueueName=name)
