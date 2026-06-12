import json
import time
import pika
from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.trafficmanager import TrafficManagerManagementClient

from config import (
    RABBITMQ_HOST,
    RABBITMQ_PORT,
    RABBITMQ_USER,
    RABBITMQ_PASSWORD,
    QUEUE_NAME,
    SUBSCRIPTION_ID,
    RESTART_COUNTDOWN_SECONDS,
    TRAFFIC_MANAGER_PROFILE_NAME,
    TRAFFIC_MANAGER_ENDPOINT_NAME
)

#Conneting to RabbitMQ
def connectRabbitmq():
    credentials = pika.PlainCredentials(RABBITMQ_USER,RABBITMQ_PASSWORD)
    while True:
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=RABBITMQ_HOST,
                    port=RABBITMQ_PORT,
                    credentials=credentials,
                    heartbeat=120,
                    blocked_connection_timeout=120,
                )
            )
            channel = connection.channel()
            channel.queue_declare(queue=QUEUE_NAME, durable=True)
            channel.basic_qos(prefetch_count=1) 
            print("Connected to RabbitMQ")
            return connection, channel
        except Exception as e:
            print(f"Connection failed: {e}")
            print("Retrying in 5 seconds...")
            time.sleep(5)

#Access to azure API
def getClient():
    credential = DefaultAzureCredential()
    return ComputeManagementClient(credential,SUBSCRIPTION_ID)

def getTrafficManagerClient():
    credential = DefaultAzureCredential()
    return TrafficManagerManagementClient(credential,SUBSCRIPTION_ID)

#disable/enable traffic manager endpoint
def setTrafficEndpointStatus(event, status):
    resource_group = event.get("resource_group")
    if not resource_group:
        raise ValueError("Missing resource_group")
    tm_client = getTrafficManagerClient()
    endpoint = tm_client.endpoints.get(
        resource_group,
        TRAFFIC_MANAGER_PROFILE_NAME,
        "externalEndpoints",
        TRAFFIC_MANAGER_ENDPOINT_NAME
    )
    endpoint.endpoint_status = status
    tm_client.endpoints.create_or_update(
        resource_group,
        TRAFFIC_MANAGER_PROFILE_NAME,
        "externalEndpoints",
        TRAFFIC_MANAGER_ENDPOINT_NAME,
        endpoint
    )
    print(f"Traffic Manager endpoint set to {status}")

#Checking is VM on
def getPowerState(compute_client, resource_group, vm_name):
    instance_view = compute_client.virtual_machines.instance_view(resource_group,vm_name)
    for status in instance_view.statuses:
        if status.code.startswith("PowerState/"):
            return status.code
    return "N/A"

#Starting VM after eviction
def startVm(event):
    vm_name = event.get("vm_name")
    resource_group = event.get("resource_group")
    if not vm_name or not resource_group:
        raise ValueError("Missing vm_name/resource_group")
    compute_client = getClient()
    print(f"Starting [{vm_name}] in [{resource_group}]")
    poller = compute_client.virtual_machines.begin_start(resource_group,vm_name)
    poller.result()
    power_state = getPowerState(compute_client,resource_group,vm_name)
    if power_state == "PowerState/running":
        print(f"[{vm_name}] is running")
        return True
    print(f"[{vm_name}] is not running")
    return False

#Whole eviction processing algorithm
def onMessage(channel, method, properties, body):
    try:
        event = json.loads(body)
        if event.get("event_type") != "Preempt":
            channel.basic_ack(delivery_tag=method.delivery_tag)
            return
        print("Received eviction event:")
        print(json.dumps(event, indent=2))
        setTrafficEndpointStatus(event, "Disabled")
        print(f"Recovery attempt in {RESTART_COUNTDOWN_SECONDS} seconds")
        time.sleep(RESTART_COUNTDOWN_SECONDS)
        started = startVm(event)
        
        if started:
            setTrafficEndpointStatus(event, "Enabled")
            channel.basic_ack(delivery_tag=method.delivery_tag)
            print("VM recovered.")
        else:
            print("VM did not start.")
            channel.basic_nack(delivery_tag=method.delivery_tag,requeue=True)
    except Exception as e:
        print(f"Worker failed: {e}")
        channel.basic_nack(delivery_tag=method.delivery_tag,requeue=True)

#Main function, calling processing algorithm on new message in RabbitMQ
def main():
    connection, channel = connectRabbitmq()
    channel.basic_consume(queue=QUEUE_NAME,on_message_callback=onMessage)
    print("Worker started. Waiting for eviction events...")
    channel.start_consuming()

if __name__ == "__main__":
    main()
