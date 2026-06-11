import os
#RabbitMQ connetion setup
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "20.86.149.24")
RABBITMQ_PORT = os.getenv("RABBITMQ_PORT", "5672")

RABBITMQ_USER = os.getenv("RABBITMQ_USER", "pijus")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "qwerty123")

QUEUE_NAME = os.getenv("QUEUE_NAME", "spot-eviction-events")
POLL_INTERVAL = 1

#Azure setup
RESOURCE_GROUP = os.getenv("RESOURCE_GROUP", "eviction-test_group")
METADATA_URL = ("http://169.254.169.254/metadata/scheduledevents?api-version=2020-07-01")
