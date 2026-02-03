## Product Requirements Document (PRD): Project "Aegis Mesh"

### 1. Executive Summary

**Project Goal:** To create a unified, self-hosted management layer for a hybrid home lab that integrates standard networking, Meshtastic/NomadNet communications, and automated infrastructure maintenance.
**Target Outcome:** A GitHub-ready, containerized repository that allows users to deploy, monitor, and maintain a resilient local network.

---

### 2. Functional Requirements

#### **A. Enhanced Network Control**

* **Traffic Management:** Integration with existing gateways (e.g., OPNsense or Unifi) via API to monitor bandwidth.
* **DNS/Ad-blocking:** Centralized control for Pi-hole or AdGuard Home.
* **Security:** Automated VLAN tagging or WireGuard VPN management for remote access.

#### **B. Meshtastic & NomadNet Integration**

* **Gateway Bridge:** A service that pipes Meshtastic LoRa packets into the home lab environment.
* **NomadNet Node:** Hosting a Nomad Network node to allow for encrypted, resilient file sharing and messaging over the mesh.
* **Cross-Protocol Alerts:** The ability to send critical lab alerts (e.g., "Server Offline") over Meshtastic if the primary ISP goes down.

#### **C. Maintenance Task Interface**

* **Scheduler:** A dashboard showing recurring tasks (e.g., "Clear server dust," "Update Docker containers," "Test UPS batteries").
* **Status Tracking:** Ability to "snooze" or "complete" tasks with a persistent log.
* **Notification Engine:** Reminders pushed via Webhooks, Email, or the Meshtastic bridge.

---

### 3. Technical Architecture & Extensibility

To ensure this isn't a "monolith" that breaks when one part updates, we will use a **Microservices Architecture**.

* **Core:** Python (FastAPI) or Go-based orchestrator.
* **Database:** PostgreSQL or InfluxDB (for time-series network data).
* **Frontend:** React or Next.js dashboard with a mobile-responsive design.
* **Deployment:** Docker Compose or Kubernetes (K3s) manifests for easy "one-click" setup.

---

### 4. Proposed Repository Structure

```text
/aegis-mesh
├── /apps
│   ├── /network-controller  # Integration scripts for OPNsense/Unifi
│   ├── /mesh-bridge        # Meshtastic/NomadNet API connectors
│   └── /maintenance-ui     # The frontend dashboard
├── /deploy
│   ├── docker-compose.yml
│   └── /k8s                # Helm charts for extensibility
├── /docs                   # Setup guides and API documentation
└── README.md

```

---

### 5. Success Metrics

* **Interoperability:** Successful message delivery from the Home Lab to a Meshtastic handheld device.
* **Reliability:** Maintenance reminders persist through system reboots.
* **Latency:** Network control dashboard updates within <2 seconds of state change.

---

### 6. Future Extensibility (Roadmap)

* **AI Integration:** Local LLM to analyze network logs and suggest maintenance.
* **Solar Monitoring:** If the home lab runs on backup power, integrate Victron/Solar data into the dashboard.

---
