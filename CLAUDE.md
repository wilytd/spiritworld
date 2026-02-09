# CLAUDE.md

Context and conventions for AI assistants working with the Aegis Mesh codebase.

## Project Overview

**Aegis Mesh** is a unified, self-hosted management layer for hybrid home labs. It integrates:
- Network infrastructure monitoring (OPNsense, Unifi, Pi-hole, AdGuard Home)
- LoRa mesh communications via Meshtastic/NomadNet for resilient out-of-band messaging
- Maintenance task scheduling with multi-channel notifications (email, webhooks, mesh)
- AI-powered task analysis via multi-provider LLM integration
- An extensible plugin system for custom integrations

Development phases 1-5 are complete. The project has a working microservices architecture with four services, a PostgreSQL database, and optional local LLM support.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+ / FastAPI 0.109 |
| Database | PostgreSQL 15 via SQLAlchemy 2.0 (async) + AsyncPG |
| Frontend | Next.js 14.1 / React 18.2 / TypeScript 5.3 |
| Scheduling | APScheduler 3.10 with croniter |
| Deployment | Docker / Docker Compose |
| Mesh | Meshtastic 2.2 (serial LoRa interface) |
| LLM | Ollama (local), OpenAI, Anthropic (multi-provider fallback) |

## Directory Structure

```
spiritworld/
├── apps/
│   ├── core/                        # Central API & orchestration (port 8000)
│   │   ├── main.py                  # FastAPI app, lifespan management
│   │   ├── database.py              # SQLAlchemy async engine & session factory
│   │   ├── models.py                # ORM models (MaintenanceTask, AlertLog, etc.)
│   │   ├── schemas.py               # Pydantic request/response schemas
│   │   ├── config.py                # Dataclass-based configuration
│   │   ├── scheduler.py             # APScheduler background jobs
│   │   ├── notifications.py         # Multi-channel notification dispatch
│   │   ├── routers/
│   │   │   ├── tasks.py             # Task CRUD (/api/tasks)
│   │   │   ├── alerts.py            # Alert routing (/api/alerts)
│   │   │   ├── status.py            # System status (/api/status)
│   │   │   ├── notifications.py     # Notification preferences (/api/notifications)
│   │   │   └── plugins.py           # Plugin management (/api/plugins)
│   │   ├── plugins/
│   │   │   ├── base.py              # Abstract PluginBase class
│   │   │   ├── manager.py           # Plugin lifecycle management
│   │   │   ├── registry.py          # Plugin registry
│   │   │   ├── discovery.py         # Auto-discovery from plugins_dir
│   │   │   └── example_plugin.py.template
│   │   ├── llm/
│   │   │   ├── service.py           # LLM orchestrator with provider fallback
│   │   │   ├── base.py              # Abstract LLM provider base
│   │   │   ├── router.py            # LLM endpoints (/api/llm)
│   │   │   ├── config.py            # LLM configuration
│   │   │   ├── prompts.py           # Prompt templates
│   │   │   └── providers/
│   │   │       ├── ollama.py        # Local Ollama provider
│   │   │       ├── openai.py        # OpenAI API provider
│   │   │       └── anthropic.py     # Anthropic API provider
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   │
│   ├── mesh-bridge/                 # Meshtastic gateway (port 8001)
│   │   ├── main.py                  # FastAPI mesh bridge service
│   │   ├── meshtastic_bridge.py     # Serial interface to Meshtastic radio
│   │   ├── nomadnet_bridge.py       # NomadNet/LXMF support
│   │   ├── service.py               # Mesh service logic
│   │   ├── message_queue.py         # Message queue with retry
│   │   ├── alerts.py                # Alert formatting for mesh
│   │   ├── models.py                # Mesh data models
│   │   ├── config.py                # Mesh configuration
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   │
│   ├── network-controller/          # Network integrations (port 8002)
│   │   ├── main.py                  # FastAPI network controller
│   │   ├── config.py                # Integration configuration
│   │   ├── models.py                # Health & connection state models
│   │   ├── schemas.py               # API schemas
│   │   ├── clients/
│   │   │   ├── base.py              # Abstract base client
│   │   │   ├── opnsense.py          # OPNsense firewall API client
│   │   │   ├── unifi.py             # Unifi controller API client
│   │   │   ├── pihole.py            # Pi-hole DNS API client
│   │   │   └── adguard.py           # AdGuard Home API client
│   │   ├── routers/
│   │   │   ├── traffic.py           # Bandwidth/traffic endpoints
│   │   │   ├── dns.py               # DNS management endpoints
│   │   │   └── vpn.py               # WireGuard/VPN endpoints
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   │
│   └── maintenance-ui/              # Next.js dashboard (port 3000)
│       ├── src/
│       │   ├── app/
│       │   │   ├── page.tsx          # Dashboard home (task list, status)
│       │   │   ├── layout.tsx        # Root layout
│       │   │   └── settings/
│       │   │       └── page.tsx      # Notification preferences UI
│       │   └── components/
│       │       ├── TaskForm.tsx      # Task creation/edit modal
│       │       └── SnoozeDialog.tsx  # Snooze dialog modal
│       ├── package.json
│       ├── tsconfig.json
│       ├── next.config.js
│       └── Dockerfile
│
├── deploy/
│   ├── docker-compose.yml           # Full service orchestration
│   └── .env.example                 # Environment variable template
│
├── docs/
│   ├── ARCHITECTURE.md              # System architecture & data flow
│   ├── API.md                       # API endpoint reference
│   └── SETUP.md                     # Deployment guide
│
├── bridge.py                        # Legacy standalone Meshtastic bridge
├── docker-compose.yml               # Legacy compose file
├── maintenance_task_sched.json      # Sample task definitions
├── README.md                        # Product requirements document
├── TASKS.md                         # Development phase tracking
└── CLAUDE.md                        # This file
```

