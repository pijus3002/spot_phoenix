import json
import socket
import time
from datetime import datetime, timezone
import pika
import requests

#Listener config
from config import (
    METADATA_URL,
    RABBITMQ_HOST,
    RABBITMQ_PORT,
    RABBITMQ_USER,
    RABBITMQ_PASSWORD,
    QUEUE_NAME,
    POLL_INTERVAL,
    RESOURCE_GROUP
)

VM_NAME = socket.gethostname()
seen_events = set()

#Connecting to a RabbitMQ server
def connectRabbitmq():
    credentials = pika.PlainCredentials(RABBITMQ_USER,RABBITMQ_PASSWORD)
    while True:
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=RABBITMQ_HOST,
                    port=RABBITMQ_PORT,
                    credentials=credentials,
                    heartbeat=30,
                    blocked_connection_timeout=30
                )
            )
            channel = connection.channel()
            channel.queue_declare(queue=QUEUE_NAME,durable=True)
            print("Connected to RabbitMQ")
            return connection, channel
        except Exception as e:
            print(f"Connection failed: {e}")
            print("Retrying in 5 seconds...")
            time.sleep(5)

#Getting events from metadata endpoint
def getEvents():
    response = requests.get(
        METADATA_URL,
        headers={"Metadata": "true"},
        timeout=10
    )
    response.raise_for_status()
    return response.json()

#Making json message for RabbitMQ
def buildMessage(event):
    return {
        "event_id": event.get("EventId"),
        "event_type": event.get("EventType"),
        "vm_name": VM_NAME,
        "resource_group": RESOURCE_GROUP,
        "not_before": event.get("NotBefore"),
        "detected_at": datetime.now(timezone.utc).isoformat(),
    }

#Sending message via pika to RabbitMQ
def publishEvent(channel, event):
    message = buildMessage(event)
    channel.basic_publish(
        exchange="",
        routing_key=QUEUE_NAME,
        body=json.dumps(message),
        properties=pika.BasicProperties(delivery_mode=2)
        )

def main():
    connection, channel = connectRabbitmq()
    #Some info about VM and RabbitMQ setup
    print("Azure Spot eviction listener started")
    print(f"VM name: {VM_NAME}")
    print(f"RabbitMQ host: {RABBITMQ_HOST}")
    print(f"Queue: {QUEUE_NAME}")
    while True:
        try:
            metadata = getEvents()
            events = metadata.get("Events", [])
            for event in events:
                event_type = event.get("EventType")
                event_id = event.get("EventId")
                if (event_type != "Preempt" or event_id in seen_events):
                    continue
                print("Detected eviction event!")
                try:
                    publishEvent(channel, event)
                    seen_events.add(event_id)
                except Exception as e:
                    print(f"Publish failed: {e}")
                    print("Reconnecting to RabbitMQ...")
                    connection, channel = connectRabbitmq()
        except Exception as e:
            print(f"Listener error: {e}")
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
