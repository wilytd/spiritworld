# Aegis Mesh Architecture

## Overview

Aegis Mesh follows a microservices architecture to ensure modularity, resilience, and easy extensibility.

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Interface                           │
│                    (maintenance-ui:3000)                        │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Aegis Core API                             │
│                     (aegis-core:8000)                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │  Tasks   │  │  Alerts  │  │  Status  │  │ Scheduler │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
└───────┬────────────────┬────────────────────────────────────────┘
        │                │
        ▼                ▼
┌───────────────┐  ┌────────────────┐  ┌─────────────────────────┐
│   PostgreSQL  │  │  Mesh Bridge   │  │   Network Controller    │
│    (db:5432)  │  │ (mesh:8001)    │  │   (network:8002)        │
└───────────────┘  └───────┬────────┘  └──────────┬──────────────┘
                           │                       │
                           ▼                       ▼
                   ┌───────────────┐       ┌─────────────────┐
                   │  Meshtastic   │       │  OPNsense/Unifi │
                   │  LoRa Device  │       │  Pi-hole/WG     │
                   └───────────────┘       └─────────────────┘
```

## Services

### Aegis Core (`apps/core`)

The central orchestration service that:
- Manages maintenance tasks (CRUD operations)
- Coordinates cross-service communication
- Sends alerts through multiple channels
- Provides unified API for the dashboard

**Tech Stack:** Python, FastAPI, SQLAlchemy, PostgreSQL

### Mesh Bridge (`apps/mesh-bridge`)

Gateway between the home lab and Meshtastic LoRa network:
- Receives messages from mesh devices
- Sends alerts to handheld radios
- Maintains message buffer for review
- Provides node discovery

**Tech Stack:** Python, FastAPI, Meshtastic SDK

### Network Controller (`apps/network-controller`)

Integration layer for network infrastructure:
- OPNsense/Unifi bandwidth monitoring
- Pi-hole/AdGuard DNS management
- WireGuard VPN peer management
- VLAN configuration

**Tech Stack:** Python, FastAPI, various API clients

### Maintenance UI (`apps/maintenance-ui`)

Web dashboard for:
- Viewing and managing maintenance tasks
- Monitoring system status
- Sending test alerts
- Viewing mesh messages

**Tech Stack:** React, Next.js, TypeScript

## Data Flow

### Alert Flow

1. Task becomes overdue or user triggers alert
2. Core service receives alert request
3. Based on `mesh_notify` flag, routes to Mesh Bridge
4. Mesh Bridge sends via LoRa to handheld devices
5. Alert logged in database

### Task Lifecycle

```
PENDING → IN_PROGRESS → COMPLETED
    ↓
  SNOOZED → PENDING (after snooze period)
```

## Extensibility

New integrations can be added by:
1. Creating a new service in `apps/`
2. Adding to `docker-compose.yml`
3. Registering endpoints in Core service for unified access