## Build & Run Commands

```bash
# Full stack (from deploy/ directory)
cd deploy
cp .env.example .env                  # Configure environment
docker compose up -d                  # Start all services

# With optional local LLM
docker compose --profile llm up -d

# Individual service development
cd apps/core && pip install -r requirements.txt && uvicorn main:app --reload --port 8000
cd apps/mesh-bridge && pip install -r requirements.txt && uvicorn main:app --reload --port 8001
cd apps/network-controller && pip install -r requirements.txt && uvicorn main:app --reload --port 8002
cd apps/maintenance-ui && npm install && npm run dev

# Frontend commands
cd apps/maintenance-ui
npm run dev                           # Development server
npm run build                         # Production build
npm run lint                          # Lint check

# Test API endpoints
curl http://localhost:8000/api/status
curl http://localhost:8000/api/tasks
curl http://localhost:8001/api/status
curl http://localhost:8002/api/health
```

## Services & Ports

| Service | Container | Port | Description |
|---------|-----------|------|-------------|
| aegis-core | aegis-core | 8000 | Central API, task management, scheduler, notifications |
| mesh-bridge | aegis-mesh-bridge | 8001 | Meshtastic/NomadNet LoRa gateway |
| network-controller | aegis-network-controller | 8002 | OPNsense, Unifi, Pi-hole, AdGuard integration |
| dashboard | aegis-dashboard | 3000 | Next.js web UI |
| db | aegis-db | 5432 | PostgreSQL 15 (internal) |
| ollama | aegis-ollama | 11434 | Local LLM (optional, `--profile llm`) |

## Key API Endpoints

### Core Service (`:8000`)
- `GET/POST /api/tasks` - List/create tasks
- `GET/PATCH/DELETE /api/tasks/{id}` - Get/update/delete task
- `POST /api/tasks/{id}/complete` - Mark task complete
- `POST /api/tasks/{id}/snooze` - Snooze task
- `POST /api/tasks/recurring` - Create recurring task
- `POST /api/alerts/send` - Send alert via mesh/webhook
- `GET /api/alerts/history` - Alert history
- `GET/POST /api/notifications/preferences` - Notification preferences
- `POST /api/notifications/test/{id}` - Test notification channel
- `GET /api/plugins` - List plugins
- `POST /api/plugins/{name}/enable|disable` - Toggle plugin
- `GET /api/llm/status` - LLM provider status
- `POST /api/llm/analyze/task` - AI task analysis
- `GET /api/status` - System status

### Mesh Bridge (`:8001`)
- `GET /api/status` - Bridge status
- `POST /api/send` - Send mesh message
- `GET /api/messages` - Recent messages
- `GET /api/nodes` - Mesh node list

### Network Controller (`:8002`)
- `GET /api/traffic/bandwidth` - Bandwidth stats
- `GET /api/dns/stats` - DNS query statistics
- `GET /api/vpn/peers` - WireGuard peer status

