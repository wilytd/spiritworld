# Aegis Mesh API Documentation

## Core Service (Port 8000)

Base URL: `http://localhost:8000`

### Health & Status

#### GET /health
Returns service health status.

#### GET /api/status/
Returns overall system status including database and mesh bridge connectivity.

**Response:**
```json
{
  "service": "Aegis Mesh Core",
  "version": "0.1.0",
  "database": "connected",
  "mesh_bridge": "connected",
  "uptime_seconds": 3600.5
}
```

### Maintenance Tasks

#### GET /api/tasks/
List all maintenance tasks.

**Query Parameters:**
- `status` (optional): Filter by status (pending, in_progress, completed, snoozed)
- `category` (optional): Filter by category

#### POST /api/tasks/
Create a new maintenance task.

**Request Body:**
```json
{
  "title": "UPS Battery Test",
  "description": "Run self-test on APC UPS",
  "category": "Hardware",
  "priority": "high",
  "due_date": "2026-03-15T00:00:00Z",
  "mesh_notify": true
}
```

#### GET /api/tasks/{task_id}
Get a specific task by ID.

#### PATCH /api/tasks/{task_id}
Update a task.

#### DELETE /api/tasks/{task_id}
Delete a task.

#### POST /api/tasks/{task_id}/complete
Mark a task as completed.

#### POST /api/tasks/{task_id}/snooze
Snooze a task.

### Alerts

#### POST /api/alerts/send
Send an alert through specified channel.

**Request Body:**
```json
{
  "message": "Server CPU temperature critical",
  "channel": "mesh"
}
```

**Channels:** `mesh`, `webhook`

#### GET /api/alerts/history
Get recent alert history.

---

## Mesh Bridge Service (Port 8001)

Base URL: `http://localhost:8001`

#### GET /status
Get mesh bridge status and connected node info.

#### POST /send
Send a message to the mesh network.

**Request Body:**
```json
{
  "message": "Test alert from home lab",
  "destination": null
}
```

#### GET /messages
Get recently received mesh messages.

#### GET /nodes
Get list of known mesh nodes.

---

## Network Controller Service (Port 8002)

Base URL: `http://localhost:8002`

> Note: Most endpoints return 501 (Not Implemented) in Phase 1.

#### GET /traffic/bandwidth
Get bandwidth usage by interface.

#### GET /dns/stats
Get Pi-hole/AdGuard statistics.

#### GET /vpn/peers
Get WireGuard peer status.
