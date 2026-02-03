# CLAUDE.md

This file provides context for AI assistants working with this codebase.

## Project Overview

**Aegis Mesh** is a unified, self-hosted management layer for hybrid home labs that integrates:
- Standard networking infrastructure (OPNsense, Unifi, Pi-hole, AdGuard Home)
- Meshtastic/NomadNet communications for resilient LoRa mesh networking
- Automated infrastructure maintenance task scheduling and notifications

This is an early-stage project in the planning and initial implementation phase.

## Tech Stack

- **Backend**: Python with FastAPI
- **Database**: PostgreSQL 15
- **Frontend**: Node.js (planned: React/Next.js)
- **Deployment**: Docker, Docker Compose
- **Mesh**: Meshtastic library for LoRa communication

## Directory Structure

Current structure:
```
/spiritworld
├── bridge.py                      # Meshtastic bridge service (FastAPI)
├── docker-compose.yml             # Container orchestration
├── maintenance_task_sched.json    # Sample maintenance task definitions
├── README.md                      # Product Requirements Document
└── TASKS.md                       # Task tracking
```

Planned structure from PRD:
```
/apps/core                # Python FastAPI orchestrator
/apps/network-controller  # OPNsense/Unifi integration
/apps/mesh-bridge         # Meshtastic/NomadNet connectors
/apps/dashboard           # React/Next.js frontend
/deploy                   # Docker Compose and Helm charts
/docs                     # Documentation
```

## Build & Run Commands

```bash
# Start all services with Docker Compose
docker-compose up -d

# Run bridge service directly (for development)
pip install meshtastic fastapi uvicorn
python bridge.py

# Test endpoints
curl http://localhost:8000/status
curl -X POST http://localhost:8000/alert/mesh -d '{"message": "Test"}' -H "Content-Type: application/json"
```

## Key Services & Ports

| Service   | Port | Description                    |
|-----------|------|--------------------------------|
| aegis-core| 8000 | Main FastAPI backend           |
| dashboard | 3000 | Frontend UI                    |
| db        | 5432 | PostgreSQL (internal)          |

## Environment Variables

- `DATABASE_URL`: PostgreSQL connection string
- `MESH_DEVICE_PATH`: Serial path to Meshtastic device (default: `/dev/ttyUSB0`)

## Code Patterns

- **Microservices Architecture**: Modular services for resilience
- **Graceful Degradation**: Services handle missing hardware gracefully
- **API-First Design**: RESTful endpoints with FastAPI
- **Configuration via Environment**: Docker Compose env vars for deployment

## Key Files

- `bridge.py`: Meshtastic bridge with `/status` and `/alert/mesh` endpoints
- `docker-compose.yml`: Defines aegis-core, db, and dashboard services
- `maintenance_task_sched.json`: Task schema with priority, category, and mesh notification flags

## Development Notes

- The Meshtastic bridge expects hardware at `/dev/ttyUSB0` but operates in fallback mode if unavailable
- Database stores maintenance tasks and network state
- All services are containerized for reproducibility
