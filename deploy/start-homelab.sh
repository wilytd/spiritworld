#!/usr/bin/env bash
# ============================================================
# Aegis Mesh — Home Server Launcher
# ============================================================
# Usage:
#   ./start-homelab.sh              # core services only
#   ./start-homelab.sh --mesh       # + Meshtastic radio
#   ./start-homelab.sh --llm        # + local Ollama LLM
#   ./start-homelab.sh --mesh --llm # everything
#   ./start-homelab.sh --down       # stop all services
#   ./start-homelab.sh --logs       # tail logs
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.homelab.yml"
ENV_FILE="$SCRIPT_DIR/.env"
ENV_TEMPLATE="$SCRIPT_DIR/.env.homelab"

# ── Ensure .env exists ──────────────────────────────────────
if [ ! -f "$ENV_FILE" ]; then
    if [ -f "$ENV_TEMPLATE" ]; then
        echo "No .env found. Copying from .env.homelab template..."
        cp "$ENV_TEMPLATE" "$ENV_FILE"

        # Auto-detect LAN IP and substitute into .env
        LAN_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "")
        if [ -n "$LAN_IP" ]; then
            sed -i "s/^HOMELAB_IP=.*/HOMELAB_IP=$LAN_IP/" "$ENV_FILE"
            echo "Detected LAN IP: $LAN_IP"
        fi

        echo ""
        echo "IMPORTANT: Review $ENV_FILE before first run."
        echo "  - Set POSTGRES_PASSWORD to something unique"
        echo "  - Verify HOMELAB_IP matches your server"
        echo "  - Add network integration credentials if you have them"
        echo ""
        echo "Then re-run this script."
        exit 0
    else
        echo "Error: No .env or .env.homelab found in $SCRIPT_DIR"
        exit 1
    fi
fi

# ── Parse arguments ─────────────────────────────────────────
PROFILES=""
ACTION="up"

for arg in "$@"; do
    case $arg in
        --mesh)
            PROFILES="$PROFILES --profile mesh"
            ;;
        --llm)
            PROFILES="$PROFILES --profile llm"
            ;;
        --down)
            ACTION="down"
            ;;
        --logs)
            ACTION="logs"
            ;;
        --status)
            ACTION="status"
            ;;
        --rebuild)
            ACTION="rebuild"
            ;;
        -h|--help)
            echo "Usage: $0 [--mesh] [--llm] [--down] [--logs] [--status] [--rebuild]"
            echo ""
            echo "  --mesh      Include Meshtastic bridge (needs radio at $MESH_DEVICE_PATH)"
            echo "  --llm       Include local Ollama LLM service"
            echo "  --down      Stop all services"
            echo "  --logs      Tail service logs"
            echo "  --status    Show service status"
            echo "  --rebuild   Rebuild images and restart"
            exit 0
            ;;
        *)
            echo "Unknown option: $arg (try --help)"
            exit 1
            ;;
    esac
done

COMPOSE_CMD="docker compose -f $COMPOSE_FILE $PROFILES"

# ── Execute ─────────────────────────────────────────────────
case $ACTION in
    up)
        echo "Starting Aegis Mesh..."
        $COMPOSE_CMD up -d --build
        echo ""
        echo "Services starting. Check status with: $0 --status"

        # Source .env to read HOMELAB_IP and ports
        set -a; source "$ENV_FILE"; set +a
        IP="${HOMELAB_IP:-localhost}"
        echo ""
        echo "  Dashboard:  http://$IP:${DASHBOARD_PORT:-3000}"
        echo "  Core API:   http://$IP:${CORE_PORT:-8000}"
        echo "  Swagger UI: http://$IP:${CORE_PORT:-8000}/docs"
        echo "  Network:    http://$IP:${NETWORK_PORT:-8002}"
        ;;
    down)
        echo "Stopping Aegis Mesh..."
        # Include all profiles so everything stops
        docker compose -f "$COMPOSE_FILE" --profile mesh --profile llm down
        ;;
    logs)
        $COMPOSE_CMD logs -f --tail=50
        ;;
    status)
        $COMPOSE_CMD ps
        ;;
    rebuild)
        echo "Rebuilding and restarting Aegis Mesh..."
        $COMPOSE_CMD up -d --build --force-recreate
        ;;
esac