## Database Models

All models are in `apps/core/models.py` using SQLAlchemy 2.0 async ORM:

- **MaintenanceTask** - Tasks with priority (low/medium/high/critical), status (pending/in_progress/completed/snoozed), recurrence rules (cron expressions), due dates, snooze support, and mesh notification flag
- **AlertLog** - Alert history with channel, success status, and error tracking
- **NotificationPreference** - Per-channel notification settings with priority filters, category filters, and quiet hours
- **LLMAnalysisLog** - Records of LLM analysis runs per task
- **PluginState** - Plugin enable/disable state, configuration, and error tracking

## Environment Variables

Copy `deploy/.env.example` to `deploy/.env`. Key groups:

- **Database**: `DATABASE_URL` (auto-configured in Docker Compose)
- **SMTP**: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_ADDRESS`
- **Webhooks**: `WEBHOOK_URL`, `SLACK_WEBHOOK_URL`, `DISCORD_WEBHOOK_URL`
- **Scheduler**: `SCHEDULER_DUE_WARNING_HOURS` (default: 24), `SCHEDULER_OVERDUE_CHECK_INTERVAL`, `SCHEDULER_SNOOZE_CHECK_INTERVAL`
- **Network**: `OPNSENSE_URL/KEY/SECRET`, `UNIFI_URL/USER/PASS`, `PIHOLE_URL/TOKEN`, `ADGUARD_URL/USER/PASS`
- **Mesh**: `MESH_DEVICE_PATH` (default: `/dev/ttyUSB0`)
- **LLM**: `LLM_ENABLED`, `LLM_PROVIDER_PRIORITY` (default: `ollama,openai,anthropic`), provider-specific keys/URLs
- **Plugins**: `PLUGINS_ENABLED`, `PLUGINS_DIR`, `PLUGINS_AUTO_DISCOVER`

## Code Patterns & Conventions

### Architecture
- **Microservices**: Each service is independently deployable with its own Dockerfile
- **Graceful degradation**: Services handle missing hardware/dependencies without crashing (e.g., mesh bridge operates in fallback mode without a radio, network controller returns empty results when integrations are unconfigured)
- **Provider fallback**: Network controller falls back between providers (OPNsense -> Unifi for traffic, Pi-hole -> AdGuard for DNS). LLM service tries providers in priority order with 60s availability cache
- **Async throughout**: Python services use `async/await` with AsyncPG for non-blocking database operations

### Backend
- **Router organization**: Endpoints grouped by feature in `routers/` directories
- **FastAPI Depends()**: Dependency injection for database sessions and shared services
- **Dataclass config**: Configuration loaded from environment into dataclasses (not Pydantic Settings)
- **Pydantic v2 schemas**: Request/response validation in `schemas.py`
- **SQLAlchemy 2.0 style**: Async session with `select()` statements, not legacy Query API

### Frontend
- **`'use client'` components**: Next.js client-side rendering for interactive UI
- **React Hook Form**: Form state management
- **Inline styles**: Dynamic style objects, not external CSS files (aside from Tailwind)
- **30-second auto-refresh**: Dashboard polls API on interval

### Plugin System
Plugins implement `PluginBase` and provide: metadata (`PluginInfo`), optional FastAPI routers (mounted at `/api/plugins/{name}/`), scheduled jobs, and event hooks (task.created, task.completed, etc.). See `apps/core/plugins/example_plugin.py.template`.

### Scheduler Jobs
Three APScheduler background jobs run in aegis-core:
1. **Snooze checker** (every 5 min) - Reactivates snoozed tasks past their snooze_until time
2. **Due notification checker** (hourly) - Sends notifications for tasks due within the warning window
3. **Recurring task generator** (daily at midnight) - Creates new task instances from cron-based recurrence rules

## Development Notes

- The Meshtastic bridge expects hardware at `/dev/ttyUSB0` but operates in fallback mode when unavailable
- Ollama service uses a Docker Compose profile (`--profile llm`) and only starts when explicitly requested
- The legacy `bridge.py` and root `docker-compose.yml` are from early development; use `deploy/docker-compose.yml` for the current stack
- No test suite or CI/CD pipeline exists yet (planned for a future phase)
- The database auto-creates tables on startup via SQLAlchemy `create_all`
- Swagger UI is available at `http://localhost:8000/docs` when aegis-core is running
