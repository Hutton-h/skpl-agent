# ADR-0002: Desktop Node & Control Center Separation

## Status

Accepted (2026-07)

## Context

SKPL Agent includes desktop automation capabilities (from Agent-S) that
require GUI access on a Windows machine. The core agent platform (from
AgentScope) runs on Linux servers. We need to decide how to architect the
relationship between the desktop automation component and the control center.

## Decision

We chose a **separated architecture** where the desktop automation node runs
as a standalone process on Windows machines and communicates with the control
center (Linux) via WebSocket.

```
┌──────────────────────┐                    ┌──────────────────────┐
│   Desktop Node       │                    │   Control Center     │
│   (Windows)          │◄─── WebSocket ────►│   (Linux)            │
│                      │    (TLS + JWT)     │                      │
│  - GUI automation    │                    │  - Agent runtime     │
│  - Screenshot/OCR    │                    │  - Context mgmt      │
│  - Local execution   │                    │  - Web scraping      │
│                      │                    │  - REST API          │
│                      │                    │  - Scheduling        │
└──────────────────────┘                    └──────────────────────┘
```

## Rationale

### Platform Constraints

Desktop automation requires a Windows GUI environment. The control center
runs on Linux servers. These are fundamentally different platforms that
cannot be colocated in a single process.

### Security Isolation

Running desktop automation separately provides security benefits:

1. **Compartmentalization**: A compromised desktop node cannot access the
   control center's database, LLM API keys, or other sensitive data.

2. **Least Privilege**: The desktop node only needs credentials to connect
   to the control center, not full database or API access.

3. **Network Segmentation**: The desktop node can be placed on a separate
   network segment from the control center.

### Scalability

The separated architecture enables:

1. **Independent Scaling**: Desktop nodes can be added or removed without
   affecting the control center.

2. **Multiple Nodes**: One control center can manage multiple desktop nodes
   (e.g., CI/CD machines, test environments).

3. **Geographic Distribution**: Desktop nodes can be in different physical
   locations while the control center remains centralized.

### Communication Protocol

We chose WebSocket over alternatives:

| Protocol | Pros | Cons |
|----------|------|------|
| **WebSocket** | Bidirectional, low latency, persistent connection | Requires connection management |
| REST polling | Simple, stateless | High latency, inefficient for real-time |
| gRPC | Strong typing, streaming | Requires protobuf, more complex setup |
| Message queue | Reliable, decoupled | Additional infrastructure, higher latency |

WebSocket is the best fit because:
- Desktop actions are interactive and require low latency
- The control center needs to push commands to the node
- The node needs to push heartbeats and results back
- JWT authentication integrates naturally with WebSocket

### Authentication

We use JWT (JSON Web Tokens) for authentication:

1. The control center and node share a secret (`SKPL_DESKTOP_JWT_SECRET`)
2. The node signs a token with the secret and sends it during WebSocket
   handshake
3. The control center validates the token before accepting the connection
4. Tokens have a configurable expiry (default: 1 hour)

### Alternatives Considered

#### Monolithic Architecture

Run everything in one process on a Windows server.

- **Pros**: Simpler deployment, no network communication
- **Cons**: Cannot run on Linux, no scalability, single point of failure,
  mixes concerns

#### REST-Based Polling

Desktop node polls the control center for pending actions.

- **Pros**: Simpler to implement, no persistent connections
- **Cons**: Higher latency, wasted bandwidth, harder to implement heartbeats

#### Message Queue (RabbitMQ/Kafka)

Use a message broker for communication.

- **Pros**: Reliable delivery, decoupled
- **Cons**: Additional infrastructure, higher operational complexity,
  overkill for the use case

## Consequences

### Positive

- **Platform Flexibility**: Control center runs on Linux, node runs on
  Windows — each on their optimal platform
- **Security**: Clear security boundary between control and execution
- **Scalability**: Independent scaling of nodes
- **Resilience**: Node disconnection does not affect the control center
- **Development Simplicity**: Each component can be developed and tested
  independently

### Negative

- **Deployment Complexity**: Two separate services to deploy and manage
- **Network Dependency**: Node requires stable network connection to
  control center
- **Connection Management**: WebSocket reconnection, heartbeat, and timeout
  logic must be implemented
- **Latency**: Network round-trip time for each action
- **Configuration**: Both sides must be configured with matching secrets

### Mitigations

1. **Automatic Reconnection**: The node implements exponential backoff for
   reconnection attempts

2. **Heartbeat**: Regular heartbeats detect disconnection within 30 seconds

3. **Offline Queue**: The control center can queue actions for offline nodes
   and execute them when the node reconnects

4. **Docker Support**: The node is available as a Docker image for easier
   deployment on Windows

5. **Health Check**: The control center exposes a health endpoint that
   includes node connectivity status

## References

- [WebSocket Protocol (RFC 6455)](https://datatracker.ietf.org/doc/html/rfc6455)
- [JWT Introduction](https://jwt.io/introduction)
- [Agent-S Architecture](https://github.com/simular-ai/Agent-S)
- [Desktop Node Deployment Guide](../desktop_node_guide.md)