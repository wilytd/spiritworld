# Aegis Mesh - Project Tasks

## Overview
This document tracks all implementation tasks for Project "Aegis Mesh" - a unified, self-hosted management layer for a hybrid home lab.

---

## Phase 1: Project Foundation & Structure

### 1.1 Repository Setup
- [ ] Create directory structure per PRD (`/apps`, `/deploy`, `/docs`)
- [ ] Initialize `apps/network-controller/` module
- [ ] Initialize `apps/mesh-bridge/` module
- [ ] Initialize `apps/maintenance-ui/` module
- [ ] Create `deploy/k8s/` directory for Helm charts
- [ ] Add `.gitignore` for Python, Node.js, and environment files
- [ ] Create `requirements.txt` for Python dependencies
- [ ] Create `package.json` for frontend dependencies

### 1.2 Development Environment
- [ ] Set up Python virtual environment configuration
- [ ] Configure ESLint/Prettier for frontend code
- [ ] Create `.env.example` with required environment variables
- [ ] Add Docker development overrides (`docker-compose.override.yml`)

---

## Phase 2: Core API & Database

### 2.1 Database Schema
- [ ] Design PostgreSQL schema for maintenance tasks
- [ ] Design schema for network device inventory
- [ ] Design schema for alert history and logs
- [ ] Create Alembic migrations setup
- [ ] Write initial migration scripts

### 2.2 FastAPI Core Service
- [ ] Refactor `bridge.py` into proper module structure (`apps/core/`)
- [ ] Implement SQLAlchemy models for all entities
- [ ] Create Pydantic schemas for API request/response
- [ ] Implement CRUD endpoints for maintenance tasks
- [ ] Add task scheduling logic (recurring tasks)
- [ ] Implement task snooze/complete functionality
- [ ] Add persistent logging for task history
- [ ] Create health check and metrics endpoints

### 2.3 Authentication & Security
- [ ] Implement API key authentication
- [ ] Add rate limiting middleware
- [ ] Configure CORS for dashboard access
- [ ] Add input validation and sanitization

---

## Phase 3: Network Controller Integration

### 3.1 OPNsense Integration
- [ ] Research OPNsense REST API endpoints
- [ ] Implement OPNsense API client class
- [ ] Add bandwidth monitoring endpoints
- [ ] Implement firewall rule management
- [ ] Add WireGuard VPN status/management

### 3.2 Unifi Integration
- [ ] Research Unifi Controller API
- [ ] Implement Unifi API client class
- [ ] Add device discovery and inventory
- [ ] Implement VLAN tagging automation
- [ ] Add client tracking and statistics

### 3.3 DNS/Ad-blocking Integration
- [ ] Implement Pi-hole API client
- [ ] Implement AdGuard Home API client
- [ ] Add centralized blocklist management
- [ ] Create DNS query statistics endpoint

---

## Phase 4: Meshtastic & NomadNet Integration

### 4.1 Meshtastic Bridge Enhancement
- [ ] Add proper error handling and reconnection logic
- [ ] Implement message queue for outbound alerts
- [ ] Add node discovery and tracking
- [ ] Create message routing based on node IDs
- [ ] Implement delivery confirmation tracking
- [ ] Add signal strength and battery monitoring

### 4.2 NomadNet Integration
- [ ] Research NomadNet/Reticulum protocol
- [ ] Implement NomadNet node service
- [ ] Add encrypted file sharing capabilities
- [ ] Create message relay between mesh and NomadNet
- [ ] Implement persistent message storage

### 4.3 Cross-Protocol Alerts
- [ ] Define alert priority levels and routing rules
- [ ] Implement ISP failover detection
- [ ] Create fallback alert path via Meshtastic
- [ ] Add alert acknowledgment system
- [ ] Implement alert escalation logic

---

## Phase 5: Maintenance Dashboard (Frontend)

