# Spot Phoenix

## Overview

Spot Phoenix is an event-driven system designed to handle
Azure Spot VM eviction events.

The system continuously monitors Azure Scheduled Events metadata endpoints
for eviction notifications. When an eviction event is detected, it is
published to a RabbitMQ queue.

A worker service consumes eviction events and performs contingency actions,
such as:
- removing the VM from traffic routing
- disabling monitoring
- waiting for a set delay and attempting VM restart or recovery

---

# Goals

- Detect Azure Spot VM eviction warnings
- Put eviction events into a message queue
- Execute automated contingency actions
- Attempt recovery after a set delay

---

# Architecture

```mermaid
graph TD

    A[Azure Spot VM]
    B[Eviction Listener]
    C[RabbitMQ]
    D[Recovery Worker]
    E[Azure API]

    A --> B
    B --> C
    C --> D
    D --> E
```

---

# Components

## 1. Eviction Listener

- Listen to Azure Scheduled Events endpoint (json)
- Detect eviction notifications
- Publish events into RabbitMQ

Example eviction event:

```json
{
  "EventId":"258F9A75-A5C9-41BD-B952-3EF1E36C7467",
  "EventStatus":"Scheduled",
  "EventType":"Preempt",
  "ResourceType":"VirtualMachine",
  "Resources":["eviction-test"],
  "NotBefore":"Mon, 23 May 2026 01:18:39 GMT",
  "Description":"",
  "EventSource":"Platform",
  "DurationInSeconds":-1
}
```

## 2. Recovery Worker

- Consume eviction events
- Execute contingency logic
- Start restart countdown
- Attempt VM restart

Potential actions:
- Remove VM from Azure Traffic Manager
- Disable monitoring alerts
- Drain active traffic

---

# Event Flow

```mermaid
sequenceDiagram

    participant Azure
    participant Listener
    participant RabbitMQ
    participant Worker

    Azure->>Listener: Eviction Warning
    Listener->>RabbitMQ: Publish Event
    RabbitMQ->>Worker: Consume Event

    Worker->>Worker: Disable Monitoring
    Worker->>Worker: Remove From Traffic
    Worker->>Worker: Wait Countdown

    Worker->>Azure: Attempt Restart
```

---

# Deployment Architecture

```mermaid
graph LR

    subgraph Docker Environment

        A[Listener Container]
        B[RabbitMQ Container]
        C[Worker Container]

    end

    A --> B
    B --> C
```

---

# Docker Deployment

The system is deployed using Docker Compose.

Services:
- rabbitmq
- listener
- worker

---

# Error Handling

## RabbitMQ Unavailable

The listener retries connection attempts periodically.

## Failed Recovery

Restart attempts may be retried with exponential backoff.

---

# Assumptions

- Spot VM eviction warnings arrive before termination.

---
