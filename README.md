# Aegis Mesh

A unified, self-hosted management layer for hybrid home labs that integrates network infrastructure monitoring, Meshtastic/NomadNet mesh communications, and automated maintenance task scheduling.

## Architecture

Aegis Mesh is built as a microservices architecture with five main components:

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Dashboard     │────▶│   Aegis Core     │────▶│   PostgreSQL    │
│   (Next.js)     │     │   (FastAPI)      │     │                 │
│   :3000         │     │   :8000          │     │   :5432         │
└─────────────────┘     └────────┬─────────┘     └─────────────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
           ┌──────────────┐ ┌──────────┐ ┌──────────┐
           │Network Ctrl  │ │Mesh Bridge│ │ Ollama   │
           │(FastAPI)     │ │(FastAPI)  │ │ (LLM)    │
           │:8002         │ │:8001      │ │ :11434   │
           └──────────────┘ └──────────┘ └──────────┘
```

## Services

### Aegis Core (`apps/core`) - Port 8000
The central orchestrator providing:
- **Task Management**: CRUD operations for maintenance tasks with priority levels, categories, and due dates
- **Scheduler**: Background jobs for due date notifications, snooze handling, and recurring task generation
- **Notifications**: Multi-channel alerts via email (SMTP), webhooks (Slack/Discord), and mesh bridge
- **Plugin System**: Extensible architecture with lifecycle management and event hooks
- **LLM Integration**: Multi-provider support (Ollama, OpenAI, Anthropic) for task analysis

### Network Controller (`apps/network-controller`) - Port 8002
Integrates with home network infrastructure:
- **OPNsense**: Firewall rules, traffic statistics, interface monitoring
- **Unifi**: Controller API for device management and statistics
- **Pi-hole**: DNS blocking statistics and query logs
- **AdGuard Home**: Filtering statistics and DNS management

### Mesh Bridge (`apps/mesh-bridge`) - Port 8001
LoRa mesh network integration:
- **Meshtastic**: Send/receive messages via LoRa radio, node discovery
- **NomadNet**: LXMF message routing and page serving
- **Message Queue**: Persistent queue with retry logic for mesh delivery
- **Alert Routing**: Route critical alerts over mesh when primary network is down

### Dashboard (`apps/maintenance-ui`) - Port 3000
Next.js frontend providing:
- Task list with filtering by status and category
- Task creation/editing forms
- Snooze dialog with preset durations
- Notification preferences configuration

## Quick Start

### Prerequisites
- Docker and Docker Compose
- (Optional) Meshtastic device at `/dev/ttyUSB0`

### Running

```bash
cd deploy

# Copy and configure environment
cp .env.example .env
# Edit .env with your settings

# Start core services
docker compose up -d

# Include local LLM (Ollama)
docker compose --profile llm up -d
```

### Accessing Services
- Dashboard: http://localhost:3000
- Core API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Network Controller: http://localhost:8002
- Mesh Bridge: http://localhost:8001

## API Endpoints

### Tasks (`/api/tasks`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | List tasks (filterable by status, category) |
| POST | `/` | Create task |
| GET | `/{id}` | Get task by ID |
| PATCH | `/{id}` | Update task |
| DELETE | `/{id}` | Delete task |
| POST | `/{id}/snooze` | Snooze task |
| POST | `/{id}/complete` | Mark task complete |
| POST | `/recurring` | Create recurring task (cron-based) |

### Notifications (`/api/notifications`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/preferences` | List notification preferences |
| POST | `/preferences` | Create preference |
| PATCH | `/preferences/{id}` | Update preference |
| POST | `/test/{id}` | Send test notification |

### LLM (`/api/llm`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/status` | Provider status and availability |
| POST | `/providers/check` | Refresh provider availability |
| POST | `/analyze/task` | Analyze single task |
| POST | `/analyze/batch` | Batch analyze pending tasks |
| POST | `/complete` | Raw LLM completion |

### Plugins (`/api/plugins`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | List discovered/loaded plugins |
| GET | `/{name}` | Get plugin details |
| POST | `/{name}/enable` | Enable plugin |
| POST | `/{name}/disable` | Disable plugin |

### Alerts (`/api/alerts`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/send` | Send alert via mesh/webhook |
| GET | `/history` | List recent alerts |

## Configuration

Configuration is done via environment variables. See `deploy/.env.example` for all options.

### Key Variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://aegis:password@db:5432/aegis

# Notifications
SMTP_HOST=smtp.example.com
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...

# Network Integrations
OPNSENSE_URL=https://192.168.1.1
OPNSENSE_KEY=your_api_key
OPNSENSE_SECRET=your_api_secret

UNIFI_URL=https://192.168.1.1:8443
UNIFI_USER=admin
UNIFI_PASS=password

PIHOLE_URL=http://192.168.1.10
PIHOLE_TOKEN=your_token

# LLM Providers (in priority order)
LLM_PROVIDER_PRIORITY=ollama,openai,anthropic
OLLAMA_URL=http://ollama:11434
OLLAMA_MODEL=llama3.2
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Meshtastic
MESH_DEVICE_PATH=/dev/ttyUSB0
```

## Plugin Development

Plugins extend Aegis Mesh functionality. Create a Python file in `apps/core/plugins/`:

```python
from plugins.base import PluginBase, PluginInfo, PluginContext

class Plugin(PluginBase):
    @property
    def info(self) -> PluginInfo:
        return PluginInfo(
            name="my-plugin",
            version="1.0.0",
            description="My custom plugin"
        )

    @property
    def is_configured(self) -> bool:
        return True

    async def initialize(self, context: PluginContext) -> bool:
        self._context = context
        return True

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass
```

Plugins can provide:
- FastAPI routers (mounted at `/api/plugins/{name}/`)
- Scheduled jobs (APScheduler)
- Event hooks (subscribe to task.created, task.completed, etc.)

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy 2.0, APScheduler
- **Frontend**: Next.js 14, React, TypeScript, Tailwind CSS
- **Database**: PostgreSQL 15
- **LLM**: Ollama (local), OpenAI, Anthropic
- **Mesh**: Meshtastic Python library, LXMF
- **Deployment**: Docker, Docker Compose

## License

MIT
