# Aegis Mesh Setup Guide

## Prerequisites

- Docker and Docker Compose v2
- Git
- (Optional) Meshtastic-compatible LoRa device (e.g., T-Beam, Heltec)
- (Optional) Access to OPNsense/Unifi/Pi-hole APIs

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/aegis-mesh.git
cd aegis-mesh
```

### 2. Configure Environment

```bash
cd deploy
cp .env.example .env
# Edit .env with your configuration
```

### 3. Start Services

```bash
docker compose up -d
```

### 4. Access the Dashboard

Open your browser to `http://localhost:3000`

## Service Ports

| Service | Port | Description |
|---------|------|-------------|
| Dashboard | 3000 | Web UI |
| Core API | 8000 | Main orchestrator |
| Mesh Bridge | 8001 | Meshtastic gateway |
| Network Controller | 8002 | Network integrations |

## Connecting Meshtastic Hardware

1. Connect your Meshtastic device via USB
2. Identify the device path (usually `/dev/ttyUSB0` on Linux)
3. Update `MESH_DEVICE_PATH` in your `.env` file
4. Restart the mesh-bridge service:
   ```bash
   docker compose restart mesh-bridge
   ```

## Troubleshooting

### Mesh device not found

- Check device is connected: `ls /dev/ttyUSB*`
- Ensure user has access to serial devices
- Try unplugging and reconnecting the device

### Database connection errors

- Wait for postgres to be fully ready
- Check logs: `docker compose logs db`

### Dashboard not loading

- Ensure aegis-core is running: `docker compose logs aegis-core`
- Check CORS settings if accessing from different host