### 5.1 Project Setup
- [ ] Initialize Next.js project in `apps/maintenance-ui/`
- [ ] Configure Tailwind CSS for styling
- [ ] Set up API client with fetch/axios
- [ ] Implement authentication flow
- [ ] Create responsive layout components

### 5.2 Task Management UI
- [ ] Build task list view with filtering
- [ ] Create task detail/edit modal
- [ ] Implement drag-and-drop task reordering
- [ ] Add task completion with confirmation
- [ ] Build snooze functionality with date picker
- [ ] Create recurring task configuration UI

### 5.3 Network Dashboard
- [ ] Build real-time bandwidth charts (Chart.js/Recharts)
- [ ] Create device inventory grid view
- [ ] Add network topology visualization
- [ ] Implement alert notification toasts
- [ ] Build VPN status indicators

### 5.4 Mesh Network View
- [ ] Create mesh node map/list view
- [ ] Build message send interface
- [ ] Add signal strength indicators
- [ ] Implement message history view
- [ ] Create node configuration panel

---

## Phase 6: Notification Engine

### 6.1 Webhook Notifications
- [ ] Implement generic webhook dispatcher
- [ ] Add Discord webhook integration
- [ ] Add Slack webhook integration
- [ ] Create custom webhook configuration UI

### 6.2 Email Notifications
- [ ] Implement SMTP email sender
- [ ] Create HTML email templates
- [ ] Add email digest scheduling
- [ ] Implement unsubscribe functionality

### 6.3 Meshtastic Notifications
- [ ] Route critical alerts to mesh bridge
- [ ] Implement priority-based message formatting
- [ ] Add notification preferences per task

---

## Phase 7: Deployment & DevOps

### 7.1 Docker Configuration
- [ ] Create production-ready Dockerfiles for each service
- [ ] Optimize image sizes with multi-stage builds
- [ ] Add health checks to all containers
- [ ] Configure proper logging drivers
- [ ] Update `docker-compose.yml` with production settings

### 7.2 Kubernetes Deployment
- [ ] Create Helm chart structure in `deploy/k8s/`
- [ ] Write deployment manifests for all services
- [ ] Configure ConfigMaps and Secrets
- [ ] Add Ingress configuration
- [ ] Create PersistentVolumeClaims for database
- [ ] Add horizontal pod autoscaling

### 7.3 CI/CD Pipeline
- [ ] Create GitHub Actions workflow for testing
- [ ] Add automated linting and type checking
- [ ] Implement container image building
- [ ] Add deployment automation scripts

---

## Phase 8: Documentation & Testing

### 8.1 Documentation
- [ ] Write API documentation (OpenAPI/Swagger)
- [ ] Create setup guide in `docs/SETUP.md`
- [ ] Write configuration reference
- [ ] Add troubleshooting guide
- [ ] Create architecture diagrams

### 8.2 Testing
- [ ] Set up pytest for backend testing
- [ ] Write unit tests for API endpoints
- [ ] Add integration tests for database operations
- [ ] Set up Jest for frontend testing
- [ ] Write component tests for dashboard
- [ ] Add E2E tests with Playwright/Cypress

---

## Phase 9: Future Roadmap (Post-MVP)

### 9.1 AI Integration
- [ ] Research local LLM options (Ollama, llama.cpp)
- [ ] Design log analysis pipeline
- [ ] Implement anomaly detection
- [ ] Create maintenance suggestion engine

### 9.2 Solar/Power Monitoring
- [ ] Research Victron VE.Direct protocol
- [ ] Implement solar charge controller integration
- [ ] Add battery state of charge monitoring
- [ ] Create power dashboard widgets

---

## Current Sprint Focus

**Priority Tasks for Initial MVP:**
1. Complete repository structure setup
2. Implement core FastAPI service with database
3. Build basic maintenance task CRUD
4. Create minimal dashboard for task management
5. Enhance Meshtastic bridge reliability

---

## Task Status Legend
- [ ] Not Started
- [x] Completed
- [~] In Progress
- [!] Blocked

---

*Last Updated: 2026-02-03*
